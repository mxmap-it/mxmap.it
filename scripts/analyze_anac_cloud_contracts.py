#!/usr/bin/env python3
"""Analyze ANAC OCDS procurement data for cloud/hyperscaler contracts.

Downloads the ANAC OCDS dataset (Italian public procurement) for a
given year, filters for cloud/hyperscaler keywords, deduplicates per
OCID (one OCID = one tender, ATI partners share the value), and
categorizes the awards by provider category.

Usage:
    .venv/bin/python scripts/analyze_anac_cloud_contracts.py --year 2024
    .venv/bin/python scripts/analyze_anac_cloud_contracts.py --year 2024 --mxmap data.json
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "anac"

OCDS_BASE = "https://data.open-contracting.org/en/publication/117/download"
PROVIDER_KEYWORDS: dict[str, list[str]] = {
    "microsoft": [
        r"\bmicrosoft\b",
        r"\boffice\s*365\b",
        r"\bm365\b",
        r"\bazure\b",
        r"\bsharepoint\b",
        r"\bteams\b",
        r"\bexchange\s*online\b",
        r"\bmicrosoft\s*365\b",
        r"\bms365\b",
        r"\boutlook\.com\b",
    ],
    "google": [
        r"\bgoogle\b",
        r"\bgoogle\s*workspace\b",
        r"\bg\s*suite\b",
        r"\bgmail\b",
        r"\bchrome\s*enterprise\b",
        r"\bgoogle\s*cloud\b",
        r"\bgcp\b",
    ],
    "aws": [
        r"\baws\b",
        r"\bamazon\s*web\s*services\b",
        r"\bamazonses\b",
        r"\bec2\b",
        r"\bs3\b",
    ],
    "oracle": [r"\boracle\b", r"\boracle\s*cloud\b", r"\boc\b"],
    "ibm": [r"\bibm\b", r"\bibm\s*cloud\b"],
    "salesforce": [r"\bsalesforce\b"],
    "sap": [r"\bsap\b", r"\bsap\s*cloud\b"],
    "psn": [r"\bpolo\s*strategico\b", r"\bpsn\b"],
    "aruba": [r"\baruba\b"],
    "fastweb": [r"\bfastweb\b"],
    "tim": [r"\btelecom\s*italia\b", r"\btim\s*s\.p\.a\.\b", r"\btim\b"],
    "leonardo": [r"\bleonardo\s*s\.p\.a\.\b"],
    "engineering": [r"\bengineering\b"],
    "almaviva": [r"\balmaviva\b"],
    "seeweb": [r"\bseeweb\b"],
    "lutech": [r"\blutech\b"],
    "cloud_generic": [
        r"\bcloud\s*computing\b",
        r"\bservizi?\s*cloud\b",
        r"\bpiattaforma\s*cloud\b",
    ],
}

PROVIDER_CATEGORY: dict[str, str] = {
    "microsoft": "hyperscaler_usa",
    "google": "hyperscaler_usa",
    "aws": "hyperscaler_usa",
    "oracle": "hyperscaler_usa",
    "ibm": "hyperscaler_usa",
    "salesforce": "hyperscaler_usa",
    "sap": "hyperscaler_eu",
    "cloud_generic": "mixed",
    "psn": "italian_sovereign",
    "aruba": "italian_commercial",
    "fastweb": "italian_commercial",
    "tim": "italian_commercial",
    "leonardo": "italian_commercial",
    "engineering": "italian_commercial",
    "almaviva": "italian_commercial",
    "seeweb": "italian_commercial",
    "lutech": "italian_commercial",
}

HYPERSCALERS = ("microsoft", "google", "aws", "oracle", "ibm", "salesforce")


def find_provider(text: str) -> str | None:
    """Identify the primary provider mentioned in text."""
    if not text:
        return None
    text_lower = text.lower()
    matches = []
    for provider, patterns in PROVIDER_KEYWORDS.items():
        for p in patterns:
            if re.search(p, text_lower, re.IGNORECASE):
                matches.append(provider)
                break
    if not matches:
        return None
    # Prioritize hyperscaler > italian
    for m in matches:
        if m in HYPERSCALERS:
            return m
    return matches[0]


def download_anac(year: int) -> Path:
    """Download ANAC OCDS dataset for the given year."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target = DATA_DIR / f"ocds_anac_{year}.jsonl.gz"
    if target.exists() and target.stat().st_size > 1_000_000:
        print(f"Using cached: {target}")
        return target
    url = f"{OCDS_BASE}?name={year}.jsonl.gz"
    print(f"Downloading {url}...")
    urllib.request.urlretrieve(url, target)
    print(f"Downloaded: {target} ({target.stat().st_size:,} bytes)")
    return target


def process_dataset(path: Path) -> list[dict]:
    """Process ANAC dataset, return list of cloud-related records."""
    records = []
    total = 0
    with gzip.open(path, "rt") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            tender = obj.get("tender") or {}
            title = tender.get("title") or ""
            desc = tender.get("description") or ""
            full_text = f"{title} {desc}"
            provider = find_provider(full_text)
            if not provider:
                continue
            buyer = obj.get("buyer") or {}
            awards = obj.get("awards") or []
            value = 0.0
            currency = "EUR"
            supplier_names: list[str] = []
            if awards:
                for award in awards:
                    v = (award.get("value") or {}).get("amount")
                    if v:
                        value = float(v)
                        currency = (award.get("value") or {}).get("currency", "EUR")
                    for sup in award.get("suppliers") or []:
                        name = sup.get("name")
                        if name:
                            supplier_names.append(name)
            records.append(
                {
                    "ocid": obj.get("ocid", ""),
                    "buyer_name": buyer.get("name", ""),
                    "buyer_id": buyer.get("id", ""),
                    "title": title[:200],
                    "desc": desc[:200],
                    "supplier": supplier_names,
                    "value": value,
                    "currency": currency,
                    "date": obj.get("date", ""),
                    "detected_provider": provider,
                }
            )
    print(f"Processed {total:,} records, found {len(records)} cloud-related")
    return records


def deduplicate_by_ocid(records: list[dict]) -> list[dict]:
    """Deduplicate by OCID; multiple suppliers in ATI share the value."""
    ocid_idx: dict[str, dict] = {}
    for r in records:
        ocid = r["ocid"]
        if ocid not in ocid_idx:
            ocid_idx[ocid] = dict(r)
            ocid_idx[ocid]["supplier"] = list(r["supplier"])
        else:
            for s in r["supplier"]:
                if s not in ocid_idx[ocid]["supplier"]:
                    ocid_idx[ocid]["supplier"].append(s)
    return list(ocid_idx.values())


def aggregate_summary(records: list[dict]) -> dict:
    """Aggregate by category and by hyperscaler vendor."""
    cat_totals: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "value": 0.0, "suppliers_value": Counter()}
    )
    hs_totals: dict[str, dict] = defaultdict(lambda: {"count": 0, "value": 0.0})

    for r in records:
        if r["value"] <= 0:
            continue
        cat = PROVIDER_CATEGORY.get(r["detected_provider"], "other")
        n_sup = max(1, len(r["supplier"]))
        per_supplier_value = r["value"] / n_sup
        cat_totals[cat]["count"] += 1
        cat_totals[cat]["value"] += r["value"]
        for sup in r["supplier"]:
            cat_totals[cat]["suppliers_value"][sup] += per_supplier_value
        if r["detected_provider"] in HYPERSCALERS:
            hs_totals[r["detected_provider"]]["count"] += 1
            hs_totals[r["detected_provider"]]["value"] += r["value"]

    return {
        "by_category": {
            cat: {
                "count": data["count"],
                "value_eur": data["value"],
                "top_suppliers": dict(data["suppliers_value"].most_common(5)),
            }
            for cat, data in cat_totals.items()
        },
        "by_hyperscaler": {
            p: {"count": data["count"], "value_eur": data["value"]}
            for p, data in hs_totals.items()
        },
    }


def crossref_mxmap(records_dedup: list[dict], mxmap_path: Path) -> dict:
    """Cross-reference ANAC contracts with mxmap.it entities."""
    if not mxmap_path.exists():
        return {"matched": [], "note": "mxmap data not found"}

    with open(mxmap_path) as f:
        raw = json.load(f)
    muni = raw["municipalities"]
    ct_entries = [(bfs, m) for bfs, m in muni.items() if "cloud_tenant_only" in m]

    def normalize(s: str) -> str:
        if not s:
            return ""
        s = s.lower().replace("'", "'").strip()
        for prefix in [
            "comune di ",
            "provincia di ",
            "regione ",
            "ordine ",
            "ordine dei ",
        ]:
            if s.startswith(prefix):
                s = s[len(prefix) :]
        return s

    anac_buyer_idx: dict[str, list[dict]] = {}
    for r in records_dedup:
        bn = normalize(r["buyer_name"])
        if bn:
            anac_buyer_idx.setdefault(bn, []).append(r)

    matched = []
    for bfs, m in ct_entries:
        name = m.get("name", "")
        n = normalize(name)
        if n in anac_buyer_idx:
            for c in anac_buyer_idx[n]:
                matched.append(
                    {
                        "bfs": bfs,
                        "mxmap_name": name,
                        "anac_buyer": c["buyer_name"],
                        "anac_ocid": c["ocid"],
                        "value": c["value"],
                        "supplier": c["supplier"],
                        "detected_provider": c["detected_provider"],
                        "mxmap_cloud_tenant": m.get("cloud_tenant_only"),
                        "regione": m.get("regione", ""),
                    }
                )
    # Dedup per (bfs, ocid)
    seen = set()
    unique = []
    for m in matched:
        k = (m["bfs"], m["anac_ocid"])
        if k not in seen:
            seen.add(k)
            unique.append(m)
    return {"matched": unique, "total_matched": len(unique)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2024, help="ANAC dataset year")
    parser.add_argument(
        "--mxmap", type=Path, help="Optional mxmap data.json for cross-ref"
    )
    args = parser.parse_args()

    # 1. Download
    dataset_path = download_anac(args.year)

    # 2. Process
    records = process_dataset(dataset_path)

    # 3. Save filtered CSV
    csv_path = DATA_DIR / f"anac_{args.year}_cloud_contracts.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ocid",
                "buyer_name",
                "buyer_id",
                "title",
                "desc",
                "supplier",
                "value",
                "currency",
                "date",
                "detected_provider",
            ],
        )
        writer.writeheader()
        for r in records:
            row = dict(r)
            row["supplier"] = "|".join(r["supplier"])
            writer.writerow(row)
    print(f"Saved: {csv_path} ({len(records)} records)")

    # 4. Deduplicate
    records_dedup = deduplicate_by_ocid(records)
    with_value = [r for r in records_dedup if r["value"] > 0]
    print(f"Deduplicated: {len(records_dedup)} OCID, {len(with_value)} with value")

    # 5. Aggregate summary
    summary = aggregate_summary(records_dedup)
    summary["total_ocid"] = len(records_dedup)
    summary["ocid_with_value"] = len(with_value)
    summary["total_value_eur"] = sum(r["value"] for r in with_value)
    summary_path = DATA_DIR / f"anac_{args.year}_cloud_summary_dedup.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Saved: {summary_path}")

    # 6. Print headline
    print("\n=== Headline (post-dedup) ===")
    for cat in [
        "italian_sovereign",
        "hyperscaler_usa",
        "italian_commercial",
        "hyperscaler_eu",
        "mixed",
        "other",
    ]:
        if cat in summary["by_category"]:
            d = summary["by_category"][cat]
            print(f"  {cat}: {d['count']} gare, €{d['value_eur']:,.0f}")
    print("\n=== Hyperscaler USA ===")
    for p in sorted(
        HYPERSCALERS,
        key=lambda x: -summary["by_hyperscaler"].get(x, {}).get("value_eur", 0),
    ):
        d = summary["by_hyperscaler"].get(p, {"count": 0, "value_eur": 0})
        print(f"  {p}: {d['count']} gare, €{d['value_eur']:,.0f}")

    # 7. Cross-ref mxmap
    if args.mxmap:
        xref = crossref_mxmap(records_dedup, args.mxmap)
        xref_path = DATA_DIR / "mxmap_anac_crossref.json"
        xref_path.write_text(json.dumps(xref, indent=2, ensure_ascii=False))
        print("\n=== mxmap.it cross-ref ===")
        print(f"  Matched: {xref['total_matched']} (bfs, ocid pairs)")
        print(f"  Saved: {xref_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
