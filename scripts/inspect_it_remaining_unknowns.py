#!/usr/bin/env python3
"""Detail of the 37 IT comuni still classified as `unknown` after the full
pipeline (preprocess + recover + reclassify_provincial + finalize).

Splits by reason category:
  - dns_fail   : primary website domain has NXDOMAIN (truly defunct)
  - no_email   : homepage fetched but regex found no email addresses
  - http_fail  : homepage HTTP error (500/4xx/timeout)
  - scrape_no_mx : emails found, but none of their domains have MX
  - other      : anything else

For each entry: name, ISTAT, primary domain, full IndicePA mail block
(including PEC, for context), website URL for the user to visit, and
category-specific hint.

Output: data/reports/it_remaining_unknowns.txt
Usage: uv run python3 scripts/inspect_it_remaining_unknowns.py
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = DATA / "reports"

CKAN_BASE = "https://indicepa.gov.it/ipa-dati/api/3/action"
RESOURCE_ID = "d09adf99-dc10-4349-8c53-27b1e5aa97b6"
USER_AGENT = "mxmap.it-remaining-inspector/0.1"


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


def categorize(reason: str) -> str:
    r = (reason or "").lower()
    if "dns failure" in r or "dns_fail" in r:
        return "dns_fail"
    if "no emails extracted" in r:
        return "no_email"
    if "homepage unreachable" in r:
        return "http_fail"
    if "none have mx" in r:
        return "scrape_no_mx"
    return "other"


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    seed = json.loads((DATA / "municipalities_it.json").read_text(encoding="utf-8"))
    seed_by_id = {e["id"]: e for e in seed}
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    muns = data["municipalities"]

    unknowns = []
    for k, v in muns.items():
        if v.get("country") != "IT":
            continue
        if v.get("provider") != "unknown":
            continue
        eid = v.get("id") or k
        seed_entry = seed_by_id.get(eid)
        unknowns.append((k, v, seed_entry))

    print(f"Found {len(unknowns)} IT entries still unknown")

    by_cat = defaultdict(list)
    for k, v, s in unknowns:
        cat = categorize(v.get("reason", ""))
        by_cat[cat].append((k, v, s))

    # Re-fetch IPA records (so we can show all 5 Mail fields incl. PEC)
    enriched = []
    for k, v, s in unknowns:
        codice_ipa = (s or {}).get("ipa_codice_ipa")
        raw = fetch_ipa_record(codice_ipa) if codice_ipa else None
        enriched.append((k, v, s, raw))
        time.sleep(0.05)

    by_cat_enriched = defaultdict(list)
    for row in enriched:
        cat = categorize(row[1].get("reason", ""))
        by_cat_enriched[cat].append(row)

    lines: list[str] = []
    lines.append("=" * 100)
    lines.append(f"Italian comuni still UNKNOWN after the full pipeline ({len(unknowns)} entries)")
    lines.append("=" * 100)
    lines.append("")
    lines.append("Categories:")
    for cat, items in sorted(by_cat_enriched.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"  {cat:<15} {len(items)}")
    lines.append("")
    lines.append("Hints per category:")
    lines.append("  dns_fail     : primary domain has NO DNS resolution (NXDOMAIN). The website")
    lines.append("                 is genuinely offline. Try searching for the comune's CURRENT")
    lines.append("                 website (often migrated to a regional / new domain).")
    lines.append("  no_email     : homepage was fetched but no email addresses were found in")
    lines.append("                 the HTML. Visit the site and look at /contatti, /trasparenza,")
    lines.append("                 or look for a phone-only contact page.")
    lines.append("  http_fail    : domain resolves but homepage returns HTTP error / timeout.")
    lines.append("                 Site may be temporarily down or behind a paywall/auth.")
    lines.append("  scrape_no_mx : emails found, but their domains have no MX. Domain owner")
    lines.append("                 does not host email there — likely a typo.")
    lines.append("")
    lines.append("=" * 100)

    for cat in sorted(by_cat_enriched, key=lambda c: -len(by_cat_enriched[c])):
        lines.append("")
        lines.append(f"### {cat.upper()} ({len(by_cat_enriched[cat])} entries)")
        lines.append("")
        for key, entry, seed_entry, raw in by_cat_enriched[cat]:
            eid = entry.get("id") or key
            name = (seed_entry or {}).get("name") or entry.get("name") or "?"
            domain = (seed_entry or {}).get("domain") or entry.get("domain") or "?"
            ipa = (seed_entry or {}).get("ipa_codice_ipa") or "?"
            istat = (seed_entry or {}).get("ipa_codice_comune_istat") or "?"
            reason = (entry.get("reason") or "")
            tried = entry.get("scrape_tried_hosts") or []
            lines.append(f"  {eid}  {name}")
            lines.append(f"    ISTAT={istat}  IPA={ipa}")
            lines.append(f"    primary_domain  : {domain}")
            lines.append(f"    website_url     : http://{domain}/  /  https://{domain}/")
            lines.append(f"    pipeline_reason : {reason}")
            if tried:
                lines.append(f"    scrape_attempted_hosts: {', '.join(tried)}")
            if raw:
                mails = []
                for n in range(1, 6):
                    addr = (raw.get(f"Mail{n}") or "").strip()
                    kind = (raw.get(f"Tipo_Mail{n}") or "").strip().lower()
                    if addr:
                        mails.append(f"Mail{n}={addr}[{kind or 'altro'}]")
                if mails:
                    lines.append(f"    indicepa_mails  : " + " | ".join(mails))
                else:
                    lines.append(f"    indicepa_mails  : (none)")
                liq = (raw.get("Ente_in_liquidazione") or "").upper()
                if liq == "S":
                    lines.append(f"    !!! ENTE_IN_LIQUIDAZIONE=S")
            lines.append("")

    out_path = REPORTS / "it_remaining_unknowns.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
