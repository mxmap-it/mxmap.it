#!/usr/bin/env python3
"""Reclassify Italian entries whose MX is on a 2-letter province SLD (XX.it).

The XX.it naming pattern is widely used in Italian PA for provincial-shared
mail infrastructure (comune.alessandria.al.it has MX on something.al.it,
where al.it is a Provincia di Alessandria shared mail server).

The provincial server's *own* backend determines the comune's true provider
— a comune relayed via al.it that is itself on Microsoft 365 IS on Microsoft
365 (US jurisdiction); a comune via a self-hosted province IS on sovereign
public infrastructure (Cloud Italiano, since the provincia is itself a
public administration).

This script consumes data/it_provincial_backends.json (built by
scripts/probe_it_provincial_backends.py — runs full mxmap classify() against
each XX.it domain) and propagates the probed backend down to each comune
that uses that province's mail. Falls back to comune-domain look-through
(DKIM / autodiscover / MS365 tenant) when the probe cache is missing.

Strategy per entry whose first MX matches XX.it (XX in the valid set):
  1. Read provincial_backends[XX].provider from the probe cache
     - hyperscaler (microsoft/google/aws) -> reclassify as that hyperscaler
     - aruba/register-it/seeweb/infocert/namirial/local-isp -> Provider Italiano
       (display label collapses these via providerDisplayMap in index.html)
     - independent / regional-public / no MX on XX.it -> regional-public
       (the provincia is a public administration, so its own infrastructure
        is sovereign-by-construction)
  2. If probe cache is missing for this XX, fall back to look-through on
     the comune's own domain (legacy behaviour).
  3. Always annotate the entry with `provincial_gateway: XX` and a reason
     string mentioning the gateway, whatever the final provider is.

Pipeline position: AFTER probe_it_provincial_backends + recover_it_unknowns.

Usage: uv run python3 scripts/reclassify_it_provincial.py
"""

from __future__ import annotations

import asyncio
import json
import re
from collections import Counter
from pathlib import Path

from mail_sovereignty.classify import classify_from_dkim, classify_from_autodiscover
from mail_sovereignty.dns import (
    lookup_autodiscover,
    lookup_dkim,
    lookup_spf,
    lookup_tenant,
    lookup_txt,
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CONCURRENCY = 20

# Italian province license-plate / ISTAT 2-letter codes used as second-level
# domains by provincial-shared mail infrastructure. Includes currently active
# province as well as historical codes still seen in legacy domains.
ITALIAN_PROVINCE_CODES = frozenset({
    "ag", "al", "an", "ao", "ap", "aq", "ar", "at", "av",
    "ba", "bg", "bi", "bl", "bn", "bo", "br", "bs", "bt", "bz",
    "ca", "cb", "ce", "ch", "ci", "cl", "cn", "co", "cr", "cs", "ct", "cz",
    "en", "fc", "fe", "fg", "fi", "fm", "fr",
    "ge", "go", "gr",
    "im", "is",
    "kr",
    "lc", "le", "li", "lo", "lt", "lu",
    "mb", "mc", "me", "mi", "mn", "mo", "ms", "mt",
    "na", "no", "nu",
    "og", "or", "ot",
    "pa", "pc", "pd", "pe", "pg", "pi", "pn", "po", "pr", "pt", "pu", "pv", "pz",
    "ra", "rc", "re", "rg", "ri", "rm", "rn", "ro",
    "sa", "si", "so", "sp", "sr", "ss", "su", "sv",
    "ta", "te", "tn", "to", "tp", "tr", "ts", "tv",
    "ud",
    "va", "vb", "vc", "ve", "vi", "vr", "vs", "vt", "vv",
})

# Match "<host>.<XX>.it" where XX is exactly two letters. We further check
# that XX is in ITALIAN_PROVINCE_CODES to avoid false positives.
PROVINCE_MX_RE = re.compile(r"^.+\.([a-z]{2})\.it\.?$", re.IGNORECASE)


def first_mx_host(entry: dict) -> str | None:
    mxes = entry.get("mx") or []
    if not mxes:
        return None
    h = mxes[0]
    if isinstance(h, dict):
        h = h.get("exchange") or h.get("host") or ""
    if not isinstance(h, str):
        return None
    h = h.strip().lower().rstrip(".")
    tokens = h.split()
    if len(tokens) == 2 and tokens[0].isdigit():
        h = tokens[1]
    return h or None


def detect_province(entry: dict) -> str | None:
    """Return the 2-letter province code if any of the entry's MX hosts
    match the XX.it pattern (with XX in the valid set). None otherwise."""
    for mx in entry.get("mx") or []:
        if isinstance(mx, dict):
            mx = mx.get("exchange") or mx.get("host") or ""
        if not isinstance(mx, str):
            continue
        h = mx.strip().lower().rstrip(".")
        tokens = h.split()
        if len(tokens) == 2 and tokens[0].isdigit():
            h = tokens[1]
        m = PROVINCE_MX_RE.match(h)
        if not m:
            continue
        code = m.group(1).lower()
        if code in ITALIAN_PROVINCE_CODES:
            return code
    return None


async def look_through(domain: str) -> tuple[str | None, str]:
    """Look-through pattern: query the comune's OWN DKIM / autodiscover /
    tenant / SPF. Return (provider, evidence_string) where provider may be
    None if nothing definitive is found."""
    dkim_task = asyncio.create_task(lookup_dkim(domain))
    autodiscover_task = asyncio.create_task(lookup_autodiscover(domain))
    tenant_task = asyncio.create_task(lookup_tenant(domain))
    spf_task = asyncio.create_task(lookup_spf(domain))
    txt_task = asyncio.create_task(lookup_txt(domain))

    dkim = await dkim_task
    autodiscover = await autodiscover_task
    tenant = await tenant_task
    spf = await spf_task
    _spf, txt_verifications = await txt_task

    # 1) DKIM CNAME — strongest signal
    p = classify_from_dkim(dkim)
    if p:
        return p, f"DKIM signs via {p}"

    # 2) Autodiscover SRV/CNAME pointing to a hyperscaler
    p = classify_from_autodiscover(autodiscover)
    if p:
        return p, f"autodiscover -> {p}"

    # 3) MS365 tenant lookup (getuserrealm.srf)
    if tenant:
        return "microsoft", f"MS365 tenant ({tenant})"

    # 4) TXT verification tokens (MS=, google-site-verification=)
    if "microsoft" in (txt_verifications or {}):
        return "microsoft", "MS= verification token"
    if "google" in (txt_verifications or {}):
        return "google", "google-site-verification token"

    return None, "no DKIM/autodiscover/tenant/TXT signal"


async def reclassify_one_lookthrough(
    key: str,
    entry: dict,
    province_code: str,
    sem: asyncio.Semaphore,
) -> tuple[str, str | None, str, str]:
    """Legacy fallback: comune-side look-through when the province probe
    cache lacks an entry for this code."""
    domain = entry.get("domain")
    if not domain:
        return key, None, "no primary domain", province_code
    async with sem:
        try:
            provider, evidence = await look_through(domain)
        except Exception as e:
            return key, None, f"error: {e!r}", province_code
    return key, provider, evidence, province_code


# Categorisation of the probed backend into the final provider tag.
def map_probed_provider(probed: dict | None) -> tuple[str | None, str]:
    """Map the probed backend on XX.it -> final provider tag for the comune
    + a short evidence string. Returns (provider_or_None, evidence)."""
    if probed is None:
        # XX.it has no MX or wasn't probed — comune is on provincial public
        # infrastructure, conservatively tag as regional-public.
        return "regional-public", "no MX on XX.it; province is public administration"
    p = probed.get("provider", "")
    reason = probed.get("reason", "")
    if p in {"microsoft", "google", "aws"}:
        return p, f"XX.it backend = {p} ({reason})"
    if p in {"aruba", "register-it", "seeweb", "infocert", "namirial",
             "local-isp", "telia", "tet", "zone", "elkdata", "zoho", "yandex"}:
        # Italian commercial provider via province — collapses to
        # 'Provider Italiano' display label (providerDisplayMap in index.html).
        return p, f"XX.it backend = {p} ({reason})"
    if p in {"regional-public", "pa-contractor-private"}:
        return p, f"XX.it backend = {p} ({reason})"
    if p == "independent":
        # XX.it is self-hosted by the province itself. Provincia is a
        # public administration, so this IS sovereign infrastructure ->
        # regional-public.
        return "regional-public", f"XX.it self-hosted by provincia ({reason})"
    if p == "unknown":
        # Probe couldn't classify — tag as regional-public since province is public
        return "regional-public", f"XX.it backend unknown; province is public administration"
    return None, f"unrecognised probed provider: {p!r}"


async def main_async() -> int:
    data_path = ROOT / "data.json"
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    muns = data["municipalities"]

    # Load the per-province backend probe cache (if present)
    probe_path = DATA / "it_provincial_backends.json"
    by_province: dict[str, dict | None] = {}
    if probe_path.exists():
        probe_doc = json.loads(probe_path.read_text(encoding="utf-8"))
        by_province = probe_doc.get("by_province_code", {})
        print(f"Loaded probe cache: {len(by_province)} provinces "
              f"({sum(1 for v in by_province.values() if v) } with MX)")
    else:
        print(f"WARNING: {probe_path} missing — falling back to comune-side "
              f"look-through. Run scripts/probe_it_provincial_backends.py first "
              f"for accurate backend attribution.")

    # Selection policy (allowing idempotent re-run after probe cache changes):
    # an entry becomes a candidate when ALL of:
    #   - country = IT
    #   - first MX matches XX.it (XX in valid Italian province codes)
    #   - provider is NOT already a hyperscaler (those are correctly attributed
    #     by preprocess regardless of the gateway)
    # Note: provincial-shared / independent / local-isp / pa-contractor-private
    # / regional-public ARE re-processed so that policy updates flow into them.
    skip_providers = {"microsoft", "google", "aws"}
    candidates: list[tuple[str, dict, str]] = []
    for key, entry in muns.items():
        if entry.get("country") != "IT":
            continue
        if entry.get("provider") in skip_providers:
            continue
        province_code = detect_province(entry)
        if not province_code:
            continue
        candidates.append((key, entry, province_code))

    print(f"Found {len(candidates)} IT entries with MX on XX.it (provincial-shared pattern)")
    if not candidates:
        return 0

    province_distribution: Counter[str] = Counter()
    backend_found: Counter[str] = Counter()
    fallback_lookthrough_keys: list[tuple[str, dict, str]] = []
    n_done = 0

    # Phase A — apply the probe cache (synchronous, fast).
    for key, entry, province_code in candidates:
        province_distribution[province_code] += 1
        entry["provincial_gateway"] = province_code
        if province_code in by_province:
            probed = by_province[province_code]
            provider, evidence = map_probed_provider(probed)
            if provider:
                entry["provider"] = provider
                entry["reason"] = (
                    f"via provincial gateway {province_code}.it; {evidence}"
                )
                backend_found[provider] += 1
                n_done += 1
                continue
        # No probe entry for this XX — queue legacy look-through
        fallback_lookthrough_keys.append((key, entry, province_code))

    # Phase B — legacy comune-side look-through for the residue.
    if fallback_lookthrough_keys:
        print(f"Probe cache missing {len(fallback_lookthrough_keys)} province codes; "
              f"falling back to comune-side look-through")
        sem = asyncio.Semaphore(CONCURRENCY)
        tasks = [reclassify_one_lookthrough(k, e, p, sem)
                 for k, e, p in fallback_lookthrough_keys]
        for coro in asyncio.as_completed(tasks):
            key, provider, evidence, province_code = await coro
            n_done += 1
            entry = muns[key]
            if provider:
                entry["provider"] = provider
                entry["reason"] = (
                    f"via provincial gateway {province_code}.it; {evidence}"
                )
                backend_found[provider] += 1
            else:
                # As per the new policy: when nothing is found, the comune
                # is on the provincia's own infrastructure -> regional-public
                entry["provider"] = "regional-public"
                entry["reason"] = (
                    f"via provincial gateway {province_code}.it; "
                    f"no hyperscaler signal — provincia is public administration"
                )
                backend_found["regional-public"] += 1

    # Recompute counts
    counts: Counter[str] = Counter(v.get("provider", "unknown") for v in muns.values())
    data["counts"] = dict(counts)

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    print()
    print("=== Reclassification summary ===")
    print(f"  Total candidates                  : {len(candidates)}")
    print(f"  Resolved (probe cache)            : {len(candidates) - len(fallback_lookthrough_keys)}")
    print(f"  Resolved (look-through fallback)  : {len(fallback_lookthrough_keys)}")
    print(f"  Total backend-attributed          : {sum(backend_found.values())}")
    print()
    print("=== Backends attributed via provincial gateways ===")
    for prov, n in backend_found.most_common():
        print(f"  {prov:<25} {n:>4}")
    print()
    print("=== Top provinces (by entry count using provincial mail) ===")
    for code, n in province_distribution.most_common(20):
        print(f"  {code:<3} {n:>4}")
    print()
    print(f"Wrote {data_path}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
