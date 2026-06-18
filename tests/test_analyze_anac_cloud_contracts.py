"""Unit tests for scripts/analyze_anac_cloud_contracts.py.

Tests the keyword detection, deduplication, and category classification
logic without needing the full 49MB ANAC dataset.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from analyze_anac_cloud_contracts import (  # noqa: E402
    PROVIDER_CATEGORY,
    aggregate_summary,
    deduplicate_by_ocid,
    find_provider,
)


# ── find_provider ──


def test_find_provider_microsoft():
    assert find_provider("Migrazione a Microsoft 365 del Comune") == "microsoft"


def test_find_provider_office_365():
    """'office 365' alone should match Microsoft."""
    assert find_provider("Fornitura licenze Office 365") == "microsoft"


def test_find_provider_azure():
    assert find_provider("Servizi cloud Azure per ASL") == "microsoft"


def test_find_provider_google_workspace():
    assert find_provider("Adozione Google Workspace") == "google"


def test_find_provider_aws():
    assert find_provider("Migrazione AWS cloud") == "aws"


def test_find_provider_amazonses():
    assert find_provider("Invio newsletter via amazonses") == "aws"


def test_find_provider_oracle():
    assert find_provider("Licenze Oracle Database") == "oracle"


def test_find_provider_ibm():
    assert find_provider("Manutenzione IBM AS/400") == "ibm"


def test_find_provider_salesforce():
    assert find_provider("CRM Salesforce per INPS") == "salesforce"


def test_find_provider_sap():
    assert find_provider("SAP Cloud Platform") == "sap"


def test_find_provider_psn():
    assert find_provider("Migrazione al Polo Strategico Nazionale") == "psn"


def test_find_provider_tim():
    assert find_provider("Cloud TIM per PA") == "tim"


def test_find_provider_fastweb():
    assert find_provider("Servizi Fastweb") == "fastweb"


def test_find_provider_aruba():
    assert find_provider("Hosting Aruba") == "aruba"


def test_find_provider_engineering():
    assert find_provider("Engineering gestisce servizi cloud") == "engineering"


def test_find_provider_lutech():
    assert find_provider("Piattaforma Lutech") == "lutech"


def test_find_provider_cloud_generic():
    """Generic 'cloud computing' → 'cloud_generic' (not a specific vendor)."""
    assert find_provider("Servizi di cloud computing") == "cloud_generic"


def test_find_provider_prefers_hyperscaler():
    """When both 'cloud computing' and 'azure' are present, prefer Azure."""
    result = find_provider("Migrazione cloud computing su Azure")
    assert result == "microsoft"


def test_find_provider_no_match():
    assert find_provider("Servizi di pulizia degli uffici") is None
    assert find_provider("") is None
    assert find_provider(None) is None


def test_find_provider_case_insensitive():
    assert find_provider("MICROSOFT OFFICE 365") == "microsoft"
    assert find_provider("google WORKSPACE") == "google"


# ── deduplicate_by_ocid ──


def test_deduplicate_single_ocid_single_supplier():
    records = [
        {
            "ocid": "ocds-1",
            "buyer_name": "PA",
            "value": 1000.0,
            "supplier": ["VENDOR_A"],
            "detected_provider": "microsoft",
            "title": "",
            "desc": "",
            "buyer_id": "",
            "currency": "EUR",
            "date": "",
        }
    ]
    dedup = deduplicate_by_ocid(records)
    assert len(dedup) == 1
    assert dedup[0]["supplier"] == ["VENDOR_A"]


def test_deduplicate_single_ocid_multiple_suppliers():
    """ATI partners in one OCID are merged into a single record."""
    records = [
        {
            "ocid": "ocds-PSN",
            "buyer_name": "PCM",
            "value": 2_563_675_000.0,
            "supplier": ["SOGEI"],
            "detected_provider": "psn",
            "title": "",
            "desc": "",
            "buyer_id": "",
            "currency": "EUR",
            "date": "",
        },
        {
            "ocid": "ocds-PSN",
            "buyer_name": "PCM",
            "value": 2_563_675_000.0,
            "supplier": ["TIM"],
            "detected_provider": "psn",
            "title": "",
            "desc": "",
            "buyer_id": "",
            "currency": "EUR",
            "date": "",
        },
        {
            "ocid": "ocds-PSN",
            "buyer_name": "PCM",
            "value": 2_563_675_000.0,
            "supplier": ["LEONARDO"],
            "detected_provider": "psn",
            "title": "",
            "desc": "",
            "buyer_id": "",
            "currency": "EUR",
            "date": "",
        },
    ]
    dedup = deduplicate_by_ocid(records)
    assert len(dedup) == 1  # 3 records → 1 OCID
    assert set(dedup[0]["supplier"]) == {"SOGEI", "TIM", "LEONARDO"}
    # Value is NOT summed (it's the same value reported for each ATI partner)
    assert dedup[0]["value"] == 2_563_675_000.0


def test_deduplicate_multiple_ocids():
    records = [
        {
            "ocid": "ocds-1",
            "buyer_name": "PA1",
            "value": 100.0,
            "supplier": ["V1"],
            "detected_provider": "microsoft",
            "title": "",
            "desc": "",
            "buyer_id": "",
            "currency": "EUR",
            "date": "",
        },
        {
            "ocid": "ocds-2",
            "buyer_name": "PA2",
            "value": 200.0,
            "supplier": ["V2"],
            "detected_provider": "google",
            "title": "",
            "desc": "",
            "buyer_id": "",
            "currency": "EUR",
            "date": "",
        },
    ]
    dedup = deduplicate_by_ocid(records)
    assert len(dedup) == 2


# ── aggregate_summary ──


def test_aggregate_basic():
    records = [
        {
            "ocid": "1",
            "value": 1000.0,
            "supplier": ["MS_DIRECT"],
            "detected_provider": "microsoft",
        },
        {
            "ocid": "2",
            "value": 500.0,
            "supplier": ["ORACLE_IT"],
            "detected_provider": "oracle",
        },
        {
            "ocid": "3",
            "value": 0.0,
            "supplier": ["PSN"],
            "detected_provider": "psn",
        },
    ]
    summary = aggregate_summary(records)
    # Only records with value > 0 are counted
    assert summary["by_category"]["hyperscaler_usa"]["count"] == 2
    assert summary["by_category"]["hyperscaler_usa"]["value_eur"] == 1500.0
    assert summary["by_hyperscaler"]["microsoft"]["value_eur"] == 1000.0
    assert summary["by_hyperscaler"]["oracle"]["value_eur"] == 500.0


def test_aggregate_ati_split_value():
    """When 1 OCID has 2 ATI suppliers, each gets half the value."""
    records = [
        {
            "ocid": "ATI-1",
            "value": 1000.0,
            "supplier": ["A", "B"],
            "detected_provider": "psn",
        },
    ]
    summary = aggregate_summary(records)
    psn = summary["by_category"]["italian_sovereign"]
    # 1 OCID with value
    assert psn["count"] == 1
    assert psn["value_eur"] == 1000.0
    # Each supplier gets 500
    assert psn["top_suppliers"]["A"] == 500.0
    assert psn["top_suppliers"]["B"] == 500.0


# ── PROVIDER_CATEGORY consistency ──


def test_provider_category_completeness():
    """Every keyword provider must have a category."""
    from analyze_anac_cloud_contracts import PROVIDER_KEYWORDS

    for provider in PROVIDER_KEYWORDS:
        assert provider in PROVIDER_CATEGORY, (
            f"Provider {provider} has keywords but no category mapping"
        )


def test_hyperscalers_marked_usa_or_eu():
    """The 3 main hyperscalers + IBM/Oracle/Salesforce should be hyperscaler_usa/eu."""
    expected_usa = {"microsoft", "google", "aws", "oracle", "ibm", "salesforce"}
    for p in expected_usa:
        assert PROVIDER_CATEGORY.get(p) == "hyperscaler_usa", (
            f"{p} should be hyperscaler_usa"
        )
    assert PROVIDER_CATEGORY["sap"] == "hyperscaler_eu"
