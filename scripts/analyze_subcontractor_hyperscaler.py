#!/usr/bin/env python3
"""Analyze ANAC contracts to find the "indirect" hyperscaler spending
that flows through Italian System Integrators (Engineering, Italware,
Maticmind, Var Group, Lutech, etc.).

Method: For each ANAC OCDS record 2022-2025, find contracts whose
`awards[].suppliers[].name` contains an Italian SI AND whose
`tender.title + tender.description` contains a hyperscaler keyword
(Microsoft, Oracle, AWS, IBM, SAP, Google, Salesforce).

Output: data/anac/anac_subcontractor_hyperscaler.json

Usage:
    .venv/bin/python scripts/analyze_subcontractor_hyperscaler.py
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
OUTPUT_PATH = DATA_DIR / "anac_subcontractor_hyperscaler.json"

# Italian System Integrators that manage hyperscaler stacks
SI_WITH_HYPERSCALER_STACK = [
    "engineering",
    "italware",
    "maticmind",
    "var group",
    "lutech",
    "gpi",
    "almaviva",
    "enterprise services italia",
    "dedalus",
    "fini",
    "finmeccanica",
    "postel",
    "reply",
    "ntt data",
    "accenture",
    "deloitte",
    "capgemini",
    "at os",
    "asta",
    "kc",
    "extra",
    "technisblu",
    "pwc",
    "kpmg",
    "ey",
    "lutech",
    "infocert",
    "poste italiane",
    "eustema",
    "abodata",
    "ag",
    "vetrya",
    "axians",
    "softlab",
    "blueit",
    "lutechgroup",
]

HYPERSCALER_KEYWORDS: dict[str, list[str]] = {
    "microsoft": [
        r"\bmicrosoft\b",
        r"\boffice\s*365\b",
        r"\bm365\b",
        r"\bazure\b",
        r"\bsharepoint\b",
        r"\bteams\b",
    ],
    "oracle": [r"\boracle\b", r"\boracle\s*cloud\b", r"\boc\b"],
    "aws": [r"\baws\b", r"\bamazon\s*web\s*services\b", r"\bamazonses\b"],
    "google": [r"\bgoogle\s*workspace\b", r"\bg\s*suite\b"],
    "ibm": [r"\bibm\b"],
    "sap": [r"\bsap\b"],
    "salesforce": [r"\bsalesforce\b"],
}

HYPERSCALERS = ("microsoft", "google", "aws", "oracle", "ibm", "salesforce")


def find_hyperscaler(text: str) -> str | None:
    if not text:
        return None
    text_lower = text.lower()
    matches = []
    for provider, patterns in HYPERSCALER_KEYWORDS.items():
        for p in patterns:
            if re.search(p, text_lower, re.IGNORECASE):
                matches.append(provider)
                break
    if not matches:
        return None
    for m in matches:
        if m in HYPERSCALERS:
            return m
    return matches[0]


def is_italian_SI(supplier_name: str) -> str | None:
    """Return SI name if supplier matches a known Italian SI, else None."""
    if not supplier_name:
        return None
    s = supplier_name.lower()
    for si in SI_WITH_HYPERSCALER_STACK:
        if si in s:
            return si
    return None


def process_dataset(path: Path) -> list[dict]:
    """Process ANAC dataset file, return list of {si, hyperscaler, value, year}."""
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
            hs = find_hyperscaler(full_text)
            if not hs:
                continue
            for award in obj.get("awards") or []:
                for sup in award.get("suppliers") or []:
                    supplier_name = sup.get("name") or ""
                    si = is_italian_SI(supplier_name)
                    if not si:
                        continue
                    value = 0.0
                    v = (award.get("value") or {}).get("amount")
                    if v:
                        try:
                            value = float(v)
                        except (ValueError, TypeError):
                            value = 0.0
                    matches.append(
                        {
                            "si": si,
                            "supplier": supplier_name,
                            "hyperscaler": hs,
                            "value": value,
                            "ocid": obj.get("ocid", ""),
                            "buyer": (obj.get("buyer") or {}).get("name", ""),
                            "title": title[:100],
                        }
                    )
    return matches


def main() -> int:
    print("=== ANAC Subcontractor Analysis — Italian SI su stack Hyperscaler ===\n")

    years = [2022, 2023, 2024, 2025]
    all_matches: list[dict] = []

    for year in years:
        path = DATA_DIR / f"ocds_anac_{year}.jsonl.gz"
        if not path.exists():
            print(f"  Skipping {year}: {path} not found")
            continue
        print(f"Processing {year}...")
        matches = process_dataset(path)
        for m in matches:
            m["year"] = year
        all_matches.extend(matches)
        print(f"  {year}: {len(matches)} matches")

    # Aggregate
    si_value_by_year: dict[str, dict[int, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    si_value_by_hs: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    si_total_value: dict[str, float] = defaultdict(float)
    si_count: Counter = Counter()

    for m in all_matches:
        si = m["si"]
        year = m["year"]
        hs = m["hyperscaler"]
        value = m["value"]
        si_value_by_year[si][year] += value
        si_value_by_hs[si][hs] += value
        si_total_value[si] += value
        si_count[si] += 1

    # Print top 15 SI
    print("\n=== Top 15 SI italiani per valore (4 anni) ===\n")
    top_si = sorted(si_total_value.items(), key=lambda x: -x[1])[:15]
    print(
        f"{'SI':<30} {'2022':>12} {'2023':>12} {'2024':>12} {'2025':>12} {'TOTALE':>14}"
    )
    print("-" * 110)
    for si, _ in top_si:
        v22 = si_value_by_year[si].get(2022, 0)
        v23 = si_value_by_year[si].get(2023, 0)
        v24 = si_value_by_year[si].get(2024, 0)
        v25 = si_value_by_year[si].get(2025, 0)
        tot = v22 + v23 + v24 + v25
        print(
            f"{si:<30} €{v22:>10,.0f} €{v23:>10,.0f} €{v24:>10,.0f} €{v25:>10,.0f} €{tot:>12,.0f}"
        )

    # Print breakdown for top 5 SI
    print("\n=== Breakdown hyperscaler (top 10 SI) ===\n")
    print(
        f"{'SI':<30} {'MS':>10} {'Oracle':>10} {'AWS':>10} {'IBM':>10} {'SAP':>10} {'Google':>10}"
    )
    print("-" * 110)
    for si, _ in top_si[:10]:
        ms = si_value_by_hs[si].get("microsoft", 0)
        orc = si_value_by_hs[si].get("oracle", 0)
        aws = si_value_by_hs[si].get("aws", 0)
        ibm = si_value_by_hs[si].get("ibm", 0)
        sap = si_value_by_hs[si].get("sap", 0)
        go = si_value_by_hs[si].get("google", 0)
        print(
            f"{si:<30} €{ms:>8,.0f} €{orc:>8,.0f} €{aws:>8,.0f} €{ibm:>8,.0f} €{sap:>8,.0f} €{go:>8,.0f}"
        )

    # Hyperscaler totals indirect
    print("\n=== Stima totale indiretto per hyperscaler ===")
    hs_indirect: dict[str, float] = defaultdict(float)
    for m in all_matches:
        hs_indirect[m["hyperscaler"]] += m["value"]
    for hs, val in sorted(hs_indirect.items(), key=lambda x: -x[1]):
        print(f"  {hs}: €{val:,.0f}")

    # Save JSON
    output = {
        "method": "keyword-search: SI name in supplier + hyperscaler keyword in tender",
        "caveat": "Conservativo: contratti 'cloud generico' senza vendor esplicito non sono catturati. Sub-subfornitori non visibili.",
        "years_analyzed": years,
        "total_matches": len(all_matches),
        "si_value_per_year": {
            si: dict(years_dict) for si, years_dict in si_value_by_year.items()
        },
        "si_value_per_hyperscaler": {
            si: dict(hs_dict) for si, hs_dict in si_value_by_hs.items()
        },
        "si_total_value": dict(si_total_value),
        "si_count": dict(si_count),
        "hyperscaler_indirect_total": dict(hs_indirect),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\nSaved: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
