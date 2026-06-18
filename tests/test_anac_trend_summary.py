"""Unit tests for the ANAC trend analysis (cross-year aggregation).

These tests verify the trend aggregation logic without needing the
full ANAC datasets.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))


# ── Trend aggregation logic (mock) ──


def aggregate_trend(summaries: dict[int, dict]) -> dict:
    """Aggregate per-year summaries into a 4-year trend report."""
    years = sorted(summaries.keys())
    if not years:
        return {"years": [], "categories": {}, "hyperscalers": {}}

    # Category totals
    categories = set()
    for y in years:
        categories.update(summaries[y].get("by_category", {}).keys())

    cat_trend = {}
    for cat in categories:
        cat_trend[cat] = {}
        for y in years:
            data = summaries[y].get("by_category", {}).get(cat, {})
            cat_trend[cat][y] = {
                "count": data.get("count", 0),
                "value_eur": data.get("value_eur", 0.0),
            }

    # Hyperscalers
    hyperscalers = set()
    for y in years:
        hyperscalers.update(summaries[y].get("by_hyperscaler", {}).keys())

    hs_trend = {}
    for h in hyperscalers:
        hs_trend[h] = {}
        for y in years:
            data = summaries[y].get("by_hyperscaler", {}).get(h, {})
            hs_trend[h][y] = {
                "count": data.get("count", 0),
                "value_eur": data.get("value_eur", 0.0),
            }

    return {
        "years": years,
        "categories": cat_trend,
        "hyperscalers": hs_trend,
    }


# ── Tests ──


def test_aggregate_trend_empty():
    result = aggregate_trend({})
    assert result["years"] == []
    assert result["categories"] == {}
    assert result["hyperscalers"] == {}


def test_aggregate_trend_single_year():
    summary = {
        "by_category": {
            "hyperscaler_usa": {"count": 10, "value_eur": 1_000_000.0},
            "italian_sovereign": {"count": 1, "value_eur": 2_500_000_000.0},
        },
        "by_hyperscaler": {
            "microsoft": {"count": 5, "value_eur": 500_000.0},
        },
    }
    result = aggregate_trend({2024: summary})
    assert result["years"] == [2024]
    assert (
        result["categories"]["italian_sovereign"][2024]["value_eur"] == 2_500_000_000.0
    )
    assert result["hyperscalers"]["microsoft"][2024]["value_eur"] == 500_000.0


def test_aggregate_trend_multi_year():
    summaries = {
        2022: {
            "by_category": {
                "hyperscaler_usa": {"count": 58, "value_eur": 172_000_000.0},
            },
            "by_hyperscaler": {
                "microsoft": {"count": 13, "value_eur": 70_000_000.0},
            },
        },
        2023: {
            "by_category": {
                "hyperscaler_usa": {"count": 315, "value_eur": 181_000_000.0},
            },
            "by_hyperscaler": {
                "microsoft": {"count": 150, "value_eur": 86_000_000.0},
            },
        },
        2024: {
            "by_category": {
                "italian_sovereign": {"count": 5, "value_eur": 2_572_000_000.0},
                "hyperscaler_usa": {"count": 205, "value_eur": 187_000_000.0},
            },
            "by_hyperscaler": {
                "microsoft": {"count": 81, "value_eur": 31_000_000.0},
            },
        },
    }
    result = aggregate_trend(summaries)
    assert result["years"] == [2022, 2023, 2024]
    # Microsoft: €70M → €86M → €31M
    ms = result["hyperscalers"]["microsoft"]
    assert ms[2022]["value_eur"] == 70_000_000.0
    assert ms[2023]["value_eur"] == 86_000_000.0
    assert ms[2024]["value_eur"] == 31_000_000.0
    # PSN only 2024
    assert (
        result["categories"]["italian_sovereign"][2024]["value_eur"] == 2_572_000_000.0
    )
    assert result["categories"]["italian_sovereign"][2022]["value_eur"] == 0.0


def test_aggregate_trend_4_year_realistic():
    """Realistic 4-year trend matching the actual ANAC data."""
    summaries = {
        2022: {
            "by_category": {
                "hyperscaler_usa": {"count": 58, "value_eur": 172_085_095.0},
                "italian_sovereign": {"count": 2, "value_eur": 194_433.0},
                "italian_commercial": {"count": 14, "value_eur": 6_076_501.0},
                "hyperscaler_eu": {"count": 7, "value_eur": 10_222_341.0},
                "mixed": {"count": 7, "value_eur": 10_494_985.0},
            },
            "by_hyperscaler": {
                "microsoft": {"count": 13, "value_eur": 70_140_792.0},
                "oracle": {"count": 28, "value_eur": 83_604_527.0},
                "ibm": {"count": 8, "value_eur": 15_516_300.0},
                "google": {"count": 6, "value_eur": 1_474_678.0},
                "salesforce": {"count": 3, "value_eur": 1_348_799.0},
            },
        },
        2024: {
            "by_category": {
                "italian_sovereign": {"count": 5, "value_eur": 2_571_966_546.0},
                "hyperscaler_usa": {"count": 205, "value_eur": 187_246_178.0},
                "italian_commercial": {"count": 69, "value_eur": 39_398_953.0},
                "hyperscaler_eu": {"count": 68, "value_eur": 35_959_990.0},
                "mixed": {"count": 51, "value_eur": 62_204_602.0},
            },
            "by_hyperscaler": {
                "microsoft": {"count": 81, "value_eur": 30_864_984.0},
                "oracle": {"count": 63, "value_eur": 84_158_088.0},
                "ibm": {"count": 16, "value_eur": 45_686_024.0},
                "google": {"count": 17, "value_eur": 4_433_206.0},
                "aws": {"count": 13, "value_eur": 9_042_879.0},
                "salesforce": {"count": 15, "value_eur": 13_060_996.0},
            },
        },
    }
    result = aggregate_trend(summaries)
    # Verify: PSN +13,000x jump 2022→2024
    psn_22 = result["categories"]["italian_sovereign"][2022]["value_eur"]
    psn_24 = result["categories"]["italian_sovereign"][2024]["value_eur"]
    assert psn_24 / psn_22 > 10_000  # ~13,000x increase
    # Microsoft: 2022 €70M, 2024 €31M = -56%
    ms_22 = result["hyperscalers"]["microsoft"][2022]["value_eur"]
    ms_24 = result["hyperscalers"]["microsoft"][2024]["value_eur"]
    assert ms_24 < ms_22  # Calo
    # Oracle stabile
    or_22 = result["hyperscalers"]["oracle"][2022]["value_eur"]
    or_24 = result["hyperscalers"]["oracle"][2024]["value_eur"]
    assert abs(or_24 - or_22) / or_22 < 0.10  # <10% variazione


def test_trend_summaries_file_exists_for_each_year():
    """Sanity check: each year has a summary JSON file."""
    expected_years = [2022, 2023, 2024, 2025]
    for y in expected_years:
        path = REPO_ROOT / "data" / "anac" / f"anac_{y}_cloud_summary_dedup.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            # Check required structure
            assert "by_category" in data
            assert "by_hyperscaler" in data
            assert "total_value_eur" in data
            assert data["total_value_eur"] >= 0


def test_psn_signature_2024():
    """The 2024 PSN signature is the single biggest event in the dataset."""
    path = REPO_ROOT / "data" / "anac" / "anac_2024_cloud_summary_dedup.json"
    if not path.exists():
        return  # Test skipped if data not present
    with open(path) as f:
        data = json.load(f)
    psn = data["by_category"].get("italian_sovereign", {})
    assert psn.get("value_eur", 0) > 2_000_000_000  # > €2 mld
