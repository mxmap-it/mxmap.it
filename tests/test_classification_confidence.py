"""Test di FEDELTÀ del port confidence vs mxmap/esorics2026 classifier.py.

Verifica i valori esatti delle 7 regole ESORICS, il modello DOMESTIC/
FOREIGN, mx_jurisdiction e il domestic-MX-override.
"""

import pytest

from mail_sovereignty.classification_confidence import (
    compute_confidence,
    mx_jurisdiction,
    needs_domestic_mx_override,
    _rule_confidence,
    _country_confidence,
    _DOMESTIC_RULES,
    _FOREIGN_RULES,
)


def entry(provider, *, mx=None, spf=False, dkim=False, autodiscover=False,
          tenant=False, gateway=None, mx_countries=None):
    e = {"provider": provider}
    if mx is not None:
        e["mx"] = mx
    if spf:
        e["spf"] = "v=spf1 -all"
    if dkim:
        e["dkim"] = {"selector1": "s1._domainkey.x.onmicrosoft.com"}
    if autodiscover:
        e["autodiscover"] = {"autodiscover_cname": "autodiscover.outlook.com"}
    if tenant:
        e["tenant"] = "Managed"
    if gateway:
        e["gateway"] = gateway
    if mx_countries is not None:
        e["mx_countries"] = mx_countries
    return e


# === 7 regole ESORICS — valori esatti ===
@pytest.mark.parametrize("e,exp_conf,exp_rule", [
    # mx+spf → mx_spf 0.90
    (entry("google", mx=["mx.g"], spf=True), 0.90, "mx_spf"),
    # mx solo → mx_only 0.80
    (entry("aruba", mx=["mx.aruba.it"]), 0.80, "mx_only"),
    # mx+spf+dkim (google): mx_spf 0.90 + boost {dkim}=1 → 0.92
    (entry("google", mx=["mx.g"], spf=True, dkim=True), 0.92, "mx_spf"),
    # microsoft mx+spf+tenant: mx_spf 0.90 + boost {tenant}=1 → 0.92
    (entry("microsoft", mx=["mx.x"], spf=True, tenant=True), 0.92, "mx_spf"),
    # microsoft full: mx_spf 0.90 + boost {dkim,autodiscover,tenant}=3 → 0.96
    (entry("microsoft", mx=["mx.x"], spf=True, dkim=True, autodiscover=True,
           tenant=True), 0.96, "mx_spf"),
    # spf + gateway → spf_gw 0.70
    (entry("microsoft", spf=True, gateway="proofpoint"), 0.70, "spf_gw"),
    # dkim + gateway → dkim_gw 0.65
    (entry("microsoft", dkim=True, gateway="proofpoint"), 0.65, "dkim_gw"),
    # dkim+spf no gateway → dkim_spf 0.60
    (entry("google", spf=True, dkim=True), 0.60, "dkim_spf"),
    # spf solo no gateway → spf_only 0.50
    (entry("aruba", spf=True), 0.50, "spf_only"),
    # niente segnali validi → fallback 0.40
    (entry("aruba"), 0.40, "fallback"),
])
def test_provider_rules_exact(e, exp_conf, exp_rule):
    conf, rule, _, _ = compute_confidence(e)
    assert rule == exp_rule, f"regola attesa {exp_rule}, ottenuta {rule}"
    assert abs(conf - exp_conf) < 1e-9, f"conf attesa {exp_conf}, ottenuta {conf}"


# === TENANT/AUTODISCOVER non determinano la base, solo boost ===
def test_tenant_not_in_base_rule():
    # microsoft con solo tenant (no mx/spf/dkim): present vuoto → fallback
    # + boost {tenant}=1 → 0.42
    conf, rule, sig, _ = compute_confidence(
        entry("microsoft", tenant=True))
    assert rule == "fallback"
    assert abs(conf - 0.42) < 1e-9
    assert "tenant" in sig


def test_tenant_only_for_ms365_boost():
    # google con tenant NON conta (non MS365) → mx_spf 0.90 senza boost
    conf, rule, sig, _ = compute_confidence(
        entry("google", mx=["mx.g"], spf=True, tenant=True))
    assert "tenant" not in sig and rule == "mx_spf" and abs(conf - 0.90) < 1e-9


# === DOMESTIC/FOREIGN ===
@pytest.mark.parametrize("e,exp_conf,exp_rule,exp_jur", [
    # independent con MX in IT + SPF → dom_mx_spf 0.80
    (entry("independent", mx=["mx.comune.it"], spf=True, mx_countries=["IT"]),
     0.80, "dom_mx_spf", "domestic"),
    # independent con MX in IT, no SPF → dom_mx_only 0.70
    (entry("independent", mx=["mx.comune.it"], mx_countries=["IT"]),
     0.70, "dom_mx_only", "domestic"),
    # independent con MX estero + SPF → frgn_mx_spf 0.60
    (entry("independent", mx=["mx.foo.de"], spf=True, mx_countries=["DE"]),
     0.60, "frgn_mx_spf", "foreign"),
    # independent con MX estero, no SPF → frgn_mx_only 0.50
    (entry("independent", mx=["mx.foo.us"], mx_countries=["US"]),
     0.50, "frgn_mx_only", "foreign"),
])
def test_domestic_foreign(e, exp_conf, exp_rule, exp_jur):
    conf, rule, _, jur = compute_confidence(e, target_country="IT")
    assert jur == exp_jur
    assert rule == exp_rule
    assert abs(conf - exp_conf) < 1e-9


# === mx_jurisdiction ===
@pytest.mark.parametrize("countries,expected", [
    (["IT"], "domestic"),
    (["IT", "IT"], "domestic"),
    (["US"], "foreign"),
    (["DE", "FR"], "foreign"),
    (["IT", "US"], "mixed"),
    ([], "unknown"),
    (None, "unknown"),
])
def test_mx_jurisdiction(countries, expected):
    e = {"provider": "independent"}
    if countries is not None:
        e["mx_countries"] = countries
    assert mx_jurisdiction(e, "IT") == expected


# === Domestic MX override ===
def test_override_fires_on_teams_only_tenant():
    # microsoft via tenant, ma MX self-hosted domestico → override
    e = entry("microsoft", mx=["mail.comune.foo.it"], tenant=True,
              mx_countries=["IT"])
    assert needs_domestic_mx_override(e) is True


def test_override_skips_genuine_cloud_mx():
    # microsoft con MX cloud genuino → NO override
    e = entry("microsoft", mx=["comune-foo-it.mail.protection.outlook.com"],
              tenant=True, mx_countries=["US"])
    assert needs_domestic_mx_override(e) is False


def test_override_skips_miur_schools():
    # scuola MIM: MX È il tenant centrale outlook → cloud genuino, no override
    e = entry("istruzione-miur-tenant",
              mx=["istruzione-it.mail.protection.outlook.com"],
              dkim=True, mx_countries=["US"])
    assert needs_domestic_mx_override(e) is False


def test_override_skips_google_genuine():
    e = entry("google", mx=["alt1.aspmx.l.google.com"], mx_countries=["US"])
    assert needs_domestic_mx_override(e) is False


def test_override_skips_gateway_cases():
    # microsoft via gateway look-through (DKIM dietro Sophos): MX è il gateway,
    # non outlook, ma il backend È Microsoft → NO override (come ESORICS)
    e = entry("microsoft", mx=["mx-01.prod.hydra.sophos.com"], dkim=True,
              gateway="sophos", mx_countries=["IT"])
    assert needs_domestic_mx_override(e) is False


# === Unknown ===
def test_unknown_no_mx():
    conf, rule, sig, jur = compute_confidence(entry("unknown"))
    assert conf == 0.0 and rule == "no_mx" and sig == []


# === Funzioni basso livello (parità upstream) ===
def test_rule_confidence_boost():
    # mx+spf+dkim: mx_spf 0.90 + boost {dkim}=1 → 0.92
    conf, rule = _rule_confidence({"mx", "spf", "dkim"}, None)
    assert rule == "mx_spf" and abs(conf - 0.92) < 1e-9


def test_country_confidence_levels():
    assert _country_confidence(True, True, False, _DOMESTIC_RULES) == (0.80, "dom_mx_spf")
    assert _country_confidence(True, False, False, _DOMESTIC_RULES) == (0.70, "dom_mx_only")
    assert _country_confidence(False, False, False, _FOREIGN_RULES) == (0.0, "frgn_none")
    assert _country_confidence(True, True, False, _FOREIGN_RULES) == (0.60, "frgn_mx_spf")
