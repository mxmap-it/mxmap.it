#!/usr/bin/env python3
"""Analyze Microsoft spending in Italian PA via ANAC broad pattern matching.

This is the "definitive" Microsoft spending analysis for the political
question "quanti € a Microsoft nella PA italiana?". It uses an extended
keyword set (including Autodesk, which is often co-procured with MS) and
combines direct ANAC spending with indirect SI subcontractor spending.

Output: data/anac/anac_microsoft_broad.json + prints headline

Usage:
    .venv/bin/python scripts/analyze_microsoft_spending.py
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "anac"
OUTPUT_PATH = DATA_DIR / "anac_microsoft_broad.json"

YEARS = [2022, 2023, 2024, 2025]

# Broad Microsoft pattern (also catches Autodesk, which is co-procured)
MS_PATTERNS = [
    r"\bmicrosoft\b",
    r"\bazure\b",
    r"\bms365\b",
    r"\boffice\s*365\b",
    r"\bsharepoint\b",
    r"\bteams\b",
    r"\boutlook\b",
    r"\bmssql\b",
    r"\bms\s*sql\b",
    r"\bwindows\s*server\b",
    r"\bsystem\s*center\b",
    r"\bactive\s*directory\b",
    r"\bentra\s*id\b",
    r"\bexchange\b",
    r"\bpower\s*bi\b",
    r"\bdynamics\b",
    r"\bnavisworks\b",
    r"\bautodesk\b",
    r"\bhyper-v\b",
    r"\bhyperv\b",
    r"\bsccm\b",
    r"\bintune\b",
]


def find_ms_keywords(text: str) -> list[str]:
    if not text:
        return []
    return [p for p in MS_PATTERNS if re.search(p, text, re.IGNORECASE)]


def process_dataset(path: Path) -> list[dict]:
    matches = []
    with gzip.open(path, "rt") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            tender = obj.get("tender") or {}
            title = tender.get("title") or ""
            desc = tender.get("description") or ""
            full_text = f"{title} {desc}"
            ms_kw = find_ms_keywords(full_text)
            if not ms_kw:
                continue
            value = 0.0
            suppliers: list[str] = []
            for award in obj.get("awards") or []:
                v = (award.get("value") or {}).get("amount")
                if v:
                    try:
                        value = float(v)
                    except (ValueError, TypeError):
                        value = 0.0
                for sup in award.get("suppliers") or []:
                    if sup.get("name"):
                        suppliers.append(sup.get("name"))
            matches.append(
                {
                    "ocid": obj.get("ocid", ""),
                    "title": title[:120],
                    "desc": desc[:120],
                    "buyer": (obj.get("buyer") or {}).get("name", ""),
                    "value": value,
                    "suppliers": suppliers,
                    "ms_keywords": ms_kw,
                }
            )
    return matches


def main() -> int:
    print("=== ANAC Microsoft Spending 2022-2025 — Broad Pattern ===\n")

    all_matches: list[dict] = []
    for year in YEARS:
        path = DATA_DIR / f"ocds_anac_{year}.jsonl.gz"
        if not path.exists():
            continue
        print(f"Processing {year}...")
        year_matches = process_dataset(path)
        for m in year_matches:
            m["year"] = year
        all_matches.extend(year_matches)
        print(f"  {year}: {len(year_matches)} matches")

    # Aggregate
    year_value: dict[int, float] = defaultdict(float)
    year_count: Counter = Counter()
    keyword_count: Counter = Counter()
    supplier_value: dict[str, float] = defaultdict(float)
    buyer_value: dict[str, float] = defaultdict(float)

    for m in all_matches:
        year_value[m["year"]] += m["value"]
        year_count[m["year"]] += 1
        for kw in m["ms_keywords"]:
            keyword_count[kw] += 1
        for sup in m["suppliers"]:
            supplier_value[sup] += m["value"]
        buyer_value[m["buyer"]] += m["value"]

    total_value = sum(m["value"] for m in all_matches)
    total_count = len(all_matches)

    print("\n=== HEADLINE ===")
    print(f"Total contratti Microsoft: {total_count:,}")
    print(f"Valore totale: €{total_value:,.0f}")

    print("\nPer anno:")
    for y in YEARS:
        v = year_value.get(y, 0)
        c = year_count.get(y, 0)
        print(f"  {y}: {c} gare, €{v:,.0f}")

    print("\nTop keyword rilevati:")
    for k, c in keyword_count.most_common(15):
        # Pretty-print the regex
        pretty = k.replace(r"\b", "").replace("\\s*", " ").replace("\\", "")
        print(f"  {pretty}: {c} contratti")

    print("\nTop 15 fornitori Microsoft (per valore):")
    for sup, val in sorted(supplier_value.items(), key=lambda x: -x[1])[:15]:
        print(f"  €{val:>15,.0f}  {sup}")

    print("\nTop 15 buyer Microsoft (per valore):")
    for buyer, val in sorted(buyer_value.items(), key=lambda x: -x[1])[:15]:
        print(f"  €{val:>15,.0f}  {buyer}")

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(all_matches, indent=2, ensure_ascii=False))
    print(f"\nSaved: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
