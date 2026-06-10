"""Confidence scoring — PORT FEDELE di davidhuser/mxmap classifier.py.

Replica l'algoritmo di confidence dell'upstream
(https://github.com/davidhuser/mxmap, src/mail_sovereignty/classifier.py),
attenendosi alle stesse regole, pesi e formula. NON aggiunge euristiche
proprie (niente bonus/malus per metodo di scoperta, country, ecc.).

Differenza di contesto:
  - Upstream calcola provider + confidence insieme: elegge il *winner*
    sommando i pesi dei segnali primari, poi calcola la confidence sul
    set di segnali attribuiti al winner.
  - Da noi il provider è GIÀ determinato da classify.py. Quindi qui
    portiamo SOLO il calcolo della confidence (`_rule_confidence` per i
    provider, `_independent_confidence` per gli independent), costruendo
    il set di segnali presenti dall'entità come fa `by_provider[winner]`
    upstream (TENANT attribuito solo a MS365).

Tabelle `_PROVIDER_RULES` / `_INDEPENDENT_RULES`, `_BOOST_PER_SIGNAL` e le
due funzioni di scoring sono copiate verbatim dall'upstream (solo
SignalKind→str per non dipendere da pydantic).
"""

from __future__ import annotations

from typing import NamedTuple

# Segnali (stringhe al posto dell'enum SignalKind upstream)
MX = "mx"
SPF = "spf"
DKIM = "dkim"
AUTODISCOVER = "autodiscover"
TENANT = "tenant"

# Provider che corrispondono a Microsoft 365 nel nostro schema. TENANT
# (getuserrealm.srf) è attribuibile solo a MS365 — come fa probe_tenant
# upstream, che emette Evidence(provider=MS365).
MS365_PROVIDERS = {"microsoft", "istruzione-miur-tenant"}

# Provider "veri" → usano _rule_confidence. Tutto il resto è independent
# o unknown.
INDEPENDENT_PROVIDERS = {"independent", "provincial-shared"}
NO_MX_PROVIDERS = {"unknown"}

# --- VERBATIM dall'upstream ---
_BOOST_PER_SIGNAL = 0.02


class _Rule(NamedTuple):
    name: str
    signals: frozenset[str]
    needs_gateway: bool
    base: float


# fmt: off
_PROVIDER_RULES: tuple[_Rule, ...] = (
    # rule name             signals                                  gw?    base
    # --- 3 signals (0.90–0.95) ---
    _Rule("mx_spf_ad",      frozenset({MX, SPF, AUTODISCOVER}),      False, 0.95),
    _Rule("mx_spf_tenant",  frozenset({MX, SPF, TENANT}),           False, 0.95),
    _Rule("ad_spf_tenant",  frozenset({AUTODISCOVER, SPF, TENANT}), False, 0.95),
    _Rule("dkim_ad_tenant", frozenset({DKIM, AUTODISCOVER, TENANT}),False, 0.90),
    _Rule("dkim_spf_tenant",frozenset({DKIM, SPF, TENANT}),         False, 0.90),
    # --- 2 signals (0.75–0.90) ---
    _Rule("mx_spf",         frozenset({MX, SPF}),                   False, 0.90),
    _Rule("spf_tenant_gw",  frozenset({SPF, TENANT}),               True,  0.90),
    _Rule("dkim_tenant_gw", frozenset({DKIM, TENANT}),              True,  0.85),
    _Rule("mx_tenant",      frozenset({MX, TENANT}),                False, 0.85),
    _Rule("spf_tenant",     frozenset({SPF, TENANT}),               False, 0.80),
    _Rule("dkim_tenant",    frozenset({DKIM, TENANT}),              False, 0.75),
    _Rule("ad_tenant",      frozenset({AUTODISCOVER, TENANT}),      False, 0.75),
    # --- 1 signal + gateway ---
    _Rule("spf_gw",         frozenset({SPF}),                       True,  0.70),
    # --- 1 signal ---
    _Rule("mx_only",        frozenset({MX}),                        False, 0.80),
    _Rule("spf_only",       frozenset({SPF}),                       False, 0.50),
    _Rule("fallback",       frozenset(),                            False, 0.40),
)

_INDEPENDENT_RULES: tuple[tuple[str, float], ...] = (
    ("ind_mx_spf",     0.90),  # MX + SPF present
    ("ind_mx_only",    0.60),  # MX only
    ("ind_secondary",  0.20),  # secondary evidence only
    ("ind_none",       0.00),  # nothing
)
# fmt: on

ALL_RULE_NAMES: tuple[str, ...] = (
    tuple(r.name for r in _PROVIDER_RULES)
    + tuple(name for name, _ in _INDEPENDENT_RULES)
    + ("no_mx",)
)


def _rule_confidence(
    provider: str, signals: set[str], gateway: str | None
) -> tuple[float, str]:
    """Return (confidence, rule_name) for a winning provider.

    Port verbatim di classifier._rule_confidence: itera _PROVIDER_RULES
    (primo match vince) via subset check rule.signals <= present. TENANT
    contato solo quando il winner è MS365. I segnali non consumati dalla
    regola aggiungono _BOOST_PER_SIGNAL ciascuno; cap a 1.0.
    """
    present: set[str] = set()
    if MX in signals:
        present.add(MX)
    if SPF in signals:
        present.add(SPF)
    if TENANT in signals and provider in MS365_PROVIDERS:
        present.add(TENANT)
    if AUTODISCOVER in signals:
        present.add(AUTODISCOVER)
    if DKIM in signals:
        present.add(DKIM)
    has_gateway = gateway is not None

    for rule in _PROVIDER_RULES:
        if rule.signals <= present and (not rule.needs_gateway or has_gateway):
            boost = len(signals - rule.signals) * _BOOST_PER_SIGNAL
            return min(1.0, rule.base + boost), rule.name

    return 0.40, "fallback"  # pragma: no cover (fallback matcha sempre)


def _independent_confidence(
    has_mx: bool, has_spf: bool, signals: set[str]
) -> tuple[float, str]:
    """Return (confidence, rule_name) for an INDEPENDENT domain.

    Port di classifier._independent_confidence. ind_mx_spf 0.90 ·
    ind_mx_only 0.60 · ind_secondary 0.20 · ind_none 0.0. I segnali extra
    oltre MX/SPF aggiungono _BOOST_PER_SIGNAL ciascuno; cap a 1.0.
    """
    if has_mx and has_spf:
        name, base = _INDEPENDENT_RULES[0]
    elif has_mx:
        name, base = _INDEPENDENT_RULES[1]
    elif signals:
        name, base = _INDEPENDENT_RULES[2]
    else:
        return 0.0, _INDEPENDENT_RULES[3][0]

    extra_kinds = signals - {MX, SPF}
    boost = len(extra_kinds) * _BOOST_PER_SIGNAL
    return min(1.0, base + boost), name


def _present_signals(entry: dict, provider: str) -> set[str]:
    """Costruisce il set di segnali presenti come fa by_provider[winner]
    upstream: MX/SPF/DKIM/AUTODISCOVER se presenti nei campi DNS, TENANT
    solo se il provider è MS365 (probe_tenant attribuisce a MS365)."""
    sig: set[str] = set()
    if entry.get("mx"):
        sig.add(MX)
    if entry.get("spf"):
        sig.add(SPF)
    if entry.get("dkim"):
        sig.add(DKIM)
    if entry.get("autodiscover"):
        sig.add(AUTODISCOVER)
    if entry.get("tenant") and provider in MS365_PROVIDERS:
        sig.add(TENANT)
    return sig


def compute_confidence(entry: dict) -> tuple[float, str, list[str]]:
    """Calcola (confidence, rule_name, signals) per un'entità data.json.

    - provider == "unknown" (nessun MX) → (0.0, "no_mx", [])
    - provider independent/provincial-shared → _independent_confidence
    - ogni altro provider "vero" → _rule_confidence
    """
    provider = entry.get("provider") or "unknown"
    if provider in NO_MX_PROVIDERS:
        return 0.0, "no_mx", []

    signals = _present_signals(entry, provider)
    gateway = entry.get("gateway")

    if provider in INDEPENDENT_PROVIDERS:
        conf, rule = _independent_confidence(MX in signals, SPF in signals, signals)
    else:
        conf, rule = _rule_confidence(provider, signals, gateway)

    return round(conf, 4), rule, sorted(signals)


__all__ = [
    "compute_confidence",
    "ALL_RULE_NAMES",
    "_PROVIDER_RULES",
    "_INDEPENDENT_RULES",
]
