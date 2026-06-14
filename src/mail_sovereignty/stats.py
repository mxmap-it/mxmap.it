"""KPI correnti dell'Osservatorio (pagina Statistiche) — logica pura, testabile.

Vedi docs/STATS_KPI.md. Calcola la *fotografia attuale* dei KPI di sovranità da
data.json (non-gated: solo aggregato del dato che la mappa già mostra). Riusa la
classificazione di sovranità di `historicize` (sovereignty_of/material_row):
unica fonte di verità, così Statistiche e storicizzazione concordano.

`assert_integrity()` verifica che i numeri prodotti siano coerenti (somme,
quote, ISD, copertura, segmentazione): chiamata a ogni build e nei test, è la
garanzia che "non ci siano errori nei KPI". L'I/O sta nella CLI
scripts/build_stats.py; qui solo logica pura.
"""

from __future__ import annotations

from collections import Counter

from mail_sovereignty.historicize import PROVIDER_DISPLAY, material_row

# Bucket di sovranità (vedi historicize.sovereignty_of). Gruppi per l'ISD.
B_CLOUD_ACT = "USA (CLOUD Act)"
B_ALTRI_EST = "Altri provider esteri"
B_SOVRANO = "Italia — Cloud sovrano"
B_COMMERC = "Italia — Provider commerciali"
B_AUTONOMO = "Italia — Infrastruttura autonoma"
B_UNKNOWN = "Sconosciuto"

ITA_BUCKETS = (B_SOVRANO, B_COMMERC, B_AUTONOMO)
EST_BUCKETS = (B_CLOUD_ACT, B_ALTRI_EST)
# ordine di presentazione (dal più sovrano al meno)
SOV_ORDER = (B_SOVRANO, B_COMMERC, B_AUTONOMO, B_ALTRI_EST, B_CLOUD_ACT, B_UNKNOWN)
SOV_GROUP = {
    **{b: "ITA" for b in ITA_BUCKETS},
    **{b: "EST" for b in EST_BUCKETS},
    B_UNKNOWN: "ND",
}

# Cluster per codice categoria del bfs IT (IT-{cat}-{ipa}). I codici sono quelli
# EFFETTIVI del seed del progetto (COM/PRO/CMM/REG per i territoriali, non i
# codici IndicePA L6/L5/...): verificati sui 54 codici presenti in data.json.
# Copertura totale → nessun "other" (assert_integrity lo impone).
CLUSTERS: list[tuple[str, str, list[str]]] = [
    (
        "territorial",
        "Enti territoriali (Comuni, Province, Città metrop., Regioni)",
        ["COM", "PRO", "CMM", "REG", "L4", "L5", "L45", "L6"],
    ),
    (
        "education",
        "Istruzione (Scuole, Università, AFAM)",
        ["L33", "L43", "L17", "L15", "L28"],
    ),
    ("healthcare", "Sanità (ASL, Aziende ospedaliere)", ["L7", "L8", "L22", "C12"]),
    (
        "central",
        "Stato centrale, Ministeri e Autorità",
        ["C1", "C2", "C5", "C10", "C11", "L46"],
    ),
    ("orders", "Ordini professionali, Camere di commercio, ACI", ["C14", "L35", "C13"]),
    (
        "consortia",
        "Consorzi, Unioni di Comuni, Comunità montane",
        ["L18", "L1", "L36", "L12", "CONS", "L24", "L42", "L47", "L20"],
    ),
    ("soe", "Società partecipate e fondazioni pubbliche", ["L37", "S01", "S01G"]),
    ("welfare", "Welfare, ASP/IPAB e case popolari", ["L34", "L39"]),
    ("environment", "Ambiente, parchi e bacini", ["L38", "L44", "L40"]),
    ("agencies", "Agenzie regionali", ["L2", "L19", "L10", "L21"]),
    ("procurement", "Stazioni appaltanti", ["SA", "SAG"]),
    ("pension", "Previdenza e casse", ["C16", "C17", "C7", "C3"]),
    ("culture", "Cultura (teatri, fondazioni)", ["L31", "L16"]),
    ("research", "Ricerca", ["C8", "L13"]),
    ("transport", "Trasporti e porti", ["L11"]),
]
CAT_TO_CLUSTER = {cat: key for key, _label, cats in CLUSTERS for cat in cats}
CLUSTER_LABEL = {key: label for key, label, _cats in CLUSTERS}

# tolleranza per i confronti su percentuali (arrotondamento a 2 decimali)
_EPS = 0.05


def _pct(n: int, d: int) -> float:
    return round(100 * n / d, 2) if d else 0.0


def _sovereignty_breakdown(rows: list[dict]) -> tuple[list[dict], int]:
    """Conteggi per bucket (ordine canonico) + n_classificati (esclusi unknown)."""
    counts = Counter(r["sovereignty"] for r in rows)
    n_class = sum(c for b, c in counts.items() if b != B_UNKNOWN)
    breakdown = []
    for bucket in SOV_ORDER:
        c = counts.get(bucket, 0)
        if c == 0 and bucket == B_UNKNOWN:
            continue  # mostra unknown solo se presente
        breakdown.append(
            {
                "bucket": bucket,
                "group": SOV_GROUP[bucket],
                "count": c,
                # quota sui classificati (unknown escluso); unknown sul totale
                "pct": _pct(c, n_class) if bucket != B_UNKNOWN else _pct(c, len(rows)),
            }
        )
    return breakdown, n_class


def _isd(rows: list[dict], n_class: int) -> float:
    """Indice di Sovranità Digitale: % enti in giurisdizione IT sui classificati."""
    ita = sum(1 for r in rows if r["sovereignty"] in ITA_BUCKETS)
    return _pct(ita, n_class)


def compute_current(entities: list[dict]) -> dict:
    """KPI correnti su tutto il campo (entità raw di data.json)."""
    rows = [material_row(e) for e in entities]
    n = len(rows)
    breakdown, n_class = _sovereignty_breakdown(rows)
    isd = _isd(rows, n_class)
    cloud_act = sum(1 for r in rows if r["sovereignty"] == B_CLOUD_ACT)

    jur = Counter(r["jurisdiction"] for r in rows)
    jurisdiction = [
        {"key": k, "count": jur.get(k, 0), "pct": _pct(jur.get(k, 0), n)}
        for k in ("domestic", "foreign", "mixed", "unknown")
    ]

    prov = Counter(r["provider"] for r in rows)
    n_prov_class = sum(c for p, c in prov.items() if p != "unknown")
    providers = [
        {
            "provider": p,
            "display": PROVIDER_DISPLAY.get(p, "Sconosciuto"),
            "count": c,
            "pct": _pct(c, n_prov_class) if p != "unknown" else _pct(c, n),
        }
        for p, c in prov.most_common()
    ]
    shares = sorted(
        (_pct(c, n_prov_class) for p, c in prov.items() if p != "unknown"),
        reverse=True,
    )
    top3 = round(sum(shares[:3]), 2)
    hhi = round(sum(s * s for s in shares), 1)  # 0..10000

    confs = [r["confidence"] for r in rows if isinstance(r["confidence"], int | float)]
    mean_conf = round(sum(confs) / len(confs), 4) if confs else 0.0
    bands: Counter = Counter()
    for c in confs:
        bands["alta" if c >= 0.8 else "media" if c >= 0.5 else "bassa"] += 1
    confidence_bands = [
        {"band": b, "count": bands.get(b, 0), "pct": _pct(bands.get(b, 0), len(confs))}
        for b in ("alta", "media", "bassa")
    ]

    has_mx = sum(1 for e in entities if e.get("mx"))
    has_spf = sum(1 for e in entities if e.get("spf"))
    has_dkim = sum(1 for e in entities if e.get("dkim"))
    has_gw = sum(1 for e in entities if e.get("gateway"))

    return {
        "n_entities": n,
        "n_classified": n_class,
        "coverage_pct": _pct(n_class, n),
        "mean_confidence": mean_conf,
        "isd": isd,
        "headline": {
            "isd": isd,
            "cloud_act_pct": _pct(cloud_act, n_class),
            "coverage_pct": _pct(n_class, n),
            "n_entities": n,
        },
        "sovereignty": breakdown,
        "jurisdiction": jurisdiction,
        "providers": providers,
        "market": {"top3_pct": top3, "hhi": hhi},
        "confidence_bands": confidence_bands,
        "signals": {
            "mx_pct": _pct(has_mx, n),
            "spf_pct": _pct(has_spf, n),
            "dkim_pct": _pct(has_dkim, n),
            "gateway_pct": _pct(has_gw, n),
        },
    }


def compute_by_category(entities: list[dict]) -> dict:
    """ISD + breakdown sovranità per cluster di categoria IPA."""
    rows_by_cluster: dict[str, list[dict]] = {}
    for e in entities:
        r = material_row(e)
        cluster = CAT_TO_CLUSTER.get(r["cat"], "other")
        rows_by_cluster.setdefault(cluster, []).append(r)

    clusters = []
    for key, label, _cats in [*CLUSTERS, ("other", "Altre categorie", [])]:
        rows = rows_by_cluster.get(key)
        if not rows:
            continue
        breakdown, n_class = _sovereignty_breakdown(rows)
        cloud_act = sum(1 for r in rows if r["sovereignty"] == B_CLOUD_ACT)
        clusters.append(
            {
                "cluster": key,
                "label": label,
                "n": len(rows),
                "n_classified": n_class,
                "isd": _isd(rows, n_class),
                "cloud_act_pct": _pct(cloud_act, n_class),
                "sovereignty": breakdown,
            }
        )
    clusters.sort(key=lambda c: c["n"], reverse=True)
    return {"clusters": clusters}


def assert_integrity(
    current: dict, by_cat: dict, *, max_other_pct: float = 1.0
) -> None:
    """Verifica la coerenza interna dei KPI. Solleva ValueError elencando TUTTE
    le violazioni trovate. È la rete di sicurezza "i numeri non devono sbagliare":
    eseguita a ogni build (CLI) e nei test."""
    errs: list[str] = []

    def close(a: float, b: float, eps: float = _EPS) -> bool:
        return abs(a - b) <= eps

    n = current["n_entities"]
    sov = current["sovereignty"]
    sov_total = sum(s["count"] for s in sov)
    n_class = current["n_classified"]
    unknown = sum(s["count"] for s in sov if s["bucket"] == B_UNKNOWN)
    ita = sum(s["count"] for s in sov if s["group"] == "ITA")
    cloud = sum(s["count"] for s in sov if s["bucket"] == B_CLOUD_ACT)

    # 1. i bucket di sovranità coprono esattamente tutti gli enti
    if sov_total != n:
        errs.append(f"sovranità: somma bucket {sov_total} != n_entities {n}")
    # 2. classificati = totale - unknown
    if n_class != n - unknown:
        errs.append(f"n_classified {n_class} != n - unknown {n - unknown}")
    # 3. coverage = classificati/totale
    if not close(current["coverage_pct"], _pct(n_class, n)):
        errs.append(f"coverage_pct {current['coverage_pct']} != {_pct(n_class, n)}")
    # 4. ISD = quota ITA sui classificati (e coerente in headline)
    if not close(current["isd"], _pct(ita, n_class)):
        errs.append(f"isd {current['isd']} != {_pct(ita, n_class)} (ITA/classificati)")
    if not close(current["headline"]["isd"], current["isd"]):
        errs.append("headline.isd != isd")
    # 5. CLOUD Act headline coerente
    if not close(current["headline"]["cloud_act_pct"], _pct(cloud, n_class)):
        errs.append("headline.cloud_act_pct incoerente")
    # 6. quote sovranità non-unknown sommano a ~100 sui classificati
    sov_pct = sum(s["pct"] for s in sov if s["bucket"] != B_UNKNOWN)
    if n_class and not close(sov_pct, 100.0, 0.2):
        errs.append(f"somma quote sovranità (classificati) = {sov_pct}, atteso ~100")
    # 7. giurisdizione MX copre tutti gli enti
    jur_total = sum(j["count"] for j in current["jurisdiction"])
    if jur_total != n:
        errs.append(f"giurisdizione: somma {jur_total} != n_entities {n}")
    # 8. provider coprono tutti gli enti
    prov_total = sum(p["count"] for p in current["providers"])
    if prov_total != n:
        errs.append(f"provider: somma {prov_total} != n_entities {n}")
    # 9. bande di confidenza sommano agli enti con confidenza (<= n)
    band_total = sum(b["count"] for b in current["confidence_bands"])
    if band_total > n:
        errs.append(f"bande confidenza: somma {band_total} > n_entities {n}")
    # 10. tutte le percentuali in [0, 100]; nessun None/NaN nei numeri chiave
    for s in sov:
        if not 0 <= s["pct"] <= 100 + _EPS:
            errs.append(f"quota fuori range: {s['bucket']} = {s['pct']}")
    for k in ("isd", "coverage_pct", "mean_confidence"):
        v = current.get(k)
        if v is None or v != v:  # None o NaN
            errs.append(f"valore non valido: {k} = {v}")

    # 11. segmentazione: ogni cluster somma agli enti; il totale copre tutto il campo
    clusters = by_cat.get("clusters", [])
    cat_total = 0
    for c in clusters:
        cl_sov = sum(s["count"] for s in c["sovereignty"])
        if cl_sov != c["n"]:
            errs.append(
                f"cluster {c['cluster']}: somma sovranità {cl_sov} != n {c['n']}"
            )
        cat_total += c["n"]
    if cat_total != n:
        errs.append(f"segmentazione: somma cluster {cat_total} != n_entities {n}")
    # 12. nessuna categoria non mappata oltre la soglia (codici nuovi nel seed)
    other = next((c for c in clusters if c["cluster"] == "other"), None)
    if other and _pct(other["n"], n) > max_other_pct:
        errs.append(
            f"cluster 'other' troppo grande: {other['n']} enti "
            f"({_pct(other['n'], n)}% > {max_other_pct}%) — codici categoria non mappati"
        )

    if errs:
        raise ValueError(
            "Integrità KPI VIOLATA (" + str(len(errs)) + "):\n- " + "\n- ".join(errs)
        )


__all__ = [
    "CLUSTERS",
    "CAT_TO_CLUSTER",
    "CLUSTER_LABEL",
    "SOV_ORDER",
    "ITA_BUCKETS",
    "compute_current",
    "compute_by_category",
    "assert_integrity",
]
