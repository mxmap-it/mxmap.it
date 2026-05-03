#!/usr/bin/env python3
"""Final pass for IT entries still classified as `unknown` after preprocess
+ recover_it_unknowns + reclassify_it_provincial.

Two strategies, applied in order per remaining unknown:

1. **RUPAR Piemonte / CSI Piemonte special case** —
   If the entry's IndicePA record has any Mail{n} on `cert.ruparpiemonte.it`
   (a publicly-owned regional PEC infrastructure run by CSI Piemonte for
   Piemonte comuni), classify as `regional-public` with reason noting the
   regional sovereign infrastructure dependency. Per user direction in the
   pipeline review session.

2. **Homepage email-scrape fallback** —
   For all other unresolved entries: fetch the comune's primary website
   homepage (single GET, polite User-Agent, 10s timeout). If DNS resolution
   itself fails → KO (mark with reason "primary domain DNS failure, no
   fallback"). If the page is fetched, regex-extract email addresses,
   filter out third-party junk (iubenda, cookiebot, etc.), and try each
   email's domain via mxmap's lookup_mx. First domain with MX wins, full
   classify() runs against it. If no email yields MX → mark as KO.

Idempotent via the existing `domain_used` field. Re-runs skip already-
recovered entries.

Usage: uv run python3 scripts/finalize_it_unknowns.py
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import httpx

from mail_sovereignty.classify import classify
from mail_sovereignty.constants import EMAIL_RE
from mail_sovereignty.dns import (
    lookup_autodiscover,
    lookup_dkim,
    lookup_mx,
    lookup_spf,
    lookup_tenant,
    lookup_txt,
    resolve_mx_asns,
    resolve_mx_cnames,
    resolve_mx_countries,
    resolve_spf_includes,
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CKAN_BASE = "https://indicepa.gov.it/ipa-dati/api/3/action"
RESOURCE_ID = "d09adf99-dc10-4349-8c53-27b1e5aa97b6"
USER_AGENT = "mxmap.it/0.1 (+https://github.com/fpietrosanti/mxmap.it)"

CONCURRENCY_DNS = 10
CONCURRENCY_HTTP = 8

# Third-party email vendors to ignore when scraping comune homepages.
EMAIL_BLOCKLIST = frozenset({
    "iubenda.com", "cookiebot.com", "cookieyes.com", "onetrust.com",
    "sentry.io", "google-analytics.com", "googletagmanager.com",
    "wpbeginner.com", "wordpress.com", "automattic.com",
    "example.com", "example.it", "test.it", "domain.com",
    "localhost", "yourcompany.com",
    "sitiwp.com", "designerthemes.com", "templatemonster.com",
    "elegantthemes.com",
})


def fetch_ipa_record(codice_ipa: str) -> dict | None:
    params = {
        "resource_id": RESOURCE_ID,
        "filters": json.dumps({"Codice_IPA": codice_ipa}),
        "limit": 1,
    }
    url = f"{CKAN_BASE}/datastore_search?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    records = data.get("result", {}).get("records", [])
    return records[0] if records else None


def detect_rupar_piemonte(raw: dict) -> bool:
    """Return True if any Mail{1..5} is on cert.ruparpiemonte.it (any case)."""
    for n in range(1, 6):
        addr = (raw.get(f"Mail{n}") or "").strip().lower()
        if not addr or "@" not in addr:
            continue
        host = addr.rsplit("@", 1)[1].rstrip(".")
        if host == "cert.ruparpiemonte.it" or host.endswith(".cert.ruparpiemonte.it"):
            return True
    return False


async def classify_domain(domain: str) -> dict | None:
    """Run the full mxmap classification pipeline against `domain`."""
    mx_records = await lookup_mx(domain)
    if not mx_records:
        return None
    spf_task = asyncio.create_task(lookup_spf(domain))
    txt_task = asyncio.create_task(lookup_txt(domain))
    cname_task = asyncio.create_task(resolve_mx_cnames(mx_records))
    asn_task = asyncio.create_task(resolve_mx_asns(mx_records))
    country_task = asyncio.create_task(resolve_mx_countries(mx_records))
    autodiscover_task = asyncio.create_task(lookup_autodiscover(domain))
    dkim_task = asyncio.create_task(lookup_dkim(domain))
    tenant_task = asyncio.create_task(lookup_tenant(domain))

    spf_record = await spf_task
    _spf_raw, txt_verifications = await txt_task
    mx_cnames = await cname_task
    mx_asns = await asn_task
    mx_countries = await country_task
    autodiscover = await autodiscover_task
    dkim = await dkim_task
    tenant = await tenant_task
    resolved_spf = await resolve_spf_includes(spf_record) if spf_record else None

    provider, reason = classify(
        mx_records=mx_records,
        spf_record=spf_record,
        mx_cnames=mx_cnames,
        mx_asns=mx_asns,
        resolved_spf=resolved_spf,
        autodiscover=autodiscover,
        dkim=dkim,
        txt_verifications=txt_verifications,
        tenant=tenant,
    )
    return {
        "mx": mx_records,
        "spf": spf_record,
        "spf_resolved": resolved_spf,
        "provider": provider,
        "reason": reason,
        "mx_cnames": mx_cnames,
        "mx_asns": sorted(mx_asns) if isinstance(mx_asns, set) else list(mx_asns or []),
        "mx_countries": sorted(mx_countries) if isinstance(mx_countries, set) else list(mx_countries or []),
        "autodiscover": autodiscover,
        "dkim": dkim,
        "txt_verifications": txt_verifications,
        "tenant": tenant,
    }


async def fetch_homepage(client: httpx.AsyncClient, domain: str) -> tuple[str | None, str]:
    """Try https://domain/ first, fall back to http://. Return (text, status)
    where status is 'ok' / 'dns_fail' / 'http_fail' / 'empty'."""
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}/"
        try:
            r = await client.get(url, follow_redirects=True, timeout=10.0)
        except httpx.ConnectError as e:
            # Distinguish DNS failure (NXDOMAIN, no IP) from connection refused.
            msg = str(e).lower()
            if "name" in msg or "resolve" in msg or "dns" in msg or "nodename" in msg or "getaddrinfo" in msg:
                return None, "dns_fail"
            continue
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError):
            continue
        except Exception:
            continue
        if r.status_code >= 400:
            continue
        if not r.text:
            return None, "empty"
        return r.text, "ok"
    return None, "http_fail"


def extract_emails(html: str, primary_domain: str) -> list[str]:
    """Pull email addresses out of the HTML, filter junk vendors, and order by
    relevance: same registrable domain as primary_domain first, then everything
    else."""
    primary_reg = ".".join(primary_domain.lower().split(".")[-2:])
    candidates = set(EMAIL_RE.findall(html or ""))
    same_dom: list[str] = []
    other: list[str] = []
    for raw in candidates:
        addr = raw.strip().lower()
        if "@" not in addr:
            continue
        host = addr.rsplit("@", 1)[1]
        # Block third-party vendors
        host_reg = ".".join(host.split(".")[-2:])
        if host_reg in EMAIL_BLOCKLIST:
            continue
        # Heuristic skip: privacy/dpo/cookie role on third-party infrastructure
        local = addr.split("@", 1)[0]
        if local in {"webmaster", "admin"} and host_reg not in {primary_reg}:
            other.append(addr)
            continue
        if host == primary_domain or host.endswith(f".{primary_domain}") or host_reg == primary_reg:
            same_dom.append(addr)
        else:
            other.append(addr)
    return same_dom + other


async def finalize_one(
    key: str,
    entry: dict,
    seed_entry: dict,
    client: httpx.AsyncClient,
    dns_sem: asyncio.Semaphore,
    http_sem: asyncio.Semaphore,
) -> tuple[str, dict, str]:
    """Run the two strategies. Returns (key, mutation_dict, status)."""
    primary = (entry.get("domain") or "").strip().lower()
    codice_ipa = seed_entry.get("ipa_codice_ipa")
    raw = fetch_ipa_record(codice_ipa) if codice_ipa else None

    # Strategy 1: cert.ruparpiemonte.it special case.
    if raw and detect_rupar_piemonte(raw):
        async with dns_sem:
            try:
                result = await classify_domain("ruparpiemonte.it")
            except Exception:
                result = None
        # We set the entry to regional-public regardless of MX result, but
        # if MX is found we use the actual classification too.
        mutation = {
            "domain_used": "ruparpiemonte.it",
            "provider": "regional-public",
            "reason": "PEC on cert.ruparpiemonte.it -> RUPAR Piemonte / CSI Piemonte (publicly-owned regional ICT)",
            "rupar_piemonte": True,
        }
        if result:
            for k, v in result.items():
                if k != "provider" and k != "reason":
                    mutation[k] = v
        return key, mutation, "rupar"

    # Strategy 2: scrape the homepage for emails, try each email's domain.
    if not primary:
        return key, {"reason": "no primary domain"}, "no_primary"
    async with http_sem:
        text, fetch_status = await fetch_homepage(client, primary)
    if fetch_status == "dns_fail":
        return key, {"reason": f"primary domain DNS failure ({primary}), no fallback"}, "dns_fail"
    if not text:
        return key, {"reason": f"homepage unreachable ({fetch_status}); no scrape candidate"}, fetch_status

    emails = extract_emails(text, primary)
    if not emails:
        return key, {"reason": "homepage fetched but no emails extracted"}, "no_email"

    # Try each email's domain via DNS
    async with dns_sem:
        tried = []
        for addr in emails[:6]:  # up to first 6 candidates
            host = addr.rsplit("@", 1)[1]
            tried.append(host)
            try:
                result = await classify_domain(host)
            except Exception:
                continue
            if result is None:
                continue
            mutation = {
                "domain_used": host,
                "scraped_email": addr,
                "scrape_tried_hosts": tried,
            }
            mutation.update(result)
            return key, mutation, "scraped"
    return key, {
        "reason": f"scraped {len(emails)} emails, none have MX (tried {', '.join(tried[:6])})",
        "scrape_tried_hosts": tried,
    }, "scrape_no_mx"


async def main_async() -> int:
    seed = json.loads((DATA / "municipalities_it.json").read_text(encoding="utf-8"))
    seed_by_id = {e["id"]: e for e in seed}
    data_path = ROOT / "data.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    muns = data["municipalities"]

    candidates: list[tuple[str, dict, dict]] = []
    for key, entry in muns.items():
        if entry.get("country") != "IT":
            continue
        if entry.get("provider") != "unknown":
            continue
        if entry.get("domain_used"):
            continue
        eid = entry.get("id") or key
        seed_entry = seed_by_id.get(eid)
        if not seed_entry:
            continue
        candidates.append((key, entry, seed_entry))

    print(f"Found {len(candidates)} IT entries still unknown after recovery+provincial passes")
    if not candidates:
        return 0

    dns_sem = asyncio.Semaphore(CONCURRENCY_DNS)
    http_sem = asyncio.Semaphore(CONCURRENCY_HTTP)

    status_counter: Counter[str] = Counter()
    provider_counter: Counter[str] = Counter()

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        verify=False,  # PA sites occasionally have self-signed certs; we just want emails
        max_redirects=3,
    ) as client:
        tasks = [
            finalize_one(k, e, s, client, dns_sem, http_sem)
            for k, e, s in candidates
        ]
        n_done = 0
        for coro in asyncio.as_completed(tasks):
            key, mutation, status = await coro
            n_done += 1
            status_counter[status] += 1
            entry = muns[key]
            for k, v in mutation.items():
                entry[k] = v
            if status in ("rupar", "scraped"):
                provider_counter[entry.get("provider", "?")] += 1
            if n_done % 10 == 0:
                print(f"  [{n_done}/{len(candidates)}] {dict(status_counter)}")

    counts: Counter[str] = Counter(v.get("provider", "unknown") for v in muns.values())
    data["counts"] = dict(counts)
    data_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print()
    print("=== Status breakdown ===")
    for s, n in status_counter.most_common():
        print(f"  {s:<20} {n:>4}")
    print()
    print("=== New provider distribution among finalized ===")
    for p, n in provider_counter.most_common():
        print(f"  {p:<25} {n:>4}")
    print()
    print(f"Wrote {data_path}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
