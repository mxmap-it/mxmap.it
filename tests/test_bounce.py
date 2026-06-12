"""Test del bounce-verifier (src/mail_sovereignty/bounce.py).

Approccio: invio via smarthost + analisi NDR. Coprono la logica pura
(identify_backend, parse_ndr, VERP, pool, reconcile, join, report,
build_probe_message, load_config) e ``send_probe`` / ``collect_ndrs`` con
SMTP/IMAP finti — nessuna rete reale.
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
    classify_ndr_origin,
    collect_ndrs,
    identify_backend,
    join_results,
    load_config,
    parse_ndr,
    reconcile,
    send_probe,
    sender_hosts_from_cfg,
    verp_address,
    verp_token,
)


# ── VERP ────────────────────────────────────────────────────────────────────
def test_verp_token_stable_and_distinct():
    assert verp_token("comune.x.it") == verp_token("comune.x.it")
    assert verp_token("comune.x.it") != verp_token("comune.y.it")
    assert verp_token("COMUNE.X.IT") == verp_token("comune.x.it")


def test_verp_address_and_token_map():
    cfg = BounceConfig(verp_format="bounce+{token}@mitt.it")
    tok = verp_token("comune.x.it")
    assert verp_address(cfg, "comune.x.it") == f"bounce+{tok}@mitt.it"
    assert build_token_map(["comune.x.it"]) == {tok: "comune.x.it"}


# ── identify_backend ────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "texts,expected",
    [
        (("dns; mx.aruba.it",), "aruba"),
        (("550 User unknown", "dns; mail.protection.outlook.com"), "microsoft"),
        (("dns; alt1.aspmx.l.google.com",), "google"),
        (("550 5.1.1 unknown (Postfix)",), "postfix"),
        (("mx-01.prod.hydra.sophos.com",), "sophos-gw"),
        (("550 generic error",), None),
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


# ── build_send_plan ─────────────────────────────────────────────────────────
def test_send_plan_serializes_same_ip():
    items = [
        ("a.it", "1.1.1.1"),
        ("b.it", "1.1.1.1"),
        ("c.it", "1.1.1.1"),
        ("d.it", "2.2.2.2"),
    ]
    plan = build_send_plan(items, per_ip_interval=45)
    off = {p["domain"]: p["offset_sec"] for p in plan}
    assert off["a.it"] == 0 and off["b.it"] == 45 and off["c.it"] == 90
    assert off["d.it"] == 0
    assert [p["offset_sec"] for p in plan] == sorted(p["offset_sec"] for p in plan)


# ── reconcile ───────────────────────────────────────────────────────────────
def test_reconcile_cloud_provider():
    r = reconcile("microsoft")
    assert r["provider"] == "microsoft" and r["mx_jurisdiction"] == "foreign"


def test_reconcile_italian_provider():
    r = reconcile("aruba")
    assert r["provider"] == "aruba" and r["mx_jurisdiction"] == "domestic"


def test_reconcile_gateway_no_reclass():
    r = reconcile("sophos-gw")
    assert "provider" not in r and r["smtp_software"] == "sophos-gw"


def test_reconcile_selfhosted_software():
    r = reconcile("postfix")
    assert r["smtp_software"] == "postfix" and r["classification_confidence"] == 0.65


def test_reconcile_none():
    assert reconcile(None) is None


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
    res = parse_ndr(email.message_from_string(_NDR))
    assert res.verp_token == "abc123def456"
    assert res.action == "failed" and res.status == "5.1.1"
    assert "User unknown" in res.diagnostic_code
    assert "aruba" in res.remote_mta
    assert res.identified_backend == "aruba"  # aruba.it precede postfix


# ── origine dell'NDR (quale hop ha rimbalzato) ──────────────────────────────
@pytest.mark.parametrize(
    "reporting,frm,sh,expected",
    [
        ("dns; mail.comune.x.it", "MAILER-DAEMON@comune.x.it", (), "destination"),
        ("dns; mx-01.prod.hydra.sophos.com", "d@sophos.com", (), "gateway"),
        (
            "dns; googlemail.com",
            "d@googlemail.com",
            ("google.com", "googlemail.com"),
            "sender",
        ),
        (None, None, (), "unknown"),
    ],
)
def test_classify_ndr_origin(reporting, frm, sh, expected):
    assert classify_ndr_origin(reporting, frm, sh) == expected


def test_sender_hosts_from_cfg_google_aliases():
    cfg = BounceConfig(
        smtp_host="smtp.gmail.com",
        from_address="probe@mitt.it",
        verp_format="bounce+{token}@mitt.it",
    )
    sh = sender_hosts_from_cfg(cfg)
    assert "google.com" in sh and "googlemail.com" in sh and "mitt.it" in sh


def _ndr_from(reporting_mta: str, frm: str) -> str:
    return (
        f"From: {frm}\n"
        "To: bounce+tok@mitt.it\n"
        "Received: from relay.a by relay.b\n"
        "Subject: Undelivered Mail\n"
        'Content-Type: multipart/report; boundary="B"\n\n'
        "--B\n"
        "Content-Type: message/delivery-status\n\n"
        f"Reporting-MTA: {reporting_mta}\n"
        "Status: 5.1.1\n"
        "Remote-MTA: dns; mx.aruba.it\n"
        "Diagnostic-Code: smtp; 550 User unknown\n\n"
        "--B--\n"
    )


def test_parse_ndr_origin_from_and_received():
    raw = _ndr_from("dns; mx-01.prod.hydra.sophos.com", "MAILER-DAEMON@sophos.com")
    res = parse_ndr(email.message_from_string(raw))
    assert res.ndr_origin == "gateway"  # gateway antispam ricevente
    assert "sophos" in res.ndr_from
    assert any("relay.b" in r for r in res.received_chain)


def test_parse_ndr_origin_sender_with_hosts():
    raw = _ndr_from("dns; googlemail.com", "MAILER-DAEMON@googlemail.com")
    res = parse_ndr(email.message_from_string(raw), ("google.com", "googlemail.com"))
    assert res.ndr_origin == "sender"  # generato dal nostro smarthost


# ── send_probe (smarthost finto) ────────────────────────────────────────────
class FakeSMTP:
    def __init__(self, refused=None, raise_exc=None):
        self._refused = refused or {}
        self._raise = raise_exc
        self.sent = []

    def sendmail(self, from_addr, to_addrs, msg):
        if self._raise:
            raise self._raise
        self.sent.append((from_addr, to_addrs))
        return self._refused


def test_send_probe_dry_run_does_not_send():
    cfg = BounceConfig(dry_run=True)
    fake = FakeSMTP()
    res = send_probe(cfg, {"domain": "x.it"}, smtp=fake)
    assert res.submitted is False and res.dry_run is True
    assert fake.sent == []  # nessun invio in dry-run


def test_send_probe_accepted_by_smarthost():
    cfg = BounceConfig(dry_run=False, verp_format="bounce+{token}@mitt.it")
    fake = FakeSMTP(refused={})
    res = send_probe(cfg, {"domain": "x.it"}, smtp=fake)
    assert res.submitted is True
    # envelope-from VERP + destinatario inesistente del dominio target
    frm, to = fake.sent[0]
    assert frm == verp_address(cfg, "x.it")
    assert to == ["mxmap-probe-no-such-mailbox@x.it"]


def test_send_probe_refused_recipient():
    cfg = BounceConfig(dry_run=False)
    fake = FakeSMTP(refused={"mxmap-probe-no-such-mailbox@x.it": (550, b"no")})
    res = send_probe(cfg, {"domain": "x.it"}, smtp=fake)
    assert res.submitted is False


def test_send_probe_smtp_error():
    cfg = BounceConfig(dry_run=False)
    fake = FakeSMTP(raise_exc=OSError("auth failed"))
    res = send_probe(cfg, {"domain": "x.it"}, smtp=fake)
    assert res.submitted is False and "auth failed" in res.error


# ── join_results + report ───────────────────────────────────────────────────
def test_join_and_summary_with_ndr():
    cfg = BounceConfig(dry_run=False)
    s_bounced = send_probe(cfg, {"domain": "target.it"}, smtp=FakeSMTP())
    s_silent = send_probe(cfg, {"domain": "silent.it"}, smtp=FakeSMTP())
    s_failed = send_probe(
        cfg, {"domain": "fail.it"}, smtp=FakeSMTP(raise_exc=OSError("x"))
    )
    # un NDR correlato a target.it (stesso token)
    ndr = parse_ndr(
        email.message_from_string(_NDR.replace("abc123def456", verp_token("target.it")))
    )
    rows = join_results([s_bounced, s_silent, s_failed], [ndr])
    by = {r["domain"]: r["outcome"] for r in rows}
    assert by["target.it"] == "bounced"
    assert by["silent.it"] == "no_bounce"
    assert by["fail.it"] == "not_submitted"
    # la riga bounced porta backend + suggerimento di riclassificazione
    target_row = next(r for r in rows if r["domain"] == "target.it")
    assert target_row["identified_backend"] == "aruba"
    assert target_row["reconcile"]["provider"] == "aruba"

    summ = build_summary([s_bounced, s_silent, s_failed], [ndr])
    assert summ["n_sent"] == 2 and summ["n_ndr"] == 1
    assert summ["by_outcome"]["bounced"] == 1
    assert summ["by_backend"]["aruba"] == 1
    assert summ["reclassifiable"] == 1
    assert build_detail([s_bounced], [ndr])[0]["domain"] == "target.it"


def test_join_no_reclassify_when_ndr_from_sender():
    cfg = BounceConfig(dry_run=False)
    s = send_probe(cfg, {"domain": "s.it"}, smtp=FakeSMTP())
    raw = _ndr_from("dns; googlemail.com", "MAILER-DAEMON@googlemail.com").replace(
        "bounce+tok@", "bounce+" + verp_token("s.it") + "@"
    )
    ndr = parse_ndr(email.message_from_string(raw), ("googlemail.com",))
    row = join_results([s], [ndr])[0]
    assert row["ndr_origin"] == "sender"
    assert row["reconcile"] is None  # il nostro smarthost non rivela il backend


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
host = "smtp.x.it"
port = 587
security = "starttls"
username = "probe@x.it"
password = "pw"
[imap]
host = "imap.x.it"
username = "probe@x.it"
[sender]
from_address = "probe@x.it"
verp_format = "bounce+{token}@x.it"
[limits]
ndr_wait_hours = 24
[run]
dry_run = false
""",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.smtp_host == "smtp.x.it" and cfg.smtp_username == "probe@x.it"
    assert cfg.imap_host == "imap.x.it"
    assert cfg.from_address == "probe@x.it" and cfg.ndr_wait_hours == 24
    assert cfg.dry_run is False
