#!/usr/bin/env python3
"""Genera il report pubblico delle ANOMALIE del dataset (vedi
docs/BOUNCE_VERIFIER_DESIGN.md §11).

Anomalia = ente la cui classificazione è incerta o la cui posta è
irraggiungibile/incoerente. Tre tag (non esclusivi tranne no_mx/geo_unknown):
  - no_mx          : nessun record MX risolto (posta non individuabile)
  - geo_unknown    : MX presente ma IP non geolocalizzato (ASN/paese ignoto)
  - low_confidence : classificato ma con confidenza < 0,60

Produce:
  data/reports/anomalies.json   (consumato da anomalie.html)
  data/reports/anomalies.md     (sintesi leggibile)

Uso: python3 scripts/report_anomalies.py [--country IT]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "data" / "reports"

TYPE_LABEL = {
    "no_mx": "Nessun MX",
    "geo_unknown": "MX non geolocalizzato",
    "low_confidence": "Bassa confidenza (<0,60)",
}


def anomaly_tags(v: dict) -> list[str]:
    tags = []
    if not v.get("mx"):
        tags.append("no_mx")
    elif not v.get("mx_countries"):
        tags.append("geo_unknown")
    conf = v.get("classification_confidence") or 0.0
    if 0.0 < conf < 0.60:
        tags.append("low_confidence")
    return tags


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--country", default="IT")
    args = ap.parse_args()
    target = args.country.upper()

    data = json.loads(args.data.read_text(encoding="utf-8"))
    muns = data.get("municipalities", data)
    enti = [v for v in muns.values() if (v.get("country") or "").upper() == target]
    n = len(enti)

    entries = []
    type_counts: Counter = Counter()
    prov_counts: Counter = Counter()
    for v in enti:
        tags = anomaly_tags(v)
        if not tags:
            continue
        for t in tags:
            type_counts[t] += 1
        prov_counts[v.get("provider", "?")] += 1
        entries.append(
            {
                "name": v.get("name", ""),
                "domain": v.get("domain", ""),
                "provider": v.get("provider", ""),
                "confidence": round(v.get("classification_confidence") or 0.0, 2),
                "anomaly": tags,
                "mx": (v.get("mx") or [None])[0],
                "reason": (v.get("reason") or "")[:140],
            }
        )
    entries.sort(key=lambda e: (e["confidence"], e["domain"]))

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "country": target,
        "total_entities": n,
        "anomalies_total": len(entries),
        "anomalies_pct": round(100 * len(entries) / n, 2) if n else 0,
        "by_type": dict(type_counts),
        "by_type_label": TYPE_LABEL,
        "by_provider": dict(prov_counts.most_common()),
        "classified_but_anomalous": sum(
            1 for e in entries if e["provider"] != "unknown"
        ),
        "entries": entries,
    }

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "anomalies.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    md = [
        f"# Anomalie — Osservatorio Sovranità PA ({target})",
        "",
        f"**{len(entries)} enti anomali** su {n} ({report['anomalies_pct']}%). "
        f"Di cui {report['classified_but_anomalous']} classificati ma anomali.",
        "",
        "| tipo | enti |",
        "|---|---:|",
    ]
    for t, c in type_counts.most_common():
        md.append(f"| {TYPE_LABEL.get(t, t)} | {c} |")
    (REPORTS / "anomalies.md").write_text("\n".join(md), encoding="utf-8")
    print(f"anomalies: {len(entries)}/{n} ({report['anomalies_pct']}%) -> {REPORTS}/anomalies.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
