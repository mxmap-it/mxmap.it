"""Pytest per src/mail_sovereignty/scrape_validator.py.

I 48 casi accept/reject sono la single source of truth in
scripts/_test_scrape_validator.py (CASES); qui li importiamo e li
parametrizziamo, più test diretti sui helper (fuzzy DL, label
concatenation, scope PA-shared, is_local_pa_domain) per coprire tutti
i rami del modulo — il validatore è il componente critico per la
correttezza dell'attribuzione MX.
"""
import importlib.util as _ilu
from pathlib import Path

import pytest

from mail_sovereignty.scrape_validator import (
    is_legit_email_domain,
    meaningful_labels,
    is_local_pa_domain,
    _fuzzy_label_match,
    _label_concatenation_match,
    _damerau_levenshtein,
    _ente_in_region,
    PA_SHARED_PLATFORMS_NATIONAL,
    PA_SHARED_PLATFORMS_LOCAL_BY_REGION,
    PEC_PROVIDERS,
)

# Importa la lista CASES dallo script standalone (single source of truth).
_script = Path(__file__).resolve().parent.parent / "scripts" / "_test_scrape_validator.py"
_spec = _ilu.spec_from_file_location("_svcases", str(_script))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
CASES = _mod.CASES


@pytest.mark.parametrize("scraped,ente,expected,desc", CASES)
def test_is_legit_email_domain_cases(scraped, ente, expected, desc):
    got, reason = is_legit_email_domain(scraped, ente)
    assert got == expected, (
        f"{scraped!r} vs {ente!r}: atteso {expected}, ottenuto {got} "
        f"(reason={reason}) — {desc}"
    )


def test_empty_inputs():
    assert is_legit_email_domain("", "comune.foo.it")[0] is False
    assert is_legit_email_domain("comune.foo.it", "")[0] is False


def test_exact_match_reason():
    ok, reason = is_legit_email_domain("comune.padova.it", "comune.padova.it")
    assert ok and reason == "exact_match"


def test_pec_providers_all_rejected():
    for pec in list(PEC_PROVIDERS)[:10]:
        ok, reason = is_legit_email_domain(pec, "comune.foo.it")
        assert not ok and reason.startswith("pec_provider")


def test_manual_override_accepts():
    ok, reason = is_legit_email_domain(
        "qualcosa.it", "comune.foo.it",
        codice_ipa="c_xxxx", manual_overrides={"c_xxxx": "qualcosa.it"})
    assert ok and reason == "manual_override"


# --- meaningful_labels ---
@pytest.mark.parametrize("domain,expected", [
    ("interno.gov.it", {"interno"}),
    ("comune.roccagorga.lt.it", {"roccagorga"}),
    ("mail.comune.padova.it", {"padova"}),
    ("interno.it", {"interno"}),
    ("", set()),
])
def test_meaningful_labels(domain, expected):
    assert meaningful_labels(domain) == expected


# --- is_local_pa_domain ---
@pytest.mark.parametrize("domain,expected", [
    ("comune.milano.it", True),
    ("provincia.lecce.it", True),
    ("comune.bolzano.bz.it", True),
    ("interno.gov.it", False),       # gov.it = nazionale, mai local
    ("salute.gov.it", False),
    ("peritiagrari.it", False),      # ordine, no marker local
])
def test_is_local_pa_domain(domain, expected):
    assert is_local_pa_domain(domain) is expected


# --- Damerau-Levenshtein ---
@pytest.mark.parametrize("a,b,dist", [
    ("abc", "abc", 0),
    ("abc", "abd", 1),       # sostituzione
    ("abc", "ab", 1),        # cancellazione
    ("ab", "abc", 1),        # inserimento
    ("ab", "ba", 1),         # trasposizione adiacente
    ("", "abc", 3),
    ("consofarm", "consorfarm", 1),
])
def test_damerau_levenshtein(a, b, dist):
    assert _damerau_levenshtein(a, b) == dist


# --- fuzzy label match (rule 6.5) ---
def test_fuzzy_label_match_positive():
    ok, pair = _fuzzy_label_match({"consofarm"}, {"consorfarm"})
    assert ok and "consofarm" in pair


def test_fuzzy_label_match_too_short():
    # label < 6 char non devono matchare (roma/noma)
    ok, _ = _fuzzy_label_match({"roma"}, {"noma"})
    assert not ok


def test_fuzzy_label_match_distance_too_large():
    ok, _ = _fuzzy_label_match({"abcdefgh"}, {"abcdwxyz"})  # DL > 1
    assert not ok


# --- label concatenation (rule 6.6) ---
def test_label_concatenation_positive():
    ok, pair = _label_concatenation_match({"aciarezzo"}, {"arezzo", "aci"})
    assert ok and "aciarezzo" in pair


def test_label_concatenation_needs_two_labels():
    # un solo label dell'ente → no match
    ok, _ = _label_concatenation_match({"aciarezzo"}, {"arezzo"})
    assert not ok


# --- region scoping ---
@pytest.mark.parametrize("ente,region,expected", [
    ("comune.milano.it", "lombardia", True),     # capoluogo
    ("comune.bologna.it", "emilia-romagna", True),
    ("comune.albianodivrea.to.it", "piemonte", True),   # province code TO
    ("comune.palermo.it", "lombardia", False),   # wrong region
    ("comune.aosta.vda.it", "valle-d-aosta", True),
])
def test_ente_in_region(ente, region, expected):
    assert _ente_in_region(ente, region) is expected


def test_national_platforms_accepted_for_gov():
    for plat in PA_SHARED_PLATFORMS_NATIONAL:
        ok, reason = is_legit_email_domain(plat, "interno.gov.it")
        assert ok, f"{plat} dovrebbe essere accettato per PA nazionale"
        assert reason.startswith("pa_shared_national")


def test_local_platform_rejected_for_national():
    # Una piattaforma regionale NON deve valere per un ministero nazionale
    for plat in list(PA_SHARED_PLATFORMS_LOCAL_BY_REGION)[:5]:
        ok, reason = is_legit_email_domain(plat, "interno.gov.it")
        assert not ok, f"{plat} non deve valere per interno.gov.it"
