#!/usr/bin/env python3
"""Calcola i KPI correnti per la pagina Statistiche (statistiche.html) — CLI (I/O).

Logica pura in src/mail_sovereignty/stats.py. Specifica: docs/STATS_KPI.md.
NON-gated: la fotografia attuale si calcola da data.json a ogni build (solo
aggregato del dato che la mappa già mostra). Le serie storiche restano gated al
run #1 (scripts/historicize.py) e qui NON si toccano.

A OGNI build esegue `assert_integrity()`: se i numeri non sono coerenti lo script
fallisce (exit 1) e — via CI smoke / nightly — la cosa non passa inosservata.

Output:
  data/summary/stats_current.json       KPI di oggi (testata, sovranità,
                                         giurisdizione MX, mercato, qualità, segnali)
  data/summary/stats_by_category.json   ISD + breakdown sovranità per cluster IPA

Uso: uv run python3 scripts/build_stats.py [--country IT]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))

# console Windows (cp1252) ⇒ evita UnicodeEncodeError sui print non-ASCII (✓, à…)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from mail_sovereignty.stats import (  # noqa: E402
    assert_integrity,
    compute_by_category,
    compute_current,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--country", default="IT")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "summary")
    args = ap.parse_args()

    d = json.loads(args.data.read_text(encoding="utf-8"))
    muns = d.get("municipalities") or d
    generated = d.get("generated", "")
    entities = [
        v
        for v in muns.values()
        if (v.get("country") or "").upper() == args.country.upper()
    ]
    print(f"=== build_stats ({args.country}): {len(entities)} enti ===")

    current = compute_current(entities)
    by_cat = compute_by_category(entities)

    # rete di sicurezza: i numeri DEVONO essere coerenti, altrimenti exit 1.
    assert_integrity(current, by_cat)
    print("  ✓ integrità KPI verificata")

    current["generated"] = generated
    current["country"] = args.country
    by_cat["generated"] = generated

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "stats_current.json").write_text(
        json.dumps(current, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (args.out_dir / "stats_by_category.json").write_text(
        json.dumps(by_cat, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    h = current["headline"]
    print(f"  ISD (sovranità IT): {h['isd']}%   CLOUD Act: {h['cloud_act_pct']}%")
    print(f"  Coverage: {h['coverage_pct']}%   enti: {h['n_entities']}")
    print(f"  Scritti: {args.out_dir}/stats_current.json + stats_by_category.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
