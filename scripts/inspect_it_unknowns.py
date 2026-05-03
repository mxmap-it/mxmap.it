#!/usr/bin/env python3
"""Detailed inspection of IT entries that remain Unknown after the full pipeline.

For each unknown:
- Shows seed data (id, name, primary domain, domain_fallbacks)
- Re-fetches the IndicePA record via CKAN to surface ALL Mail{1..5} fields
  including PEC (which the pipeline deliberately ignored), so we can spot
  patterns and decide on next-step fixes.
- Suggests a category: defunct, pec-only, scrape-candidate, etc.

Output: data/reports/it_unknowns_detail.txt
Run after the full pipeline. Usage: uv run python3 scripts/inspect_it_unknowns.py
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = DATA / "reports"

CKAN_BASE = "https://indicepa.gov.it/ipa-dati/api/3/action"
RESOURCE_ID = "d09adf99-dc10-4349-8c53-27b1e5aa97b6"
USER_AGENT = "mxmap.it-unknown-inspector/0.1"


def fetch_ipa_record(codice_ipa: str) -> dict | None:
    """Pull a single IndicePA record by Codice_IPA (no PEC filtering)."""
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
    except Exception as e:
        print(f"  IPA fetch error for {codice_ipa}: {e!r}")
        return None
    records = data.get("result", {}).get("records", [])
    return records[0] if records else None


def categorize(seed_entry: dict, raw_ipa: dict | None) -> str:
    """Classify the unknown into a fix-category."""
    fb = seed_entry.get("domain_fallbacks") or []
    if not fb:
        # No non-PEC email at all in IndicePA
        if raw_ipa:
            has_pec = any(
                (raw_ipa.get(f"Tipo_Mail{n}") or "").lower() == "pec"
                for n in range(1, 6)
            )
            if has_pec:
                return "PEC_ONLY"
            return "NO_EMAIL_AT_ALL"
        return "NO_FALLBACK"
    # Has fallbacks but none had MX → all email domains broken/defunct
    return "FALLBACKS_NO_MX"


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    seed = json.loads((DATA / "municipalities_it.json").read_text(encoding="utf-8"))
    seed_by_id = {e["id"]: e for e in seed}
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    muns = data["municipalities"]

    unknowns: list[tuple[str, dict, dict | None, str]] = []
    print("Identifying IT unknowns...")
    for key, entry in muns.items():
        if entry.get("country") != "IT":
            continue
        if entry.get("provider") != "unknown":
            continue
        eid = entry.get("id") or key
        seed_entry = seed_by_id.get(eid)
        if not seed_entry:
            continue
        unknowns.append((key, entry, seed_entry, ""))

    print(f"Found {len(unknowns)} IT unknowns. Re-fetching IndicePA records to surface PEC mails...")
    enriched: list[tuple[str, dict, dict, dict | None, str]] = []
    for i, (key, entry, seed_entry, _) in enumerate(unknowns):
        codice_ipa = seed_entry.get("ipa_codice_ipa")
        raw = fetch_ipa_record(codice_ipa) if codice_ipa else None
        category = categorize(seed_entry, raw)
        enriched.append((key, entry, seed_entry, raw, category))
        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(unknowns)}]")
        time.sleep(0.05)

    # Report
    lines: list[str] = []
    lines.append("=" * 100)
    lines.append(f"Italian comuni still classified as UNKNOWN after full pipeline ({len(enriched)} entries)")
    lines.append("=" * 100)
    lines.append("")

    cat_counter = Counter(e[4] for e in enriched)
    lines.append("Categories:")
    for cat, n in cat_counter.most_common():
        lines.append(f"  {cat:<25} {n:>4}")
    lines.append("")
    lines.append("Categories explained:")
    lines.append("  FALLBACKS_NO_MX   — IndicePA has non-PEC emails but their domains have no MX")
    lines.append("                      (likely all defunct; could try website scrape but user opted out)")
    lines.append("  PEC_ONLY          — only PEC emails in IndicePA (deliberately skipped per ITALY.md)")
    lines.append("                      MAY want to relax PEC-skip rule for these specific cases")
    lines.append("  NO_EMAIL_AT_ALL   — IndicePA has neither non-PEC nor PEC emails (rare)")
    lines.append("  NO_FALLBACK       — no domain_fallbacks in seed (defunct upstream)")
    lines.append("")
    lines.append("=" * 100)
    lines.append("")

    # Per-entry detail, grouped by category
    by_cat: dict[str, list] = {}
    for row in enriched:
        by_cat.setdefault(row[4], []).append(row)

    for cat in sorted(by_cat, key=lambda c: -len(by_cat[c])):
        lines.append("")
        lines.append(f"### {cat} ({len(by_cat[cat])} entries)")
        lines.append("")
        for key, entry, seed_entry, raw, _ in by_cat[cat]:
            name = seed_entry.get("name", "?")
            domain = seed_entry.get("domain", "?")
            fbs = seed_entry.get("domain_fallbacks") or []
            ipa = seed_entry.get("ipa_codice_ipa", "?")
            istat = seed_entry.get("ipa_codice_comune_istat", "?")
            lines.append(f"  {seed_entry.get('id', '?'):<14} {name}")
            lines.append(f"    ipa={ipa}  istat={istat}  primary_domain={domain}")
            if fbs:
                lines.append(f"    domain_fallbacks (tried, all NO MX): {', '.join(fbs)}")
            else:
                lines.append(f"    domain_fallbacks: (none)")
            if raw:
                mails = []
                for n in range(1, 6):
                    addr = (raw.get(f"Mail{n}") or "").strip()
                    kind = (raw.get(f"Tipo_Mail{n}") or "").strip().lower()
                    if addr:
                        mails.append(f"Mail{n}={addr} [{kind or 'altro'}]")
                if mails:
                    lines.append(f"    IPA raw mails: {' | '.join(mails)}")
                liq = raw.get("Ente_in_liquidazione") or ""
                if liq.upper() == "S":
                    lines.append(f"    !!! ENTE_IN_LIQUIDAZIONE=S")
            lines.append("")

    out_path = REPORTS / "it_unknowns_detail.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {out_path}")
    print()
    print("Top categories:")
    for cat, n in cat_counter.most_common():
        print(f"  {cat:<25} {n:>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
