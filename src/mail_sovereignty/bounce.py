"""Bounce-verifier — verifica attiva del backend di posta per i casi a bassa
confidenza (vedi docs/BOUNCE_VERIFIER_DESIGN.md).

Approccio: si **invia** un'email di test verso un indirizzo inesistente di ogni
dominio target **attraverso lo smarthost autenticato** (es. Google Workspace,
SPF/DKIM/DMARC allineati → buona deliverability, niente direct-to-MX che
finirebbe in spam). Si **analizzano poi i bounce/NDR** che tornano alla casella
mittente: dal Diagnostic-Code / Remote-MTA dell'NDR si identifica l'MTA reale del
backend e si corregge provider/giurisdizione/confidenza.

Niente RCPT TO sincrono: il fatto che il destinatario validi o no il destinatario
emerge comunque dall'NDR (es. "550 User unknown"), in modo asincrono.

Le funzioni di logica pura sono testabili senza rete; ``send_probe`` e
``collect_ndrs`` accettano connessioni iniettabili per i test.
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
    # smarthost di invio (submission autenticata)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_security: str = "starttls"  # "starttls" | "tls"
    smtp_username: str = ""
    smtp_password: str = ""
    connect_timeout_sec: int = 20
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
        smtp_host=smtp.get("host", ""),
        smtp_port=int(smtp.get("port", 587)),
        smtp_security=smtp.get("security", "starttls"),
        smtp_username=smtp.get("username", ""),
        smtp_password=smtp.get("password", ""),
        connect_timeout_sec=int(limits.get("connect_timeout_sec", 20)),
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


# ── Identificazione del backend ─────────────────────────────────────────────

# keyword (su diagnostic-code/Remote-MTA dell'NDR) -> backend reale
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
    (diagnostic-code, Remote-MTA, Reporting-MTA dell'NDR)."""
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
    # da quale hop è nato l'NDR: sender (nostro smarthost) / gateway
    # (antispam ricevente) / destination (MTA backend finale) / unknown
    ndr_from: str | None = None
    ndr_origin: str = "unknown"
    received_chain: list[str] = field(default_factory=list)


# Keyword di gateway antispam riceventi (origine intermedia dell'NDR)
GATEWAY_ORIGINS: tuple[str, ...] = (
    "sophos",
    "proofpoint",
    "pphosted",
    "barracuda",
    "mailspamprotection",
    "fortimail",
    "ironport",
    "mimecast",
    "spamtitan",
    "libraesva",
)


def sender_hosts_from_cfg(cfg: BounceConfig) -> tuple[str, ...]:
    """Host che identificano il NOSTRO smarthost di invio (per riconoscere gli
    NDR generati dal nostro lato): host SMTP + dominio mittente/VERP, più gli
    alias Google se lo smarthost è Workspace/Gmail."""
    hosts: set[str] = set()
    if cfg.smtp_host:
        hosts.add(cfg.smtp_host.lower())
    for addr in (cfg.from_address, cfg.verp_format):
        if "@" in addr:
            hosts.add(addr.split("@", 1)[1].split(">")[0].strip().lower())
    if any("gmail" in h or "google" in h for h in hosts):
        hosts.update({"google.com", "googlemail.com"})
    return tuple(h for h in hosts if h)


def classify_ndr_origin(
    reporting_mta: str | None, ndr_from: str | None, sender_hosts: tuple[str, ...]
) -> str:
    """Da quale hop è nato l'NDR, dal Reporting-MTA + mittente (MAILER-DAEMON):
    ``gateway`` (antispam ricevente), ``sender`` (nostro smarthost), altrimenti
    ``destination`` (MTA backend finale); ``unknown`` se nessun segnale.

    Nota: se smarthost e destinazione sono lo stesso cloud (es. entrambi Google)
    il Reporting-MTA non basta a distinguere sender da destination → restano i
    campi grezzi (remote_mta, diagnostic, received_chain) per disambiguare."""
    blob = " ".join(t.lower() for t in (reporting_mta, ndr_from) if t)
    if not blob:
        return "unknown"
    for gw in GATEWAY_ORIGINS:
        if gw in blob:
            return "gateway"
    for sh in sender_hosts:
        if sh and sh in blob:
            return "sender"
    return "destination"


def _header_from_part(part: Message, name: str) -> str | None:
    val = part.get(name)
    return str(val) if val is not None else None


def parse_ndr(msg: Message, sender_hosts: tuple[str, ...] = ()) -> NdrResult:
    """Estrae i campi diagnostici da un NDR multipart/report (RFC 3464):
    cerca la parte ``message/delivery-status`` e i suoi header per-recipient, e
    registra in modo strutturato **da quale hop** nasce il bounce (mittente
    MAILER-DAEMON, catena Received, Reporting-MTA → ``ndr_origin``)."""
    res = NdrResult()
    res.ndr_from = _header_from_part(msg, "From")
    res.received_chain = [str(r) for r in msg.get_all("Received", [])]
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
    res.ndr_origin = classify_ndr_origin(res.reporting_mta, res.ndr_from, sender_hosts)
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


# ── Pool di invio (serializzazione per IP di destinazione) ──────────────────


def build_send_plan(
    items: list[tuple[str, str | None]], per_ip_interval: int
) -> list[dict]:
    """Ordina gli invii distanziando nel tempo quelli verso lo STESSO IP di
    destinazione (per non saturare un singolo backend ricevente).

    ``items`` = lista di (domain, dest_ip). Ritorna {domain, ip, offset_sec}.
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


# ── Invio via smarthost ─────────────────────────────────────────────────────


@dataclass
class SendResult:
    domain: str
    verp_token: str
    submitted: bool = False
    smtp_text: str | None = None
    error: str | None = None
    dry_run: bool = True


def send_probe(cfg: BounceConfig, cand: dict, *, smtp=None) -> SendResult:
    """Invia l'email di probe verso il dominio target ATTRAVERSO lo smarthost.

    Non apre connessioni in ``cfg.dry_run``. ``smtp`` (connessione smarthost già
    aperta e autenticata) è iniettabile per i test; il chiamante reale la apre
    una volta con ``open_smarthost`` e la riusa per tutti gli invii.
    """
    domain = cand["domain"]
    token = verp_token(domain)
    res = SendResult(domain=domain, verp_token=token, dry_run=cfg.dry_run)
    if cfg.dry_run:
        return res
    msg = build_probe_message(cfg, domain, token)
    target = f"mxmap-probe-no-such-mailbox@{domain}"
    try:
        refused = smtp.sendmail(verp_address(cfg, domain), [target], msg.as_bytes())
        # sendmail ritorna {} se accettato; un dict non vuoto = destinatari rifiutati
        res.submitted = not refused
        res.smtp_text = "accepted" if not refused else str(refused)
    except Exception as exc:  # pragma: no cover - rete reale
        res.error = f"send: {exc}"
    return res


def open_smarthost(cfg: BounceConfig):  # pragma: no cover - rete reale
    """Apre e autentica una connessione allo smarthost (submission)."""
    import smtplib

    if cfg.smtp_security == "tls":
        conn = smtplib.SMTP_SSL(
            cfg.smtp_host, cfg.smtp_port, timeout=cfg.connect_timeout_sec
        )
    else:
        conn = smtplib.SMTP(
            cfg.smtp_host, cfg.smtp_port, timeout=cfg.connect_timeout_sec
        )
        conn.ehlo()
        conn.starttls()
        conn.ehlo()
    conn.login(cfg.smtp_username, cfg.smtp_password)
    return conn


# ── Riconciliazione (backend NDR -> nuova classificazione) ──────────────────

_RECONCILE: dict[str, tuple[str, str | None, float]] = {
    "microsoft": ("microsoft", "foreign", 0.85),
    "google": ("google", "foreign", 0.85),
    "aws": ("aws", "foreign", 0.85),
    "aruba": ("aruba", "domestic", 0.85),
    "register-it": ("register-it", "domestic", 0.85),
    "seeweb": ("seeweb", "domestic", 0.85),
}


def reconcile(backend: str | None) -> dict | None:
    """Mappa il backend identificato (dall'NDR) a un eventuale aggiornamento di
    provider/jurisdiction/confidence. None se inconcludente; per software
    self-hosted resta ``independent`` ma annotiamo il software e alziamo la
    confidenza perché ora corroborato."""
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
        return {"smtp_software": backend}
    return {"smtp_software": backend, "classification_confidence": 0.65}


# ── Join + report ───────────────────────────────────────────────────────────


def join_results(sends: list[SendResult], ndrs: list[NdrResult]) -> list[dict]:
    """Unisce invii e NDR per token VERP. Esito per dominio:
    ``bounced`` (NDR ricevuto → backend), ``no_bounce`` (inviato, nessun NDR →
    catch-all/accettato/silent), ``not_submitted`` (invio fallito)."""
    ndr_by_token: dict[str, NdrResult] = {n.verp_token: n for n in ndrs if n.verp_token}
    rows = []
    for s in sends:
        ndr = ndr_by_token.get(s.verp_token)
        if not s.submitted and not s.dry_run:
            outcome = "not_submitted"
        elif ndr is not None:
            outcome = "bounced"
        elif s.dry_run:
            outcome = "dry_run"
        else:
            outcome = "no_bounce"
        backend = ndr.identified_backend if ndr else None
        # riclassifica il provider solo se l'NDR ha RAGGIUNTO il backend:
        # destination (il backend stesso) o gateway (il cui Remote-MTA nomina il
        # backend). NON ci fidiamo degli NDR 'sender' (fallimento del nostro
        # relay, il backend non è stato raggiunto).
        trust = bool(ndr) and ndr.ndr_origin in ("destination", "gateway")
        rows.append(
            {
                "domain": s.domain,
                "verp_token": s.verp_token,
                "submitted": s.submitted,
                "outcome": outcome,
                "identified_backend": backend,
                "ndr_origin": ndr.ndr_origin if ndr else None,
                "ndr_from": ndr.ndr_from if ndr else None,
                "ndr_status": ndr.status if ndr else None,
                "ndr_diagnostic": ndr.diagnostic_code if ndr else None,
                "reporting_mta": ndr.reporting_mta if ndr else None,
                "remote_mta": ndr.remote_mta if ndr else None,
                "reconcile": reconcile(backend) if trust else None,
                "error": s.error,
            }
        )
    return rows


def build_summary(sends: list[SendResult], ndrs: list[NdrResult]) -> dict:
    """Rendiconto sintetico: invii, bounce, esiti, backend identificati,
    enti riclassificabili."""
    from collections import Counter

    rows = join_results(sends, ndrs)
    outcomes = Counter(r["outcome"] for r in rows)
    backends = Counter(r["identified_backend"] for r in rows if r["identified_backend"])
    origins = Counter(n.ndr_origin for n in ndrs)
    reclassifiable = sum(1 for r in rows if r["reconcile"])
    return {
        "n_sent": sum(1 for s in sends if s.submitted),
        "n_ndr": len(ndrs),
        "by_outcome": dict(outcomes),
        "by_backend": dict(backends),
        "by_ndr_origin": dict(origins),
        "reclassifiable": reclassifiable,
    }


def build_detail(sends: list[SendResult], ndrs: list[NdrResult]) -> list[dict]:
    """Rendiconto analitico: una riga per dominio (invio + NDR + suggerimento)."""
    return join_results(sends, ndrs)


# ── Raccolta NDR via IMAP ───────────────────────────────────────────────────


def collect_ndrs(cfg: BounceConfig, *, imap=None) -> list[NdrResult]:
    """Legge gli NDR dalla casella IMAP e li parsa. ``imap`` è iniettabile per
    i test (oggetto con ``iter_messages()`` sui messaggi grezzi). In dry_run o
    senza host IMAP ritorna []."""
    if cfg.dry_run or not cfg.imap_host:
        return []
    if imap is None:  # pragma: no cover - rete reale
        imap = _default_imap(cfg)
    sh = sender_hosts_from_cfg(cfg)
    out: list[NdrResult] = []
    for raw in imap.iter_messages():
        import email

        msg = email.message_from_bytes(raw)
        if msg.get_content_type().startswith("multipart/report") or "delivery" in (
            msg.get("Subject", "").lower()
        ):
            out.append(parse_ndr(msg, sh))
    return out


def _default_imap(cfg: BounceConfig):  # pragma: no cover - rete reale
    import imaplib

    cls = imaplib.IMAP4_SSL if cfg.imap_security == "ssl" else imaplib.IMAP4
    conn = cls(cfg.imap_host, cfg.imap_port)
    conn.login(cfg.imap_username, cfg.imap_password)
    conn.select(cfg.imap_mailbox)

    class _Wrap:
        def iter_messages(self):
            _typ, data = conn.search(None, "ALL")
            for num in data[0].split():
                _t, d = conn.fetch(num, "(RFC822)")
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
    "identify_backend",
    "parse_ndr",
    "classify_ndr_origin",
    "sender_hosts_from_cfg",
    "NdrResult",
    "build_probe_message",
    "build_send_plan",
    "SendResult",
    "send_probe",
    "open_smarthost",
    "reconcile",
    "join_results",
    "collect_ndrs",
    "build_summary",
    "build_detail",
    "write_jsonl",
    "asdict",
]
