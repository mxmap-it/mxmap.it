"""Unit tests for scripts/analyze_hidden_backends.py.

These tests verify the detection logic without depending on the full
data.json (which is too large for fast unit tests). They use synthetic
entries that exercise each detection path.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from analyze_hidden_backends import (  # noqa: E402
    detect_backend,
    detect_backend_spf,
    detect_backend_strong,
)


def test_detect_backend_strong_microsoft():
    """DKIM CNAME → onmicrosoft.com is a strong MS365 signal."""
    entry = {
        "dkim": {
            "selector1": "selector1-foo._domainkey.foo.onmicrosoft.com",
            "selector2": "selector2-foo._domainkey.foo.onmicrosoft.com",
        }
    }
    assert detect_backend_strong(entry) == "microsoft"


def test_detect_backend_strong_google():
    """DKIM CNAME → google is a strong Google Workspace signal."""
    entry = {
        "dkim": {
            "google": "google._domainkey.foo.com",
        }
    }
    assert detect_backend_strong(entry) == "google"


def test_detect_backend_strong_aws():
    """DKIM CNAME → amazonses is a strong AWS SES signal."""
    entry = {
        "dkim": {
            "selector1": "abc123.amazonses.com",
        }
    }
    assert detect_backend_strong(entry) == "aws"


def test_detect_backend_strong_no_dkim():
    """No DKIM → no strong signal."""
    entry = {"dkim": {}}
    assert detect_backend_strong(entry) is None

    entry = {"dkim": None}
    assert detect_backend_strong(entry) is None


def test_detect_backend_strong_self_hosted_dkim():
    """DKIM pointing to a self-hosted selector (no cloud) → None."""
    entry = {
        "dkim": {
            "selector1": "selector1._domainkey.comune.foo.it",
        }
    }
    assert detect_backend_strong(entry) is None


def test_detect_backend_spf_microsoft():
    """SPF include → spf.protection.outlook.com is a MS365 signal."""
    entry = {"spf": "v=spf1 mx a include:spf.protection.outlook.com -all"}
    assert detect_backend_spf(entry) == "microsoft"


def test_detect_backend_spf_google():
    """SPF include → _spf.google.com is a Google signal."""
    entry = {"spf": "v=spf1 mx a include:_spf.google.com ~all"}
    assert detect_backend_spf(entry) == "google"


def test_detect_backend_spf_aws():
    """SPF include → amazonses is an AWS signal."""
    entry = {"spf": "v=spf1 include:amazonses.com ~all"}
    assert detect_backend_spf(entry) == "aws"


def test_detect_backend_spf_empty():
    """Empty/missing SPF → None."""
    assert detect_backend_spf({"spf": ""}) is None
    assert detect_backend_spf({"spf": None}) is None
    assert detect_backend_spf({}) is None


def test_detect_backend_spf_local_only():
    """SPF with only local IPs/MX → no cloud signal."""
    entry = {"spf": "v=spf1 mx a:mail.comune.foo.it ip4:85.159.115.17 -all"}
    assert detect_backend_spf(entry) is None


def test_detect_backend_priority_dkim_over_spf():
    """DKIM takes priority over SPF when both are present."""
    entry = {
        "dkim": {
            "selector1": "selector1._domainkey.foo.onmicrosoft.com",
        },
        "spf": "v=spf1 include:_spf.google.com ~all",  # would say Google
    }
    # Microsoft from DKIM wins
    assert detect_backend(entry) == "microsoft"


def test_detect_backend_falls_back_to_spf():
    """When no DKIM, SPF is used as fallback."""
    entry = {
        "dkim": None,
        "spf": "v=spf1 include:_spf.google.com ~all",
    }
    assert detect_backend(entry) == "google"


def test_detect_backend_returns_none_when_no_evidence():
    """No DKIM and no SPF cloud markers → None."""
    entry = {
        "dkim": {"selector1": "selector1._domainkey.comune.foo.it"},
        "spf": "v=spf1 mx a:mail.comune.foo.it -all",
    }
    assert detect_backend(entry) is None


def test_detect_backend_handles_lowercase():
    """Detection is case-insensitive."""
    entry = {
        "dkim": {
            "selector1": "SELECTOR1._DOMAINKEY.FOO.ONMICROSOFT.COM",
        }
    }
    assert detect_backend_strong(entry) == "microsoft"

    entry = {"spf": "v=SPF1 include:SPF.PROTECTION.OUTLOOK.COM -all"}
    assert detect_backend_spf(entry) == "microsoft"
