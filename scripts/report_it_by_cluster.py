#!/usr/bin/env python3
"""Citizen-friendly clustered provider-distribution report.

Reads data/it_citizen_clusters.json (the canonical mapping of IPA categories
into clusters citizens recognise — Istruzione, Sanità, PA Centrale, etc.)
and emits per-cluster + per-category distributions.

Output:
  data/reports/it_by_cluster.txt   Human-readable
  data/reports/it_by_cluster.json  Machine-readable (for the frontend)
  data/reports/it_pa_centrale_table.json  Sortable-table source for PA Centrale

Run after preprocess + recover + reclassify_provincial + finalize on a seed
that includes --include-others.

Usage: uv run python3 scripts/report_it_by_cluster.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = DATA / "reports"

CLUSTERS_PATH = DATA / "it_citizen_clusters.json"

PROVIDER_DISPLAY = {
    "microsoft": "Microsoft 365",
    "google": "Google Workspace",
    "aws": "AWS",
    "aruba": "Provider Italiano",
    "register-it": "Provider Italiano",
    "seeweb": "Provider Italiano",
    "infocert": "Provider Italiano",
    "namirial": "Provider Italiano",
    "local-isp": "Provider Italiano",
    "telia": "Provider Italiano",
    "tet": "Provider Italiano",
    "zone": "Provider Italiano",
    "elkdata": "Provider Italiano",
    "regional-public": "Cloud Italiano",
    "pa-contractor-private": "Contractor PA privato",
    "independent": "Infrastruttura autonoma",
    "provincial-shared": "Mail provinciale condivisa",
    "zoho": "Zoho",
    "yandex": "Yandex",
    "unknown": "Sconosciuto",
}

USA_PROVIDERS = {"microsoft", "google", "aws"}


def usa_share(counts: Counter[str], total: int) -> float:
    if total == 0:
        return 0.0
    n_usa = sum(counts.get(p, 0) for p in USA_PROVIDERS)
    return n_usa / total * 100


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    cl_doc = json.loads(CLUSTERS_PATH.read_text(encoding="utf-8"))
    clusters = cl_doc["clusters"]

    seed = json.loads((DATA / "municipalities_it.json").read_text(encoding="utf-8"))
    seed_by_id = {e["id"]: e for e in seed}
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    muns = data["municipalities"]

    # Group IT entries by cluster name
    category_to_cluster: dict[str, str] = {}
    for cluster_key, cluster in clusters.items():
        for cat in cluster.get("categories", []):
            category_to_cluster[cat] = cluster_key

    by_cluster: dict[str, list[dict]] = defaultdict(list)
    by_cat_within_cluster: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    uncategorised: list[dict] = []

    for key, entry in muns.items():
        if entry.get("country") != "IT":
            continue
        eid = entry.get("id") or key
        s = seed_by_id.get(eid)
        if not s:
            continue
        cat = s.get("ipa_codice_categoria") or ""
        cluster_key = category_to_cluster.get(cat)
        merged = dict(entry)
        merged["_seed_name"] = s.get("name", "")
        merged["_seed_region"] = s.get("region", "")
        merged["_ipa_categoria"] = cat
        merged["_ipa_codice"] = s.get("ipa_codice_ipa", "")
        if cluster_key is None:
            uncategorised.append(merged)
            continue
        by_cluster[cluster_key].append(merged)
        by_cat_within_cluster[cluster_key][cat].append(merged)

    # === Build text report ===
    lines: list[str] = []
    n_total = sum(len(v) for v in by_cluster.values()) + len(uncategorised)
    lines.append("=" * 100)
    lines.append("Italian PA — citizen-friendly cluster report")
    lines.append("=" * 100)
    lines.append(f"Total classified IT entries: {n_total}")
    lines.append(f"Distinct clusters:           {len(by_cluster)}")
    if uncategorised:
        lines.append(f"Uncategorised entries:       {len(uncategorised)}")
    lines.append("")

    grand: Counter[str] = Counter()
    for entries in by_cluster.values():
        for e in entries:
            grand[e.get("provider", "unknown")] += 1
    lines.append("=== Aggregate (all clusters) ===")
    lines.append(f"  USA share: {usa_share(grand, n_total):>5.1f}%")
    for p, n in sorted(grand.items(), key=lambda kv: -kv[1]):
        if n == 0:
            continue
        lines.append(f"    {PROVIDER_DISPLAY.get(p, p):<25} {n:>6}  ({n/n_total*100:>5.1f}%)")
    lines.append("")

    # Per cluster
    cluster_order = list(clusters.keys())
    for ck in cluster_order:
        if ck not in by_cluster:
            continue
        entries = by_cluster[ck]
        n = len(entries)
        cluster = clusters[ck]
        counts: Counter[str] = Counter(e.get("provider", "unknown") for e in entries)
        lines.append("=" * 100)
        lines.append(f"## {cluster['label_it']}  (cluster: {ck}, viz={cluster['visualization']})")
        lines.append("=" * 100)
        lines.append(f"  N: {n}    USA share: {usa_share(counts, n):>5.1f}%")
        lines.append(f"  {cluster.get('description_it', '')}")
        lines.append("")
        for p, c in sorted(counts.items(), key=lambda kv: -kv[1]):
            if c == 0:
                continue
            lines.append(f"    {PROVIDER_DISPLAY.get(p, p):<25} {c:>5}  ({c/n*100:>5.1f}%)")
        lines.append("")
        # Per-category breakdown within cluster
        cat_breakdown = by_cat_within_cluster[ck]
        if len(cat_breakdown) > 1:
            lines.append("  --- breakdown per Codice IPA ---")
            for cat in cluster.get("categories", []):
                if cat not in cat_breakdown:
                    continue
                cat_entries = cat_breakdown[cat]
                cn = len(cat_entries)
                cat_counts: Counter[str] = Counter(e.get("provider", "unknown") for e in cat_entries)
                lines.append(f"    {cat:<5} N={cn:<5}  USA={usa_share(cat_counts, cn):>4.1f}%   "
                             f"top: {', '.join(f'{PROVIDER_DISPLAY.get(p, p)}={c}' for p, c in cat_counts.most_common(3))}")
            lines.append("")

    if uncategorised:
        lines.append("=" * 100)
        lines.append("## UNCATEGORISED (categories not in any citizen cluster — bug?)")
        lines.append("=" * 100)
        unc_cats = Counter(e["_ipa_categoria"] for e in uncategorised)
        for cat, n in unc_cats.most_common():
            lines.append(f"  {cat}: {n}")

    out_txt = REPORTS / "it_by_cluster.txt"
    out_txt.write_text("\n".join(lines), encoding="utf-8")
    print(out_txt)

    # === Build JSON report (frontend-ready) ===
    payload = {
        "total": n_total,
        "aggregate": {
            "providers": dict(grand),
            "usa_share_pct": round(usa_share(grand, n_total), 2),
        },
        "clusters": {},
    }
    for ck, cluster in clusters.items():
        if ck not in by_cluster:
            continue
        entries = by_cluster[ck]
        counts = Counter(e.get("provider", "unknown") for e in entries)
        payload["clusters"][ck] = {
            "label_it": cluster["label_it"],
            "label_en": cluster.get("label_en", ""),
            "visualization": cluster["visualization"],
            "n": len(entries),
            "usa_share_pct": round(usa_share(counts, len(entries)), 2),
            "providers": dict(counts),
            "categories": {
                cat: {
                    "n": len(cat_entries),
                    "providers": dict(Counter(e.get("provider", "unknown") for e in cat_entries)),
                }
                for cat, cat_entries in by_cat_within_cluster[ck].items()
            },
        }
    out_json = REPORTS / "it_by_cluster.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_json)

    # === PA Centrale table source (for the table sketch) ===
    pa_centrale = by_cluster.get("pa_centrale", [])
    if pa_centrale:
        rows = []
        for e in pa_centrale:
            cat = e.get("_ipa_categoria", "")
            rows.append({
                "id": e.get("bfs") or e.get("id"),
                "name": e.get("_seed_name") or e.get("name", ""),
                "ipa_categoria": cat,
                "ipa_categoria_label": _category_pretty_label(cat),
                "domain": e.get("domain", ""),
                "provider": e.get("provider", "unknown"),
                "provider_display": PROVIDER_DISPLAY.get(e.get("provider", "unknown"),
                                                         e.get("provider", "unknown")),
                "sovereignty": _sovereignty_tag(e.get("provider", "")),
                "reason": e.get("reason", ""),
                "ipa_codice_ipa": e.get("_ipa_codice", ""),
            })
        rows.sort(key=lambda r: (r["ipa_categoria"], r["name"]))
        out_table = REPORTS / "it_pa_centrale_table.json"
        out_table.write_text(json.dumps({
            "label_it": "PA Centrale",
            "rows": rows,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(out_table)
    return 0


def _category_pretty_label(cat: str) -> str:
    return {
        "C1": "Ministero / PCM / Avvocatura Stato",
        "C2": "Organo Costituzionale",
        "C5": "Autorità Indipendente",
        "C10": "Agenzia Fiscale",
        "C11": "Forze di Polizia",
        "L46": "Azienda Stato Autonomo",
    }.get(cat, cat)


def _sovereignty_tag(provider: str) -> str:
    if provider in USA_PROVIDERS:
        return "🇺🇸 USA (CLOUD Act)"
    if provider == "regional-public":
        return "🇮🇹 Cloud sovrano"
    if provider in {"aruba", "register-it", "seeweb", "infocert", "namirial",
                    "local-isp", "telia", "tet", "zone", "elkdata"}:
        return "🇮🇹 Provider italiano"
    if provider == "pa-contractor-private":
        return "🇮🇹 Contractor privato"
    if provider == "independent":
        return "🇮🇹 Self-hosted"
    if provider == "provincial-shared":
        return "🇮🇹 Mail provinciale condivisa"
    if provider == "unknown":
        return "❓ Sconosciuto"
    return provider


if __name__ == "__main__":
    raise SystemExit(main())
