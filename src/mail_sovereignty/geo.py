"""Crosswalk geografico comune → provincia → regione — arricchimento strutturale.

IndicePA è sporco sul dato territoriale: il campo `region` del seed è incompleto
(7.685/22.987) e a volte contiene il *nome dell'ente* invece della regione. La
fonte pulita è **`ipa_codice_comune_istat`** (il comune-sede di ogni ente,
presente al 100%) risolto sul crosswalk ufficiale ISTAT (`data/istat_comuni.json`,
da scripts/fetch_istat_comuni.py): codice ISTAT → `codice_regione` + `sigla_auto`.
Vedi mxmap.it#2 (qualità della fonte).

Logica pura e testabile; il caricamento del file ISTAT e l'I/O su data.json
stanno in scripts/enrich_geo.py.
"""

from __future__ import annotations

# Codice regione ISTAT (01..20) → (nome, macroarea). Tabella ufficiale stabile.
REGIONI: dict[str, tuple[str, str]] = {
    "01": ("Piemonte", "Nord"),
    "02": ("Valle d'Aosta", "Nord"),
    "03": ("Lombardia", "Nord"),
    "04": ("Trentino-Alto Adige", "Nord"),
    "05": ("Veneto", "Nord"),
    "06": ("Friuli-Venezia Giulia", "Nord"),
    "07": ("Liguria", "Nord"),
    "08": ("Emilia-Romagna", "Nord"),
    "09": ("Toscana", "Centro"),
    "10": ("Umbria", "Centro"),
    "11": ("Marche", "Centro"),
    "12": ("Lazio", "Centro"),
    "13": ("Abruzzo", "Sud"),
    "14": ("Molise", "Sud"),
    "15": ("Campania", "Sud"),
    "16": ("Puglia", "Sud"),
    "17": ("Basilicata", "Sud"),
    "18": ("Calabria", "Sud"),
    "19": ("Sicilia", "Isole"),
    "20": ("Sardegna", "Isole"),
}
SCONOSCIUTA = "Sconosciuta"

# campi che l'arricchimento scrive su ogni ente
GEO_FIELDS = ("comune", "provincia", "codice_regione", "regione", "macroarea")


def build_istat_index(comuni: list[dict]) -> dict[str, dict]:
    """`codice_istat` (+ `codici_storici` come alias, per i codici legacy che
    IndicePA usa ancora, es. Sardegna) → entry comune ISTAT."""
    idx: dict[str, dict] = {}
    for c in comuni:
        code = c.get("codice_istat")
        if code:
            idx[code] = c
        for s in c.get("codici_storici", []) or []:
            idx.setdefault(s, c)
    return idx


def resolve_geo(istat_code: str | None, index: dict[str, dict]) -> dict:
    """Risolve un codice comune ISTAT in {comune, provincia, codice_regione,
    regione, macroarea}. Se non risolve, regione/macroarea = 'Sconosciuta' (onesto,
    mai un'attribuzione inventata)."""
    c = index.get(istat_code) if istat_code else None
    if not c:
        return {
            "comune": None,
            "provincia": None,
            "codice_regione": None,
            "regione": SCONOSCIUTA,
            "macroarea": SCONOSCIUTA,
        }
    cr = c.get("codice_regione")
    nome, macro = REGIONI.get(cr or "", (SCONOSCIUTA, SCONOSCIUTA))
    return {
        "comune": c.get("denominazione_it"),
        "provincia": c.get("sigla_auto"),
        "codice_regione": cr,
        "regione": nome,
        "macroarea": macro,
    }


__all__ = [
    "REGIONI",
    "SCONOSCIUTA",
    "GEO_FIELDS",
    "build_istat_index",
    "resolve_geo",
]
