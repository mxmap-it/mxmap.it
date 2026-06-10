"""Pytest per src/mail_sovereignty/mx_discovery.py (taxonomy provenance MX)."""

import pytest

from mail_sovereignty.mx_discovery import (
    METHODS,
    set_discovery,
    infer_method_from_entry,
    SEED_SOURCE_TO_METHOD,
)


def test_methods_well_formed():
    """Ogni method ha (label, tooltip) non vuoti."""
    assert "unknown" in METHODS
    assert "seed_primary_mx" in METHODS
    for tag, val in METHODS.items():
        assert isinstance(val, tuple) and len(val) == 2
        label, tip = val
        assert label and tip, f"{tag} ha label/tooltip vuoto"


def test_seed_source_map_targets_valid_methods():
    """Ogni valore di SEED_SOURCE_TO_METHOD è un tag valido in METHODS."""
    for src, method in SEED_SOURCE_TO_METHOD.items():
        assert method in METHODS, f"{src} -> {method} non in METHODS"


def test_set_discovery_valid():
    e = {}
    set_discovery(e, "seed_primary_mx", "interno.it")
    assert e["mx_discovery_method"] == "seed_primary_mx"
    assert e["mx_discovery_evidence"] == "interno.it"


def test_set_discovery_no_evidence():
    e = {}
    set_discovery(e, "unknown")
    assert e["mx_discovery_method"] == "unknown"
    assert "mx_discovery_evidence" not in e


def test_set_discovery_rejects_unknown_tag():
    with pytest.raises(ValueError):
        set_discovery({}, "not_a_real_tag")


@pytest.mark.parametrize(
    "entry,expected_method",
    [
        ({"miur_tenant_dependency": True}, "istruzione_miur_tenant"),
        (
            {
                "domain_correction_source": "indicepa_aoo_uo_tier6",
                "domain_used": "x.it",
            },
            "aoo_uo_tier6",
        ),
        (
            {"domain_correction_source": "wikidata_p856", "domain_used": "x.it"},
            "wikidata_p856",
        ),
        (
            {
                "domain_correction_source": "homepage_scrape_primary",
                "domain_used": "x.it",
            },
            "homepage_scrape",
        ),
        (
            {"domain_correction_source": "search_engine", "domain_used": "x.it"},
            "search_engine_scrape",
        ),
        ({"public_pec_match": "cert.ruparpiemonte.it"}, "public_pec_inference"),
        ({"scraped_email": "info@x.it"}, "homepage_scrape"),
        (
            {"recovery_legit_reason": "fuzzy_match:a~b", "domain_used": "x.it"},
            "domain_fallback",
        ),
        ({"domain_used": "x.it"}, "domain_fallback"),
        ({"provider": "unknown"}, "unknown"),
        ({"mx": ["mx.x.it"], "domain": "x.it"}, "seed_primary_mx"),
        ({}, "unknown"),
    ],
)
def test_infer_method_from_entry(entry, expected_method):
    method, _evidence = infer_method_from_entry(entry)
    assert method == expected_method
