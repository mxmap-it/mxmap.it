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

4. Attribuzione PER-PROVIDER dei segnali (#29 fix B, 2026-11): come il
   by_provider[winner] upstream, un segnale conta solo se PUNTA al provider
   eletto (keyword/ASN match), non se il campo semplicemente esiste. Senza
   questo, dietro gateway scattava mx_spf 0,90–0,96 sui verdetti più deboli.
   In più: gateway_no_primary → unknown con confidence 0.0 (come paper), e i
   verdetti vendor-hosted (pa-contractor-private dal fallback gateway,
   scenario B) usano la scala per giurisdizione come gli independent.

Riferimento: https://github.com/mxmap/esorics2026
"""

from __future__ import annotations

from typing import NamedTuple

from mail_sovereignty.classify import (
    classify_from_autodiscover,
    classify_from_dkim,
)
from mail_sovereignty.constants import (
    ITALIAN_PA_VENDOR_GATEWAYS,
    ITALIAN_PROVIDER_ASN_OVERRIDES,
    LOCAL_ISP_ASNS,
    PROVIDER_KEYWORDS,
)

# Segnali (stringhe al posto dell'enum SignalKind upstream)
MX = "mx"
SPF = "spf"
DKIM = "dkim"
AUTODISCOVER = "autodiscover"
TENANT = "tenant"
TXT_VERIFICATION = "txt_verification"

# I keyword del MIM/MIUR sono quelli Microsoft (tenant centrale MS365).
_PROVIDER_KEYWORD_ALIASES = {"istruzione-miur-tenant": "microsoft"}

# Provider che corrispondono a Microsoft 365 (TENANT/AUTODISCOVER attribuiti
# a MS365 come fa probe_tenant/probe_autodiscover upstream).
MS365_PROVIDERS = {"microsoft", "istruzione-miur-tenant"}

# Provider cloud esteri soggetti al domestic-MX-override (MX cloud-specifico).
# Pattern MX del cloud: se l'MX NON contiene questi, il verdetto è venuto
# da un segnale non-MX (tenant/dkim) → candidato override.
CLOUD_MX_PATTERNS = {
    "microsoft": (
        "protection.outlook.com",
        "outlook.com",
        "outlook.de",
        "mx.microsoft",
    ),
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
    + ("no_mx", "gateway_no_primary")
)


def _rule_confidence(signals: set[str], gateway: str | None) -> tuple[float, str]:
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
    has_mx: bool,
    has_spf: bool,
    has_secondary: bool,
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


def _keyword_blob_matches(blob: str, provider: str) -> bool:
    """True se il blob contiene una keyword del provider (con alias MIM)."""
    key = _PROVIDER_KEYWORD_ALIASES.get(provider, provider)
    keywords = PROVIDER_KEYWORDS.get(key) or ()
    return any(k in blob for k in keywords)


def _mx_points_at(entry: dict, provider: str) -> bool:
    """MX attribuito al provider: hostname/CNAME con keyword del provider,
    oppure IP del MX nell'AS del provider (override ASN / local-isp) — il
    routing verso il provider è provato anche con hostname custom."""
    mx = entry.get("mx") or []
    if not any((h or "").strip() for h in mx):
        return False
    blob = " ".join((h or "").lower() for h in mx)
    cnames = entry.get("mx_cnames") or {}
    if isinstance(cnames, dict) and cnames:
        blob += " " + " ".join(str(v).lower() for v in cnames.values())
    if _keyword_blob_matches(blob, provider):
        return True
    key = _PROVIDER_KEYWORD_ALIASES.get(provider, provider)
    asns = set(entry.get("mx_asns") or [])
    if asns:
        if key == "local-isp" and asns & set(LOCAL_ISP_ASNS):
            return True
        if any(ITALIAN_PROVIDER_ASN_OVERRIDES.get(a) == key for a in asns):
            return True
    return False


def _spf_points_at(entry: dict, provider: str) -> bool:
    """SPF attribuito al provider: keyword nel record diretto o risolto
    (upstream probe_spf segue gli include)."""
    blob = " ".join(
        s for s in ((entry.get("spf") or ""), (entry.get("spf_resolved") or "")) if s
    ).lower()
    return bool(blob) and _keyword_blob_matches(blob, provider)


def _attributed_signals(entry: dict, provider: str) -> set[str]:
    """Segnali ATTRIBUITI al provider eletto, come by_provider[winner]
    upstream (#29 fix B): MX/SPF/DKIM solo se puntano al provider;
    AUTODISCOVER/TENANT solo per MS365 e solo se coerenti; il token TXT del
    provider (MS=/google-site-verification) è boost-only come upstream."""
    sig: set[str] = set()
    key = _PROVIDER_KEYWORD_ALIASES.get(provider, provider)
    if _mx_points_at(entry, provider):
        sig.add(MX)
    if _spf_points_at(entry, provider):
        sig.add(SPF)
    if classify_from_dkim(entry.get("dkim")) == key:
        sig.add(DKIM)
    if provider in MS365_PROVIDERS:
        if classify_from_autodiscover(entry.get("autodiscover")) == "microsoft":
            sig.add(AUTODISCOVER)
        if entry.get("tenant"):
            sig.add(TENANT)
    txt = entry.get("txt_verifications") or {}
    if isinstance(txt, dict) and key in txt:
        sig.add(TXT_VERIFICATION)
    return sig


def _is_vendor_hosted(entry: dict, provider: str) -> bool:
    """pa-contractor-private assegnato dal fallback vendor-relay (#29 B):
    l'MX è la farm/relay del fornitore (match da GATEWAY_KEYWORDS, non
    dalle keyword del provider) → confidence per giurisdizione come gli
    independent, non con le regole provider."""
    if provider != "pa-contractor-private":
        return False
    if (entry.get("gateway") or "") not in ITALIAN_PA_VENDOR_GATEWAYS:
        return False
    blob = " ".join((h or "").lower() for h in entry.get("mx") or [])
    return not _keyword_blob_matches(blob, provider)


def needs_domestic_mx_override(entry: dict) -> bool:
    """True se il verdetto cloud (microsoft/google/aws) NON è supportato dal
    MX (l'MX non è quello del cloud → il segnale era tenant/DKIM, es. MS365
    solo per Teams) E il MX è domestico/estero → la posta in entrata è
    self-hosted, da riclassificare per giurisdizione.

    NON scatta per le scuole istruzione-miur-tenant (il loro MX È
    istruzione-it.mail.protection.outlook.com → cloud genuino), NÉ quando
    c'è un gateway: in quel caso il verdetto cloud viene dal look-through
    del gateway (DKIM prova il backend reale dietro l'appliance antispam),
    quindi è legittimo e non va riclassificato. Come ESORICS: l'override
    è 'if not gateway and not has_cloud_mx'."""
    provider = entry.get("provider") or ""
    if provider not in CLOUD_MX_PATTERNS:
        return False
    if entry.get("gateway"):
        return False  # backend cloud identificato via gateway look-through
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

    - unknown senza MX → (0.0, 'no_mx', [], jur)
    - unknown con MX dietro gateway → (0.0, 'gateway_no_primary', [], jur)
    - independent/provincial-shared e vendor-hosted (#29 B) →
      _country_confidence per giurisdizione
    - ogni altro provider (cloud o IT specifico) → _rule_confidence sui
      segnali ATTRIBUITI al provider (#29 fix B)
    """
    provider = entry.get("provider") or "unknown"
    jur = mx_jurisdiction(entry, target_country)

    if provider in NO_MX_PROVIDERS:
        # Paper: dietro gateway senza segnale primario il backend è
        # indeterminabile → unknown con MX presente (gateway_no_primary,
        # confidence 0.0). Senza MX resta il classico no_mx.
        if entry.get("gateway") and any(
            (h or "").strip() for h in entry.get("mx") or []
        ):
            return 0.0, "gateway_no_primary", [], jur
        return 0.0, "no_mx", [], jur

    if provider in INDEPENDENT_PROVIDERS or _is_vendor_hosted(entry, provider):
        # Scala per giurisdizione: qui i segnali sono PRESENZA di evidenza
        # DNS (il verdetto è "la posta resta su questa infrastruttura"),
        # non attribuzione a un provider cloud.
        signals: set[str] = set()
        if any((h or "").strip() for h in entry.get("mx") or []):
            signals.add(MX)
        if entry.get("spf"):
            signals.add(SPF)
        if entry.get("dkim"):
            signals.add(DKIM)
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
        signals = _attributed_signals(entry, provider)
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
