"""Report «Stato della sovranità digitale della posta elettronica della PA» —
payload strutturato (logica pura, testabile).

Generato da MxMap e pubblicato come `report.json` alla root del deploy: il sito
dell'Osservatorio lo **scarica e pesca** (come kpi.json) e lo integra in una
pagina Hugo brandizzata; `report.html` ne è il rendering consulting di
riferimento. I numeri riusano stats/kpi (unica fonte di verità). La prosa
editoriale fissa sta nel layer di rendering; qui solo dati + finding derivati.

`assert_report_integrity()` verifica la coerenza del payload — eseguita a ogni
build e nei test (regola CLAUDE.md "numeri sempre testati-verificati").
"""

from __future__ import annotations

from mail_sovereignty.kpi import assert_kpi_integrity, build_kpi
from mail_sovereignty.stats import compute_by_category, compute_current

MESI_IT = [
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
]

# Raccomandazioni di policy (editoriali, owner assegnato) — sintesi delle 5
# raccomandazioni dell'Osservatorio nelle 3 a più alto impatto per la testata.
RECOMMENDATIONS = [
    {
        "n": 1,
        "text": "Censire i servizi email della PA in IndicePA e renderli monitorabili.",
        "owner": "AgID · Dip. Trasformazione Digitale",
    },
    {
        "n": 2,
        "text": "Inserire requisiti di sovranità nelle convenzioni quadro per la PA.",
        "owner": "Consip · MEF",
    },
    {
        "n": 3,
        "text": "Avviare un piano di migrazione prioritario per i settori a dati sensibili.",
        "owner": "MIM · Ministero della Salute",
    },
]

SOURCES = [
    {
        "name": "MxMap.it — fonte dati",
        "url": "https://mxmap.it/",
    },
    {
        "name": "Osservatorio Nazionale Sovranità Digitale",
        "url": "https://fpietrosanti.github.io/osservatorio-nazionale-sovranita-digitale/",
    },
]

METHODOLOGY_FOOTER = (
    "Classificazione del provider di posta via analisi DNS pubblica (record MX, "
    "SPF, DKIM) dei domini PA in IndicePA, rielaborata da MxMap. IndicePA non è "
    "una base dati pulita da cui inferire senza rielaborazioni i domini email "
    "(vedi limiti della fonte, mxmap.it#2). Licenza CC BY-SA 4.0."
)


def _edition(generated_at: str) -> str:
    """`2026-06-14T...` → `giugno 2026`. Fallback: stringa vuota."""
    try:
        y, m = int(generated_at[0:4]), int(generated_at[5:7])
        return f"{MESI_IT[m - 1]} {y}"
    except (ValueError, IndexError):
        return ""


# Cluster da NON mettere in evidenza nell'allarme di testata. La PA Centrale
# (ministeri, autorità, forze di polizia) è un tema sensibile e su numeri piccoli
# (~52 enti, di cui pochissimi per segmento): un allarme di testata sarebbe
# politicamente troppo "acceso" e statisticamente fragile. Resta nella tabella
# settori (trasparenza piena) e va trattata a parte, per segmenti specifici e con
# framing di policy (es. comparti a missione di sicurezza), non come percentuale.
SPOTLIGHT_EXCLUDE = {"central"}


def _spotlight(clusters: list[dict], n_min: int = 50, top: int = 3) -> list[dict]:
    """Settori più esposti al CLOUD Act per la narrazione di testata. Filtra i
    cluster minuscoli (massa < n_min) e quelli in SPOTLIGHT_EXCLUDE (PA Centrale)."""
    eligible = [
        c
        for c in clusters
        if c["n"] >= n_min and c.get("cluster") not in SPOTLIGHT_EXCLUDE
    ]
    return sorted(eligible, key=lambda c: c["cloud_act_pct"], reverse=True)[:top]


def build_report(
    entities: list[dict], *, generated_at: str, run_id: str | None
) -> dict:
    """Payload strutturato del report dalle entità raw IT di data.json."""
    kpi = build_kpi(entities, generated_at=generated_at, run_id=run_id)
    cur = compute_current(entities)
    by_cat = compute_by_category(entities)
    clusters = by_cat["clusters"]

    sov = kpi["sovereignty"]
    it_pct = sov["it"]["pct"]
    usa_pct = sov["extra_eu"]["pct"]
    isd = cur["isd"]
    jur = {j["key"]: j["pct"] for j in cur["jurisdiction"]}
    spot = _spotlight(clusters)

    # finding derivati dai dati (brevi, citabili)
    findings = [
        f"Il {usa_pct}% delle PA usa provider extra-UE soggetti al CLOUD Act statunitense.",
        f"I provider italiani restano la prima scelta ({it_pct}%), ma frammentati.",
        f"Scarto tra controllo legale ({it_pct}%) e collocazione tecnica dell'MX "
        f"(domestico {jur.get('domestic', 0)}%): è esso stesso un segnale.",
    ]
    if spot:
        sectors_str = " · ".join(
            f"{c['label'].split(' (')[0]} {c['cloud_act_pct']}%" for c in spot
        )
        findings.append(f"Settori più esposti al CLOUD Act: {sectors_str}.")

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "edition": _edition(generated_at),
        "title": "Stato della sovranità digitale della posta elettronica della PA italiana",
        "headline": (
            "Quasi una pubblica amministrazione su due affida la posta a provider "
            "extra-UE soggetti al CLOUD Act statunitense."
        ),
        "license": "CC BY-SA 4.0",
        "sections": [
            {
                "id": "sintesi",
                "title": "Sintesi per i decisori",
                "kind": "executive",
                "findings": findings,
                "metrics": [
                    {
                        "label": "Enti monitorati",
                        "value": f"{cur['n_entities']:,}".replace(",", "."),
                    },
                    {"label": "Sovranità italiana", "value": f"{it_pct}%"},
                    {"label": "Soggette al CLOUD Act", "value": f"{usa_pct}%"},
                    {"label": "Copertura del dato", "value": f"{cur['coverage_pct']}%"},
                ],
                "recommendations": RECOMMENDATIONS,
            },
            {
                "id": "fotografia",
                "title": "La fotografia nazionale",
                "kind": "overview",
                "sovereignty": [
                    {
                        "key": k,
                        "label": sov[k]["label"],
                        "pct": sov[k]["pct"],
                        "count": sov[k]["count"],
                    }
                    for k in ("it", "eu_non_it", "extra_eu", "unknown")
                ],
                "top_providers": kpi["top_providers"],
                "jurisdiction": cur["jurisdiction"],
                "market": cur["market"],
            },
            {
                "id": "settori",
                "title": "Analisi per gruppi — i settori della PA",
                "kind": "sectors",
                "clusters": [
                    {
                        "cluster": c["label"],
                        "n_entities": c["n"],
                        "usa_pct": c["cloud_act_pct"],
                        "isd": c["isd"],
                    }
                    for c in clusters
                ],
                "spotlight": [
                    {
                        "cluster": c["label"],
                        "usa_pct": c["cloud_act_pct"],
                        "n_entities": c["n"],
                    }
                    for c in spot
                ],
            },
            {
                "id": "aree",
                "title": "Analisi per aree — la geografia della sovranità",
                "kind": "areas",
                "status": "pending",
                "note": (
                    "Sezione in allestimento: richiede il dato regionale per ente, "
                    "oggi vincolato alla qualità della fonte IndicePA (vedi mxmap.it#2)."
                ),
            },
            {
                "id": "andamento",
                "title": "Andamento nel tempo",
                "kind": "trend",
                "status": "just_started",
                "series": [{"date": generated_at[:7] or "", "isd": isd}],
                "note": (
                    "Monitoraggio appena avviato: la serie storica parte da questa "
                    "edizione; i trend compariranno dai prossimi rilevamenti."
                ),
            },
            {
                "id": "metodologia",
                "title": "Metodologia, limiti e dati aperti",
                "kind": "methodology",
                "coverage_pct": cur["coverage_pct"],
                "mean_confidence": cur["mean_confidence"],
                "limits": (
                    "IndicePA non è una base dati pulita da cui inferire in modo "
                    "immediato e senza rielaborazioni i domini email (non-PEC) degli "
                    "enti: la bonifica continua è una dipendenza funzionale core, "
                    "tracciata in mxmap.it#2."
                ),
                "license": "CC BY-SA 4.0",
            },
        ],
        "sources": SOURCES,
        "methodology_footer": METHODOLOGY_FOOTER,
    }


def assert_report_integrity(report: dict) -> None:
    """Verifica la coerenza del payload report.json. Solleva ValueError con
    l'elenco delle violazioni. Eseguita a ogni build e nei test."""
    errs: list[str] = []
    ids = [s["id"] for s in report.get("sections", [])]
    for needed in (
        "sintesi",
        "fotografia",
        "settori",
        "aree",
        "andamento",
        "metodologia",
    ):
        if needed not in ids:
            errs.append(f"sezione mancante: {needed}")

    sec = {s["id"]: s for s in report.get("sections", [])}

    foto = sec.get("fotografia", {})
    sov_pct = sum(b["pct"] for b in foto.get("sovereignty", []))
    if foto.get("sovereignty") and abs(sov_pct - 100.0) > 0.3:
        errs.append(f"fotografia: somma quote sovranità {sov_pct} != ~100")

    settori = sec.get("settori", {})
    for c in settori.get("clusters", []):
        if not 0 <= c["usa_pct"] <= 100:
            errs.append(f"settori: usa_pct fuori range per {c['cluster']}")
    if not settori.get("clusters"):
        errs.append("settori: nessun cluster")

    trend = sec.get("andamento", {})
    if trend.get("status") != "just_started" and not trend.get("series"):
        errs.append("andamento: serie mancante e stato non 'just_started'")

    meto = sec.get("metodologia", {})
    if "mxmap.it#2" not in (meto.get("limits") or ""):
        errs.append(
            "metodologia: manca il riferimento alla dipendenza fonte (mxmap.it#2)"
        )

    if not report.get("sources"):
        errs.append("sources: mancano i link (MxMap / Osservatorio)")
    if not report.get("headline"):
        errs.append("headline mancante")

    if errs:
        raise ValueError(
            "Integrità report.json VIOLATA ("
            + str(len(errs))
            + "):\n- "
            + "\n- ".join(errs)
        )


def build_and_check(
    entities: list[dict], *, generated_at: str, run_id: str | None
) -> dict:
    """Costruisce il report e ne verifica l'integrità (anche dei KPI sottostanti)."""
    kpi = build_kpi(entities, generated_at=generated_at, run_id=run_id)
    assert_kpi_integrity(kpi)
    report = build_report(entities, generated_at=generated_at, run_id=run_id)
    assert_report_integrity(report)
    return report


__all__ = [
    "build_report",
    "assert_report_integrity",
    "build_and_check",
    "RECOMMENDATIONS",
    "SOURCES",
]
