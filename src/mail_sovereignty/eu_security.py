"""EU Security Map — sovranità email relativa al paese dell'ente (mxmap.it#33).

A differenza del dataset italiano (dove "sovrano" = italiano), qui la sovranità
è **relativa al paese dell'ente**: un dominio della polizia tedesca su un
provider tedesco è `national`, su Microsoft è `us` (esposto al CLOUD Act), su
OVH è `eu_other`. Il rischio headline del rendiconto è `us_exposure_pct`.

Il modulo è puro (stdlib + costanti del progetto), unit-testato a valori attesi
a mano, con `assert_integrity()` chiamato dal build (regola KPI "numbers
tested"). Non tocca la pipeline italiana.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

# --- Provider → paese di giurisdizione legale (ISO alpha-2 uppercase) ---------
# Chiavi allineate a constants.PROVIDER_KEYWORDS. I provider italiani restano
# qui per completezza (un ente italiano su Aruba = national in IT).
PROVIDER_COUNTRY: dict[str, str] = {
    # USA → CLOUD Act
    "microsoft": "US",
    "google": "US",
    "aws": "US",
    "istruzione-miur-tenant": "US",  # tenant MS365
    # Estero non-USA non-UE
    "zoho": "IN",
    "yandex": "RU",
    # Provider europei
    "ovh": "FR",
    "gandi": "FR",
    "scaleway": "FR",
    "hetzner": "DE",
    "ionos": "DE",
    "infomaniak": "CH",
    "zone": "EE",
    "telia": "SE",
    "tet": "LV",
    "elkdata": "EE",
    # Provider italiani
    "aruba": "IT",
    "register-it": "IT",
    "seeweb": "IT",
    "infocert": "IT",
    "namirial": "IT",
    "regional-public": "IT",
    "pa-contractor-private": "IT",
}

# Paesi UE-27 (per il bucket eu_other). CH/NO/IS/LI/UK e i candidati NON sono
# UE: un ente su un provider di quei paesi conta come eu_other solo se il
# provider ha sede UE; altrimenti other_foreign. Qui elenchiamo gli stati UE.
EU27: frozenset[str] = frozenset(
    {
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IE",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
    }
)

# Paesi "europei" ai fini del display (UE + EFTA + UK): un provider di questi,
# diverso dal paese dell'ente, è comunque europeo → eu_other. Gli enti delle
# istituzioni UE (cc="EU") trattano qualunque provider europeo come eu_other.
EUROPEAN_PROVIDER_COUNTRIES: frozenset[str] = EU27 | frozenset(
    {"CH", "NO", "IS", "LI", "GB"}
)

BUCKETS = ("national", "us", "eu_other", "other_foreign", "unknown")

# Provider considerati "autonomi/self-hosted": la giurisdizione viene dagli
# mx_countries (dove sta l'MTA), non da una sede legale di provider.
# local-isp: riconosciuto via ASN di ISP nazionali (di qualunque paese) →
# giurisdizione dal paese dell'MTA, non da una sede fissa.
SELF_HOSTED_PROVIDERS: frozenset[str] = frozenset(
    {"independent", "local-isp", "unknown"}
)


def provider_country(provider: str, mx_countries: list[str] | None) -> str | None:
    """Paese di giurisdizione del provider (ISO alpha-2), o None se ignoto.

    Per i provider noti è la sede legale (PROVIDER_COUNTRY). Per
    independent/self-hosted si usa il paese dell'MTA (mx_countries) se univoco.
    """
    if provider in PROVIDER_COUNTRY:
        return PROVIDER_COUNTRY[provider]
    if provider in SELF_HOSTED_PROVIDERS:
        ccs = {c.upper() for c in (mx_countries or []) if c}
        if len(ccs) == 1:
            return next(iter(ccs))
    return None


def bucket_for(entity_cc: str, provider: str, mx_countries: list[str] | None) -> str:
    """Bucket di sovranità relativo al paese dell'ente.

    entity_cc: ISO alpha-2 del paese dell'ente ("EU" per le istituzioni UE).
    """
    if provider == "unknown":
        return "unknown"
    pc = provider_country(provider, mx_countries)
    if pc is None:
        # independent con MTA multi-paese o non risolto → ignoto
        return "unknown"
    cc = entity_cc.upper()
    if cc == "EU":
        # Istituzioni UE: "national" = provider di uno stato UE (sovranità
        # europea); USA resta us; altro estero other_foreign.
        if pc in EU27:
            return "national"
        if pc == "US":
            return "us"
        if pc in EUROPEAN_PROVIDER_COUNTRIES:
            return "national"
        return "other_foreign"
    if pc == cc:
        return "national"
    if pc == "US":
        return "us"
    if pc in EUROPEAN_PROVIDER_COUNTRIES:
        return "eu_other"
    return "other_foreign"


def classify_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggiunge `bucket` a ogni ente scansionato (non muta l'input)."""
    out = []
    for e in entities:
        row = dict(e)
        row["bucket"] = bucket_for(
            e.get("country", ""),
            e.get("provider", "unknown"),
            e.get("mx_countries"),
        )
        out.append(row)
    return out


def _pct(n: int, d: int) -> float:
    return round(100 * n / d, 1) if d else 0.0


def compute_kpi(
    entities: list[dict[str, Any]], min_classified: int = 5
) -> dict[str, Any]:
    """KPI per il rendiconto. `entities` devono avere già `bucket`.

    Ranking (us_exposure / national) solo per paesi con >= min_classified enti
    classificati (bucket != unknown). RU/BY e EU restano nei dati per-paese ma
    fuori dal ranking headline (lo decide il page builder via `ranking_eligible`).
    """
    rows = entities
    n = len(rows)
    overall = Counter(r["bucket"] for r in rows)
    by_type: dict[str, Counter] = {}
    by_country: dict[str, dict[str, Any]] = {}

    for r in rows:
        by_type.setdefault(r.get("type", "other_natsec"), Counter())[r["bucket"]] += 1
        cc = r.get("country", "??")
        c = by_country.setdefault(
            cc,
            {"country": cc, "n": 0, "buckets": Counter(), "classified": 0},
        )
        c["n"] += 1
        c["buckets"][r["bucket"]] += 1
        if r["bucket"] != "unknown":
            c["classified"] += 1

    countries = []
    for cc, c in by_country.items():
        classified = c["classified"]
        us = c["buckets"]["us"]
        nat = c["buckets"]["national"]
        countries.append(
            {
                "country": cc,
                "n": c["n"],
                "classified": classified,
                "national": nat,
                "us": us,
                "eu_other": c["buckets"]["eu_other"],
                "other_foreign": c["buckets"]["other_foreign"],
                "unknown": c["buckets"]["unknown"],
                "us_exposure_pct": _pct(us, classified),
                "national_pct": _pct(nat, classified),
                "ranking_eligible": classified >= min_classified,
            }
        )
    countries.sort(key=lambda x: (-x["us_exposure_pct"], -x["n"], x["country"]))

    return {
        "n_entities": n,
        "n_countries": len(by_country),
        "overall": {b: overall[b] for b in BUCKETS},
        "overall_pct": {b: _pct(overall[b], n) for b in BUCKETS},
        "by_type": {
            t: {b: cnt[b] for b in BUCKETS} for t, cnt in sorted(by_type.items())
        },
        "countries": countries,
        "min_classified_for_ranking": min_classified,
    }


def assert_integrity(kpi: dict[str, Any], entities: list[dict[str, Any]]) -> None:
    """Invarianti runtime (regola KPI). Exit non-zero se violate."""
    n = kpi["n_entities"]
    if n != len(entities):
        raise AssertionError(f"n_entities {n} != len(entities) {len(entities)}")
    if sum(kpi["overall"].values()) != n:
        raise AssertionError("overall buckets non sommano alla popolazione")
    for r in entities:
        if r["bucket"] not in BUCKETS:
            raise AssertionError(f"bucket invalido: {r['bucket']}")
    if n:
        tot_pct = sum(kpi["overall_pct"].values())
        if not (99.0 <= tot_pct <= 101.0):
            raise AssertionError(f"overall_pct somma {tot_pct}, atteso ~100")
    sum_country_n = sum(c["n"] for c in kpi["countries"])
    if sum_country_n != n:
        raise AssertionError(f"somma per-paese {sum_country_n} != {n}")
    for c in kpi["countries"]:
        if (
            c["national"] + c["us"] + c["eu_other"] + c["other_foreign"] + c["unknown"]
            != c["n"]
        ):
            raise AssertionError(f"bucket per-paese {c['country']} non sommano")
        if not (0.0 <= c["us_exposure_pct"] <= 100.0):
            raise AssertionError(f"us_exposure_pct fuori range per {c['country']}")
    # ranking monotono decrescente in us_exposure_pct
    elig = [c["us_exposure_pct"] for c in kpi["countries"] if c["ranking_eligible"]]
    if elig != sorted(elig, reverse=True):
        raise AssertionError("countries non ordinati per us_exposure_pct")


__all__ = [
    "PROVIDER_COUNTRY",
    "EU27",
    "EUROPEAN_PROVIDER_COUNTRIES",
    "BUCKETS",
    "provider_country",
    "bucket_for",
    "classify_entities",
    "compute_kpi",
    "assert_integrity",
]
