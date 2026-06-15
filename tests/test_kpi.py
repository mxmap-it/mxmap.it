"""Test dei KPI aggregati per l'Osservatorio (src/mail_sovereignty/kpi.py).

Stessa fixture di 9 enti di test_stats: verifica la rimappatura 6→4 bucket, le
quote (~100), top_providers, by_cluster (cluster citizen, % CLOUD Act, provider
dominante) e che assert_kpi_integrity scatti sui dati corrotti.
"""

import pytest

from mail_sovereignty import kpi as kpi_mod
from mail_sovereignty.kpi import (
    SOV4_LABELS,
    assert_kpi_integrity,
    build_kpi,
    provider_to_sov4,
)


def _e(bfs, provider, jur, conf, mx=True, **extra):
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


FIXTURE = [
    _e("IT-COM-a", "aruba", "domestic", 0.90, spf="v=spf1"),  # it, territoriale
    _e("IT-COM-b", "microsoft", "foreign", 0.95),  # extra_eu (USA)
    _e("IT-L33-c", "google", "foreign", 0.85),  # extra_eu, istruzione
    _e("IT-L33-d", "istruzione-miur-tenant", "foreign", 0.92),  # extra_eu (M365), istr.
    _e(
        "IT-C1-e", "regional-public", "domestic", 0.70
    ),  # it (cloud sovrano), PA centrale
    _e("IT-COM-f", "independent", "domestic", 0.60),  # it (autonomo), territoriale
    _e("IT-COM-g", "zoho", "foreign", 0.55),  # extra_eu (non-UE), territoriale
    _e("IT-L33-h", "unknown", "unknown", 0.30, mx=False),  # unknown, istruzione
    _e("IT-COM-i", "aruba", "mixed", 0.80, spf="v=spf1"),  # it, territoriale
]


@pytest.fixture
def kpi():
    return build_kpi(FIXTURE, generated_at="2026-01-01T00:00:00Z", run_id=None)


# ── mappatura 6→4 bucket ────────────────────────────────────────────────────
def test_provider_to_sov4():
    assert provider_to_sov4("microsoft") == "extra_eu"
    assert provider_to_sov4("google") == "extra_eu"
    assert provider_to_sov4("aws") == "extra_eu"
    assert provider_to_sov4("istruzione-miur-tenant") == "extra_eu"
    assert provider_to_sov4("zoho") == "extra_eu"  # non-UE
    assert provider_to_sov4("yandex") == "extra_eu"  # non-UE
    assert provider_to_sov4("aruba") == "it"
    assert provider_to_sov4("regional-public") == "it"
    assert provider_to_sov4("independent") == "it"
    assert provider_to_sov4("unknown") == "unknown"


def test_eu_non_it_extension(monkeypatch):
    # punto di estensione: se un provider è marcato UE-non-IT, finisce in eu_non_it
    monkeypatch.setattr(kpi_mod, "EU_NON_IT_PROVIDERS", frozenset({"aruba"}))
    assert provider_to_sov4("aruba") == "eu_non_it"


def test_sovereignty_buckets(kpi):
    s = kpi["sovereignty"]
    assert set(s) == set(SOV4_LABELS)
    assert s["extra_eu"]["count"] == 4  # microsoft, google, istruzione, zoho
    assert s["it"]["count"] == 4  # aruba×2, regional-public, independent
    assert s["eu_non_it"]["count"] == 0
    assert s["unknown"]["count"] == 1
    assert s["it"]["label"] == "Italiano"
    assert sum(b["count"] for b in s.values()) == 9
    assert abs(sum(b["pct"] for b in s.values()) - 100.0) <= 0.3


# ── top_providers ───────────────────────────────────────────────────────────
def test_top_providers(kpi):
    tp = kpi["top_providers"]
    assert len(tp) <= 10
    assert tp[0]["name"] == "Provider Italiano" and tp[0]["count"] == 2  # aruba
    assert tp[0]["sovereignty"] == "it"
    assert all(p["sovereignty"] in SOV4_LABELS for p in tp)


# ── by_cluster ──────────────────────────────────────────────────────────────
def test_by_cluster(kpi):
    by = {c["cluster"]: c for c in kpi["by_cluster"]}
    terr = by["Enti territoriali"]
    assert terr["n_entities"] == 5
    assert terr["usa_pct"] == 20.0  # 1 microsoft su 5
    assert terr["dominant_provider"] == "Provider Italiano"  # aruba ×2
    istr = by["Istruzione"]
    assert istr["n_entities"] == 3
    assert istr["usa_pct"] == round(100 * 2 / 3, 1)  # google + istruzione
    assert sum(c["n_entities"] for c in kpi["by_cluster"]) == 9


# ── totals / confidence ─────────────────────────────────────────────────────
def test_totals_and_confidence(kpi):
    t = kpi["totals"]
    assert t["n_entities"] == 9
    assert t["n_with_mx"] == 8  # uno senza MX
    assert 0 <= t["coverage_pct"] <= 100
    assert kpi["confidence"]["mean"] == 0.73
    assert kpi["confidence"]["high_pct"] == round(100 * 5 / 9, 1)  # 5 enti ≥0.8


# ── indici-bandiera (sui classificati) ──────────────────────────────────────
def test_indices(kpi):
    idx = kpi["indices"]
    assert idx["n_classified"] == 8  # 9 - 1 unknown
    assert idx["isd"] == 50.0  # 4 ITA su 8 classificati (identico a statistiche.html)
    assert idx["cloud_act_pct"] == 37.5  # 3 USA (CLOUD Act) su 8
    # l'ISD (sui classificati) ≠ la fetta "it" della composizione (sul totale)
    assert idx["isd"] != kpi["sovereignty"]["it"]["pct"]


# ── integrità ───────────────────────────────────────────────────────────────
def test_integrity_passes(kpi):
    assert_kpi_integrity(kpi)


def test_integrity_passes_empty():
    assert_kpi_integrity(build_kpi([], generated_at="x", run_id=None))


def test_integrity_catches_sovereignty_tamper(kpi):
    kpi["sovereignty"]["it"]["count"] += 5
    with pytest.raises(ValueError, match="sovereignty"):
        assert_kpi_integrity(kpi)


def test_integrity_catches_cluster_tamper(kpi):
    kpi["by_cluster"][0]["n_entities"] += 3
    with pytest.raises(ValueError, match="by_cluster"):
        assert_kpi_integrity(kpi)


def test_integrity_catches_bad_bucket_key(kpi):
    kpi["sovereignty"]["mars"] = {"count": 0, "pct": 0.0, "label": "Marte"}
    with pytest.raises(ValueError, match="chiavi"):
        assert_kpi_integrity(kpi)


def test_integrity_catches_indices_tamper(kpi):
    kpi["indices"]["isd"] = 150.0  # fuori range
    with pytest.raises(ValueError, match="indices"):
        assert_kpi_integrity(kpi)
