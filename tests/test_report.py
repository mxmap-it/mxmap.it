"""Test del payload report.json (src/mail_sovereignty/report.py).

Verifica struttura (6 sezioni), parsing edizione, finding derivati, spotlight per
esposizione, e che assert_report_integrity scatti sui payload incoerenti.
"""

import pytest

from mail_sovereignty.report import (
    _edition,
    _region_extremes,
    _spotlight,
    assert_report_integrity,
    build_and_check,
    build_report,
)


def _e(bfs, provider, jur, conf, mx=True, regione=None, macroarea=None):
    e = {
        "bfs": bfs,
        "country": "IT",
        "provider": provider,
        "mx_jurisdiction": jur,
        "classification_confidence": conf,
        "mx": ["mx.example.it"] if mx else [],
    }
    if regione:
        e["regione"] = regione
    if macroarea:
        e["macroarea"] = macroarea
    return e


# 3 regioni da 3 enti (vedi test_stats.GEO_FIXTURE per le somme attese)
FIXTURE = [
    _e("IT-COM-a", "aruba", "domestic", 0.90, regione="Lazio", macroarea="Centro"),
    _e("IT-COM-b", "microsoft", "foreign", 0.95, regione="Lazio", macroarea="Centro"),
    _e("IT-L33-c", "google", "foreign", 0.85, regione="Lombardia", macroarea="Nord"),
    _e(
        "IT-L33-d",
        "istruzione-miur-tenant",
        "foreign",
        0.92,
        regione="Lombardia",
        macroarea="Nord",
    ),
    _e(
        "IT-C1-e",
        "regional-public",
        "domestic",
        0.70,
        regione="Lombardia",
        macroarea="Nord",
    ),
    _e(
        "IT-COM-f",
        "independent",
        "domestic",
        0.60,
        regione="Sicilia",
        macroarea="Isole",
    ),
    _e("IT-COM-g", "zoho", "foreign", 0.55, regione="Sicilia", macroarea="Isole"),
    _e(
        "IT-L33-h",
        "unknown",
        "unknown",
        0.30,
        mx=False,
        regione="Sicilia",
        macroarea="Isole",
    ),
    _e("IT-COM-i", "aruba", "mixed", 0.80, regione="Lazio", macroarea="Centro"),
]

GEN = "2026-06-15T08:00:00Z"


@pytest.fixture
def report():
    return build_report(FIXTURE, generated_at=GEN, run_id=None)


# ── struttura ───────────────────────────────────────────────────────────────
def test_structure(report):
    ids = [s["id"] for s in report["sections"]]
    assert ids == [
        "sintesi",
        "fotografia",
        "settori",
        "aree",
        "andamento",
        "metodologia",
    ]
    assert report["edition"] == "giugno 2026"
    assert report["headline"]
    assert report["license"] == "CC BY-SA 4.0"
    assert len(report["sources"]) == 2


def test_edition_parsing():
    assert _edition("2026-06-15T00:00:00Z") == "giugno 2026"
    assert _edition("2025-01-01T00:00:00Z") == "gennaio 2025"
    assert _edition("garbage") == ""


def test_sintesi(report):
    s = next(x for x in report["sections"] if x["id"] == "sintesi")
    assert len(s["findings"]) >= 3
    assert len(s["metrics"]) == 4
    assert len(s["recommendations"]) == 3
    assert all("owner" in r for r in s["recommendations"])


def test_fotografia_sovereignty_sums_100(report):
    foto = next(x for x in report["sections"] if x["id"] == "fotografia")
    assert abs(sum(b["pct"] for b in foto["sovereignty"]) - 100.0) <= 0.3
    assert {b["key"] for b in foto["sovereignty"]} == {
        "it",
        "eu_non_it",
        "extra_eu",
        "unknown",
    }


def test_settori_and_andamento(report):
    sett = next(x for x in report["sections"] if x["id"] == "settori")
    assert sett["clusters"] and all(0 <= c["usa_pct"] <= 100 for c in sett["clusters"])
    trend = next(x for x in report["sections"] if x["id"] == "andamento")
    assert trend["status"] == "just_started" and trend["series"]


def test_spotlight_orders_by_exposure_with_mass():
    clusters = [
        {"label": "Grande esposto", "n": 8000, "cloud_act_pct": 78.0, "isd": 22.0},
        {"label": "Piccolo estremo", "n": 10, "cloud_act_pct": 99.0, "isd": 1.0},
        {"label": "Medio esposto", "n": 200, "cloud_act_pct": 60.0, "isd": 40.0},
        {
            "label": "Stato centrale",
            "cluster": "central",
            "n": 5000,
            "cloud_act_pct": 90.0,
        },
    ]
    spot = _spotlight(clusters, n_min=50)
    labels = [c["label"] for c in spot]
    assert "Piccolo estremo" not in labels  # escluso per massa < 50
    assert "Stato centrale" not in labels  # PA Centrale esclusa dallo spotlight
    assert labels[0] == "Grande esposto"  # ordinato per esposizione


# ── analisi per aree ────────────────────────────────────────────────────────
def test_aree(report):
    aree = next(x for x in report["sections"] if x["id"] == "aree")
    assert aree["status"] == "active"
    assert aree["n_total"] == 9
    reg = {r["regione"]: r for r in aree["regions"]}
    assert set(reg) == {"Lazio", "Lombardia", "Sicilia"}
    assert reg["Lazio"]["n"] == 3 and reg["Lazio"]["isd"] == round(100 * 2 / 3, 2)
    assert sum(r["n"] for r in aree["regions"]) == 9
    assert sum(m["n"] for m in aree["macroaree"]) == 9
    assert aree["regions"][0]["regione"] == "Lazio"  # ordinata per ISD desc
    # massa < 50 nella fixture sintetica → estremi non calcolati (robustezza)
    assert aree["most_sovereign"] is None


def test_region_extremes():
    regions = [
        {"regione": "Alpha", "n": 1000, "isd": 70.0, "cloud_act_pct": 20.0},
        {"regione": "Beta", "n": 800, "isd": 30.0, "cloud_act_pct": 65.0},
        {"regione": "Mini", "n": 10, "isd": 99.0, "cloud_act_pct": 0.0},
        {"regione": "Sconosciuta", "n": 5000, "isd": 95.0, "cloud_act_pct": 0.0},
    ]
    sov, exp = _region_extremes(regions, n_min=50)
    assert sov["regione"] == "Alpha"  # ISD max tra gli eleggibili
    assert exp["regione"] == "Beta"  # esposizione CLOUD Act max
    assert sov["regione"] not in ("Mini", "Sconosciuta")  # massa / unknown esclusi


def test_region_extremes_empty():
    assert _region_extremes([], n_min=50) == (None, None)
    sub = [{"regione": "X", "n": 3, "isd": 50.0, "cloud_act_pct": 1.0}]
    assert _region_extremes(sub) == (None, None)  # tutte sotto soglia


# ── integrità ───────────────────────────────────────────────────────────────
def test_integrity_passes(report):
    assert_report_integrity(report)


def test_build_and_check(report):
    assert (
        build_and_check(FIXTURE, generated_at=GEN, run_id=None)["edition"]
        == "giugno 2026"
    )


def test_integrity_catches_missing_section(report):
    report["sections"] = [s for s in report["sections"] if s["id"] != "metodologia"]
    with pytest.raises(ValueError, match="metodologia"):
        assert_report_integrity(report)


def test_integrity_catches_methodology_without_dependency(report):
    meto = next(x for x in report["sections"] if x["id"] == "metodologia")
    meto["limits"] = "nessun riferimento alla dipendenza"
    with pytest.raises(ValueError, match="mxmap.it#2"):
        assert_report_integrity(report)


def test_integrity_catches_sovereignty_sum(report):
    foto = next(x for x in report["sections"] if x["id"] == "fotografia")
    foto["sovereignty"][0]["pct"] += 20
    with pytest.raises(ValueError, match="sovranità"):
        assert_report_integrity(report)


def test_integrity_catches_region_sum(report):
    aree = next(x for x in report["sections"] if x["id"] == "aree")
    aree["regions"][0]["n"] += 50  # somma regioni != n_total
    with pytest.raises(ValueError, match="aree"):
        assert_report_integrity(report)
