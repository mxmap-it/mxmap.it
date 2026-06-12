"""Bounce-verifier — verifica attiva del backend di posta per i casi a bassa
confidenza (vedi docs/BOUNCE_VERIFIER_DESIGN.md).

Flusso unico: per ogni dominio si tenta SEMPRE l'invio direct-to-MX, registrando
``rcpt_validation`` (``rejected_5xx`` / ``accepted_2xx`` / ``tempfail`` /
``unreachable``); se accettato a RCPT TO si invia anche DATA. Gli NDR asincroni
(per gli ``accepted_2xx`` che poi rimbalzano) si raccolgono via IMAP correlati
per VERP.

NOTA TRANSPORT: per *vedere* la risposta RCPT TO del destinatario (requisito R1)
l'invio è **direct-to-MX** (connessione diretta all'MX di destinazione, porta
25). Inviare via smarthost autenticato nasconderebbe la RCPT (lo smarthost
accetta sempre e rilancia, e il rifiuto torna solo come NDR asincrono).

Le funzioni di logica pura sono testabili senza rete; ``probe_domain`` e
``collect_ndrs`` accettano factory iniettabili per i test.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import asdict, dataclass, field
from email.message import EmailMessage, Message
from pathlib import Path

# ── Configurazione ──────────────────────────────────────────────────────────


@dataclass
class BounceConfig:
    # invio direct-to-MX
    helo_hostname: str = "localhost"
    connect_timeout_sec: int = 20
    starttls: bool = True  # STARTTLS opportunistico se l'MX lo offre
    # mittente / VERP
    from_name: str = "Osservatorio mxmap.it"
    from_address: str = "probe@example.invalid"
    verp_format: str = "bounce+{token}@example.invalid"
    subject: str = "[TEST] Verifica tecnica di recapito — Osservatorio mxmap.it"
    # IMAP per gli NDR
    imap_host: str = ""
    imap_port: int = 993
    imap_security: str = "ssl"
    imap_username: str = ""
    imap_password: str = ""
    imap_mailbox: str = "INBOX"
    # rate-limit / pool
    per_ip_min_interval_sec: int = 45
    max_per_hour: int = 60
    ndr_wait_hours: int = 48
    # sicurezza
    dry_run: bool = True


def load_config(path: str | Path) -> BounceConfig:
    """Carica config/bounce.toml (tomllib). I campi mancanti usano i default."""
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    smtp = raw.get("smtp", {})
    imap = raw.get("imap", {})
    sender = raw.get("sender", {})
    limits = raw.get("limits", {})
    run = raw.get("run", {})
    return BounceConfig(
        helo_hostname=smtp.get("helo_hostname", "localhost"),
        connect_timeout_sec=int(limits.get("connect_timeout_sec", 20)),
        starttls=bool(smtp.get("starttls", True)),
        from_name=sender.get("from_name", BounceConfig.from_name),
        from_address=sender.get("from_address", BounceConfig.from_address),
        verp_format=sender.get("verp_format", BounceConfig.verp_format),
        subject=sender.get("subject", BounceConfig.subject),
        imap_host=imap.get("host", ""),
        imap_port=int(imap.get("port", 993)),
        imap_security=imap.get("security", "ssl"),
        imap_username=imap.get("username", ""),
        imap_password=imap.get("password", ""),
        imap_mailbox=imap.get("mailbox", "INBOX"),
        per_ip_min_interval_sec=int(limits.get("per_ip_min_interval_sec", 45)),
        max_per_hour=int(limits.get("max_per_hour", 60)),
        ndr_wait_hours=int(limits.get("ndr_wait_hours", 48)),
        dry_run=bool(run.get("dry_run", True)),
    )


# ── VERP (correlazione bounce) ──────────────────────────────────────────────


def verp_token(domain: str) -> str:
    """Token opaco e stabile per un dominio target (per correlare l'NDR)."""
    return hashlib.sha1(domain.lower().encode("utf-8")).hexdigest()[:16]


def verp_address(cfg: BounceConfig, domain: str) -> str:
    return cfg.verp_format.format(token=verp_token(domain))


def build_token_map(domains: list[str]) -> dict[str, str]:
    """token -> domain, da persistere insieme al log per decodificare gli NDR."""
    return {verp_token(d): d for d in domains}


# ── Classificazione RCPT TO ─────────────────────────────────────────────────


def classify_rcpt(code: int | None) -> str:
    """Mappa il codice SMTP della RCPT TO al campo ``rcpt_validation``."""
    if code is None:
        return "unreachable"
    if 200 <= code < 300:
        return "accepted_2xx"
    if 400 <= code < 500:
        return "tempfail"
    if 500 <= code < 600:
        return "rejected_5xx"
    return "unknown"


# ── Identificazione del backend ─────────────────────────────────────────────

# keyword (su banner EHLO, testo del 5xx, diagnostic-code NDR) -> backend
BACKEND_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("protection.outlook.com", "microsoft"),
    ("outlook.com", "microsoft"),
    ("exchange", "microsoft"),
    ("office365", "microsoft"),
    ("onmicrosoft.com", "microsoft"),
    ("aspmx.l.google.com", "google"),
    ("googlemail.com", "google"),
    ("gmail", "google"),
    ("google.com", "google"),
    ("amazonses.com", "aws"),
    ("amazonaws.com", "aws"),
    ("aruba.it", "aruba"),
    ("arubabusiness", "aruba"),
    ("register.it", "register-it"),
    ("seeweb", "seeweb"),
    ("sophos", "sophos-gw"),
    ("proofpoint", "proofpoint-gw"),
    ("pphosted", "proofpoint-gw"),
    ("barracuda", "barracuda-gw"),
    ("mailspamprotection", "spamexperts-gw"),
    ("postfix", "postfix"),
    ("exim", "exim"),
    ("zimbra", "zimbra"),
    ("zextras", "zimbra"),
    ("mdaemon", "mdaemon"),
    ("kerio", "kerio"),
    ("qmail", "qmail"),
    ("microsoft", "microsoft"),
)


def identify_backend(*texts: str | None) -> str | None:
    """Identifica il backend reale cercando keyword note nei testi forniti
    (banner EHLO, testo del rifiuto 5xx, diagnostic-code dell'NDR)."""
    blob = " ".join(t.lower() for t in texts if t)
    for kw, backend in BACKEND_KEYWORDS:
        if kw in blob:
            return backend
    return None


# ── Parsing NDR (RFC 3464) ──────────────────────────────────────────────────


@dataclass
class NdrResult:
    verp_token: str | None = None
    action: str | None = None
    status: str | None = None
    diagnostic_code: str | None = None
    remote_mta: str | None = None
    reporting_mta: str | None = None
    identified_backend: str | None = None


def _header_from_part(part: Message, name: str) -> str | None:
    val = part.get(name)
    return str(val) if val is not None else None


def parse_ndr(msg: Message) -> NdrResult:
    """Estrae i campi diagnostici da un NDR multipart/report (RFC 3464):
    cerca la parte ``message/delivery-status`` e i suoi header per-recipient."""
    res = NdrResult()
    # token VERP: l'NDR arriva sull'envelope-from VERP (header To), o lo si
    # ritrova negli header di ritorno / nella delivery-status.
    for hdr in ("To", "X-Failed-Recipients", "Original-Recipient", "Final-Recipient"):
        v = msg.get(hdr)
        if v and "bounce+" in str(v):
            res.verp_token = str(v).split("bounce+", 1)[1].split("@", 1)[0]
            break
    for part in msg.walk():
        if part.get_content_type() == "message/delivery-status":
            payload = part.get_payload()
            blocks = payload if isinstance(payload, list) else [part]
            for block in blocks:
                if not isinstance(block, Message):
                    continue
                res.action = res.action or _header_from_part(block, "Action")
                res.status = res.status or _header_from_part(block, "Status")
                res.diagnostic_code = res.diagnostic_code or _header_from_part(
                    block, "Diagnostic-Code"
                )
                res.remote_mta = res.remote_mta or _header_from_part(
                    block, "Remote-MTA"
                )
                res.reporting_mta = res.reporting_mta or _header_from_part(
                    block, "Reporting-MTA"
                )
                fr = _header_from_part(block, "Final-Recipient")
                if fr and not res.verp_token and "bounce+" in fr:
                    res.verp_token = fr.split("bounce+", 1)[1].split("@", 1)[0]
    res.identified_backend = identify_backend(
        res.diagnostic_code, res.remote_mta, res.reporting_mta
    )
    return res


# ── Email di probe ──────────────────────────────────────────────────────────

_PROBE_BODY = """\
Questo è un TEST AUTOMATICO di recapito email, inviato dall'Osservatorio sulla
Sovranità Digitale della Posta Elettronica della Pubblica Amministrazione
Italiana (mxmap.it), progetto di pubblico interesse.

Serve esclusivamente a verificare la configurazione tecnica del servizio di
posta di questo dominio pubblico. NON richiede alcuna azione: può essere
ignorato. Nessun dato personale è raccolto.

Informazioni e contatto: https://github.com/fpietrosanti/mxmap.it
"""


def build_probe_message(cfg: BounceConfig, domain: str, token: str) -> EmailMessage:
    """Costruisce un'email ben formata (header anti-spam, dichiarazione di TEST,
    return-path VERP) verso un indirizzo inesistente del dominio target."""
    msg = EmailMessage()
    msg["From"] = f"{cfg.from_name} <{cfg.from_address}>"
    msg["To"] = f"mxmap-probe-no-such-mailbox@{domain}"
    msg["Subject"] = cfg.subject
    msg["Auto-Submitted"] = "auto-generated"  # RFC 3834: evita loop auto-reply
    msg["Precedence"] = "bulk"
    msg["X-Mxmap-Probe"] = token
    msg.set_content(_PROBE_BODY)
    return msg


# ── Pool di invio (serializzazione per IP) ──────────────────────────────────


def build_send_plan(
    items: list[tuple[str, str | None]], per_ip_interval: int
) -> list[dict]:
    """Ordina gli invii distanziando nel tempo quelli verso lo STESSO IP.

    ``items`` = lista di (domain, dest_ip). Ritorna una lista di
    {domain, ip, offset_sec}: gli invii allo stesso IP sono spaziati di almeno
    ``per_ip_interval`` secondi; domini diversi su IP diversi partono subito.
    """
    next_free: dict[str, int] = {}
    plan: list[dict] = []
    for domain, ip in items:
        key = ip or f"__noip__:{domain}"
        offset = next_free.get(key, 0)
        plan.append({"domain": domain, "ip": ip, "offset_sec": offset})
        next_free[key] = offset + per_ip_interval
    plan.sort(key=lambda r: r["offset_sec"])
    return plan


# ── Riconciliazione (esito -> nuova classificazione) ────────────────────────

# backend identificato -> (provider, hint giurisdizione, confidence)
_RECONCILE: dict[str, tuple[str, str | None, float]] = {
    "microsoft": ("microsoft", "foreign", 0.85),
    "google": ("google", "foreign", 0.85),
    "aws": ("aws", "foreign", 0.85),
    "aruba": ("aruba", "domestic", 0.85),
    "register-it": ("register-it", "domestic", 0.85),
    "seeweb": ("seeweb", "domestic", 0.85),
}


def reconcile(backend: str | None, rcpt_validation: str) -> dict | None:
    """Mappa il backend identificato a un eventuale aggiornamento di
    provider/jurisdiction/confidence. Ritorna None se inconcludente o se il
    backend è solo un software self-hosted (resta ``independent``, ma annotiamo
    il software e alziamo un po' la confidenza perché ora è corroborato)."""
    if not backend:
        return None
    if backend in _RECONCILE:
        prov, jur, conf = _RECONCILE[backend]
        return {
            "provider": prov,
            "mx_jurisdiction": jur,
            "classification_confidence": conf,
        }
    if backend.endswith("-gw"):
        # gateway identificato ma backend dietro ancora ignoto: non riclassifica
        return {"smtp_software": backend}
    # software self-hosted (postfix/exim/zimbra/…): resta independent, corroborato
    return {"smtp_software": backend, "classification_confidence": 0.65}


# ── Esito del probe ─────────────────────────────────────────────────────────


@dataclass
class ProbeResult:
    domain: str
    mx_host: str | None = None
    mx_ip: str | None = None
    banner: str | None = None
    rcpt_code: int | None = None
    rcpt_text: str | None = None
    rcpt_validation: str = "unreachable"
    data_code: int | None = None
    outcome: str = "unreachable"
    identified_backend: str | None = None
    verp_token: str | None = None
    error: str | None = None
    dry_run: bool = True
    extra: dict = field(default_factory=dict)


def _outcome(rcpt_validation: str, data_code: int | None) -> str:
    if rcpt_validation == "rejected_5xx":
        return "rcpt_rejected"
    if rcpt_validation == "accepted_2xx":
        # ingerita: l'eventuale bounce arriva dopo via IMAP
        return (
            "ingested" if (data_code and 200 <= data_code < 300) else "accept_partial"
        )
    if rcpt_validation == "tempfail":
        return "tempfail"
    return "mx_unreachable"


def probe_domain(cfg: BounceConfig, cand: dict, *, connect=None) -> ProbeResult:
    """Esegue il flusso unico verso il primo MX del candidato.

    Se ``cfg.dry_run`` non apre connessioni: ritorna un ProbeResult marcato
    dry_run. ``connect(host, port, timeout)`` è iniettabile (per i test);
    di default usa smtplib direct-to-MX.
    """
    domain = cand["domain"]
    mx_list = cand.get("mx") or []
    mx_host = mx_list[0] if mx_list else None
    token = verp_token(domain)
    res = ProbeResult(
        domain=domain, mx_host=mx_host, verp_token=token, dry_run=cfg.dry_run
    )

    if cfg.dry_run:
        res.outcome = "dry_run"
        return res
    if not mx_host:
        res.outcome = "mx_unreachable"
        res.error = "no MX"
        return res

    if connect is None:
        connect = _default_connect
    try:
        conn = connect(mx_host, 25, cfg.connect_timeout_sec)
    except Exception as exc:  # pragma: no cover - rete reale
        res.outcome = "mx_unreachable"
        res.rcpt_validation = "unreachable"
        res.error = f"connect: {exc}"
        return res

    try:
        res.banner = getattr(conn, "banner", None)
        conn.ehlo(cfg.helo_hostname)
        if cfg.starttls and getattr(conn, "has_extn", lambda x: False)("starttls"):
            conn.starttls()
            conn.ehlo(cfg.helo_hostname)
        res.mx_ip = getattr(conn, "peer_ip", None)
        conn.mail(verp_address(cfg, domain))
        code, text = conn.rcpt(f"mxmap-probe-no-such-mailbox@{domain}")
        res.rcpt_code, res.rcpt_text = code, _as_text(text)
        res.rcpt_validation = classify_rcpt(code)
        if res.rcpt_validation == "accepted_2xx":
            msg = build_probe_message(cfg, domain, token)
            dcode, _dtext = conn.data(msg.as_bytes())
            res.data_code = dcode
        res.identified_backend = identify_backend(res.banner, res.rcpt_text)
        res.outcome = _outcome(res.rcpt_validation, res.data_code)
    except Exception as exc:  # pragma: no cover - rete reale
        res.error = f"smtp: {exc}"
        res.outcome = res.outcome or "error"
    finally:
        try:
            conn.quit()
        except Exception:  # pragma: no cover
            pass
    return res


def _as_text(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return str(v)


def _default_connect(host: str, port: int, timeout: int):  # pragma: no cover - rete
    import smtplib

    conn = smtplib.SMTP(timeout=timeout)
    code, banner = conn.connect(host, port)
    conn.banner = _as_text(banner)
    try:
        conn.peer_ip = conn.sock.getpeername()[0]
    except Exception:
        conn.peer_ip = None
    return conn


# ── Report ──────────────────────────────────────────────────────────────────


def build_summary(results: list[ProbeResult], ndrs: list[NdrResult]) -> dict:
    """Rendiconto sintetico: conteggi per esito, per rcpt_validation, per
    backend identificato, e n. enti riclassificabili."""
    from collections import Counter

    outcomes = Counter(r.outcome for r in results)
    rcpt = Counter(r.rcpt_validation for r in results)
    backends = Counter(
        b
        for b in (
            [r.identified_backend for r in results]
            + [n.identified_backend for n in ndrs]
        )
        if b
    )
    reclassifiable = sum(
        1 for r in results if reconcile(r.identified_backend, r.rcpt_validation)
    ) + sum(1 for n in ndrs if reconcile(n.identified_backend, "accepted_2xx"))
    return {
        "n_probed": len(results),
        "n_ndr": len(ndrs),
        "by_outcome": dict(outcomes),
        "by_rcpt_validation": dict(rcpt),
        "by_backend": dict(backends),
        "reclassifiable": reclassifiable,
    }


def build_detail(results: list[ProbeResult]) -> list[dict]:
    """Rendiconto analitico: una riga per dominio con la transazione + il
    suggerimento di riclassificazione."""
    rows = []
    for r in results:
        row = asdict(r)
        row["reconcile"] = reconcile(r.identified_backend, r.rcpt_validation)
        rows.append(row)
    return rows


# ── Raccolta NDR via IMAP ───────────────────────────────────────────────────


def collect_ndrs(cfg: BounceConfig, *, imap=None) -> list[NdrResult]:
    """Legge gli NDR dalla casella IMAP e li parsa. ``imap`` è iniettabile per
    i test (oggetto con .search/.fetch sui messaggi grezzi). In dry_run o senza
    host IMAP ritorna []."""
    if cfg.dry_run or not cfg.imap_host:
        return []
    if imap is None:  # pragma: no cover - rete reale
        imap = _default_imap(cfg)
    out: list[NdrResult] = []
    for raw in imap.iter_messages():
        import email

        msg = email.message_from_bytes(raw)
        if msg.get_content_type().startswith("multipart/report") or "delivery" in (
            msg.get("Subject", "").lower()
        ):
            out.append(parse_ndr(msg))
    return out


def _default_imap(cfg: BounceConfig):  # pragma: no cover - rete reale
    import imaplib

    cls = imaplib.IMAP4_SSL if cfg.imap_security == "ssl" else imaplib.IMAP4
    conn = cls(cfg.imap_host, cfg.imap_port)
    conn.login(cfg.imap_username, cfg.imap_password)
    conn.select(cfg.imap_mailbox)

    class _Wrap:
        def iter_messages(self):
            typ, data = conn.search(None, "ALL")
            for num in data[0].split():
                t, d = conn.fetch(num, "(RFC822)")
                if d and d[0]:
                    yield d[0][1]

    return _Wrap()


def write_jsonl(path: str | Path, records: list[dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


__all__ = [
    "BounceConfig",
    "load_config",
    "verp_token",
    "verp_address",
    "build_token_map",
    "classify_rcpt",
    "identify_backend",
    "parse_ndr",
    "NdrResult",
    "build_probe_message",
    "build_send_plan",
    "reconcile",
    "ProbeResult",
    "probe_domain",
    "collect_ndrs",
    "build_summary",
    "build_detail",
    "write_jsonl",
]
