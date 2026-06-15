#!/usr/bin/env python3
"""Genera report.json — il report «Stato della sovranità digitale della PA» — CLI.

Logica pura in src/mail_sovereignty/report.py. Artefatto statico pubblico
(CC BY-SA 4.0) pubblicato alla ROOT del deploy: il sito dell'Osservatorio lo
**scarica e pesca** (come kpi.json) e lo integra in una pagina Hugo brandizzata.
report.html ne è il rendering consulting di riferimento.

A OGNI build esegue assert_report_integrity (+ assert_kpi_integrity): se i numeri
non sono coerenti lo script fallisce (exit 1) → intercettato da CI smoke / nightly.

Uso: uv run python3 scripts/build_report.py [--country IT]
URL pubblico: https://mxmap.it/report.json
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

from mail_sovereignty.report import build_and_check  # noqa: E402


def last_run_id(history: Path) -> str | None:
    runs = history / "runs.jsonl"
    if not runs.exists():
        return None
    last = None
    for line in runs.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                last = json.loads(line)
            except json.JSONDecodeError:
                continue
    return last.get("run_id") if last else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--country", default="IT")
    ap.add_argument("--out", type=Path, default=ROOT / "report.json")
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
    print(f"=== build_report ({args.country}): {len(entities)} enti · {generated_at} ===")

    report = build_and_check(entities, generated_at=generated_at, run_id=run_id)
    print("  ✓ integrità report.json verificata")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"  Edizione: {report['edition']}  · sezioni: {len(report['sections'])}")
    print(f"  Scritto: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
