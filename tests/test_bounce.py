"""Test del bounce-verifier (src/mail_sovereignty/bounce.py).

Coprono la logica pura (classify_rcpt, identify_backend, parse_ndr, VERP,
pool, reconcile, report, build_probe_message, load_config) e il flusso
``probe_domain`` / ``collect_ndrs`` con SMTP/IMAP finti — nessuna rete reale.
"""

import email

import pytest

from mail_sovereignty.bounce import (
    BounceConfig,
    build_detail,
    build_probe_message,
    build_send_plan,
    build_summary,
    build_token_map,
    classify_rcpt,
    collect_ndrs,
    identify_backend,
    load_config,
    parse_ndr,
    probe_domain,
    reconcile,
    verp_address,
    verp_token,
)


# ── classify_rcpt ───────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "code,expected",
    [
        (250, "accepted_2xx"),
        (251, "accepted_2xx"),
        (550, "rejected_5xx"),
        (551, "rejected_5xx"),
        (450, "tempfail"),
        (None, "unreachable"),
    ],
)
def test_classify_rcpt(code, expected):
    assert classify_rcpt(code) == expected


# ── VERP ────────────────────────────────────────────────────────────────────
def test_verp_token_stable_and_distinct():
    assert verp_token("comune.x.it") == verp_token("comune.x.it")
    assert verp_token("comune.x.it") != verp_token("comune.y.it")
    assert verp_token("COMUNE.X.IT") == verp_token("comune.x.it")  # case-insensitive


def test_verp_address_and_token_map():
    cfg = BounceConfig(verp_format="bounce+{token}@mitt.it")
    addr = verp_address(cfg, "comune.x.it")
    tok = verp_token("comune.x.it")
    assert addr == f"bounce+{tok}@mitt.it"
    assert build_token_map(["comune.x.it"]) == {tok: "comune.x.it"}


# ── identify_backend ────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "texts,expected",
    [
        (("220 mx.aruba.it ESMTP",), "aruba"),
        (("550 User unknown", "dns; mail.protection.outlook.com"), "microsoft"),
        (("dns; alt1.aspmx.l.google.com",), "google"),
        (("550 5.1.1 unknown (Postfix)",), "postfix"),
        (("mx-01.prod.hydra.sophos.com",), "sophos-gw"),
        (("220 generic esmtp",), None),
    ],
)
def test_identify_backend(texts, expected):
    assert identify_backend(*texts) == expected


# ── build_probe_message ─────────────────────────────────────────────────────
def test_probe_message_headers_and_test_declaration():
    cfg = BounceConfig(from_address="probe@mitt.it", from_name="Oss")
    msg = build_probe_message(cfg, "comune.x.it", "tok123")
    assert msg["To"] == "mxmap-probe-no-such-mailbox@comune.x.it"
    assert msg["Auto-Submitted"] == "auto-generated"
    assert msg["Precedence"] == "bulk"
    assert "probe@mitt.it" in msg["From"]
    body = msg.get_content()
    assert "TEST" in body and "mxmap.it" in body  # dichiara che è un test


# ── build_send_plan (serializzazione per IP) ────────────────────────────────
def test_send_plan_serializes_same_ip():
    items = [
        ("a.it", "1.1.1.1"),
        ("b.it", "1.1.1.1"),
        ("c.it", "1.1.1.1"),
        ("d.it", "2.2.2.2"),
    ]
    plan = build_send_plan(items, per_ip_interval=45)
    off = {p["domain"]: p["offset_sec"] for p in plan}
    # stesso IP -> distanziati di 45s; IP diverso -> parte subito
    assert off["a.it"] == 0 and off["b.it"] == 45 and off["c.it"] == 90
    assert off["d.it"] == 0
    # ordinato per offset crescente
    assert [p["offset_sec"] for p in plan] == sorted(p["offset_sec"] for p in plan)


# ── reconcile ───────────────────────────────────────────────────────────────
def test_reconcile_cloud_provider():
    r = reconcile("microsoft", "rejected_5xx")
    assert r["provider"] == "microsoft" and r["mx_jurisdiction"] == "foreign"


def test_reconcile_italian_provider():
    r = reconcile("aruba", "accepted_2xx")
    assert r["provider"] == "aruba" and r["mx_jurisdiction"] == "domestic"


def test_reconcile_gateway_no_reclass():
    r = reconcile("sophos-gw", "accepted_2xx")
    assert "provider" not in r and r["smtp_software"] == "sophos-gw"


def test_reconcile_selfhosted_software():
    r = reconcile("postfix", "rejected_5xx")
    assert r["smtp_software"] == "postfix" and r["classification_confidence"] == 0.65


def test_reconcile_none():
    assert reconcile(None, "accepted_2xx") is None


# ── parse_ndr ───────────────────────────────────────────────────────────────
_NDR = """\
From: Mail Delivery System <MAILER-DAEMON@mail.example.com>
To: bounce+abc123def456@mitt.it
Subject: Undelivered Mail Returned to Sender
Content-Type: multipart/report; report-type=delivery-status; boundary="B"

--B
Content-Type: text/plain

Delivery to the following recipient failed permanently.

--B
Content-Type: message/delivery-status

Reporting-MTA: dns; mail.example.com
Final-Recipient: rfc822; mxmap-probe-no-such-mailbox@target.it
Action: failed
Status: 5.1.1
Remote-MTA: dns; mx.aruba.it
Diagnostic-Code: smtp; 550 5.1.1 <x> User unknown (Postfix)

--B--
"""


def test_parse_ndr_extracts_fields_and_backend():
    msg = email.message_from_string(_NDR)
    res = parse_ndr(msg)
    assert res.verp_token == "abc123def456"
    assert res.action == "failed"
    assert res.status == "5.1.1"
    assert "User unknown" in res.diagnostic_code
    assert "aruba" in res.remote_mta
    # aruba.it precede postfix nelle keyword -> backend = aruba
    assert res.identified_backend == "aruba"


# ── probe_domain ────────────────────────────────────────────────────────────
class FakeSMTP:
    def __init__(
        self, rcpt_code=250, rcpt_text=b"OK", banner="220 mx.test ESMTP", has_tls=False
    ):
        self.banner = banner
        self.peer_ip = "9.9.9.9"
        self._rcpt = (rcpt_code, rcpt_text)
        self._has_tls = has_tls
        self.data_sent = False
        self.quit_called = False

    def ehlo(self, name):
        return (250, b"ok")

    def has_extn(self, name):
        return self._has_tls and name == "starttls"

    def starttls(self):
        return (220, b"ready")

    def mail(self, addr):
        return (250, b"ok")

    def rcpt(self, addr):
        return self._rcpt

    def data(self, payload):
        self.data_sent = True
        return (250, b"queued")

    def quit(self):
        self.quit_called = True


def test_probe_dry_run_does_not_connect():
    cfg = BounceConfig(dry_run=True)
    called = []
    res = probe_domain(
        cfg, {"domain": "x.it", "mx": ["mx.x.it"]}, connect=lambda *a: called.append(a)
    )
    assert res.outcome == "dry_run" and res.dry_run is True
    assert called == []  # nessuna connessione in dry-run


def test_probe_accepted_sends_data_and_ingested():
    cfg = BounceConfig(dry_run=False, starttls=False)
    fake = FakeSMTP(rcpt_code=250)
    res = probe_domain(
        cfg, {"domain": "x.it", "mx": ["mx.x.it"]}, connect=lambda *a: fake
    )
    assert res.rcpt_validation == "accepted_2xx"
    assert fake.data_sent is True  # invio SEMPRE fino a DATA quando accettato
    assert res.outcome == "ingested"
    assert fake.quit_called is True


def test_probe_rejected_records_validation_no_data():
    cfg = BounceConfig(dry_run=False, starttls=False)
    fake = FakeSMTP(rcpt_code=550, rcpt_text=b"550 User unknown (Postfix)")
    res = probe_domain(
        cfg, {"domain": "x.it", "mx": ["mx.x.it"]}, connect=lambda *a: fake
    )
    assert res.rcpt_validation == "rejected_5xx"
    assert fake.data_sent is False  # rifiutato a RCPT -> niente DATA
    assert res.outcome == "rcpt_rejected"
    assert res.identified_backend == "postfix"


def test_probe_no_mx_unreachable():
    cfg = BounceConfig(dry_run=False)
    res = probe_domain(cfg, {"domain": "x.it", "mx": []}, connect=lambda *a: FakeSMTP())
    assert res.outcome == "mx_unreachable"


def test_probe_connect_failure():
    cfg = BounceConfig(dry_run=False)

    def boom(*a):
        raise OSError("refused")

    res = probe_domain(cfg, {"domain": "x.it", "mx": ["mx.x.it"]}, connect=boom)
    assert res.outcome == "mx_unreachable" and "refused" in res.error


# ── report ──────────────────────────────────────────────────────────────────
def test_build_summary_and_detail():
    cfg = BounceConfig(dry_run=False, starttls=False)
    r_ok = probe_domain(
        cfg, {"domain": "a.it", "mx": ["mx.a.it"]}, connect=lambda *a: FakeSMTP(250)
    )
    r_rej = probe_domain(
        cfg,
        {"domain": "b.it", "mx": ["mx.b.it"]},
        connect=lambda *a: FakeSMTP(550, b"User unknown (Exchange)"),
    )
    summ = build_summary([r_ok, r_rej], [])
    assert summ["n_probed"] == 2
    assert summ["by_rcpt_validation"]["rejected_5xx"] == 1
    assert summ["by_backend"].get("microsoft") == 1  # Exchange -> microsoft
    detail = build_detail([r_rej])
    assert detail[0]["domain"] == "b.it"
    assert detail[0]["reconcile"]["provider"] == "microsoft"


# ── collect_ndrs (IMAP finto) ───────────────────────────────────────────────
class FakeIMAP:
    def __init__(self, raw_messages):
        self._raw = raw_messages

    def iter_messages(self):
        yield from self._raw


def test_collect_ndrs_parses_from_imap():
    cfg = BounceConfig(dry_run=False, imap_host="imap.test")
    ndrs = collect_ndrs(cfg, imap=FakeIMAP([_NDR.encode("utf-8")]))
    assert len(ndrs) == 1 and ndrs[0].verp_token == "abc123def456"


def test_collect_ndrs_dry_run_empty():
    cfg = BounceConfig(dry_run=True, imap_host="imap.test")
    assert collect_ndrs(cfg, imap=FakeIMAP([_NDR.encode("utf-8")])) == []


# ── load_config ─────────────────────────────────────────────────────────────
def test_load_config(tmp_path):
    p = tmp_path / "bounce.toml"
    p.write_text(
        """
[smtp]
starttls = false
[imap]
host = "imap.x.it"
port = 993
username = "u@x.it"
[sender]
from_address = "probe@x.it"
verp_format = "bounce+{token}@x.it"
[limits]
per_ip_min_interval_sec = 30
ndr_wait_hours = 24
[run]
dry_run = false
""",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.starttls is False
    assert cfg.imap_host == "imap.x.it" and cfg.imap_username == "u@x.it"
    assert cfg.from_address == "probe@x.it"
    assert cfg.per_ip_min_interval_sec == 30 and cfg.ndr_wait_hours == 24
    assert cfg.dry_run is False
