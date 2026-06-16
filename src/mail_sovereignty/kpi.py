"""KPI aggregati per l'Osservatorio Nazionale Sovranità Digitale — logica pura.

Produce il payload di `kpi.json` (servito alla root del deploy GitHub Pages,
come data-summary.json), file statico pubblico (CC BY-SA 4.0) consumato dal
sito Hugo dell'Osservatorio per sostituire i placeholder `—%`.
Schema concordato (vedi docs/STATS_KPI.md §Osservatorio): totals, indices (ISD e
CLOUD Act sui classificati, numeri di testata), sovereignty a 4 bucket
(composizione sul totale), top_providers, by_cluster, confidence.

Riusa `stats.compute_current` (numeri già validati da assert_integrity) e
rimappa i **6 bucket MxMap → 4 bucket Osservatorio**:
  extra_eu  = USA (CLOUD Act) + provider esteri non-UE (zoho/IN, yandex/RU…)
  eu_non_it = provider con sede in UE ma non Italia (oggi 0; punto di estensione)
  it        = i 3 bucket "Italia — …"
  unknown   = Sconosciuto

`assert_kpi_integrity()` verifica la coerenza del payload (somme, quote ~100,
range): chiamata a ogni build e nei test (regola CLAUDE.md "numeri sempre
testati-verificati"). L'I/O sta in scripts/build_kpi.py.
"""

from __future__ import annotations

from collections import Counter

from mail_sovereignty.historicize import PROVIDER_DISPLAY, material_row, sovereignty_of
from mail_sovereignty.stats import (
    B_CLOUD_ACT,
    CAT_TO_CLUSTER,
    ITA_BUCKETS,
    compute_current,
)

# Bucket di sovranità a 4 valori dell'Osservatorio (chiave → etichetta IT).
SOV4_LABELS = {
    "extra_eu": "Extra-UE (CLOUD Act)",
    "eu_non_it": "UE (non italiano)",
    "it": "Italiano",
    "unknown": "Sconosciuto",
}

# Provider con sede legale in UE ma non Italia. OGGI VUOTO: nessun provider del
# dataset è classificato così. Punto di estensione: aggiungere qui le chiavi
# provider quando si distingueranno (es. "ovh", "hetzner", "ionos", "scaleway").
EU_NON_IT_PROVIDERS: frozenset[str] = frozenset()

# Etichette cluster citizen-friendly (mirror di data/it_citizen_clusters.json),
# keyed sulle chiavi cluster di stats.CLUSTERS.
CLUSTER_LABEL_KPI = {
    "territorial": "Enti territoriali",
    "education": "Istruzione",
    "healthcare": "Sanità",
    "central": "PA Centrale",
    "orders": "Ordini professionali e Camere",
    "consortia": "Consorzi e Unioni di enti locali",
    "soe": "Gestori di pubblici servizi",
    "welfare": "Welfare e politiche sociali",
    "environment": "Ambiente e Territorio",
    "agencies": "Agenzie regionali",
    "procurement": "Stazioni Appaltanti",
    "pension": "Previdenza e Assistenza Sociale",
    "culture": "Cultura",
    "research": "Ricerca",
    "transport": "Trasporti e Porti",
    "other": "Altre categorie",
}


def provider_to_sov4(provider: str) -> str:
    """Mappa un provider MxMap nel bucket di sovranità a 4 valori dell'Osservatorio."""
    if provider in EU_NON_IT_PROVIDERS:
        return "eu_non_it"
    sov6 = sovereignty_of(provider)
    if sov6 in ITA_BUCKETS:
        return "it"
    if sov6 == "Sconosciuto":
        return "unknown"
    return "extra_eu"  # USA (CLOUD Act) + Altri provider esteri (non-UE)


def _pct(n: int, d: int) -> float:
    return round(100 * n / d, 1) if d else 0.0


def _by_cluster(rows: list[dict]) -> list[dict]:
    """Per cluster citizen: n, % CLOUD Act (bucket USA, include il tenant MIM
    delle scuole — più ampio del set {microsoft,google,aws}), provider dominante."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        key = CAT_TO_CLUSTER.get(r["cat"], "other")
        groups.setdefault(key, []).append(r)

    out = []
    for key, grp in groups.items():
        n = len(grp)
        usa = sum(1 for r in grp if r["sovereignty"] == B_CLOUD_ACT)
        prov_counts = Counter(r["provider"] for r in grp)
        top_prov = prov_counts.most_common(1)[0][0] if prov_counts else ""
        out.append(
            {
                "cluster": CLUSTER_LABEL_KPI.get(key, key),
                "n_entities": n,
                "usa_pct": _pct(usa, n),
                "dominant_provider": PROVIDER_DISPLAY.get(top_prov, top_prov),
            }
        )
    out.sort(key=lambda c: c["n_entities"], reverse=True)
    return out


def build_kpi(entities: list[dict], *, generated_at: str, run_id: str | None) -> dict:
    """Costruisce il payload kpi.json dalle entità raw IT di data.json."""
    cur = compute_current(entities)
    # ancora i numeri alla computazione già validata (coerenza con statistiche.html)
    n = cur["n_entities"]
    rows = [material_row(e) for e in entities]

    # sovranità a 4 bucket (somma sui provider → bucket); le pct sono sul totale
    # così i 4 bucket coprono il 100% degli enti.
    sov4_counts: Counter[str] = Counter()
    for p in cur["providers"]:
        sov4_counts[provider_to_sov4(p["provider"])] += p["count"]
    sovereignty = {
        key: {
            "count": sov4_counts.get(key, 0),
            "pct": _pct(sov4_counts.get(key, 0), n),
            "label": label,
        }
        for key, label in SOV4_LABELS.items()
    }

    # top_providers aggregati per NOME-display (come la mappa): più provider grezzi
    # condividono un display (aruba/local-isp/register-it/seeweb = "Provider
    # Italiano"; microsoft + tenant MIM = "Microsoft 365"). Evita doppioni e dà il
    # footprint reale per categoria. Ogni display ha un solo bucket di sovranità.
    disp_counts: Counter[str] = Counter()
    disp_sov: dict[str, str] = {}
    for p in cur["providers"]:
        disp_counts[p["display"]] += p["count"]
        disp_sov[p["display"]] = provider_to_sov4(p["provider"])
    top_providers = [
        {
            "name": disp,
            "count": c,
            "pct": _pct(c, n),
            "sovereignty": disp_sov[disp],
        }
        for disp, c in disp_counts.most_common(10)
    ]

    # confidenza: media + % alta (≥0.8)
    alta = next((b["count"] for b in cur["confidence_bands"] if b["band"] == "alta"), 0)
    n_conf = sum(b["count"] for b in cur["confidence_bands"])

    n_with_mx = sum(1 for e in entities if e.get("mx"))

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "license": "CC BY-SA 4.0",
        "source": "https://github.com/mxmap-it/mxmap.it",
        "totals": {
            "n_entities": n,
            "n_with_mx": n_with_mx,
            "coverage_pct": cur["coverage_pct"],
        },
        # Indici-bandiera sui CLASSIFICATI (unknown esclusi) — definizione canonica
        # della metodologia, identica a statistiche.html / report.html. Da usare per
        # la TESTATA. Distinti dalla composizione `sovereignty` qui sotto, che è sul
        # TOTALE (somma 100, include il bucket "unknown"): l'ISD ≠ la fetta "it".
        "indices": {
            "isd": cur["isd"],
            "cloud_act_pct": cur["headline"]["cloud_act_pct"],
            "n_classified": cur["n_classified"],
        },
        "sovereignty": sovereignty,
        "top_providers": top_providers,
        "by_cluster": _by_cluster(rows),
        "confidence": {
            "mean": cur["mean_confidence"],
            "high_pct": _pct(alta, n_conf),
        },
    }


def assert_kpi_integrity(kpi: dict) -> None:
    """Verifica la coerenza del payload kpi.json. Solleva ValueError elencando
    TUTTE le violazioni. Eseguita a ogni build e nei test."""
    errs: list[str] = []
    n = kpi["totals"]["n_entities"]

    # 1. i 4 bucket di sovranità coprono esattamente tutti gli enti
    sov = kpi["sovereignty"]
    if set(sov) != set(SOV4_LABELS):
        errs.append(f"sovereignty: chiavi {sorted(sov)} != {sorted(SOV4_LABELS)}")
    sov_total = sum(b["count"] for b in sov.values())
    if sov_total != n:
        errs.append(f"sovereignty: somma count {sov_total} != n_entities {n}")
    # 2. le quote sommano a ~100
    sov_pct = sum(b["pct"] for b in sov.values())
    if n and abs(sov_pct - 100.0) > 0.3:
        errs.append(f"sovereignty: somma pct {sov_pct} != ~100")
    # 3. totals coerenti
    t = kpi["totals"]
    if not 0 <= t["n_with_mx"] <= n:
        errs.append(f"n_with_mx {t['n_with_mx']} fuori range [0,{n}]")
    if not 0 <= t["coverage_pct"] <= 100:
        errs.append(f"coverage_pct {t['coverage_pct']} fuori range")
    # 4. top_providers validi
    for p in kpi["top_providers"]:
        if p["sovereignty"] not in SOV4_LABELS:
            errs.append(f"provider {p['name']}: bucket '{p['sovereignty']}' non valido")
        if not 0 <= p["pct"] <= 100:
            errs.append(f"provider {p['name']}: pct {p['pct']} fuori range")
    if len(kpi["top_providers"]) > 10:
        errs.append("top_providers: più di 10 elementi")
    # 5. by_cluster: somma enti == totale, usa_pct in range
    cl_total = sum(c["n_entities"] for c in kpi["by_cluster"])
    if cl_total != n:
        errs.append(f"by_cluster: somma enti {cl_total} != n_entities {n}")
    for c in kpi["by_cluster"]:
        if not 0 <= c["usa_pct"] <= 100:
            errs.append(f"cluster {c['cluster']}: usa_pct {c['usa_pct']} fuori range")
    # 6. confidence in range
    conf = kpi["confidence"]
    if not 0 <= conf["mean"] <= 1:
        errs.append(f"confidence.mean {conf['mean']} fuori [0,1]")
    if not 0 <= conf["high_pct"] <= 100:
        errs.append(f"confidence.high_pct {conf['high_pct']} fuori range")
    # 7. indici-bandiera (sui classificati) presenti, coerenti e nel range
    idx = kpi.get("indices", {})
    nclass = idx.get("n_classified")
    if nclass is None or not 0 <= nclass <= n:
        errs.append(f"indices.n_classified {nclass} fuori [0,{n}]")
    for k in ("isd", "cloud_act_pct"):
        v = idx.get(k)
        if v is None or not 0 <= v <= 100:
            errs.append(f"indices.{k} {v} non valido / fuori range")

    if errs:
        raise ValueError(
            "Integrità kpi.json VIOLATA ("
            + str(len(errs))
            + "):\n- "
            + "\n- ".join(errs)
        )


__all__ = [
    "SOV4_LABELS",
    "EU_NON_IT_PROVIDERS",
    "provider_to_sov4",
    "build_kpi",
    "assert_kpi_integrity",
]
