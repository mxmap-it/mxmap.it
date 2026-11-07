"""Test di FEDELTÀ del port confidence vs mxmap/esorics2026 classifier.py.

Verifica i valori esatti delle 7 regole ESORICS, il modello DOMESTIC/
FOREIGN, mx_jurisdiction, il domestic-MX-override e — dal fix #29 B —
l'ATTRIBUZIONE per-provider dei segnali: un segnale conta solo se PUNTA
al provider eletto (come by_provider[winner] upstream), non se il campo
semplicemente esiste.
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

# Fixture realistiche: l'attribuzione richiede hostname/record che puntano
# davvero al provider (keyword match), non placeholder.
MS_MX = ["comune-foo-it.mail.protection.outlook.com"]
MS_SPF = "v=spf1 include:spf.protection.outlook.com -all"
MS_DKIM = {"selector1": "selector1-x._domainkey.tenant.onmicrosoft.com"}
G_MX = ["aspmx.l.google.com"]
G_SPF = "v=spf1 include:_spf.google.com ~all"
G_DKIM = {"google": "dkim.googlemail.com"}


def entry(
    provider,
    *,
    mx=None,
    spf=None,
    dkim=None,
    autodiscover=False,
    tenant=False,
    gateway=None,
    mx_countries=None,
    txt=None,
    mx_asns=None,
):
    e = {"provider": provider}
    if mx is not None:
        e["mx"] = mx
    if spf is True:
        e["spf"] = "v=spf1 -all"
    elif spf:
        e["spf"] = spf
    if dkim is True:
        e["dkim"] = dict(MS_DKIM)
    elif dkim:
        e["dkim"] = dkim
    if autodiscover:
        e["autodiscover"] = {"autodiscover_cname": "autodiscover.outlook.com"}
    if tenant:
        e["tenant"] = "Managed"
    if gateway:
        e["gateway"] = gateway
    if mx_countries is not None:
        e["mx_countries"] = mx_countries
    if txt:
        e["txt_verifications"] = txt
    if mx_asns:
        e["mx_asns"] = mx_asns
    return e


# === 7 regole ESORICS — valori esatti (con segnali ATTRIBUITI) ===
@pytest.mark.parametrize(
    "e,exp_conf,exp_rule",
    [
        # mx+spf che puntano a google → mx_spf 0.90
        (entry("google", mx=G_MX, spf=G_SPF), 0.90, "mx_spf"),
        # mx solo → mx_only 0.80
        (entry("aruba", mx=["mx.aruba.it"]), 0.80, "mx_only"),
        # mx+spf+dkim (google): mx_spf 0.90 + boost {dkim}=1 → 0.92
        (entry("google", mx=G_MX, spf=G_SPF, dkim=G_DKIM), 0.92, "mx_spf"),
        # microsoft mx+spf+tenant: mx_spf 0.90 + boost {tenant}=1 → 0.92
        (entry("microsoft", mx=MS_MX, spf=MS_SPF, tenant=True), 0.92, "mx_spf"),
        # microsoft full: mx_spf 0.90 + boost {dkim,autodiscover,tenant}=3 → 0.96
        (
            entry(
                "microsoft",
                mx=MS_MX,
                spf=MS_SPF,
                dkim=True,
                autodiscover=True,
                tenant=True,
            ),
            0.96,
            "mx_spf",
        ),
        # dietro gateway l'MX è del gateway (NON attribuito al cloud):
        # SPF del provider + gateway → spf_gw 0.70 — il cuore del fix #29 B
        (
            entry(
                "microsoft",
                mx=["mx1.ppe-hosted.com"],
                spf=MS_SPF,
                gateway="proofpoint",
            ),
            0.70,
            "spf_gw",
        ),
        # dkim + gateway → dkim_gw 0.65
        (
            entry(
                "microsoft",
                mx=["mx1.ppe-hosted.com"],
                dkim=True,
                gateway="proofpoint",
            ),
            0.65,
            "dkim_gw",
        ),
        # dkim+spf senza routing (self-hosted gateway, step 4) → dkim_spf 0.60
        (
            entry("google", mx=["mail.comune.it"], spf=G_SPF, dkim=G_DKIM),
            0.60,
            "dkim_spf",
        ),
        # spf solo, no gateway → spf_only 0.50
        (
            entry("aruba", mx=["mail.comune.it"], spf="v=spf1 include:aruba.it -all"),
            0.50,
            "spf_only",
        ),
        # niente segnali attribuibili → fallback 0.40
        (entry("aruba"), 0.40, "fallback"),
    ],
)
def test_provider_rules_exact(e, exp_conf, exp_rule):
    conf, rule, _, _ = compute_confidence(e)
    assert rule == exp_rule, f"regola attesa {exp_rule}, ottenuta {rule}"
    assert abs(conf - exp_conf) < 1e-9, f"conf attesa {exp_conf}, ottenuta {conf}"


# === Attribuzione per-provider (#29 fix B) ===
def test_field_existence_is_not_attribution():
    """Il bug #29: dietro gateway, mx/spf esistono ma puntano ad ALTRO →
    non contano per il provider eletto. Qui solo il tenant (boost) resta:
    fallback 0.40 + 0.02 = 0.42, NON mx_spf 0.92."""
    e = entry(
        "microsoft",
        mx=["filter.seppmail.cloud"],
        spf="v=spf1 include:_spf.halley.it -all",
        tenant=True,
        gateway="seppmail",
    )
    conf, rule, sig, _ = compute_confidence(e)
    assert rule == "fallback"
    assert abs(conf - 0.42) < 1e-9
    assert sig == ["tenant"]


def test_dkim_of_another_provider_not_attributed():
    # google eletto ma DKIM punta a Microsoft → dkim NON attribuito
    e = entry("google", mx=G_MX, spf=G_SPF, dkim=dict(MS_DKIM))
    conf, rule, sig, _ = compute_confidence(e)
    assert rule == "mx_spf" and abs(conf - 0.90) < 1e-9
    assert "dkim" not in sig


def test_autodiscover_must_point_at_microsoft():
    # autodiscover verso la farm (proxy.zimbraopen.it) NON è un segnale
    # Microsoft (lezione #31)
    e = entry("microsoft", mx=["mx1.ppe-hosted.com"], dkim=True, gateway="proofpoint")
    e["autodiscover"] = {"autodiscover_cname": "proxy.zimbraopen.it"}
    conf, rule, sig, _ = compute_confidence(e)
    assert rule == "dkim_gw" and abs(conf - 0.65) < 1e-9
    assert "autodiscover" not in sig


def test_mx_attributed_via_asn_override():
    """Hostname custom su AS del provider (Aruba AS31034): il routing è
    provato dall'ASN → mx attribuito, mx_only 0.80."""
    e = entry("aruba", mx=["mail.comune.foo.it"], mx_asns=[31034])
    conf, rule, sig, _ = compute_confidence(e)
    assert rule == "mx_only" and abs(conf - 0.80) < 1e-9
    assert "mx" in sig


def test_mx_attributed_via_local_isp_asn():
    e = entry("local-isp", mx=["mail.foo.it"], mx_asns=[2586])
    conf, rule, sig, _ = compute_confidence(e)
    assert rule == "mx_only" and abs(conf - 0.80) < 1e-9


def test_miur_alias_uses_microsoft_keywords():
    e = entry(
        "istruzione-miur-tenant",
        mx=["istruzione-it.mail.protection.outlook.com"],
        spf=MS_SPF,
        dkim=True,
        tenant=True,
    )
    conf, rule, sig, _ = compute_confidence(e)
    assert rule == "mx_spf"
    assert abs(conf - 0.94) < 1e-9  # 0.90 + boost {dkim, tenant}
    assert {"mx", "spf", "dkim", "tenant"} <= set(sig)


def test_txt_token_boosts_matching_provider():
    e = entry("google", mx=G_MX, spf=G_SPF, txt={"google": "R9vBEx8"})
    conf, rule, sig, _ = compute_confidence(e)
    assert rule == "mx_spf" and abs(conf - 0.92) < 1e-9
    assert "txt_verification" in sig


def test_txt_token_of_other_provider_no_boost():
    e = entry("google", mx=G_MX, spf=G_SPF, txt={"microsoft": "ms123"})
    conf, rule, sig, _ = compute_confidence(e)
    assert abs(conf - 0.90) < 1e-9
    assert "txt_verification" not in sig


# === TENANT/AUTODISCOVER non determinano la base, solo boost ===
def test_tenant_not_in_base_rule():
    # microsoft con solo tenant (no mx/spf/dkim): present vuoto → fallback
    # + boost {tenant}=1 → 0.42
    conf, rule, sig, _ = compute_confidence(entry("microsoft", tenant=True))
    assert rule == "fallback"
    assert abs(conf - 0.42) < 1e-9
    assert "tenant" in sig


def test_tenant_only_for_ms365_boost():
    # google con tenant NON conta (non MS365) → mx_spf 0.90 senza boost
    conf, rule, sig, _ = compute_confidence(
        entry("google", mx=G_MX, spf=G_SPF, tenant=True)
    )
    assert "tenant" not in sig and rule == "mx_spf" and abs(conf - 0.90) < 1e-9


# === DOMESTIC/FOREIGN ===
@pytest.mark.parametrize(
    "e,exp_conf,exp_rule,exp_jur",
    [
        # independent con MX in IT + SPF → dom_mx_spf 0.80
        (
            entry("independent", mx=["mx.comune.it"], spf=True, mx_countries=["IT"]),
            0.80,
            "dom_mx_spf",
            "domestic",
        ),
        # independent con MX in IT, no SPF → dom_mx_only 0.70
        (
            entry("independent", mx=["mx.comune.it"], mx_countries=["IT"]),
            0.70,
            "dom_mx_only",
            "domestic",
        ),
        # independent con MX estero + SPF → frgn_mx_spf 0.60
        (
            entry("independent", mx=["mx.foo.de"], spf=True, mx_countries=["DE"]),
            0.60,
            "frgn_mx_spf",
            "foreign",
        ),
        # independent con MX estero, no SPF → frgn_mx_only 0.50
        (
            entry("independent", mx=["mx.foo.us"], mx_countries=["US"]),
            0.50,
            "frgn_mx_only",
            "foreign",
        ),
    ],
)
def test_domestic_foreign(e, exp_conf, exp_rule, exp_jur):
    conf, rule, _, jur = compute_confidence(e, target_country="IT")
    assert jur == exp_jur
    assert rule == exp_rule
    assert abs(conf - exp_conf) < 1e-9


# === Vendor-hosted (#29 scenario B): scala per giurisdizione ===
def test_vendor_hosted_domestic_mx_spf():
    """pa-contractor-private dal fallback vendor-relay: l'MX è la farm del
    fornitore → confidence per giurisdizione (dom_mx_spf 0.80), non regole
    provider."""
    e = entry(
        "pa-contractor-private",
        mx=["mx3.halley.it"],
        spf=True,
        gateway="halley",
        mx_countries=["IT"],
    )
    conf, rule, _, jur = compute_confidence(e)
    assert jur == "domestic"
    assert rule == "dom_mx_spf" and abs(conf - 0.80) < 1e-9


def test_vendor_hosted_domestic_mx_only():
    e = entry(
        "pa-contractor-private",
        mx=["mx.zimbraopen.it"],
        gateway="zimbraopen",
        mx_countries=["IT"],
    )
    conf, rule, _, _ = compute_confidence(e)
    assert rule == "dom_mx_only" and abs(conf - 0.70) < 1e-9


def test_contractor_direct_keyword_uses_provider_rules():
    """pa-contractor-private per match DIRETTO (MX eng.it, niente gateway):
    restano le regole provider (mx_only 0.80)."""
    e = entry("pa-contractor-private", mx=["mail.eng.it"])
    conf, rule, _, _ = compute_confidence(e)
    assert rule == "mx_only" and abs(conf - 0.80) < 1e-9


# === mx_jurisdiction ===
@pytest.mark.parametrize(
    "countries,expected",
    [
        (["IT"], "domestic"),
        (["IT", "IT"], "domestic"),
        (["US"], "foreign"),
        (["DE", "FR"], "foreign"),
        (["IT", "US"], "mixed"),
        ([], "unknown"),
        (None, "unknown"),
    ],
)
def test_mx_jurisdiction(countries, expected):
    e = {"provider": "independent"}
    if countries is not None:
        e["mx_countries"] = countries
    assert mx_jurisdiction(e, "IT") == expected


# === Domestic MX override ===
def test_override_fires_on_teams_only_tenant():
    # microsoft via tenant, ma MX self-hosted domestico → override
    e = entry("microsoft", mx=["mail.comune.foo.it"], tenant=True, mx_countries=["IT"])
    assert needs_domestic_mx_override(e) is True


def test_override_skips_genuine_cloud_mx():
    # microsoft con MX cloud genuino → NO override
    e = entry(
        "microsoft",
        mx=["comune-foo-it.mail.protection.outlook.com"],
        tenant=True,
        mx_countries=["US"],
    )
    assert needs_domestic_mx_override(e) is False


def test_override_skips_miur_schools():
    # scuola MIM: MX È il tenant centrale outlook → cloud genuino, no override
    e = entry(
        "istruzione-miur-tenant",
        mx=["istruzione-it.mail.protection.outlook.com"],
        dkim=True,
        mx_countries=["US"],
    )
    assert needs_domestic_mx_override(e) is False


def test_override_skips_google_genuine():
    e = entry("google", mx=["alt1.aspmx.l.google.com"], mx_countries=["US"])
    assert needs_domestic_mx_override(e) is False


def test_override_skips_gateway_cases():
    # microsoft via gateway look-through (DKIM dietro Sophos): MX è il gateway,
    # non outlook, ma il backend È Microsoft → NO override (come ESORICS)
    e = entry(
        "microsoft",
        mx=["mx-01.prod.hydra.sophos.com"],
        dkim=True,
        gateway="sophos",
        mx_countries=["IT"],
    )
    assert needs_domestic_mx_override(e) is False


# === Unknown ===
def test_unknown_no_mx():
    conf, rule, sig, jur = compute_confidence(entry("unknown"))
    assert conf == 0.0 and rule == "no_mx" and sig == []


def test_unknown_behind_gateway_is_gateway_no_primary():
    """#29 B: unknown CON MX dietro gateway → gateway_no_primary 0.0
    (come il paper), non no_mx."""
    e = entry("unknown", mx=["mx.hydra.sophos.com"], gateway="sophos")
    conf, rule, sig, _ = compute_confidence(e)
    assert conf == 0.0 and rule == "gateway_no_primary" and sig == []


# === Funzioni basso livello (parità upstream) ===
def test_rule_confidence_boost():
    # mx+spf+dkim: mx_spf 0.90 + boost {dkim}=1 → 0.92
    conf, rule = _rule_confidence({"mx", "spf", "dkim"}, None)
    assert rule == "mx_spf" and abs(conf - 0.92) < 1e-9


def test_country_confidence_levels():
    assert _country_confidence(True, True, False, _DOMESTIC_RULES) == (
        0.80,
        "dom_mx_spf",
    )
    assert _country_confidence(True, False, False, _DOMESTIC_RULES) == (
        0.70,
        "dom_mx_only",
    )
    assert _country_confidence(False, False, False, _FOREIGN_RULES) == (
        0.0,
        "frgn_none",
    )
    assert _country_confidence(True, True, False, _FOREIGN_RULES) == (
        0.60,
        "frgn_mx_spf",
    )
