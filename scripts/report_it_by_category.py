#!/usr/bin/env python3
"""Per-IndicePA-category provider distribution report.

Slices the classified IT entries in data.json by IndicePA category
(Codice_Categoria), so we can see digital-sovereignty patterns across the
~50 distinct categories of Italian public administrations beyond just the
territorial four (regioni / province / CM / comuni).

Output:
  data/reports/it_by_category.txt   Human-readable per-category breakdown
  data/reports/it_by_category.json  Machine-readable

Run AFTER scripts/fetch_indicepa.py --include-others + preprocess +
recover/reclassify/finalize. Categories without DNS data appear with
zero rows but are still listed so we know which were collected.

Usage: uv run python3 scripts/report_it_by_category.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = DATA / "reports"

# IPA Tipologia clusters from our analysis. Used to group categories into
# digestible report sections.
TIPOLOGIA_CLUSTERS: dict[str, list[str]] = {
    "Territorial (Tier 1)": ["L4", "L5", "L45", "L6"],
    "Education": ["L33", "L17", "L43", "L15", "L28"],
    "Healthcare": ["L7", "L8", "L22", "C12"],
    "Central state / Authorities": ["C1", "C2", "C5", "C10", "C11", "L46"],
    "Professional orders / Chambers": ["C14", "L35", "C13"],
    "Local consortia & sub-municipal": ["L18", "L36", "L12", "L1", "L24", "L47", "L20"],
    "Welfare / Housing": ["L34", "L39"],
    "Environment & Territory": ["L38", "L40", "L42", "L44"],
    "Culture": ["L31", "L16", "C7"],
    "Research": ["C8", "L13", "L21"],
    "Transport / Ports": ["L11"],
    "Public services / SOEs": ["L37", "S01", "S01G", "C3"],
    "Agencies (regional)": ["L2", "L19", "L10"],
    "Procurement (Stazioni Appaltanti)": ["SA", "SAG"],
    "Pension / Social security": ["C16", "C17"],
}

# IPA category descriptions (subset — used for the category-row label)
CATEGORY_LABELS: dict[str, str] = {
    "L4": "Regioni e Prov. Autonome", "L5": "Province", "L45": "Città Metropolitane",
    "L6": "Comuni",
    "L33": "Istituti Istruzione Statale", "L17": "Università", "L43": "AFAM",
    "L15": "Diritto allo Studio Univ.", "L28": "Consorzi Interuniversitari",
    "L7": "ASL", "L8": "Aziende Ospedaliere/IRCCS", "L22": "Agenzie Reg. Sanitarie",
    "C12": "Istituti Zooprofilattici",
    "C1": "Presidenza/Ministeri", "C2": "Organi Costituzionali",
    "C5": "Autorità Indipendenti", "C10": "Agenzie Fiscali",
    "C11": "Forze Polizia", "L46": "Aziende Stato Autonomo",
    "C14": "Federazioni/Ordini/Collegi", "L35": "Camere di Commercio",
    "C13": "ACI Federati",
    "L18": "Unioni Comuni", "L36": "Consorzi Amm.ni Locali",
    "L12": "Comunità Montane", "L1": "Altri Enti Locali",
    "L24": "Consorzi Bacino Imbrifero", "L47": "Commissari Straordinari",
    "L20": "Rappresentanza Negoziale",
    "L34": "Aziende Servizi alla Persona", "L39": "Edilizia Residenziale",
    "L38": "Parchi/Aree Naturali", "L40": "Autorità di Bacino",
    "L42": "Consorzi Sviluppo Industriale", "L44": "Enti Idrici/Rifiuti",
    "L31": "Teatri Stabili", "L16": "Fondazioni Lirico-Sinfoniche",
    "C7": "Servizi Ricreativi/Culturali",
    "C8": "Enti di Ricerca", "L13": "Sviluppo Agricolo",
    "L21": "Erogazioni Agricoltura",
    "L11": "Autorità Portuali",
    "L37": "Gestori Pubblici Servizi", "S01": "Soc. Conto Econ. Consolidato",
    "S01G": "Gestori Pubblici Servizi (S01G)", "C3": "Enti Pubblici Non Economici",
    "L2": "Agenzie Reg. Formazione/Ricerca", "L19": "Agenzie Reg. Lavoro",
    "L10": "Agenzie Turismo",
    "SA": "Stazioni Appaltanti", "SAG": "Stazioni Appaltanti GPS",
    "C17": "Previdenza Privata", "C16": "Previdenza Pubblica",
}

PROVIDER_ORDER = [
    "microsoft", "google", "aws",
    "aruba", "register-it", "seeweb", "infocert", "namirial",
    "regional-public", "pa-contractor-private", "provincial-shared",
    "local-isp", "independent",
    "zoho", "yandex", "unknown",
]


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    seed = json.loads((DATA / "municipalities_it.json").read_text(encoding="utf-8"))
    seed_by_id = {e["id"]: e for e in seed}
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    muns = data["municipalities"]

    # Group IT entries by IPA category from seed
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for key, entry in muns.items():
        if entry.get("country") != "IT":
            continue
        eid = entry.get("id") or key
        seed_entry = seed_by_id.get(eid)
        if not seed_entry:
            continue
        cat = seed_entry.get("ipa_codice_categoria") or ""
        if not cat:
            continue
        merged = dict(entry)
        merged["_seed_name"] = seed_entry.get("name", "")
        by_cat[cat].append(merged)

    # Build report
    lines: list[str] = []
    lines.append("=" * 100)
    lines.append("IT public administrations — provider distribution by IndicePA category")
    lines.append("=" * 100)
    n_total = sum(len(v) for v in by_cat.values())
    lines.append(f"Total classified IT entries: {n_total}")
    lines.append(f"Distinct IPA categories:     {len(by_cat)}")
    lines.append("")

    # Aggregate across all
    grand: Counter[str] = Counter()
    for entries in by_cat.values():
        for e in entries:
            grand[e.get("provider", "unknown")] += 1
    lines.append("=== Aggregate across ALL Italian PA categories ===")
    for p in PROVIDER_ORDER + sorted(set(grand) - set(PROVIDER_ORDER)):
        n = grand.get(p, 0)
        if n == 0:
            continue
        pct = (n / n_total * 100) if n_total else 0.0
        lines.append(f"  {p:<25} {n:>6}  ({pct:>5.1f}%)")
    lines.append("")
    # USA vs Italy aggregate
    usa = grand.get("microsoft", 0) + grand.get("google", 0) + grand.get("aws", 0)
    ita = n_total - usa - grand.get("unknown", 0) - grand.get("zoho", 0) - grand.get("yandex", 0)
    lines.append("=== USA vs Italy ===")
    lines.append(f"  USA hyperscalers:    {usa:>6}  ({(usa/n_total*100):>5.1f}%)" if n_total else "")
    lines.append(f"  Italy / EU / IT:     {ita:>6}  ({(ita/n_total*100):>5.1f}%)" if n_total else "")
    lines.append("")

    # Per-cluster, then per-category
    seen_cats: set[str] = set()
    for cluster_name, cats in TIPOLOGIA_CLUSTERS.items():
        present = [c for c in cats if c in by_cat]
        if not present:
            continue
        lines.append("=" * 100)
        lines.append(f"# {cluster_name}")
        lines.append("=" * 100)
        for cat in present:
            seen_cats.add(cat)
            entries = by_cat[cat]
            label = CATEGORY_LABELS.get(cat, cat)
            n = len(entries)
            counts: Counter[str] = Counter(e.get("provider", "unknown") for e in entries)
            usa_c = counts.get("microsoft", 0) + counts.get("google", 0) + counts.get("aws", 0)
            usa_pct = (usa_c / n * 100) if n else 0.0
            lines.append(f"\n  {cat:<5} {label:<40} N={n:>5}   USA share={usa_pct:>4.1f}%")
            for p in PROVIDER_ORDER:
                v = counts.get(p, 0)
                if v == 0:
                    continue
                pct = (v / n * 100) if n else 0.0
                lines.append(f"      {p:<25} {v:>5}  ({pct:>5.1f}%)")
        lines.append("")

    # Anything not in known clusters
    leftover = sorted(set(by_cat) - seen_cats)
    if leftover:
        lines.append("=" * 100)
        lines.append("# Other categories")
        lines.append("=" * 100)
        for cat in leftover:
            entries = by_cat[cat]
            n = len(entries)
            counts = Counter(e.get("provider", "unknown") for e in entries)
            label = CATEGORY_LABELS.get(cat, cat)
            usa_c = counts.get("microsoft", 0) + counts.get("google", 0) + counts.get("aws", 0)
            usa_pct = (usa_c / n * 100) if n else 0.0
            lines.append(f"\n  {cat:<5} {label:<40} N={n:>5}   USA share={usa_pct:>4.1f}%")
            for p, v in counts.most_common():
                pct = (v / n * 100) if n else 0.0
                lines.append(f"      {p:<25} {v:>5}  ({pct:>5.1f}%)")

    out_txt = REPORTS / "it_by_category.txt"
    out_txt.write_text("\n".join(lines), encoding="utf-8")
    print(out_txt)

    # JSON output
    out_json = REPORTS / "it_by_category.json"
    payload = {
        "total": n_total,
        "aggregate": dict(grand),
        "per_category": {},
    }
    for cat, entries in by_cat.items():
        counts = Counter(e.get("provider", "unknown") for e in entries)
        payload["per_category"][cat] = {
            "label": CATEGORY_LABELS.get(cat, cat),
            "n": len(entries),
            "providers": dict(counts),
        }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
