#!/usr/bin/env python3
"""Genera dist/kpi.json — KPI aggregati pubblici per l'Osservatorio Sovranità Digitale.

Logica pura in src/mail_sovereignty/kpi.py. File statico pubblico (CC BY-SA 4.0)
consumato dal sito Hugo dell'Osservatorio (sostituisce i placeholder —%).
NON-gated: fotografia da data.json a ogni build. Il run_id si legge da
history/runs.jsonl se presente (storicizzazione gated → altrimenti null).

A OGNI build esegue assert_kpi_integrity(): se i numeri non sono coerenti lo
script fallisce (exit 1) → intercettato da CI smoke / nightly.

Uso: uv run python3 scripts/build_kpi.py [--country IT]
URL pubblico: https://fpietrosanti.github.io/mxmap.it/dist/kpi.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))

try:  # console Windows (cp1252) ⇒ evita UnicodeEncodeError sui print non-ASCII
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from mail_sovereignty.kpi import assert_kpi_integrity, build_kpi  # noqa: E402


def last_run_id(history: Path) -> str | None:
    """Ultimo run_id da history/runs.jsonl (None se lo storico non è attivo)."""
    runs = history / "runs.jsonl"
    if not runs.exists():
        return None
    last = None
    for line in runs.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                last = json.loads(line)
            except json.JSONDecodeError:
                continue
    return last.get("run_id") if last else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--country", default="IT")
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "kpi.json")
    args = ap.parse_args()

    d = json.loads(args.data.read_text(encoding="utf-8"))
    muns = d.get("municipalities") or d
    entities = [
        v
        for v in muns.values()
        if (v.get("country") or "").upper() == args.country.upper()
    ]
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = last_run_id(ROOT / "history")
    print(f"=== build_kpi ({args.country}): {len(entities)} enti · run_id={run_id} ===")

    kpi = build_kpi(entities, generated_at=generated_at, run_id=run_id)

    # rete di sicurezza: i numeri DEVONO essere coerenti, altrimenti exit 1.
    assert_kpi_integrity(kpi)
    print("  ✓ integrità kpi.json verificata")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(kpi, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    s = kpi["sovereignty"]
    print(
        f"  IT {s['it']['pct']}% · Extra-UE {s['extra_eu']['pct']}% · "
        f"UE-non-IT {s['eu_non_it']['pct']}% · ? {s['unknown']['pct']}%"
    )
    print(f"  enti={kpi['totals']['n_entities']}  coverage={kpi['totals']['coverage_pct']}%")
    print(f"  Scritto: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
