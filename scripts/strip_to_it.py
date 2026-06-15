#!/usr/bin/env python3
"""Mantiene in data.json SOLO gli enti italiani (country == IT).

Il progetto attivo è l'Osservatorio italiano: `data.json` deve contenere **solo
l'Italia**, per non confondersi con i dati del fork mondiale (166 paesi). Questo
passo rende data.json IT-only e ricalcola `total` + `counts` (distribuzione
provider). Idempotente.

Uso: uv run python3 scripts/strip_to_it.py [--keep IT]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--keep", default="IT")
    args = ap.parse_args()

    d = json.loads(args.data.read_text(encoding="utf-8"))
    muns = d.get("municipalities")
    if muns is None:
        print("data.json senza chiave 'municipalities': niente da fare")
        return 0

    keep = args.keep.upper()
    before = len(muns)
    kept = {
        k: v for k, v in muns.items() if (v.get("country") or "").upper() == keep
    }
    d["municipalities"] = kept
    d["total"] = len(kept)
    d["counts"] = dict(
        Counter(v.get("provider", "unknown") for v in kept.values()).most_common()
    )

    args.data.write_text(
        json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(
        f"strip_to_it: {before} → {len(kept)} enti "
        f"(rimossi {before - len(kept)} non-{keep})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
