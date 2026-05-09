#!/usr/bin/env python3
"""IMPACT ANALYSIS for the postprocess.process_unknown() scrape-and-assign
bug: when an ente has no MX, the website is scraped for any email; the
first email's domain is MX-looked-up; if it has MX, that MX is ASSIGNED
to the ente. If the website happens to mention a 3rd-party email (event
contact, referral, footer of a hosted municipality, etc.), the WRONG MX
is recorded on the ente.

This audits data.json for evidence: entities whose `m["mx"]` MX hosts do
not match the entity's `m["domain"]` (case-insensitive substring or
canonical Microsoft tenant naming). High-confidence false positives are
flagged.

Detection rules (heuristic):
  - Microsoft tenant pattern: <slug>-<tld>.mail.protection.outlook.com
    where <slug> = m["domain"].replace(".","-").rsplit("-",1)[0]
  - Generic: m["domain"] should appear (without dots) somewhere in MX
    hostname OR be the same registrable domain
  - Foreign generic providers (gmail.com, outlook.com, etc.) are
    ALSO suspicious for a PA entity but not bug-of-this-kind.

Output:
  data/reports/scraped_mx_bug_audit.json
  data/reports/scraped_mx_bug_audit.txt
"""
import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent

data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
muns = data["municipalities"]
seed = json.loads((ROOT / "data" / "municipalities_it.json").read_text(encoding="utf-8"))
seed_by_id = {e["id"]: e for e in seed}

# Generic mail-provider hostnames where a "mismatch" is expected
EXPECTED_THIRD_PARTY_HOSTS = (
    "outlook.com", "google.com", "googlemail.com", "aspmx.l.google.com",
    "amazonaws.com", "yandex", "zoho", "aruba", "register.it",
    "seeweb", "pec.it", "legalmail.it", "postecert.it", "messagenet",
    "fastmail.com", "telecomitalia", "tiscali",
)


def domain_root(d: str) -> str:
    """foo.bar.it -> bar.it; foo.bar.gov.it -> bar.gov.it (best-effort)."""
    if not d:
        return ""
    parts = d.lower().split(".")
    if len(parts) >= 2:
        # 2-letter region SLD: gov.it, regione.lombardia.it, etc.
        if parts[-2] in {"gov", "edu", "co", "ac", "or"} and parts[-1] in {"it", "uk", "in"}:
            if len(parts) >= 3:
                return ".".join(parts[-3:])
        return ".".join(parts[-2:])
    return d.lower()


def microsoft_tenant_slug(d: str) -> str:
    """interno.it -> interno-it ; comune.roma.it -> comune-roma-it."""
    return d.lower().replace(".", "-")


def mx_matches_domain(mx_host: str, domain: str) -> bool:
    if not mx_host or not domain:
        return False
    h = mx_host.lower().rstrip(".")
    d = domain.lower()
    droot = domain_root(d)
    # 1. Domain root appears in MX host
    if droot and droot in h:
        return True
    # 2. Microsoft tenant: <slug>.mail.protection.outlook.com
    slug = microsoft_tenant_slug(d).rstrip("-it").rstrip("-")
    if slug and slug in h:
        return True
    slug2 = microsoft_tenant_slug(droot).rstrip("-it").rstrip("-")
    if slug2 and slug2 in h:
        return True
    # 3. Tenant could include subdomain (e.g. comune.foo.it -> comune-foo-it)
    return False


def is_third_party_legitimate(mx_host: str) -> bool:
    h = mx_host.lower()
    return any(t in h for t in EXPECTED_THIRD_PARTY_HOSTS)


# Audit
suspicious = []
total_with_mx = 0
total_it = 0
mx_per_domain_count: dict = Counter()
for bid, m in muns.items():
    if not (m.get("country") == "IT"):
        continue
    total_it += 1
    mx = m.get("mx") or []
    if not mx:
        continue
    total_with_mx += 1
    domain = m.get("domain") or ""
    primary_mx = mx[0]
    domain_matches = mx_matches_domain(primary_mx, domain)
    if domain_matches:
        continue
    # Doesn't match — could be legitimate 3rd-party (Aruba, Google) or BUG
    is_3p = is_third_party_legitimate(primary_mx)
    # The bug pattern: Microsoft tenant for a DIFFERENT domain, e.g.
    #   domain: interno.gov.it  ->  mx: comune-roma-it.mail.protection.outlook.com
    is_ms_tenant = "mail.protection.outlook.com" in primary_mx
    if is_3p and not is_ms_tenant:
        # Aruba / Google for an Italian PA → legitimate
        continue
    if is_ms_tenant:
        # Strong suspect: tenant name should match the entity's domain
        # — extract tenant slug, look it up against domain root
        slug = primary_mx.split(".mail.protection.outlook.com")[0]
        # Reverse lookup: tenant slug → likely domain. e.g. "comune-roma-it" -> comune.roma.it
        tenant_dom = slug.replace("-", ".") + ""
        # Check if tenant_dom IS a different ente's domain
        for bid2, m2 in muns.items():
            if bid2 == bid:
                continue
            if (m2.get("domain") or "").lower() == tenant_dom:
                tenant_owner = m2.get("name", "?")
                break
        else:
            tenant_owner = "(unknown)"
        suspicious.append({
            "bfs": bid,
            "name": m.get("name", ""),
            "domain": domain,
            "mx": primary_mx,
            "tenant_slug": slug,
            "tenant_likely_owner": tenant_owner,
            "provider": m.get("provider"),
            "reason": (m.get("reason") or "")[:120],
        })
    else:
        # MX from a non-tenant 3rd-party that we don't expect: still suspect
        suspicious.append({
            "bfs": bid,
            "name": m.get("name", ""),
            "domain": domain,
            "mx": primary_mx,
            "tenant_slug": None,
            "tenant_likely_owner": None,
            "provider": m.get("provider"),
            "reason": (m.get("reason") or "")[:120],
            "category": "non_tenant_mismatch",
        })

print(f"Total IT enti: {total_it}")
print(f"  with MX:     {total_with_mx}")
print(f"  SUSPICIOUS:  {len(suspicious)}  "
      f"({len(suspicious)/total_with_mx*100:.2f}% of with-mx)")
print()
print("Top 20 most-shared 'wrong tenant' MXs (MX assigned to multiple unrelated enti):")
mx_count = Counter(s["mx"] for s in suspicious if "category" not in s)
for mx_host, n in mx_count.most_common(20):
    if n < 2:
        break
    print(f"  {n:>4}x  {mx_host}")
print()
print("=== First 25 suspicious entries ===")
for s in suspicious[:25]:
    print(f"  [{s['bfs']:<22}] {s['name'][:40]:<40}")
    print(f"      domain: {s['domain']!r}")
    print(f"      mx[0]:  {s['mx']!r}")
    print(f"      tenant slug: {s.get('tenant_slug')!r} likely owner: {s.get('tenant_likely_owner')!r}")
    print(f"      provider: {s['provider']}")
    print()

# Save full report
out_dir = ROOT / "data" / "reports"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "scraped_mx_bug_audit.json").write_text(
    json.dumps({"total_it": total_it, "total_with_mx": total_with_mx,
                "suspicious_count": len(suspicious),
                "shared_mx": dict(mx_count.most_common(30)),
                "items": suspicious},
               ensure_ascii=False, indent=2),
    encoding="utf-8")
print(f"\nFull report: {out_dir / 'scraped_mx_bug_audit.json'}")
