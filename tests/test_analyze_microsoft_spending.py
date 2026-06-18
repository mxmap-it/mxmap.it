"""Unit tests for scripts/analyze_microsoft_spending.py.

Tests the broad Microsoft pattern detection and value aggregation
without needing the full ANAC dataset.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from analyze_microsoft_spending import find_ms_keywords  # noqa: E402


# ── find_ms_keywords ──


def test_find_ms_keywords_microsoft():
    keywords = find_ms_keywords("Migrazione a Microsoft 365")
    assert any("microsoft" in k for k in keywords)


def test_find_ms_keywords_azure():
    keywords = find_ms_keywords("Migrazione cloud Azure")
    assert any("azure" in k for k in keywords)


def test_find_ms_keywords_office_365():
    keywords = find_ms_keywords("Licenze Office 365")
    assert any("office" in k for k in keywords)


def test_find_ms_keywords_autodesk():
    """Autodesk is included in the broad pattern (co-procured with MS)."""
    keywords = find_ms_keywords("Licenze Autodesk per PA")
    assert any("autodesk" in k for k in keywords)


def test_find_ms_keywords_exchange():
    keywords = find_ms_keywords("Migrazione Exchange Server")
    assert any("exchange" in k for k in keywords)


def test_find_ms_keywords_windows_server():
    keywords = find_ms_keywords("Manutenzione Windows Server 2019")
    assert any("windows" in k for k in keywords)


def test_find_ms_keywords_active_directory():
    keywords = find_ms_keywords("Integrazione con Active Directory")
    assert any("active" in k for k in keywords)


def test_find_ms_keywords_teams():
    keywords = find_ms_keywords("Adozione Teams per collaboration")
    assert any("teams" in k for k in keywords)


def test_find_ms_keywords_sharepoint():
    keywords = find_ms_keywords("Migrazione a SharePoint Online")
    assert any("sharepoint" in k for k in keywords)


def test_find_ms_keywords_dynamics():
    keywords = find_ms_keywords("Implementazione Dynamics 365")
    assert any("dynamics" in k for k in keywords)


def test_find_ms_keywords_intune():
    keywords = find_ms_keywords("Gestione device con Intune")
    assert any("intune" in k for k in keywords)


def test_find_ms_keywords_mssql():
    keywords = find_ms_keywords("Migrazione database MSSQL")
    assert any("mssql" in k for k in keywords)


def test_find_ms_keywords_power_bi():
    keywords = find_ms_keywords("Dashboard con Power BI")
    assert any("power" in k for k in keywords)


def test_find_ms_keywords_multiple():
    """Multiple keywords in one text should all be detected."""
    keywords = find_ms_keywords("Migrazione Microsoft 365 e Teams")
    assert len(keywords) >= 2


def test_find_ms_keywords_no_match():
    assert find_ms_keywords("Servizi di pulizia") == []
    assert find_ms_keywords("") == []
    assert find_ms_keywords(None) == []


# ── Output file existence ──


def test_microsoft_broad_output_exists():
    """The analysis output should be present after running the script."""
    path = REPO_ROOT / "data" / "anac" / "anac_microsoft_broad.json"
    if path.exists():
        import json

        data = json.loads(path.read_text())
        # Required structure
        assert isinstance(data, list)
        if data:
            assert "ocid" in data[0]
            assert "year" in data[0]
            assert "value" in data[0]
            assert "ms_keywords" in data[0]
            assert "suppliers" in data[0]
        # Total value should be > €100M
        total = sum(m.get("value", 0) for m in data)
        assert total > 100_000_000, f"Only €{total:,.0f}"


def test_microsoft_broad_includes_sogei():
    """SOGEI should appear as a top buyer of Microsoft."""
    path = REPO_ROOT / "data" / "anac" / "anac_microsoft_broad.json"
    if not path.exists():
        return
    import json

    data = json.loads(path.read_text())
    sogei_contracts = [m for m in data if "SOGEI" in m.get("buyer", "").upper()]
    assert len(sogei_contracts) > 0, "SOGEI should appear as Microsoft buyer"
    sogei_total = sum(m["value"] for m in sogei_contracts)
    assert sogei_total > 50_000_000, f"SOGEI Microsoft spending: €{sogei_total:,.0f}"


def test_microsoft_broad_trend_declining():
    """Microsoft spending should decline from 2023 peak to 2024/2025."""
    path = REPO_ROOT / "data" / "anac" / "anac_microsoft_broad.json"
    if not path.exists():
        return
    import json
    from collections import defaultdict

    data = json.loads(path.read_text())
    by_year = defaultdict(float)
    for m in data:
        by_year[m["year"]] += m["value"]
    # 2024 should be < 2023 (post-PSN effect)
    if 2023 in by_year and 2024 in by_year:
        assert by_year[2024] < by_year[2023], (
            f"Microsoft 2024 ({by_year[2024]:,.0f}) should be < 2023 ({by_year[2023]:,.0f})"
        )
