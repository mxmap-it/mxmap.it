"""Confidence scoring + sovereignty refinement — PORT FEDELE di
mxmap/esorics2026 (paper ESORICS 2026), src/.../provider_classification.

Replica l'algoritmo del classifier ESORICS, più autorevole della versione
davidhuser/mxmap (peer-reviewed). Differenze chiave adottate:

1. Rule set semplificato a 7 regole: solo MX/SPF/DKIM determinano la base;
   TENANT/AUTODISCOVER contribuiscono SOLO come boost (+0.02). Razionale
   upstream: avere un tenant MS365 (Teams) non prova l'hosting della posta.

2. DOMESTIC/FOREIGN via ASN country (Team Cymru CC): gli enti senza match
   cloud non sono un indistinto "independent" ma vengono qualificati per
   giurisdizione dell'IP del MX — sovrano (IT) vs estero. Regole dedicate
   _DOMESTIC_RULES / _FOREIGN_RULES (base flat, no boost).

3. Domestic MX override: se il MX esiste ma NON è quello del cloud (il
   verdetto microsoft/google veniva da tenant/DKIM, es. MS365 solo per
   Teams) e l'MX è domestico, la posta in entrata è self-hosted →
   riclassifica per giurisdizione invece che cloud.

Contesto: da noi il provider è già determinato da classify.py (keyword).
Qui portiamo il CALCOLO della confidence + il refinement di sovranità,
usando i segnali già presenti nell'entità (mx/spf/dkim/autodiscover/
tenant/mx_countries/gateway). Le tabelle _PROVIDER_RULES / _DOMESTIC_RULES
/ _FOREIGN_RULES e le funzioni di scoring sono verbatim dall'upstream
ESORICS (SignalKind→str per non dipendere da pydantic).

Riferimento: https://github.com/mxmap/esorics2026
"""

from __future__ import annotations

from typing import NamedTuple

# Segnali (stringhe al posto dell'enum SignalKind upstream)
MX = "mx"
SPF = "spf"
DKIM = "dkim"
AUTODISCOVER = "autodiscover"
TENANT = "tenant"

# Provider che corrispondono a Microsoft 365 (TENANT/AUTODISCOVER attribuiti
# a MS365 come fa probe_tenant/probe_autodiscover upstream).
MS365_PROVIDERS = {"microsoft", "istruzione-miur-tenant"}

# Provider cloud esteri soggetti al domestic-MX-override (MX cloud-specifico).
# Pattern MX del cloud: se l'MX NON contiene questi, il verdetto è venuto
# da un segnale non-MX (tenant/dkim) → candidato override.
CLOUD_MX_PATTERNS = {
    "microsoft": ("protection.outlook.com", "outlook.com", "outlook.de", "mx.microsoft"),
    "istruzione-miur-tenant": ("protection.outlook.com", "outlook.com"),
    "google": ("aspmx.l.google.com", "googlemail.com", "smtp.google.com", "google.com"),
    "aws": ("amazonaws.com", "awsapps.com"),
}

# Provider "residuo" (MX esiste ma nessun keyword/backend) → giurisdizione.
INDEPENDENT_PROVIDERS = {"independent", "provincial-shared"}
NO_MX_PROVIDERS = {"unknown"}

_BOOST_PER_SIGNAL = 0.02


class _Rule(NamedTuple):
    name: str
    signals: frozenset[str]
    needs_gateway: bool
    base: float


# fmt: off
# VERBATIM dall'upstream ESORICS classifier.py (_PROVIDER_RULES, 7 regole).
_PROVIDER_RULES: tuple[_Rule, ...] = (
    # rule name        signals                  gw?    base
    _Rule("mx_spf",    frozenset({MX, SPF}),    False, 0.90),  # routing + authorization
    _Rule("mx_only",   frozenset({MX}),         False, 0.80),  # routing alone
    _Rule("spf_gw",    frozenset({SPF}),        True,  0.70),  # SPF visible through gateway
    _Rule("dkim_gw",   frozenset({DKIM}),       True,  0.65),  # DKIM proves signer behind gw
    _Rule("dkim_spf",  frozenset({DKIM, SPF}),  False, 0.60),  # two signals, no routing
    _Rule("spf_only",  frozenset({SPF}),        False, 0.50),  # authorization only
    _Rule("fallback",  frozenset(),             False, 0.40),  # catch-all
)

# Domestic: IP del MX confermato nel paese target via Cymru CC.
_DOMESTIC_RULES: tuple[tuple[str, float], ...] = (
    ("dom_mx_spf",     0.80),  # MX domestico + SPF
    ("dom_mx_only",    0.70),  # MX domestico, no SPF
    ("dom_secondary",  0.20),  # solo evidenza secondaria (no MX)
    ("dom_none",       0.00),
)

# Foreign: IP del MX in un altro paese — segnale più debole (CDN, shared hosting).
_FOREIGN_RULES: tuple[tuple[str, float], ...] = (
    ("frgn_mx_spf",    0.60),
    ("frgn_mx_only",   0.50),
    ("frgn_secondary", 0.10),
    ("frgn_none",      0.00),
)
# fmt: on

ALL_RULE_NAMES: tuple[str, ...] = (
    tuple(r.name for r in _PROVIDER_RULES)
    + tuple(n for n, _ in _DOMESTIC_RULES)
    + tuple(n for n, _ in _FOREIGN_RULES)
    + ("no_mx",)
)


def _rule_confidence(
    signals: set[str], gateway: str | None
) -> tuple[float, str]:
    """Port verbatim di ESORICS _rule_confidence.

    Solo MX/SPF/DKIM partecipano al matching delle regole; gli altri
    segnali (TENANT, AUTODISCOVER, …) contribuiscono solo via boost
    (+0.02 ciascuno). Cap a 1.0.
    """
    present: set[str] = set()
    for kind in (MX, SPF, DKIM):
        if kind in signals:
            present.add(kind)
    has_gateway = gateway is not None

    for rule in _PROVIDER_RULES:
        if rule.signals <= present and (not rule.needs_gateway or has_gateway):
            boost = len(signals - rule.signals) * _BOOST_PER_SIGNAL
            return min(1.0, rule.base + boost), rule.name

    return 0.40, "fallback"  # pragma: no cover


def _country_confidence(
    has_mx: bool, has_spf: bool, has_secondary: bool,
    rules: tuple[tuple[str, float], ...],
) -> tuple[float, str]:
    """Port di ESORICS _country_confidence. Base flat (no boost) perché i
    segnali cloud (tenant, txt) sono irrilevanti alla classificazione per
    paese."""
    if has_mx and has_spf:
        name, base = rules[0]
    elif has_mx:
        name, base = rules[1]
    elif has_secondary:
        name, base = rules[2]
    else:
        return 0.0, rules[3][0]
    return base, name


def mx_jurisdiction(entry: dict, target_country: str = "IT") -> str:
    """Giurisdizione dell'infrastruttura MX in base a mx_countries (Team
    Cymru CC): 'domestic' (tutti nel paese target), 'foreign' (nessuno),
    'mixed' (alcuni), 'unknown' (nessun dato)."""
    countries = entry.get("mx_countries") or []
    if not countries:
        return "unknown"
    t = target_country.upper()
    in_target = [c for c in countries if (c or "").upper() == t]
    if len(in_target) == len(countries):
        return "domestic"
    if not in_target:
        return "foreign"
    return "mixed"


def _present_signals(entry: dict, provider: str) -> set[str]:
    """Segnali presenti come by_provider[winner] upstream: MX/SPF/DKIM se
    nei campi DNS; TENANT/AUTODISCOVER solo per MS365 (probe_tenant/
    probe_autodiscover li attribuiscono a MS365)."""
    sig: set[str] = set()
    if entry.get("mx"):
        sig.add(MX)
    if entry.get("spf"):
        sig.add(SPF)
    if entry.get("dkim"):
        sig.add(DKIM)
    if provider in MS365_PROVIDERS:
        if entry.get("autodiscover"):
            sig.add(AUTODISCOVER)
        if entry.get("tenant"):
            sig.add(TENANT)
    return sig


def needs_domestic_mx_override(entry: dict) -> bool:
    """True se il verdetto cloud (microsoft/google/aws) NON è supportato dal
    MX (l'MX non è quello del cloud → il segnale era tenant/DKIM, es. MS365
    solo per Teams) E il MX è domestico/estero → la posta in entrata è
    self-hosted, da riclassificare per giurisdizione.

    NON scatta per le scuole istruzione-miur-tenant (il loro MX È
    istruzione-it.mail.protection.outlook.com → cloud genuino)."""
    provider = entry.get("provider") or ""
    if provider not in CLOUD_MX_PATTERNS:
        return False
    mx = entry.get("mx") or []
    if not mx:
        return False
    patterns = CLOUD_MX_PATTERNS[provider]
    mx_is_cloud = any(p in (h or "").lower() for h in mx for p in patterns)
    if mx_is_cloud:
        return False  # routing cloud genuino → tieni il provider
    # MX non-cloud + verdetto cloud → veniva da tenant/dkim. Riclassifica
    # solo se abbiamo la giurisdizione (altrimenti resta com'è).
    return mx_jurisdiction(entry) in ("domestic", "foreign", "mixed")


def compute_confidence(
    entry: dict, target_country: str = "IT"
) -> tuple[float, str, list[str], str]:
    """Calcola (confidence, rule_name, signals, jurisdiction) per un'entità.

    - unknown (no MX) → (0.0, 'no_mx', [], 'unknown')
    - independent/provincial-shared → _country_confidence per giurisdizione
    - ogni altro provider (cloud o IT specifico) → _rule_confidence
    """
    provider = entry.get("provider") or "unknown"
    jur = mx_jurisdiction(entry, target_country)

    if provider in NO_MX_PROVIDERS:
        return 0.0, "no_mx", [], jur

    signals = _present_signals(entry, provider)

    if provider in INDEPENDENT_PROVIDERS:
        has_mx = MX in signals
        has_spf = SPF in signals
        has_secondary = bool(signals - {MX, SPF}) or bool(entry.get("mx_countries"))
        if jur == "domestic":
            rules = _DOMESTIC_RULES
        elif jur == "foreign":
            rules = _FOREIGN_RULES
        elif jur == "mixed":
            # misto: usa domestic ma con cap leggermente più basso → trattalo
            # come domestic (almeno un hop in IT). Conservativo.
            rules = _DOMESTIC_RULES
        else:
            # nessun dato paese: degrada a foreign-secondary style
            rules = _FOREIGN_RULES
        conf, rule = _country_confidence(has_mx, has_spf, has_secondary, rules)
    else:
        conf, rule = _rule_confidence(signals, entry.get("gateway"))

    return round(conf, 4), rule, sorted(signals), jur


__all__ = [
    "compute_confidence",
    "mx_jurisdiction",
    "needs_domestic_mx_override",
    "ALL_RULE_NAMES",
    "_PROVIDER_RULES",
    "_DOMESTIC_RULES",
    "_FOREIGN_RULES",
]
