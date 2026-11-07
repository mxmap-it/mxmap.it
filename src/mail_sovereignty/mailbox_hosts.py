"""Verifica attiva dei "mailbox host" (farm Zimbra/Carbonio) — mxmap.it#31.

Semantica delle evidenze (vedi docs/MAILBOX_HOSTS.md):

- una **pagina di login Zimbra/Carbonio/Zextras** raggiungibile sul webmail
  dell'ente (o sul proxy della farm a cui punta il suo autodiscover) prova che
  le caselle vivono sulla farm → il verdetto cloud da token TXT / tenant
  getuserrealm è un falso positivo;
- un **autodiscover che risolve sulla farm** (es. ``proxy.zimbraopen.it``) è
  evidenza positiva di hosting locale anche senza probe HTTP;
- un autodiscover/DKIM del **cloud provider** (``autodiscover.outlook.com``,
  ``*.onmicrosoft.com``) indica un ibrido genuino: il fix #31 NON lo tocca.

Qui vive la logica pura (parsing dei marker, scelta dei candidati, farm note):
unit-testata in tests/test_mailbox_hosts.py. L'I/O di rete sta nel CLI sottile
scripts/verify_mailbox_hosts.py (convenzione del repo: logic in src/).
"""

from __future__ import annotations

# Domini delle farm Zimbra/Carbonio note (SLD): usati per riconoscere MX,
# autodiscover e webmail che risolvono sulla farm stessa.
FARM_DOMAINS: tuple[str, ...] = (
    "zimbraopen.it",
    "zimbramail.it",
    "carboniocloud.com",
    "zimbraoffice.it",
)

# Marker DELIBERATAMENTE specifici delle pagine di login Zimbra/Carbonio/
# Zextras. "carbonio" da solo NON è un marker: in italiano è l'elemento
# chimico (una pagina comunale su "impronta di carbonio" sarebbe un falso
# positivo) — il test negativo in test_mailbox_hosts.py lo fissa.
MAILBOX_LOGIN_MARKERS: tuple[tuple[str, str], ...] = (
    ("zimbra web client", "zimbra"),
    ("zimbraloginurl", "zimbra"),
    ("zmlogin", "zimbra"),
    ("carbonio authentication", "carbonio"),
    ("zextras authentication", "zextras"),
    ("/zx/login/", "zextras"),
)

# Host/CNAME che indicano il CLOUD provider (ibrido genuino, non farm).
CLOUD_HOST_HINTS: tuple[str, ...] = (
    "outlook.com",
    "office365.com",
    "onmicrosoft.com",
    "microsoft",
    "googlemail.com",
    "google.com",
)

_SKIP_HOST_HINTS: tuple[str, ...] = (".invalid", "localhost")

WEBMAIL_PREFIXES: tuple[str, ...] = ("webmail", "mail", "posta", "zimbra")


def classify_login_page(body: str, title: str = "") -> str | None:
    """Ritorna il software della pagina di login ("zimbra"/"carbonio"/
    "zextras") se un marker specifico è presente, altrimenti None."""
    blob = f"{title}\n{body}".lower()
    for marker, software in MAILBOX_LOGIN_MARKERS:
        if marker in blob:
            return software
    return None


def is_farm_host(host: str | None) -> bool:
    """True se l'host appartiene a una farm Zimbra/Carbonio nota."""
    h = (host or "").lower().rstrip(".")
    return any(h == d or h.endswith("." + d) for d in FARM_DOMAINS)


def is_cloud_host(host: str | None) -> bool:
    """True se l'host indica il cloud provider (ibrido genuino)."""
    h = (host or "").lower()
    return any(k in h for k in CLOUD_HOST_HINTS)


def autodiscover_hosts(entry: dict) -> list[str]:
    """Gli host (cname/srv) del campo autodiscover, normalizzati."""
    ad = entry.get("autodiscover") or {}
    if not isinstance(ad, dict):
        return []
    out = []
    for v in ad.values():
        h = (v or "").strip().lower().rstrip(".")
        if h and h not in out:
            out.append(h)
    return out


def candidate_hosts(entry: dict) -> list[str]:
    """Host da sondare via HTTPS per l'ente: autodiscover (non-cloud) +
    webmail convenzionali sul dominio + gli stessi MX (se farm).

    Esclude host cloud (sono già un verdetto, non un candidato) e sentinelle
    non risolvibili (*.invalid). Ordine deterministico, max 6.
    """
    out: list[str] = []

    def add(h: str | None) -> None:
        h = (h or "").strip().lower().rstrip(".")
        if not h or h in out or len(out) >= 6:
            return
        if any(k in h for k in _SKIP_HOST_HINTS) or is_cloud_host(h):
            return
        out.append(h)

    for h in autodiscover_hosts(entry):
        add(h)
    domain = (entry.get("domain") or "").strip().lower()
    if domain:
        for pfx in WEBMAIL_PREFIXES:
            add(f"{pfx}.{domain}")
    for h in entry.get("mx") or []:
        if is_farm_host(h):
            add(h)
    return out


def entity_verdict(
    entry: dict,
    probed: dict[str, str | None],
    confirmed_farms: set[str],
) -> tuple[str, str]:
    """(verdetto, evidenza) per un ente, dai risultati probe per-host.

    - mailbox_host_confirmed: login Zimbra/Carbonio visto su un host dell'ente
      o della sua farm;
    - farm_autodiscover: autodiscover punta a una farm nota (anche senza
      risposta HTTP);
    - farm_mx_confirmed: MX su una farm il cui frontend è stato confermato
      altrove in questo run;
    - hybrid_cloud: DKIM o autodiscover puntano al cloud provider — segnale
      primario, vince anche su un webmail farm raggiungibile (migrazioni);
    - unverified: nessuna evidenza attiva raccolta (follow-up manuale).
    """
    dkim = entry.get("dkim") or {}
    dkim_blob = (
        " ".join(str(v) for v in dkim.values()) if isinstance(dkim, dict) else str(dkim)
    ).lower()
    if any(k in dkim_blob for k in CLOUD_HOST_HINTS):
        return "hybrid_cloud", "DKIM → cloud provider"
    for h in autodiscover_hosts(entry):
        if is_cloud_host(h):
            return "hybrid_cloud", f"autodiscover → {h}"
    for host in candidate_hosts(entry):
        sw = probed.get(host)
        if sw:
            return "mailbox_host_confirmed", f"{host} → login {sw}"
    for h in autodiscover_hosts(entry):
        if is_farm_host(h):
            return "farm_autodiscover", f"autodiscover → {h}"
    for h in entry.get("mx") or []:
        hl = (h or "").lower().rstrip(".")
        for farm in FARM_DOMAINS:
            if (hl == farm or hl.endswith("." + farm)) and farm in confirmed_farms:
                return "farm_mx_confirmed", f"MX {hl} su farm confermata {farm}"
    return "unverified", ""


def farm_of(host: str | None) -> str | None:
    """Il dominio-farm a cui appartiene l'host, se noto."""
    h = (host or "").lower().rstrip(".")
    for d in FARM_DOMAINS:
        if h == d or h.endswith("." + d):
            return d
    return None
