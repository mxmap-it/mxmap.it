"""Test della logica di storicizzazione (src/mail_sovereignty/historicize.py).

Coprono: estrazione material_row (parse bfs, sovranità, giurisdizione,
confidence, normalizzazione mx0, dkim tenant), classify_change (tutti i tipi),
diff_runs, build_manifest, build_timeseries. Niente attribuzione di causa:
esiste una sola realtà (metodologia congelata al primo scan).
"""

import pytest

from mail_sovereignty.historicize import (
    build_manifest,
    build_timeseries,
    classify_change,
    diff_runs,
    dkim_tenant_of,
    material_row,
    parse_bfs,
    sovereignty_of,
    update_entity_timeline,
)
from collections import Counter


# ── parse_bfs / sovereignty_of ──────────────────────────────────────────────
@pytest.mark.parametrize(
    "bfs,cat,ipa",
    [
        ("IT-C1-m_it", "C1", "m_it"),
        ("IT-L6-KH5RHFCV", "L6", "KH5RHFCV"),
        ("IT-C1-a-b", "C1", "a-b"),  # ipa con trattino
        ("", "", ""),
    ],
)
def test_parse_bfs(bfs, cat, ipa):
    assert parse_bfs(bfs) == (cat, ipa)


@pytest.mark.parametrize(
    "provider,expected",
    [
        ("microsoft", "USA (CLOUD Act)"),
        ("google", "USA (CLOUD Act)"),
        ("istruzione-miur-tenant", "USA (CLOUD Act)"),
        ("regional-public", "Italia — Cloud sovrano"),
        ("aruba", "Italia — Provider commerciali"),
        ("independent", "Italia — Infrastruttura autonoma"),
        ("zoho", "Altri provider esteri"),
        ("unknown", "Sconosciuto"),
    ],
)
def test_sovereignty_of(provider, expected):
    assert sovereignty_of(provider) == expected


# ── material_row ────────────────────────────────────────────────────────────
def test_material_row_extraction():
    entry = {
        "bfs": "IT-C1-m_it",
        "name": "Ministero dell'Interno",
        "country": "IT",
        "provider": "microsoft",
        "mx": ["INTERNO-IT.mail.protection.OUTLOOK.com."],
        "mx_discovery_method": "aoo_uo_tier6",
        "classification_confidence": 0.92,
        "mx_jurisdiction": "foreign",
        "domain_used": "Interno.IT",
        "gateway": None,
        "dkim": {"selector1": "selector1-x._domainkey.tenant.onmicrosoft.com"},
    }
    r = material_row(entry)
    assert r["id"] == "IT-C1-m_it" and r["cat"] == "C1" and r["ipa"] == "m_it"
    assert r["provider"] == "microsoft" and r["sovereignty"] == "USA (CLOUD Act)"
    assert r["jurisdiction"] == "foreign"
    assert r["confidence"] == 0.92
    assert r["mx0"] == "interno-it.mail.protection.outlook.com"  # lower, no dot
    assert r["domain_used"] == "interno.it"
    assert r["has_mx"] is True
    assert r["dkim_tenant"] == "tenant.onmicrosoft.com"


def test_material_row_no_mx_unknown():
    r = material_row({"bfs": "IT-L6-x", "provider": "unknown", "mx": []})
    assert r["mx0"] is None and r["has_mx"] is False
    assert r["sovereignty"] == "Sconosciuto" and r["jurisdiction"] == "unknown"
    assert r["confidence"] is None


def test_dkim_tenant_of():
    assert (
        dkim_tenant_of({"dkim": {"s1": "x._domainkey.acme.onmicrosoft.com"}})
        == "acme.onmicrosoft.com"
    )
    assert dkim_tenant_of({"dkim": {"s1": "x.dkim.amazonses.com"}}) is None
    assert dkim_tenant_of({}) is None


# ── classify_change ─────────────────────────────────────────────────────────
def _row(**kw):
    base = {
        "id": "IT-C1-x",
        "ipa": "x",
        "cat": "C1",
        "name": "Ente X",
        "provider": "aruba",
        "sovereignty": "Italia — Provider commerciali",
        "jurisdiction": "domestic",
        "method": "seed_primary_mx",
        "domain_used": "x.it",
        "mx0": "mx.x.it",
        "has_mx": True,
        "confidence": 0.9,
        "dkim_tenant": None,
        "gateway": None,
    }
    base.update(kw)
    return base


def test_change_new_and_removed():
    assert classify_change(None, _row())[0]["change"] == "new"
    assert classify_change(_row(), None)[0]["change"] == "removed"


def test_change_resolved():
    prev = _row(
        provider="unknown",
        sovereignty="Sconosciuto",
        method="unknown",
        mx0=None,
        has_mx=False,
    )
    curr = _row(
        provider="microsoft", sovereignty="USA (CLOUD Act)", method="aoo_uo_tier6"
    )
    assert any(e["change"] == "resolved" for e in classify_change(prev, curr))


def test_change_regressed():
    prev = _row(provider="microsoft", sovereignty="USA (CLOUD Act)")
    curr = _row(provider="unknown", sovereignty="Sconosciuto", mx0=None, has_mx=False)
    assert any(e["change"] == "regressed" for e in classify_change(prev, curr))


def test_change_provider():
    prev = _row(provider="aruba", sovereignty="Italia — Provider commerciali")
    curr = _row(provider="microsoft", sovereignty="USA (CLOUD Act)")
    evs = classify_change(prev, curr)
    assert any(e["change"] == "provider_change" for e in evs)
    assert all("cause" not in e for e in evs)  # niente attribuzione di causa


def test_change_sovereignty_and_jurisdiction():
    prev = _row(jurisdiction="domestic")
    curr = _row(jurisdiction="foreign")
    assert any(
        e["change"] == "jurisdiction_change" for e in classify_change(prev, curr)
    )


def test_change_method_only():
    prev = _row(method="seed_primary_mx")
    curr = _row(method="smtp_banner")
    evs = classify_change(prev, curr)
    assert len(evs) == 1 and evs[0]["change"] == "method_change"


def test_change_none_when_identical():
    assert classify_change(_row(), _row()) == []


# ── diff_runs / build_manifest / build_timeseries ───────────────────────────
def test_diff_runs_counts():
    prev = {
        "a": _row(id="a"),
        "b": _row(id="b", provider="microsoft", sovereignty="USA (CLOUD Act)"),
    }
    curr = {
        "b": _row(
            id="b", provider="microsoft", sovereignty="USA (CLOUD Act)"
        ),  # invariato
        "c": _row(id="c"),  # nuovo
    }
    events, counts = diff_runs(prev, curr)
    assert counts["removed"] == 1  # a sparito
    assert counts["new"] == 1  # c nuovo
    assert all("id" in e and "name" in e for e in events)


def test_build_manifest_and_timeseries():
    rows = {
        "a": _row(
            id="a",
            provider="microsoft",
            sovereignty="USA (CLOUD Act)",
            jurisdiction="foreign",
            confidence=0.9,
        ),
        "b": _row(id="b", provider="aruba", jurisdiction="domestic", confidence=0.8),
        "c": _row(
            id="c",
            provider="unknown",
            sovereignty="Sconosciuto",
            jurisdiction="unknown",
            confidence=None,
        ),
    }
    m = build_manifest(
        "2026-06-12",
        "abc123",
        "1.0.0",
        rows,
        Counter({"new": 3}),
        3,
        "2026-06-12T04:00Z",
    )
    assert m["n_entities"] == 3 and m["n_new"] == 3
    assert m["provider_counts"]["microsoft"] == 1
    assert m["jurisdiction"]["domestic"] == 1 and m["jurisdiction"]["foreign"] == 1
    assert m["coverage_pct"] == round(100 * 2 / 3, 2)  # 1 unknown su 3
    assert m["mean_confidence"] == round((0.9 + 0.8) / 2, 4)  # c (None) escluso

    ts = build_timeseries([m])
    assert ts["sovereignty"][0]["date"] == "2026-06-12"
    assert ts["jurisdiction"][0]["domestic"] == 1
    assert ts["coverage"][0]["coverage_pct"] == m["coverage_pct"]


# ── F2: scheda storica per-ente ─────────────────────────────────────────────
def test_update_entity_timeline_idempotent():
    curr = _row(provider="microsoft", sovereignty="USA (CLOUD Act)")
    evs = [
        {
            "change": "provider_change",
            "field": "provider",
            "from": "aruba",
            "to": "microsoft",
        }
    ]
    e1 = update_entity_timeline(None, "2026-06-12", curr, evs)
    assert e1["n_changes"] == 1 and e1["first_seen"] == "2026-06-12"
    assert e1["current"]["provider"] == "microsoft"
    assert "cause" not in e1["timeline"][0]  # niente attribuzione di causa

    evs2 = [
        {
            "change": "method_change",
            "field": "method",
            "from": "a",
            "to": "b",
        }
    ]
    e2 = update_entity_timeline(e1, "2026-06-13", curr, evs2)
    assert e2["n_changes"] == 2
    assert e2["first_seen"] == "2026-06-12" and e2["last_change"] == "2026-06-13"

    # ri-eseguire lo stesso run non duplica
    e2b = update_entity_timeline(e2, "2026-06-13", curr, evs2)
    assert e2b["n_changes"] == 2
