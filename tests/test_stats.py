"""Test dei KPI della pagina Statistiche (src/mail_sovereignty/stats.py).

Fixture sintetica di 9 enti con valori attesi calcolati a mano: copre tutti i
bucket di sovranità, le giurisdizioni MX, le bande di confidenza, i segnali e la
segmentazione per categoria. `assert_integrity` è testata sia sul caso valido sia
su dati corrotti (deve sollevare). È la garanzia che "i numeri non sbaglino".
"""

import pytest

from mail_sovereignty.stats import (
    assert_integrity,
    compute_by_category,
    compute_current,
)


def _e(bfs, provider, jur, conf, mx=True, **extra):
    """Costruisce un'entità raw minimale di data.json."""
    e = {
        "bfs": bfs,
        "country": "IT",
        "provider": provider,
        "mx_jurisdiction": jur,
        "classification_confidence": conf,
        "mx": ["mx.example.it"] if mx else [],
    }
    e.update(extra)
    return e


# 9 enti: somme e quote note. provider → bucket via historicize.sovereignty_of.
FIXTURE = [
    _e("IT-COM-a", "aruba", "domestic", 0.90, spf="v=spf1"),  # ITA commerciali, territ.
    _e(
        "IT-COM-b", "microsoft", "foreign", 0.95, dkim={"s1": "x.onmicrosoft.com"}
    ),  # USA
    _e("IT-L33-c", "google", "foreign", 0.85),  # USA, education
    _e("IT-L33-d", "istruzione-miur-tenant", "foreign", 0.92),  # USA, education
    _e("IT-C1-e", "regional-public", "domestic", 0.70),  # ITA cloud sovrano, central
    _e(
        "IT-COM-f", "independent", "domestic", 0.60, gateway="barracuda"
    ),  # ITA autonomo
    _e("IT-COM-g", "zoho", "foreign", 0.55),  # Altri esteri, territoriale
    _e("IT-L33-h", "unknown", "unknown", 0.30, mx=False),  # Sconosciuto, education
    _e(
        "IT-COM-i", "aruba", "mixed", 0.80, spf="v=spf1"
    ),  # ITA commerciali, territoriale
]


@pytest.fixture
def cur():
    return compute_current(FIXTURE)


@pytest.fixture
def bycat():
    return compute_by_category(FIXTURE)


# ── KPI di testata ──────────────────────────────────────────────────────────
def test_headline_totals(cur):
    assert cur["n_entities"] == 9
    assert cur["n_classified"] == 8  # 9 - 1 unknown
    assert cur["coverage_pct"] == round(100 * 8 / 9, 2)  # 88.89
    assert cur["isd"] == 50.0  # 4 ITA su 8 classificati
    assert cur["headline"]["cloud_act_pct"] == 37.5  # 3 USA su 8
    assert cur["headline"]["isd"] == cur["isd"]
    assert cur["mean_confidence"] == 0.73


def test_sovereignty_breakdown(cur):
    by = {s["bucket"]: s["count"] for s in cur["sovereignty"]}
    assert by["Italia — Cloud sovrano"] == 1
    assert by["Italia — Provider commerciali"] == 2
    assert by["Italia — Infrastruttura autonoma"] == 1
    assert by["Altri provider esteri"] == 1
    assert by["USA (CLOUD Act)"] == 3
    assert by["Sconosciuto"] == 1
    assert sum(by.values()) == 9
    # quote dei classificati sommano a 100
    sov_pct = sum(s["pct"] for s in cur["sovereignty"] if s["bucket"] != "Sconosciuto")
    assert abs(sov_pct - 100.0) < 0.2


def test_jurisdiction(cur):
    by = {j["key"]: j["count"] for j in cur["jurisdiction"]}
    assert by == {"domestic": 3, "foreign": 4, "mixed": 1, "unknown": 1}
    assert sum(by.values()) == 9


def test_providers_and_market(cur):
    by = {p["provider"]: p["count"] for p in cur["providers"]}
    assert by["aruba"] == 2
    assert sum(p["count"] for p in cur["providers"]) == 9
    assert 0 <= cur["market"]["hhi"] <= 10000
    assert cur["market"]["top3_pct"] <= 100


def test_confidence_bands(cur):
    by = {b["band"]: b["count"] for b in cur["confidence_bands"]}
    assert by == {"alta": 5, "media": 3, "bassa": 1}  # ≥0.8 / 0.5–0.8 / <0.5
    assert sum(by.values()) == 9


def test_signals(cur):
    s = cur["signals"]
    assert s["mx_pct"] == round(100 * 8 / 9, 2)  # 8 con MX
    assert s["spf_pct"] == round(100 * 2 / 9, 2)
    assert s["dkim_pct"] == round(100 * 1 / 9, 2)
    assert s["gateway_pct"] == round(100 * 1 / 9, 2)


# ── segmentazione per categoria ─────────────────────────────────────────────
def test_by_category(bycat):
    by = {c["cluster"]: c for c in bycat["clusters"]}
    assert by["territorial"]["n"] == 5 and by["territorial"]["isd"] == 60.0
    assert by["education"]["n"] == 3
    assert by["education"]["isd"] == 0.0 and by["education"]["cloud_act_pct"] == 100.0
    assert by["central"]["n"] == 1 and by["central"]["isd"] == 100.0
    # nessun "other": tutti i cat della fixture sono mappati
    assert "other" not in by
    # ogni cluster: la sovranità somma a n
    for c in bycat["clusters"]:
        assert sum(s["count"] for s in c["sovereignty"]) == c["n"]
    assert sum(c["n"] for c in bycat["clusters"]) == 9


# ── integrità ───────────────────────────────────────────────────────────────
def test_integrity_passes(cur, bycat):
    assert_integrity(cur, bycat)  # non solleva


def test_integrity_passes_empty():
    assert_integrity(compute_current([]), compute_by_category([]))


def test_integrity_catches_sovereignty_tamper(cur, bycat):
    cur["sovereignty"][0]["count"] += 5  # rompe la somma dei bucket
    with pytest.raises(ValueError, match="sovranità"):
        assert_integrity(cur, bycat)


def test_integrity_catches_isd_tamper(cur, bycat):
    cur["isd"] = 99.9  # ISD incoerente con i conteggi
    with pytest.raises(ValueError, match="isd"):
        assert_integrity(cur, bycat)


def test_integrity_catches_category_tamper(cur, bycat):
    bycat["clusters"][0]["n"] += 3  # somma cluster != n_entities
    with pytest.raises(ValueError):
        assert_integrity(cur, bycat)


def test_integrity_catches_jurisdiction_tamper(cur, bycat):
    cur["jurisdiction"][0]["count"] += 2  # somma giurisdizione != n
    with pytest.raises(ValueError, match="giurisdizione"):
        assert_integrity(cur, bycat)


def test_integrity_catches_provider_tamper(cur, bycat):
    cur["providers"][0]["count"] += 1  # somma provider != n
    with pytest.raises(ValueError, match="provider"):
        assert_integrity(cur, bycat)


def test_integrity_catches_coverage_tamper(cur, bycat):
    cur["coverage_pct"] = 12.3  # copertura incoerente coi conteggi
    with pytest.raises(ValueError, match="coverage"):
        assert_integrity(cur, bycat)


def test_unmapped_category_flagged():
    # tutti enti con cat non mappato → finiscono in 'other' → integrità lo segnala
    ents = [_e(f"IT-ZZZ-{i}", "aruba", "domestic", 0.9) for i in range(5)]
    cur = compute_current(ents)
    bycat = compute_by_category(ents)
    assert any(c["cluster"] == "other" for c in bycat["clusters"])
    with pytest.raises(ValueError, match="other"):
        assert_integrity(cur, bycat)
