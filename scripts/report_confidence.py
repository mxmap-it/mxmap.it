#!/usr/bin/env python3
"""Report di una pagina sui livelli di confidence — analitico + aggregato.

Anticipazione del meccanismo bounce: identifica DOVE la classificazione è
meno certa (confidence bassa) così la futura campagna di bounce-probing
può prioritizzare quegli enti.

Legge data.json (dopo compute_confidence.py) e produce:
  data/reports/confidence_report.md    (la pagina leggibile)
  data/reports/confidence_report.json  (machine-readable)

Uso: uv run python3 scripts/report_confidence.py [--country IT]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))
from mail_sovereignty.classification_confidence import ALL_RULE_NAMES  # noqa

REPORTS = ROOT / "data" / "reports"


def bucket(c: float) -> str:
    if c >= 0.90:
        return "0.90-1.00 (molto alta)"
    if c >= 0.80:
        return "0.80-0.89 (alta)"
    if c >= 0.60:
        return "0.60-0.79 (media)"
    if c > 0.0:
        return "0.01-0.59 (bassa)"
    return "0.00 (nulla / unknown)"


BUCKET_ORDER = [
    "0.90-1.00 (molto alta)", "0.80-0.89 (alta)", "0.60-0.79 (media)",
    "0.01-0.59 (bassa)", "0.00 (nulla / unknown)",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--country", default="IT")
    args = ap.parse_args()
    target = args.country.upper()

    data = json.loads(args.data.read_text(encoding="utf-8"))
    muns = data.get("municipalities") or data
    enti = [v for v in muns.values() if (v.get("country") or "").upper() == target]
    n = len(enti)

    confs = [v.get("classification_confidence", 0.0) for v in enti]
    buckets = Counter(bucket(c) for c in confs)
    rule_hist = Counter(v.get("classification_rule", "?") for v in enti)
    jur_hist = Counter(v.get("mx_jurisdiction", "unknown") for v in enti)
    n_override = sum(1 for v in enti if v.get("domestic_mx_override"))

    # confidence media per provider
    by_prov: dict[str, list[float]] = defaultdict(list)
    for v in enti:
        by_prov[v.get("provider", "?")].append(v.get("classification_confidence", 0.0))

    # candidati bounce: confidence bassa ma classificati (non unknown)
    bounce_candidates = [
        v for v in enti
        if 0.0 < v.get("classification_confidence", 0.0) < 0.60
    ]
    # priorità: per provider e per giurisdizione
    bc_by_prov = Counter(v.get("provider") for v in bounce_candidates)
    bc_by_jur = Counter(v.get("mx_jurisdiction") for v in bounce_candidates)

    mean = round(statistics.mean(confs), 3) if confs else 0
    median = round(statistics.median(confs), 3) if confs else 0
    nonzero = [c for c in confs if c > 0]
    mean_nz = round(statistics.mean(nonzero), 3) if nonzero else 0

    # ---- markdown ----
    md = []
    md.append(f"# Report Confidence — Osservatorio Sovranità PA ({target})")
    md.append("")
    md.append("Livelli di confidenza della classificazione email, analitici e "
              "aggregati. Metodologia: regole ESORICS 2026 "
              "(7 regole MX/SPF/DKIM + modello DOMESTIC/FOREIGN via ASN). "
              "Anticipazione per la futura validazione via **bounce-probing**: "
              "gli enti a confidenza bassa sono i candidati prioritari.")
    md.append("")
    md.append(f"**{n} enti** analizzati. Confidenza media **{mean}** "
              f"(mediana {median}; media esclusi unknown {mean_nz}).")
    md.append("")

    # 1. distribuzione aggregata
    md.append("## 1. Distribuzione aggregata della confidenza")
    md.append("")
    md.append("| fascia | enti | % |")
    md.append("|---|---:|---:|")
    for b in BUCKET_ORDER:
        c = buckets.get(b, 0)
        md.append(f"| {b} | {c} | {100*c/n:.1f}% |")
    md.append("")

    # 2. confidence per provider
    md.append("## 2. Confidenza media per provider")
    md.append("")
    md.append("| provider | enti | confidenza media | min | max |")
    md.append("|---|---:|---:|---:|---:|")
    for prov, vals in sorted(by_prov.items(), key=lambda kv: -len(kv[1])):
        if not vals:
            continue
        md.append(f"| {prov} | {len(vals)} | {statistics.mean(vals):.3f} | "
                  f"{min(vals):.2f} | {max(vals):.2f} |")
    md.append("")

    # 3. regole
    md.append("## 3. Regole di confidenza attivate")
    md.append("")
    md.append("| regola | enti | % |")
    md.append("|---|---:|---:|")
    for rule, c in rule_hist.most_common():
        md.append(f"| `{rule}` | {c} | {100*c/n:.1f}% |")
    md.append("")

    # 4. sovranità (DOMESTIC/FOREIGN)
    md.append("## 4. Giurisdizione dell'infrastruttura MX (sovranità)")
    md.append("")
    md.append("Dove risiede fisicamente il server di posta in entrata "
              "(Team Cymru ASN country):")
    md.append("")
    md.append("| giurisdizione | enti | % |")
    md.append("|---|---:|---:|")
    for jur in ("domestic", "mixed", "foreign", "unknown"):
        c = jur_hist.get(jur, 0)
        label = {"domestic": "🇮🇹 Domestica (IT)", "mixed": "Mista (IT + estero)",
                 "foreign": "🌍 Estera", "unknown": "Sconosciuta"}[jur]
        md.append(f"| {label} | {c} | {100*c/n:.1f}% |")
    md.append("")
    md.append(f"**Domestic MX override** applicato a **{n_override}** enti: "
              "classificati cloud (Microsoft/Google) per segnale tenant/DKIM, "
              "ma con MX in entrata self-hosted domestico → riclassificati "
              "`independent` (il tenant cloud riflette Teams/SharePoint, non "
              "la posta).")
    md.append("")

    # 5. anticipazione bounce
    md.append("## 5. Anticipazione bounce-probing: candidati prioritari")
    md.append("")
    md.append(f"**{len(bounce_candidates)} enti** hanno confidenza < 0.60 "
              "pur essendo classificati: sono i casi dove la verifica via "
              "bounce (invio a indirizzo inesistente + analisi NDR) aggiunge "
              "più valore. Priorità per provider:")
    md.append("")
    md.append("| provider | enti a bassa confidenza |")
    md.append("|---|---:|")
    for prov, c in bc_by_prov.most_common(10):
        md.append(f"| {prov} | {c} |")
    md.append("")
    md.append("Per giurisdizione: " + ", ".join(
        f"{k}={v}" for k, v in bc_by_jur.most_common()))
    md.append("")
    md.append("> La validazione bounce confermerà o smentirà queste "
              "classificazioni incerte analizzando il backend MTA reale dal "
              "messaggio di ritorno, chiudendo il gap di confidenza.")
    md.append("")

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "confidence_report.md").write_text("\n".join(md), encoding="utf-8")
    (REPORTS / "confidence_report.json").write_text(json.dumps({
        "country": target, "n": n, "mean": mean, "median": median,
        "mean_nonzero": mean_nz,
        "buckets": dict(buckets), "rules": dict(rule_hist),
        "jurisdiction": dict(jur_hist), "domestic_mx_override": n_override,
        "bounce_candidates": len(bounce_candidates),
        "bounce_by_provider": dict(bc_by_prov),
        "bounce_by_jurisdiction": dict(bc_by_jur),
        "provider_confidence": {
            p: round(statistics.mean(v), 3) for p, v in by_prov.items() if v},
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # stampa a stdout pure
    print("\n".join(md))
    print(f"\n\nScritti: data/reports/confidence_report.md + .json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
