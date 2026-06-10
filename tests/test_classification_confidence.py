"""Test di FEDELTÀ del port confidence vs davidhuser/mxmap classifier.py.

Ogni caso verifica il valore esatto di confidence prodotto dalle regole
upstream — se il port diverge, il test fallisce.
"""

import pytest

from mail_sovereignty.classification_confidence import (
    compute_confidence,
    _rule_confidence,
    _independent_confidence,
)


def entry(provider, *, mx=False, spf=False, dkim=False, autodiscover=False,
          tenant=False, gateway=None):
    e = {"provider": provider}
    if mx:
        e["mx"] = ["mx.example.it"]
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
    return e


# === Valori esatti attesi dalle regole _PROVIDER_RULES upstream ===
@pytest.mark.parametrize("e,exp_conf,exp_rule", [
    # 3 segnali
    (entry("microsoft", mx=True, spf=True, autodiscover=True), 0.95, "mx_spf_ad"),
    (entry("microsoft", mx=True, spf=True, tenant=True), 0.95, "mx_spf_tenant"),
    # mx+spf (no tenant) → mx_spf 0.90
    (entry("google", mx=True, spf=True), 0.90, "mx_spf"),
    # mx+spf+dkim (google, no tenant): mx_spf 0.90 + boost 1×0.02 = 0.92
    (entry("google", mx=True, spf=True, dkim=True), 0.92, "mx_spf"),
    # microsoft full house: mx_spf_ad 0.95 + boost {dkim,tenant}=2×0.02 = 0.99
    (entry("microsoft", mx=True, spf=True, dkim=True, autodiscover=True, tenant=True),
     0.99, "mx_spf_ad"),
    # mx solo → mx_only 0.80
    (entry("aruba", mx=True), 0.80, "mx_only"),
    # spf solo → spf_only 0.50
    (entry("aruba", spf=True), 0.50, "spf_only"),
    # spf + gateway → spf_gw 0.70 (gateway richiesto)
    (entry("microsoft", spf=True, gateway="mxgate.proofpoint.it"), 0.70, "spf_gw"),
    # tenant solo su MS365: nessuna regola 1-tenant → fallback 0.40
    # + boost 1×0.02 per il segnale tenant non consumato dalla regola = 0.42
    # (comportamento upstream: boost = len(signals - rule.signals))
    (entry("microsoft", tenant=True), 0.42, "fallback"),
])
def test_provider_confidence_exact(e, exp_conf, exp_rule):
    conf, rule, _ = compute_confidence(e)
    assert rule == exp_rule, f"regola attesa {exp_rule}, ottenuta {rule}"
    assert abs(conf - exp_conf) < 1e-9, f"conf attesa {exp_conf}, ottenuta {conf}"


# === TENANT contato solo per MS365 ===
def test_tenant_only_for_ms365():
    # google con tenant presente NON deve usare tenant (non è MS365)
    conf_g, rule_g, sig_g = compute_confidence(
        entry("google", mx=True, spf=True, tenant=True))
    assert "tenant" not in sig_g
    assert rule_g == "mx_spf" and abs(conf_g - 0.90) < 1e-9
    # microsoft con stessi segnali USA tenant → mx_spf_tenant 0.95
    conf_m, rule_m, sig_m = compute_confidence(
        entry("microsoft", mx=True, spf=True, tenant=True))
    assert "tenant" in sig_m
    assert rule_m == "mx_spf_tenant" and abs(conf_m - 0.95) < 1e-9


def test_istruzione_miur_tenant_is_ms365():
    # il tenant centrale MIM È Microsoft 365 → tenant conta
    conf, rule, sig = compute_confidence(
        entry("istruzione-miur-tenant", mx=True, dkim=True, tenant=True))
    assert "tenant" in sig
    # mx+dkim+tenant: dkim_spf_tenant? no spf. dkim_ad_tenant? no ad.
    # mx_tenant {mx,tenant} → 0.85 + boost {dkim}=1×0.02 = 0.87
    assert rule == "mx_tenant" and abs(conf - 0.87) < 1e-9


# === Independent ===
@pytest.mark.parametrize("e,exp_conf,exp_rule", [
    (entry("independent", mx=True, spf=True), 0.90, "ind_mx_spf"),
    (entry("independent", mx=True), 0.60, "ind_mx_only"),
    # dkim solo (no mx, no spf) → ind_secondary 0.20 + boost {dkim}=1 → 0.22
    (entry("independent", dkim=True), 0.22, "ind_secondary"),
    (entry("independent"), 0.0, "ind_none"),
])
def test_independent_confidence_exact(e, exp_conf, exp_rule):
    conf, rule, _ = compute_confidence(e)
    assert rule == exp_rule
    assert abs(conf - exp_conf) < 1e-9


# === Unknown (nessun MX) ===
def test_unknown_no_mx():
    conf, rule, sig = compute_confidence(entry("unknown"))
    assert conf == 0.0 and rule == "no_mx" and sig == []


# === Funzioni di basso livello (parità con upstream) ===
def test_rule_confidence_boost():
    # mx+spf+dkim (no autodiscover): mx_spf 0.90 + boost {dkim}=1×0.02 = 0.92
    # (con autodiscover invece matcherebbe mx_spf_ad, regola a 3 segnali)
    conf, rule = _rule_confidence("google", {"mx", "spf", "dkim"}, None)
    assert rule == "mx_spf" and abs(conf - 0.92) < 1e-9


def test_rule_confidence_cap_at_one():
    # base alta + molti boost: cap a 1.0
    conf, _ = _rule_confidence(
        "microsoft", {"mx", "spf", "autodiscover", "dkim", "tenant"}, None)
    assert conf <= 1.0


def test_independent_confidence_levels():
    assert _independent_confidence(True, True, {"mx", "spf"}) == (0.90, "ind_mx_spf")
    assert _independent_confidence(True, False, {"mx"}) == (0.60, "ind_mx_only")
    assert _independent_confidence(False, False, set()) == (0.0, "ind_none")
