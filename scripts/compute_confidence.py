#!/usr/bin/env python3
"""Applica confidence ESORICS + refinement di sovranità a data.json.

Aggiunge a ogni entità:
  classification_confidence  float 0-1   (7-rule ESORICS / DOMESTIC-FOREIGN)
  classification_rule        nome regola
  classification_signals     segnali presenti
  mx_jurisdiction            domestic | foreign | mixed | unknown

E applica il DOMESTIC MX OVERRIDE: gli enti classificati cloud (microsoft/
google/aws) il cui MX NON è del cloud (verdetto da tenant/DKIM, es. MS365
solo per Teams) e con MX domestico vengono riclassificati 'independent'
(la posta in entrata è self-hosted). Il provider cloud originale è
conservato in 'cloud_tenant_only' per la narrazione.

Step pipeline: dopo recovery/cleanup, prima di build_frontend.

Uso: uv run python3 scripts/compute_confidence.py [--country IT]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))
from mail_sovereignty.classification_confidence import (  # noqa
    compute_confidence,
    needs_domestic_mx_override,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--country", default="IT")
    args = ap.parse_args()
    target = args.country.upper()

    data = json.loads(args.data.read_text(encoding="utf-8"))
    muns = data.get("municipalities") or data

    n = 0
    n_override = 0
    conf_buckets: Counter[str] = Counter()
    for v in muns.values():
        if (v.get("country") or "").upper() != target:
            continue

        # 0. idempotenza: se un override precedente è già stato applicato,
        #    ripristina il provider cloud originale prima di rivalutare.
        if v.get("domestic_mx_override") and v.get("cloud_tenant_only"):
            v["provider"] = v["cloud_tenant_only"]
            v.pop("cloud_tenant_only", None)
            v.pop("domestic_mx_override", None)

        # 1. domestic MX override (prima della confidence, così la confidence
        #    riflette il provider riclassificato)
        if needs_domestic_mx_override(v):
            v["cloud_tenant_only"] = v.get("provider")
            v["provider"] = "independent"
            v["domestic_mx_override"] = True
            v["reason"] = (
                f"riclassificato da {v['cloud_tenant_only']}: segnale cloud "
                f"(tenant/DKIM) presente ma MX in entrata self-hosted domestico "
                f"(il tenant cloud riflette uso Teams/SharePoint, non l'email)"
            )
            n_override += 1

        # 2. confidence + jurisdiction
        conf, rule, signals, jur = compute_confidence(v, target_country=target)
        v["classification_confidence"] = conf
        v["classification_rule"] = rule
        v["classification_signals"] = signals
        v["mx_jurisdiction"] = jur

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

    print(f"Confidence + sovranità calcolata su {n} enti {target}")
    print(f"Domestic MX override applicato a {n_override} enti "
          f"(cloud→independent: tenant Teams-only)\n")
    print("Distribuzione confidence:")
    for k in ("alta (>=0.80)", "media (0.60-0.79)", "bassa (<0.60)", "nulla (unknown)"):
        v = conf_buckets.get(k, 0)
        pct = 100 * v / n if n else 0
        print(f"  {k:<22} {v:>6}  ({pct:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
