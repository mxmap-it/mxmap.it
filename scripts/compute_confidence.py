#!/usr/bin/env python3
"""Applica il confidence scoring (port fedele upstream) a data.json.

Aggiunge a ogni entità:
  classification_confidence  float 0-1
  classification_rule        nome regola (es. mx_spf_tenant)
  classification_signals     lista segnali presenti

Step di pipeline: eseguire dopo postprocess/recovery, prima di
build_frontend (così i campi finiscono in data-detail.json per il popup).

Uso:
  uv run python3 scripts/compute_confidence.py [--country IT] [--data data.json]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))
from mail_sovereignty.classification_confidence import compute_confidence  # noqa


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--country", default="", help="limita a un paese (es. IT)")
    args = ap.parse_args()

    data = json.loads(args.data.read_text(encoding="utf-8"))
    muns = data.get("municipalities") or data

    n = 0
    rule_hist: Counter[str] = Counter()
    conf_buckets = Counter()
    for v in muns.values():
        if args.country and (v.get("country") or "").upper() != args.country.upper():
            continue
        conf, rule, signals = compute_confidence(v)
        v["classification_confidence"] = conf
        v["classification_rule"] = rule
        v["classification_signals"] = signals
        rule_hist[rule] += 1
        # bucket per istogramma
        if conf >= 0.80:
            conf_buckets["alta (>=0.80)"] += 1
        elif conf >= 0.60:
            conf_buckets["media (0.60-0.79)"] += 1
        elif conf > 0.0:
            conf_buckets["bassa (<0.60)"] += 1
        else:
            conf_buckets["nulla (unknown)"] += 1
        n += 1

    args.data.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")

    print(f"Confidence calcolata su {n} entità"
          f"{' (' + args.country + ')' if args.country else ''}\n")
    print("Distribuzione confidence:")
    for k in ("alta (>=0.80)", "media (0.60-0.79)", "bassa (<0.60)", "nulla (unknown)"):
        v = conf_buckets.get(k, 0)
        pct = 100 * v / n if n else 0
        print(f"  {k:<22} {v:>6}  ({pct:.1f}%)")
    print("\nRegole più frequenti (top 12):")
    for rule, cnt in rule_hist.most_common(12):
        print(f"  {rule:<18} {cnt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
