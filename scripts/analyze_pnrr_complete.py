#!/usr/bin/env python3
"""Analyze PNRR PA Digitale 2026 complete dataset (altri enti + comuni + scuole).

Downloads the three PNRR open-data files from the teamdigitale GitHub
repo, computes the cloud spending breakdown per Misura per PA tier, and
cross-references with mxmap.it entities.

Output:
  - data/pnrr/pnrr_complete_summary.json (machine-readable)
  - reports/pnrr_cloud_completo.md (politically spendable)

Usage:
    .venv/bin/python scripts/analyze_pnrr_complete.py
"""

from __future__ import annotations

import csv
import json
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "pnrr"
MXMAP_PATH = REPO_ROOT / "data.json"

GITHUB_BASE = (
    "https://github.com/teamdigitale/padigitale2026-opendata/raw/refs/heads/main/data"
)
FILES = {
    "altrienti": "candidature_altrienti_finanziate.csv",
    "comuni": "candidature_comuni_finanziate.csv",
    "scuole": "candidature_scuole_finanziate.csv",
}


def normalize_misura(avviso: str) -> str:
    if "1.1" in avviso and "1.2" not in avviso:
        return "1.1_Infrastrutture_digitali"
    elif "1.2" in avviso:
        return "1.2_Abilitazione_cloud"
    elif "1.3" in avviso:
        return "1.3_PDND"
    elif "1.4" in avviso:
        return "1.4_Servizi_digitali"
    elif "1.5" in avviso:
        return "1.5_Cybersecurity"
    elif "1.6" in avviso:
        return "1.6_Digital_skills"
    return "altro"


def parse_amount(s: str | None) -> float:
    try:
        return float(s) if s else 0.0
    except (ValueError, TypeError):
        return 0.0


def download_file(key: str) -> Path:
    filename = FILES[key]
    target = DATA_DIR / filename
    if target.exists() and target.stat().st_size > 10_000:
        print(f"  Using cached: {target}")
        return target
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    url = f"{GITHUB_BASE}/{filename}"
    print(f"  Downloading {url}...")
    urllib.request.urlretrieve(url, target)
    print(f"  Downloaded: {target} ({target.stat().st_size:,} bytes)")
    return target


def load_csv(path: Path) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def normalize_name(s: str) -> str:
    if not s:
        return ""
    s = s.lower().replace("'", "'").strip()
    for prefix in ["comune di ", "provincia di ", "regione ", "ordine ", "ordine dei "]:
        if s.startswith(prefix):
            s = s[len(prefix) :]
    return s


def build_mxmap_index() -> dict[str, dict]:
    """Build {normalized_name: entry} index for mxmap.it."""
    if not MXMAP_PATH.exists():
        return {}
    with open(MXMAP_PATH) as f:
        raw = json.load(f)
    idx = {}
    for bfs, m in raw["municipalities"].items():
        n = normalize_name(m.get("name", ""))
        if n:
            idx[n] = {"bfs": bfs, **m}
    return idx


def main() -> int:
    print("=== PNRR PA Digitale 2026 — Complete Dataset Analysis ===\n")

    # 1. Download
    print("Step 1: Download datasets")
    datasets = {}
    for key in FILES:
        path = download_file(key)
        datasets[key] = load_csv(path)
        print(f"  {key}: {len(datasets[key]):,} records")

    # 2. Breakdown per Misura
    print("\nStep 2: Breakdown per Misura")
    misure_breakdown: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    importi_per_misura: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for key, records in datasets.items():
        for r in records:
            m = normalize_misura(r.get("avviso", ""))
            misure_breakdown[m][key] += 1
            importi_per_misura[m][key] += parse_amount(r.get("importo_finanziamento"))

    for m in sorted(misure_breakdown):
        cnt = misure_breakdown[m]
        imp = importi_per_misura[m]
        total_cnt = sum(cnt.values())
        total_imp = sum(imp.values())
        print(
            f"  {m}: {total_cnt:,} record | €{total_imp:,.0f}"
            f" (altri={cnt['altrienti']}, comuni={cnt['comuni']}, scuole={cnt['scuole']})"
        )

    # 3. Cloud-only (1.1 + 1.2)
    print("\nStep 3: Cloud-only (Misura 1.1 + 1.2) totali")
    cloud_totals: dict[str, dict] = {}
    for key, records in datasets.items():
        cloud_recs = [
            r
            for r in records
            if "1.1" in r.get("avviso", "") or "1.2" in r.get("avviso", "")
        ]
        importo = sum(parse_amount(r.get("importo_finanziamento")) for r in cloud_recs)
        cloud_totals[key] = {"count": len(cloud_recs), "importo_eur": importo}
        print(f"  {key}: {len(cloud_recs):,} record, €{importo:,.0f}")

    # 4. Per regione
    print("\nStep 4: Cloud per regione")
    regione_totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"comuni": 0.0, "altri": 0.0, "scuole": 0.0}
    )
    regione_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"comuni": 0, "altri": 0, "scuole": 0}
    )
    # Mapping: key → friendly name
    KEY_TO_FRIENDLY = {"altrienti": "altri", "comuni": "comuni", "scuole": "scuole"}
    for key in datasets:
        friendly = KEY_TO_FRIENDLY[key]
        for r in datasets[key]:
            if "1.1" not in r.get("avviso", "") and "1.2" not in r.get("avviso", ""):
                continue
            reg = r.get("regione", "Unknown")
            regione_totals[reg][friendly] += parse_amount(
                r.get("importo_finanziamento")
            )
            regione_counts[reg][friendly] += 1

    # 5. Cross-ref mxmap.it
    print("\nStep 5: Cross-ref con mxmap.it")
    mxmap_idx = build_mxmap_index()
    matched: dict[str, dict] = {
        "comuni": {"count": 0, "importo_eur": 0.0},
        "altri": {"count": 0, "importo_eur": 0.0},
        "scuole": {"count": 0, "importo_eur": 0.0},
    }
    for key, records in datasets.items():
        friendly = KEY_TO_FRIENDLY[key]
        for r in records:
            if "1.1" not in r.get("avviso", "") and "1.2" not in r.get("avviso", ""):
                continue
            n = normalize_name(r.get("ente", ""))
            if n in mxmap_idx:
                matched[friendly]["count"] += 1
                matched[friendly]["importo_eur"] += parse_amount(
                    r.get("importo_finanziamento")
                )
    total_matched = sum(m["count"] for m in matched.values())
    total_eur = sum(m["importo_eur"] for m in matched.values())
    print(f"  Enti PNRR cloud matchati: {total_matched:,}")
    print(f"  Importo totale: €{total_eur:,.0f}")
    for key, m in matched.items():
        print(f"    {key}: {m['count']:,} enti, €{m['importo_eur']:,.0f}")

    # 6. Top 20 comuni per importo cloud
    print("\nStep 6: Top 20 Comuni per finanziamento cloud")
    comuni_cloud = [
        r
        for r in datasets["comuni"]
        if ("1.1" in r.get("avviso", "") or "1.2" in r.get("avviso", ""))
        and parse_amount(r.get("importo_finanziamento")) > 0
    ]
    for r in sorted(
        comuni_cloud, key=lambda x: -parse_amount(x.get("importo_finanziamento"))
    )[:20]:
        print(
            f"  €{parse_amount(r.get('importo_finanziamento')):>10,.0f}  "
            f"{r.get('ente', '')[:35]:35s} ({r.get('regione', '')[:20]})"
        )

    # 7. Save summary
    summary = {
        "datasets": {
            key: {
                "count": len(records),
                "size_bytes": (DATA_DIR / FILES[key]).stat().st_size,
            }
            for key, records in datasets.items()
        },
        "totale_pa_records": sum(len(r) for r in datasets.values()),
        "cloud_pnrr_importi": {
            key: {
                "count": data["count"],
                "importo_eur": data["importo_eur"],
            }
            for key, data in cloud_totals.items()
        },
        "cloud_pnrr_totale_eur": sum(d["importo_eur"] for d in cloud_totals.values()),
        "per_regione": {
            reg: {
                "importo_eur": regione_totals[reg],
                "count": regione_counts[reg],
            }
            for reg in regione_totals
        },
        "crossref_mxmap": {
            **{k: v for k, v in matched.items()},
            "totale_matched": total_matched,
            "totale_eur_matched": total_eur,
        },
        "misure_breakdown": {
            m: {
                "counts": dict(misure_breakdown[m]),
                "importi_eur": dict(importi_per_misura[m]),
            }
            for m in misure_breakdown
        },
    }
    out_path = DATA_DIR / "pnrr_complete_summary.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
