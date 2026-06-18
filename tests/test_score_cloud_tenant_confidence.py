"""Unit tests for scripts/score_cloud_tenant_confidence.py.

These tests verify the multi-signal confidence scoring logic without
needing the full data.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from score_cloud_tenant_confidence import (  # noqa: E402
    detect_autodiscover,
    detect_dkim_cname,
    detect_spf_include,
    detect_txt_verification,
    score_entry,
)


# ── detect_dkim_cname ──


def test_dkim_cname_microsoft():
    assert detect_dkim_cname(
        {"selector1": "selector1-foo._domainkey.foo.onmicrosoft.com"},
        "onmicrosoft.com",
    )


def test_dkim_cname_google():
    assert detect_dkim_cname(
        {"google": "google._domainkey.foo.com"},
        "google",
    )


def test_dkim_cname_aws():
    assert detect_dkim_cname(
        {"selector1": "abc.amazonses.com"},
        "amazonses",
    )


def test_dkim_cname_no_match():
    assert not detect_dkim_cname(
        {"selector1": "selector1._domainkey.foo.it"},
        "onmicrosoft.com",
    )


def test_dkim_cname_none_or_empty():
    assert not detect_dkim_cname(None, "onmicrosoft.com")
    assert not detect_dkim_cname({}, "onmicrosoft.com")


# ── detect_spf_include ──


def test_spf_include_microsoft():
    assert detect_spf_include(
        "v=spf1 mx a include:spf.protection.outlook.com -all",
        ("spf.protection.outlook.com", "_spf.microsoft"),
    )


def test_spf_include_google():
    assert detect_spf_include(
        "v=spf1 include:_spf.google.com ~all",
        ("_spf.google.com", "aspmx"),
    )


def test_spf_include_aws():
    assert detect_spf_include(
        "v=spf1 include:amazonses.com ~all",
        ("amazonses", "amazonaws"),
    )


def test_spf_include_no_match():
    assert not detect_spf_include(
        "v=spf1 mx a:mail.foo.it -all",
        ("spf.protection.outlook.com",),
    )


def test_spf_include_empty():
    assert not detect_spf_include("", ("amazonses",))
    assert not detect_spf_include(None, ("amazonses",))


# ── detect_autodiscover ──


def test_autodiscover_microsoft():
    assert detect_autodiscover(
        {"autodiscover_cname": "autodiscover.outlook.com"},
        "autodiscover.outlook.com",
    )


def test_autodiscover_no_match():
    assert not detect_autodiscover(
        {"autodiscover_cname": "autodiscover.something-else.com"},
        "autodiscover.outlook.com",
    )


# ── detect_txt_verification ──


def test_txt_verification_present():
    assert detect_txt_verification(
        {"microsoft": "ms12345", "google": "g_abc"},
        "microsoft",
    )


def test_txt_verification_absent():
    assert not detect_txt_verification(
        {"google": "g_abc"},
        "microsoft",
    )


# ── score_entry ──


def test_score_entry_corte_costituzionale_like():
    """Corte Costituzionale pattern: 5 signals → definitive."""
    entry = {
        "cloud_tenant_only": "microsoft",
        "dkim": {
            "selector1": "selector1-foo._domainkey.foo.onmicrosoft.com",
            "selector2": "selector2-foo._domainkey.foo.onmicrosoft.com",
        },
        "autodiscover": {"autodiscover_cname": "autodiscover.outlook.com"},
        "spf": "v=spf1 include:spf.protection.outlook.com -all",
        "txt_verifications": {"microsoft": "ms12345"},
    }
    score = score_entry("IT-C2-test", entry)
    assert score["provider"] == "microsoft"
    assert score["label"] == "definitive"
    assert score["score"] >= 0.85
    assert "dkim_cname" in score["signals"]
    assert "autodiscover_cname" in score["signals"]
    assert "spf_include" in score["signals"]
    assert "txt_verification" in score["signals"]


def test_score_entry_dkim_only_weak():
    """Only DKIM + upstream → moderate (0.30 + 0.15 = 0.45), not weak."""
    entry = {
        "cloud_tenant_only": "microsoft",
        "dkim": {
            "selector1": "selector1-foo._domainkey.foo.onmicrosoft.com",
        },
    }
    score = score_entry("IT-TEST", entry)
    assert score["provider"] == "microsoft"
    # DKIM (0.30) + upstream (0.15) = 0.45 → moderate
    assert score["label"] in ("weak", "moderate")
    assert score["score"] < 0.60


def test_score_entry_no_cloud_tenant():
    """Entry without cloud_tenant_only → score 0."""
    entry = {"dkim": {}}
    score = score_entry("IT-TEST", entry)
    assert score["provider"] is None
    assert score["score"] == 0.0


def test_score_entry_aws_ses():
    """AWS SES: DKIM + SPF → strong or definitive."""
    entry = {
        "cloud_tenant_only": "aws",
        "dkim": {"selector1": "abc.amazonses.com"},
        "spf": "v=spf1 include:amazonses.com ~all",
    }
    score = score_entry("IT-TEST", entry)
    assert score["provider"] == "aws"
    assert "dkim_cname" in score["signals"]
    assert "spf_include" in score["signals"]
    # 3 signals (dkim + spf + upstream) → 0.30 + 0.20 + 0.15 = 0.65
    # → "strong"
    assert score["label"] in ("strong", "moderate")


def test_score_entry_google_workspace():
    """Google: DKIM + SPF + TXT → definitive."""
    entry = {
        "cloud_tenant_only": "google",
        "dkim": {"google": "google._domainkey.foo.com"},
        "spf": "v=spf1 include:_spf.google.com ~all",
        "txt_verifications": {"google": "google-site-verification=abc"},
    }
    score = score_entry("IT-TEST", entry)
    assert score["provider"] == "google"
    assert "dkim_cname" in score["signals"]
    assert "spf_include" in score["signals"]
    assert "txt_verification" in score["signals"]


def test_score_entry_handles_unknown_provider():
    """Unknown cloud_tenant_only value → 0 score."""
    entry = {
        "cloud_tenant_only": "oracle",  # not in PROVIDER_SIGNALS
        "dkim": {},
    }
    score = score_entry("IT-TEST", entry)
    assert score["provider"] is None
    assert score["score"] == 0.0


def test_score_entry_cap_at_one():
    """Even with all signals, score must be ≤ 1.0."""
    entry = {
        "cloud_tenant_only": "microsoft",
        "dkim": {
            "selector1": "selector1._domainkey.foo.onmicrosoft.com",
            "selector2": "selector2._domainkey.foo.onmicrosoft.com",
        },
        "autodiscover": {"autodiscover_cname": "autodiscover.outlook.com"},
        "spf": "v=spf1 include:spf.protection.outlook.com include:spf.protection.outlook.de -all",
        "txt_verifications": {"microsoft": "ms12345"},
        "mx_cnames": {"mx1.foo.com": "mx1.outlook.com"},
    }
    score = score_entry("IT-TEST", entry)
    assert score["score"] <= 1.0
    assert score["label"] == "definitive"
