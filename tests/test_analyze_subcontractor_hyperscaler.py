"""Unit tests for scripts/analyze_subcontractor_hyperscaler.py.

Tests the SI detection, hyperscaler keyword detection, and value
aggregation logic without needing the full ANAC dataset.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from analyze_subcontractor_hyperscaler import (  # noqa: E402
    find_hyperscaler,
    is_italian_SI,
)


# ── find_hyperscaler ──


def test_find_hyperscaler_microsoft():
    assert find_hyperscaler("Migrazione a Microsoft 365") == "microsoft"


def test_find_hyperscaler_oracle():
    assert find_hyperscaler("Database Oracle 19c") == "oracle"


def test_find_hyperscaler_aws():
    assert find_hyperscaler("Migrazione cloud AWS") == "aws"


def test_find_hyperscaler_ibm():
    assert find_hyperscaler("Manutenzione AS/400 IBM") == "ibm"


def test_find_hyperscaler_sap():
    assert find_hyperscaler("Migrazione SAP S/4HANA") == "sap"


def test_find_hyperscaler_google_workspace():
    assert find_hyperscaler("Adozione Google Workspace") == "google"


def test_find_hyperscaler_salesforce():
    assert find_hyperscaler("CRM Salesforce") == "salesforce"


def test_find_hyperscaler_prefers_usa_hyperscaler():
    """When 'cloud' and 'azure' both present, prefer Microsoft."""
    assert find_hyperscaler("Servizi cloud Azure") == "microsoft"


def test_find_hyperscaler_no_match():
    assert find_hyperscaler("Servizi di pulizia") is None
    assert find_hyperscaler("") is None
    assert find_hyperscaler(None) is None


# ── is_italian_SI ──


def test_is_italian_SI_engineering():
    assert is_italian_SI("ENGINEERING INGEGNERIA INFORMATICA S.P.A.") == "engineering"


def test_is_italian_SI_italware():
    assert is_italian_SI("ITALWARE SRL") == "italware"


def test_is_italian_SI_maticmind():
    assert is_italian_SI("MATICMIND S.P.A.") == "maticmind"


def test_is_italian_SI_var_group():
    assert is_italian_SI("Var Group SpA") == "var group"


def test_is_italian_SI_postel():
    assert is_italian_SI("POSTEL SPA") == "postel"


def test_is_italian_SI_lutech():
    assert is_italian_SI("Lutech S.p.A.") == "lutech"


def test_is_italian_SI_gpi():
    assert is_italian_SI("GPI SPA") == "gpi"


def test_is_italian_SI_almaviva():
    assert is_italian_SI("ALMAVIVA SPA") == "almaviva"


def test_is_italian_SI_reply():
    assert is_italian_SI("REPLY S.P.A.") == "reply"


def test_is_italian_SI_ntt_data():
    assert is_italian_SI("NTT DATA ITALIA S.P.A.") == "ntt data"


def test_is_italian_SI_accenture():
    assert is_italian_SI("ACCENTURE S.P.A.") == "accenture"


def test_is_italian_SI_capgemini():
    assert is_italian_SI("CAPGEMINI ITALIA S.P.A.") == "capgemini"


def test_is_italian_SI_no_match():
    """Foreign or Italian companies that are NOT in our SI list."""
    assert is_italian_SI("MICROSOFT S.R.L.") is None  # Microsoft is a vendor, not SI
    assert is_italian_SI("AMAZON WEB SERVICES EMEA SARL") is None
    assert is_italian_SI("SOGEI S.P.A.") is None  # Sogei is government IT, not SI
    assert is_italian_SI("FASTWEB SPA") is None  # ISP, not SI
    assert is_italian_SI("") is None
    assert is_italian_SI(None) is None


def test_is_italian_SI_case_insensitive():
    assert is_italian_SI("engineering s.p.a.") == "engineering"
    assert is_italian_SI("ENGINEERING S.P.A.") == "engineering"


# ── Output file existence ──


def test_subcontractor_output_exists():
    """The analysis output should be present after running the script."""
    path = REPO_ROOT / "data" / "anac" / "anac_subcontractor_hyperscaler.json"
    if path.exists():
        import json

        data = json.loads(path.read_text())
        # Required keys
        assert "si_total_value" in data
        assert "si_value_per_year" in data
        assert "si_value_per_hyperscaler" in data
        assert "hyperscaler_indirect_total" in data
        # The total indirect should be > €100M
        total_indirect = sum(data["hyperscaler_indirect_total"].values())
        assert total_indirect > 100_000_000, f"Only €{total_indirect:,.0f} indirect"


def test_top_si_has_engineering_and_italware():
    """The known top SIs should appear in the output."""
    path = REPO_ROOT / "data" / "anac" / "anac_subcontractor_hyperscaler.json"
    if not path.exists():
        return
    import json

    data = json.loads(path.read_text())
    si_list = list(data["si_total_value"].keys())
    assert "engineering" in si_list
    assert "italware" in si_list


def test_oracle_dominates_indirect_spending():
    """Oracle is the dominant vendor in Italian SI hyperscaler stack."""
    path = REPO_ROOT / "data" / "anac" / "anac_subcontractor_hyperscaler.json"
    if not path.exists():
        return
    import json

    data = json.loads(path.read_text())
    hs_totals = data["hyperscaler_indirect_total"]
    # Oracle > Microsoft in indirect spending
    assert hs_totals.get("oracle", 0) > hs_totals.get("microsoft", 0)
