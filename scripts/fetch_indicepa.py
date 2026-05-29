#!/usr/bin/env python3
"""Fetch Italian public-administration seed data from IndicePA.

Default mode (no flag): fetches only territorial entities (Regioni /
Province / Città Metropolitane / Comuni) from the IndicePA `enti` dataset
via CKAN's datastore_search JSON API.

`--include-others` mode: ALSO fetches every other IndicePA category
(schools L33, ASL L7, hospitals L8, universities L17, ministries C1,
authorities C5, professional orders C14, procurement SA, etc.) and emits
them in the same seed file with `IT-{categoria}-{codice_ipa}` ID format.
The same DNS/classify pipeline downstream will classify each of these
entities by their MX / SPF / DKIM / etc. so we can analyse digital
sovereignty across the entire Italian PA, not just territorial bodies.

Territorial filtering (per docs/countries/ITALY.md):
- Drop Ente_in_liquidazione = "S"
- Drop rows without a usable Sito_istituzionale (any TLD accepted)
- Drop consorzi/associazioni/unioni/comunità montane via name regex
- Encode level in the `id` prefix (IT-REG / IT-PRO / IT-CMM / IT-COM)

Non-territorial filtering (when --include-others):
- Drop Ente_in_liquidazione = "S"
- Drop rows without a usable Sito_istituzionale
- NO name regex filter (all enti accepted within the category)
- Keep ipa_codice_categoria for downstream slicing

If `data/it_istat_osm_crosswalk.json` exists (built by
`scripts/build_istat_osm_crosswalk.py`), `osm_relation_id` is populated by
joining first on Codice_IPA (P6832 in Wikidata) and falling back to the
ISTAT code. Otherwise the field is left null.

Usage:
    uv run python3 scripts/build_istat_osm_crosswalk.py   # one-time
    uv run python3 scripts/fetch_indicepa.py              # territorial only
    uv run python3 scripts/fetch_indicepa.py --include-others   # +Tier 2/3
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CKAN_BASE = "https://indicepa.gov.it/ipa-dati/api/3/action"
RESOURCE_ID = "d09adf99-dc10-4349-8c53-27b1e5aa97b6"  # enti dataset

CROSSWALK_PATH = ROOT / "data" / "it_istat_osm_crosswalk.json"

# Codice_Categoria → (level prefix, human-readable label)
LEVEL_MAP = {
    "L4": ("IT-REG", "Regione / Provincia Autonoma"),
    "L5": ("IT-PRO", "Provincia"),
    "L45": ("IT-CMM", "Città Metropolitana"),
    "L6": ("IT-COM", "Comune"),
}

# Names matching this regex are consorzi / associazioni / unioni — no polygon,
# excluded from v1 scope. Case-insensitive. Used as the L6 (comuni) filter.
NON_TERRITORIAL_NAME_RE = re.compile(
    r"\b(consorzio|associazione|unione\s+(?:dei|di|del)\s+comuni|"
    r"unione\s+montana|unione\s+territoriale|"
    r"comunit[aà]\s+montana|comunit[aà]\s+collinare|comunit[aà]\s+isolana)\b",
    re.IGNORECASE,
)

# Positive name patterns per level — IPA labels its categories L4/L5/L45 loosely
# (a "Regione" category includes interregional consortia, agencies, etc.). We
# accept ONLY entries whose Denominazione_ente clearly identifies the entity
# type. Case-insensitive. Pre-compiled.
LEVEL_NAME_RE = {
    "L4":  re.compile(r"^\s*(regione\b|provincia\s+autonoma\s+(di|del)\b)", re.IGNORECASE),
    "L5":  re.compile(r"^\s*(provincia\b|libero\s+consorzio\s+comunale\b)", re.IGNORECASE),
    "L45": re.compile(r"^\s*citt[aà]'?\s+metropolitana\b", re.IGNORECASE),
    # L6: NIENTE name regex. Vedi is_real_comune() — usiamo ISTAT come
    # autorità (codice_comune_ISTAT + denominazione) invece del nome
    # IndicePA che è instabile (ROMA CAPITALE, comuni ladini, varianti
    # locali, ecc.).
    "L6":  None,
}

# Lookup ISTAT lazy-loaded: codice_istat -> ente ISTAT con denominazione,
# catastale, codici storici. Inizializzato a None; popolato dal primo
# accesso a is_real_comune() o esplicitamente da main().
_ISTAT_INDEX: dict[str, dict] | None = None
_ISTAT_ISTAT_CODES: set[str] | None = None


def _load_istat_index() -> tuple[dict[str, dict], set[str]]:
    """Carica data/istat_comuni.json e ritorna (codice_istat -> entry,
    set di tutti i codici validi inclusi storici)."""
    global _ISTAT_INDEX, _ISTAT_ISTAT_CODES
    if _ISTAT_INDEX is not None:
        return _ISTAT_INDEX, _ISTAT_ISTAT_CODES  # type: ignore
    p = ROOT / "data" / "istat_comuni.json"
    if not p.exists():
        print(f"WARN: {p} missing. Esegui prima "
              f"`uv run python3 scripts/fetch_istat_comuni.py`.")
        _ISTAT_INDEX = {}
        _ISTAT_ISTAT_CODES = set()
        return _ISTAT_INDEX, _ISTAT_ISTAT_CODES
    payload = json.loads(p.read_text(encoding="utf-8"))
    idx: dict[str, dict] = {}
    codes: set[str] = set()
    for c in payload.get("comuni") or []:
        cur = c.get("codice_istat")
        if cur:
            idx[cur] = c
            codes.add(cur)
        for storico in c.get("codici_storici") or []:
            codes.add(storico)
            # Storici puntano allo stesso entry corrente
            if storico not in idx:
                idx[storico] = c
    _ISTAT_INDEX = idx
    _ISTAT_ISTAT_CODES = codes
    print(f"Loaded ISTAT lookup: {len(idx)} comuni indexed "
          f"({len(codes)} codici totali correnti+storici)")
    return idx, codes


def _normalize_for_match(s: str) -> str:
    """Lowercase + rimozione diacritici + rimozione punteggiatura
    (mantiene spazi e trattini per match parziale)."""
    import unicodedata
    n = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    # Rimuovi punteggiatura ma mantieni spazi e trattini
    return re.sub(r"[^a-z0-9 \-]", " ", n).strip()


def is_real_comune(name: str, codice_ipa: str, codice_comune_istat: str) -> bool:
    """Decide autoritativamente se una riga IndicePA L6 è un vero comune,
    USANDO ISTAT come fonte ufficiale (non il nome IndicePA che è instabile).

    Una L6 è un vero comune SSE almeno UNO di:
      T1. codice_ipa segue il pattern catastale (c_<X> o solo <X>, X = catastale).
          Cattura: c_h501 (Roma), c_a007 (Abbasanta), B432 (Calto), c_0319 (Dolcedo),
          A690_bpe (variante mista). Discriminante: codice IPA con questa forma
          esiste storicamente solo per veri comuni.

      T2. codice_ipa è un codice opaco UUID-like (8-char) MA il nome ente
          INIZIA con la denominazione ISTAT del comune (dopo opzionale
          "Comune di" prefix). Cattura: 3BEP4ZAX (Moransengo-Tonengo),
          40B59AWR (Sovizzo). Discrimina UNCEM (BRM2B3KM, nome "UNCEM..."
          non inizia con "Roma") da Sovizzo (nome "COMUNE DI SOVIZZO"
          inizia con "Sovizzo").

      T3. codice_ipa ha forma legacy (c_<N digits>, c_<weird>) MA:
          (a) codice_comune_ISTAT è in ISTAT (corrente o storico)
          (b) il nome ente INIZIA con la denominazione ISTAT dopo opzionale
              "Comune di" prefix.

    Rifiuta:
      - UNCEM Lazio (BRM2B3KM, istat=058091=Roma): T2 fallisce (nome
        "UNCEM..." non inizia con "Roma").
      - Patrimonio Mobilita Rimini (ampr, istat=099014): T2 fallisce
        (nome "Patrimonio..." non inizia con "Rimini").
      - ATS Madonie (atsms, istat=082036): T2 fallisce.
    """
    if not name:
        return False

    name_norm = _normalize_for_match(name)
    ipa = (codice_ipa or "").strip().lower()
    istat = (codice_comune_istat or "").strip()

    # T1: codice IPA segue pattern catastale.
    # Forme accettate:
    #   c_h501          → c_<lettera>+<3 alfanumerici>
    #   B432            → <lettera>+<3 digit> nudo
    #   c_a690_bpe      → c_<catastale>_<suffisso>
    #   c_0319          → c_<4 digit> (legacy)
    #   c_067039        → c_<6 digit> (legacy lungo)
    #   c_11j8          → c_<misti>
    CATASTAL_PATTERNS = [
        re.compile(r"^c_[a-z][a-z0-9]{3}(_[a-z0-9]+)?$", re.IGNORECASE),
        re.compile(r"^[a-z]\d{3}$", re.IGNORECASE),
        re.compile(r"^c_\d{4,6}$", re.IGNORECASE),
        re.compile(r"^c_[a-z0-9]{4}$", re.IGNORECASE),
    ]
    for p in CATASTAL_PATTERNS:
        if p.match(ipa):
            return True

    # T2/T3: codice IPA opaco o legacy → richiediamo cross-validation con
    # nome ↔ ISTAT denominazione.
    idx, _ = _load_istat_index()
    istat_entry = idx.get(istat)
    if not istat_entry:
        return False  # codice ISTAT non in ISTAT → reject conservativo

    den_it = (istat_entry.get("denominazione_it") or "").strip()
    den_full = (istat_entry.get("denominazione_full") or "").strip() or den_it
    if not den_it:
        return False

    # Rimuovi prefisso "Comune di/del/della/..." dal nome
    name_stripped = re.sub(
        r"^\s*comune\s+(di|del|della|degli|delle|dei|dell['’])?\s*",
        "", name_norm
    ).strip()

    den_norm = _normalize_for_match(den_it)
    den_full_norm = _normalize_for_match(den_full)

    # Il nome deve INIZIARE con la denominazione ISTAT (o sua variante full
    # bilingue). Cattura "ROMA CAPITALE" (inizia con "roma"), rifiuta
    # "Patrimonio Mobilita Provincia di Rimini" (inizia con "patrimonio",
    # NON con "rimini").
    if name_stripped.startswith(den_norm) or name_stripped.startswith(den_full_norm):
        return True
    # Match equivalence stretta
    if name_stripped == den_norm or name_norm == den_norm:
        return True
    return False

# Italian regioni: IPA Codice_IPA → ISTAT 2-digit region code. Hand-curated;
# 22 entries (20 regioni + 2 province autonome). Used to look up the OSM
# relation via crosswalk.by_istat_region. Province autonome (Bolzano, Trento)
# are mapped via PROV_AUTONOME_IPA_TO_PROVINCE_ISTAT instead because their
# OSM relation lives at admin_level=6 (province), not admin_level=4 (region).
REGIONI_IPA_TO_ISTAT2 = {
    "r_piemon": "01",
    "r_vda":    "02",
    "r_lombar": "03",
    "r_trenti": "04",
    "r_veneto": "05",
    "r_friuve": "06",
    "r_liguri": "07",
    "r_emiro":  "08",
    "r_toscan": "09",
    "r_umbria": "10",
    "r_marche": "11",
    "r_lazio":  "12",
    "r_abruzz": "13",
    "r_molise": "14",
    "r_campan": "15",
    "r_puglia": "16",
    "r_basili": "17",
    "regcal":   "18",  # Calabria — note no r_ prefix in IPA
    "r_sicili": "19",
    "r_sardeg": "20",
}

# Province autonome: IPA → 3-digit province ISTAT code (look up in
# crosswalk.by_istat_province since their OSM lives at admin_level=6).
PROV_AUTONOME_IPA_TO_PROVINCE_ISTAT = {
    "p_bz": "021",  # Provincia Autonoma di Bolzano
    "p_TN": "022",  # Provincia Autonoma di Trento
}

# Permissive hostname validation — used to reject obviously-broken Sito_istituzionale
# entries (typos, "n.d.", "in fase di attivazione", etc.). We accept any TLD,
# any length.
HOSTNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$")

PAGE_SIZE = 5000  # CKAN datastore_search limit
USER_AGENT = "mxmap.it-indicepa-fetcher/0.1 (+https://github.com/fpietrosanti/mxmap.it)"


# Italian ISTAT 3-digit province code -> region name (Italian).
# Source: ISTAT classification of administrative units. Region names match
# OSM admin_level=4 `name` tag so the frontend's matchGroupFeature() can join.
# Region-level aggregation in the renderer uses comune.region as group key.
ISTAT_PROVINCE_TO_REGION: dict[str, str] = {
    # Piemonte
    "001": "Piemonte", "002": "Piemonte", "003": "Piemonte", "004": "Piemonte",
    "005": "Piemonte", "006": "Piemonte", "096": "Piemonte", "103": "Piemonte",
    # Valle d'Aosta
    "007": "Valle d'Aosta / Vallée d'Aoste",
    # Lombardia
    "012": "Lombardia", "013": "Lombardia", "014": "Lombardia", "015": "Lombardia",
    "016": "Lombardia", "017": "Lombardia", "018": "Lombardia", "019": "Lombardia",
    "020": "Lombardia", "097": "Lombardia", "098": "Lombardia", "108": "Lombardia",
    # Trentino-Alto Adige (autonomous provinces under one region)
    "021": "Trentino-Alto Adige/Südtirol", "022": "Trentino-Alto Adige/Südtirol",
    # Veneto
    "023": "Veneto", "024": "Veneto", "025": "Veneto", "026": "Veneto",
    "027": "Veneto", "028": "Veneto", "029": "Veneto",
    # Friuli-Venezia Giulia
    "030": "Friuli-Venezia Giulia", "031": "Friuli-Venezia Giulia",
    "032": "Friuli-Venezia Giulia", "093": "Friuli-Venezia Giulia",
    # Liguria
    "008": "Liguria", "009": "Liguria", "010": "Liguria", "011": "Liguria",
    # Emilia-Romagna
    "033": "Emilia-Romagna", "034": "Emilia-Romagna", "035": "Emilia-Romagna",
    "036": "Emilia-Romagna", "037": "Emilia-Romagna", "038": "Emilia-Romagna",
    "039": "Emilia-Romagna", "040": "Emilia-Romagna", "099": "Emilia-Romagna",
    # Toscana
    "045": "Toscana", "046": "Toscana", "047": "Toscana", "048": "Toscana",
    "049": "Toscana", "050": "Toscana", "051": "Toscana", "052": "Toscana",
    "053": "Toscana", "100": "Toscana",
    # Umbria
    "054": "Umbria", "055": "Umbria",
    # Marche
    "041": "Marche", "042": "Marche", "043": "Marche", "044": "Marche",
    "109": "Marche",
    # Lazio
    "056": "Lazio", "057": "Lazio", "058": "Lazio", "059": "Lazio", "060": "Lazio",
    # Abruzzo
    "066": "Abruzzo", "067": "Abruzzo", "068": "Abruzzo", "069": "Abruzzo",
    # Molise
    "070": "Molise", "094": "Molise",
    # Campania
    "061": "Campania", "062": "Campania", "063": "Campania", "064": "Campania",
    "065": "Campania",
    # Puglia
    "071": "Puglia", "072": "Puglia", "073": "Puglia", "074": "Puglia",
    "075": "Puglia", "110": "Puglia",
    # Basilicata
    "076": "Basilicata", "077": "Basilicata",
    # Calabria
    "078": "Calabria", "079": "Calabria", "080": "Calabria", "101": "Calabria",
    "102": "Calabria",
    # Sicilia
    "081": "Sicilia", "082": "Sicilia", "083": "Sicilia", "084": "Sicilia",
    "085": "Sicilia", "086": "Sicilia", "087": "Sicilia", "088": "Sicilia",
    "089": "Sicilia",
    # Sardegna (current Sardinian provinces — historical 104-107, 111 split)
    "090": "Sardigna/Sardegna", "091": "Sardigna/Sardegna",
    "092": "Sardigna/Sardegna", "095": "Sardigna/Sardegna",
    "104": "Sardigna/Sardegna", "105": "Sardigna/Sardegna",
    "106": "Sardigna/Sardegna", "107": "Sardigna/Sardegna",
    "111": "Sardigna/Sardegna",
}


def istat_to_region(codice_comune_istat: str | None) -> str | None:
    """Comune ISTAT 6-digit -> region name. None if mapping unknown."""
    if not codice_comune_istat:
        return None
    s = str(codice_comune_istat).strip().zfill(6)
    if len(s) < 3:
        return None
    return ISTAT_PROVINCE_TO_REGION.get(s[:3])


# Manual ISTAT3 -> topo province-feature `name` overrides for cases where
# the Wikidata SPARQL crosswalk is incomplete (Sardegna 2016 reform legacy
# codes, bilingual Friuli names that Wikidata doesn't tag). Without these,
# comuni with these ISTAT codes have district=None and the frontend can't
# join them to a province polygon. Each value MUST match the exact `name`
# property in topo/it_province.topo.json verbatim.
ISTAT3_TO_TOPO_NAME_MANUAL: dict[str, str] = {
    # Valle d'Aosta — single-province region. OSM has it at admin_level=4
    # only, but scripts/fetch_extra_it_provinces.py copies the relation
    # 35394 polygon into it_province.topo.json with this name so the
    # province choropleth has full coverage.
    "007": "Valle d'Aosta / Vallée d'Aoste",
    # Friuli — bilingual Italian/Friulian/Slovene names
    "030": "Udine / Udin / Videm",
    "031": "Gorizia / Gurize / Gorica",
    # Sardegna current provinces (2016 reform reorg)
    "091": "Nuoro",
    "092": "Sud Sardegna",  # 2016 merger — relation 8829893 added by extra-provinces
    "095": "Aristanis/Oristano",
    "111": "Casteddu/Cagliari",
    # Sardegna historical / pre-2016 provinces — IndicePA still uses these
    # ISTAT codes for some comuni; topo has the historical polygons.
    "104": "Gallura Nord-Est Sardegna",
    "105": "Ogliastra",
    "106": "Medio Campidano",
    "107": "Sulcis Iglesiente",
}

# Lazily-built ISTAT 3-digit province code -> OSM province name (matching
# the `name` tag on topo/it_province.topo.json features). Used to populate
# m.district so the frontend's district-level (province) aggregation can
# join comuni to province polygons by name. Built from:
#   1. data/it_istat_osm_crosswalk.json's by_istat_province (ISTAT3 -> osm)
#   2. topo/it_province.topo.json features (osm relation/N -> name)
#   3. ISTAT3_TO_TOPO_NAME_MANUAL overrides (above) applied last to fill gaps.
_ISTAT3_TO_PROVINCE_NAME: dict[str, str] | None = None


def _load_istat3_to_province_name() -> dict[str, str]:
    global _ISTAT3_TO_PROVINCE_NAME
    if _ISTAT3_TO_PROVINCE_NAME is not None:
        return _ISTAT3_TO_PROVINCE_NAME
    out: dict[str, str] = {}
    crosswalk_path = ROOT / "data" / "it_istat_osm_crosswalk.json"
    topo_path = ROOT / "topo" / "it_province.topo.json"
    if not crosswalk_path.exists() or not topo_path.exists():
        _ISTAT3_TO_PROVINCE_NAME = out
        return out
    try:
        crosswalk = json.loads(crosswalk_path.read_text(encoding="utf-8"))
        by_istat_province = crosswalk.get("by_istat_province", {})  # ISTAT3 -> osm
        topo = json.loads(topo_path.read_text(encoding="utf-8"))
        # Build osm_id -> name from topo features
        osm_to_name: dict[int, str] = {}
        for obj in topo.get("objects", {}).values():
            for feat in obj.get("geometries", []):
                fid = feat.get("id", "")
                if isinstance(fid, str) and fid.startswith("relation/"):
                    try:
                        osm_id = int(fid.split("/", 1)[1])
                    except ValueError:
                        continue
                    name = (feat.get("properties") or {}).get("name") or ""
                    if name:
                        osm_to_name[osm_id] = name
        # Compose: ISTAT3 -> name (via osm)
        for istat3, osm_id in by_istat_province.items():
            try:
                osm_id_int = int(osm_id)
            except (TypeError, ValueError):
                continue
            name = osm_to_name.get(osm_id_int)
            if name:
                out[str(istat3).zfill(3)] = name
    except Exception as e:
        print(f"  _load_istat3_to_province_name: skipping ({e!r})")
    # Apply manual overrides (Sardegna legacy codes + Friuli bilingual names
    # not covered by Wikidata crosswalk). Only fills gaps; does NOT overwrite
    # crosswalk-derived entries since those have already been verified to
    # match the topo feature name.
    for k, v in ISTAT3_TO_TOPO_NAME_MANUAL.items():
        out.setdefault(k, v)
    _ISTAT3_TO_PROVINCE_NAME = out
    return out


def istat_to_province_name(codice_comune_istat: str | None) -> str | None:
    """Comune ISTAT 6-digit -> OSM province name (e.g., 'Salerno', 'Roma')."""
    if not codice_comune_istat:
        return None
    s = str(codice_comune_istat).strip().zfill(6)
    if len(s) < 3:
        return None
    return _load_istat3_to_province_name().get(s[:3])


# Manual domain overrides — applied at seed-build time when IndicePA's
# Sito_istituzionale is wrong (typo, defunct .gov.it migration, missing
# subdomain, etc.) and the standard recovery flow (domain_fallbacks,
# Wikidata P856, homepage scrape, search-engine fallback) doesn't fix it.
#
# Keyed by Codice_IPA (lowercase). Value is the corrected bare hostname
# (no scheme, no path, no leading "www."). The pipeline runs full mxmap
# classify() against the corrected domain — same MX checking path as the
# original. This is the canonical place to record persistent IndicePA
# data-quality fixes; keep one comment per override explaining why.
IT_PEC_ENRICHMENT_PATH = ROOT / "data" / "enrichment_pec_only.json"
IT_MANUAL_LLM_ENRICHMENT_PATH = ROOT / "data" / "manual_llm_enrichment.json"
IT_AOO_UO_EXTENSION_PATH = ROOT / "data" / "indicepa_extended_emails.json"


def load_aoo_uo_extension() -> dict[str, list[str]]:
    """Load the AOO+UO-derived non-PEC domain harvest produced by
    scripts/enrich_from_aoo_uo.py (Tier 6 in the recovery chain).

    Returns {codice_ipa_lowercase: [domain, ...]}. Each domain has
    already been filtered through is_legit_email_domain to ensure
    structural relation to the parent ente — no cross-tenant leaks.
    """
    if not IT_AOO_UO_EXTENSION_PATH.exists():
        return {}
    try:
        d = json.loads(IT_AOO_UO_EXTENSION_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"WARNING: cannot parse {IT_AOO_UO_EXTENSION_PATH}: {e!r}")
        return {}
    out: dict[str, list[str]] = {}
    for ipa, info in d.get("by_ipa", {}).items():
        doms = info.get("non_pec_domains") or []
        out[ipa.strip().lower()] = doms
    return out


def load_manual_llm_enrichment() -> dict[str, str]:
    """Load data/manual_llm_enrichment.json (Tier-3 manual LLM enrichment).

    This file is hand-produced by feeding scripts/generate_llm_enrichment_prompt.py
    output into a Claude Code session, then saving the JSON response. The file is
    committed to the repo and treated as part of the software's enriched dataset:
    generation is non-reproducible (LLM-mediated, possibly with human curation),
    but consumption is fully deterministic (loaded verbatim on every fetch).

    Schema: {codice_ipa_lowercase: {"domain": "...", "confidence": "high|medium|low",
                                    "rationale": "..."}}
    Returns {codice_ipa: domain} only for entries with a syntactically valid hostname.
    """
    if not IT_MANUAL_LLM_ENRICHMENT_PATH.exists():
        return {}
    try:
        d = json.loads(IT_MANUAL_LLM_ENRICHMENT_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"WARNING: cannot parse {IT_MANUAL_LLM_ENRICHMENT_PATH}: {e!r}")
        return {}
    out: dict[str, str] = {}
    for k, entry in d.items():
        if not isinstance(entry, dict):
            continue
        host = (entry.get("domain") or "").strip().lower()
        if host.startswith("www."):
            host = host[4:]
        if host and HOSTNAME_RE.match(host):
            out[k.strip().lower()] = host
    return out


def load_pec_enrichment() -> dict[str, str]:
    """Load data/enrichment_pec_only.json (produced by scripts/enrich_pec_only.py)
    as a {codice_ipa_lower: domain} map. Skips entries where the discovered
    domain failed MX verification (verified_mx == False).

    Returns empty dict if the file doesn't exist (enrichment hasn't been run).
    """
    if not IT_PEC_ENRICHMENT_PATH.exists():
        return {}
    try:
        d = json.loads(IT_PEC_ENRICHMENT_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"WARNING: cannot parse {IT_PEC_ENRICHMENT_PATH}: {e!r}")
        return {}
    out: dict[str, str] = {}
    for k, entry in d.items():
        if not isinstance(entry, dict):
            continue
        if not entry.get("verified_mx"):
            continue  # skip enrichments that didn't have MX records
        host = (entry.get("domain") or "").strip().lower()
        if host and HOSTNAME_RE.match(host):
            out[k.strip().lower()] = host
    return out


IT_MANUAL_DOMAIN_OVERRIDES: dict[str, str] = {
    # San Marcello Piteglio (PT) — IndicePA lists comune-sanmarcellopiteglio.info
    # which has no MX; the working comune site is on .it.
    "cdsmpi":  "comunesanmarcellopiteglio.it",
    # Roccagorga (LT) — IndicePA's `comuneroccagorga.it` is DNS-defunct;
    # the comune uses the standard provincial-prefixed pattern.
    "c_h413":  "comune.roccagorga.lt.it",
    # Giungano (SA) — IndicePA's `comune.giungano.sa.it` has no MX; the
    # working email host is `comunegiungano.sa.it` (no dot before giungano).
    "c_e060":  "comunegiungano.sa.it",
    # Pisciotta (SA) — IndicePA's `pisciotta.comune.sa.it` is DNS-defunct;
    # the working comune site is on the standard pattern.
    "c_g707":  "comune.pisciotta.sa.it",
    # Sala Biellese (BI) — IndicePA lists `comune.salabiellese.bi.it` (no MX);
    # email is hosted on the Provincia Tecnologica Biellese consortium at
    # ptb.provincia.biella.it.
    "c_h681":  "ptb.provincia.biella.it",
    # ASL n.3 di Nuoro — IndicePA lists `asl3nuoro.it` (no MX); the working
    # domain is `aslnuoro.it` with MX on mx01/mx02.sardegnasalute.it (Sardegna
    # regional health IT — sovereign infrastructure).
    "7t093cg4": "aslnuoro.it",
    # Ordine Architetti Biella — IndicePA lists `bi.archiworld.it` (no MX);
    # working subdomain is `biella.archiworld.it` with MX on
    # mx1/mx2-cnappc.innovazionedigitale.it (CNAPPC national architects council
    # infrastructure on Italian provider innovazionedigitale.it).
    "oda_096": "biella.archiworld.it",
    # Ordine Dottori Agronomi/Forestali Ascoli Piceno — IndicePA lists
    # `agronomiforestali.ap.it` (no MX); the working email is on the national
    # CONAF domain `conaf.it` with MX on efa.conaf.it (self-hosted).
    "odad_044": "conaf.it",
    # Comune di Castelnuovo Cilento (SA) — IndicePA lists `castelnuovocilento.eu`
    # (no MX); the comune actually uses `castelnuovoutc@virgilio.it` so the
    # mail domain is virgilio.it (Italiaonline — Italian commercial provider).
    "c_c231": "virgilio.it",
    # Agenzia Sviluppo Sociale ed Economico Provincia Autonoma Bolzano —
    # IndicePA lists `asse.provincia.bz.it` (no MX); main provincia.bz.it
    # has MX on pphosted.com (ProofPoint gateway — backend resolved by
    # gateway look-through downstream).
    "alsse_vi": "provincia.bz.it",
    # Collegio Periti Agrari Nuoro — IndicePA lists `peritiagrarinuoro.it`
    # (no MX); office uses `peritiagrari@tiscali.it`, mail domain tiscali.it
    # (Italiaonline / Tiscali — Italian commercial provider).
    "cpan": "tiscali.it",
    # Scuole professionali Provincia Autonoma di Bolzano — IndicePA lists
    # subdomain-specific hostnames (no MX); the actual mail domain shared by
    # all the South Tyrol vocational schools is `schule.suedtirol.it`
    # (MX on pphosted.com / ProofPoint, same backend as provincia.bz.it).
    "spcgg":  "schule.suedtirol.it",  # Scuola Comm/Grafica Gutenberg
    "spledb": "schule.suedtirol.it",  # Scuola Econ. Domestica Asiago/Egna/Bolzano (haslach)
    # Scuola Professionale Artigianato/Industria Luigi Einaudi — Bolzano IT
    # vocational school. Italian-language counterpart to schule.suedtirol.it;
    # mail domain `scuola.alto-adige.it` (MX pphosted.com — same ProofPoint
    # backend as provincia.bz.it).
    "sppai": "scuola.alto-adige.it",
    # Universita' Agraria di Civitella di Licenza — IndicePA lists
    # `agrariacivitella.it` (no MX); office uses `uniagrariacivcesi@gmail.com`
    # so the mail provider is Google (personal gmail.com — note: NOT Workspace,
    # this is genuinely a free Google account used institutionally).
    "uacl": "gmail.com",
    # ASP Maria Cristina di Savoia (Foggia) — IndicePA lists
    # `aspmariacristinadisavoia.it` (no MX); office uses
    # `aspmcdisavoiafoggia@gmail.com`, so mail is on personal gmail.com.
    "apspmcs": "gmail.com",
    # ACI Ravenna — IndicePA lists `ravenna.aci.it` (no MX); il sito
    # ufficiale è http://www.acravenna.it/ (Sito_istituzionale dichiarato
    # dal Direttore). MX su alt{1,2,3}.aspmx.l.google.com (Google).
    "ac_ra": "acravenna.it",
    # ACI Trapani — IndicePA lists `trapani.aci.it` (no MX sul subdomain
    # provinciale; solo HTTP). La posta dell'ufficio è gestita
    # centralmente sul tenant Google di ACI nazionale (aci.it).
    "ac_tp": "aci.it",
    # ACI Taranto — analogo a Trapani: `taranto.aci.it` solo HTTP, posta
    # operativa sul tenant Google centrale aci.it.
    "acta":  "aci.it",
}


def http_get_json(url: str, *, retries: int = 3, sleep_s: float = 2.0) -> dict[str, Any]:
    """GET a JSON URL with simple retry on transient failures."""
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            if attempt < retries:
                print(f"    HTTP error {e!r} — retry {attempt}/{retries} in {sleep_s}s")
                time.sleep(sleep_s)
                sleep_s *= 2
    raise RuntimeError(f"GET {url} failed after {retries} attempts: {last_err}")


def fetch_all_categories() -> list[str]:
    """Pull the complete list of Codice_categoria values from IndicePA's
    categorie-enti dataset, so we can iterate over every category."""
    cat_resource_id = "84ebb2e7-0e61-427b-a1dd-ab8bb2a84f07"
    params = {
        "resource_id": cat_resource_id,
        "limit": 1000,
    }
    url = f"{CKAN_BASE}/datastore_search?{urllib.parse.urlencode(params)}"
    data = http_get_json(url)
    rows = data.get("result", {}).get("records", []) if data.get("success") else []
    codes: list[str] = []
    for r in rows:
        c = (r.get("Codice_categoria") or "").strip()
        if c:
            codes.append(c)
    return sorted(codes)


def fetch_category(codice_categoria: str) -> list[dict[str, Any]]:
    """Pull all rows from IndicePA enti where Codice_Categoria = codice_categoria.

    Paginates until result set is exhausted.
    """
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {
            "resource_id": RESOURCE_ID,
            "filters": json.dumps({"Codice_Categoria": codice_categoria}),
            "limit": PAGE_SIZE,
            "offset": offset,
        }
        url = f"{CKAN_BASE}/datastore_search?{urllib.parse.urlencode(params)}"
        data = http_get_json(url)
        if not data.get("success"):
            raise RuntimeError(f"CKAN error for {codice_categoria}: {data}")
        records = data["result"]["records"]
        rows.extend(records)
        if len(records) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.5)  # be polite
    return rows


def extract_domain(sito: str | None) -> str | None:
    """Parse Sito_istituzionale into a bare hostname.

    Accepts any TLD verbatim — see ITALY.md "Domain extraction".
    Returns None if input is empty, unparseable, or the resulting hostname
    is syntactically invalid.
    """
    if not sito:
        return None
    s = sito.strip()
    if not s:
        return None
    # Some IPA values lack a scheme — urlparse handles those poorly. Prefix with //.
    if "://" not in s:
        s = "//" + s
    parsed = urlparse(s)
    host = (parsed.hostname or "").lower().strip()
    if not host:
        return None
    if host.startswith("www."):
        host = host[4:]
    if not HOSTNAME_RE.match(host):
        return None
    return host


# Stop-tokens del nome ente — parole strutturali che NON portano identità.
# Usate da _email_fallback_gate() per estrarre i token significativi del
# nome ufficiale IndicePA e verificare se intersecano i label del dominio
# candidato. Tenuto qui (non in scrape_validator) perché è specifico alle
# convenzioni di naming IndicePA + lingua italiana.
_NAME_NOISE = {
    "di","del","della","dello","dei","delle","degli","da","dal","dalla",
    "in","con","su","per","tra","fra","ed","e","a","al","alla","i","la",
    "il","lo","gli","le","l","d","de",
    "comune","comuni","provincia","provincie","regione","municipio",
    "citta","metropolitana","ministero","istituto","istituzione",
    "scuola","scuole","liceo","circolo","didattico","ordine","collegio",
    "federazione","azienda","agenzia","ente","consorzio","unione",
    "consiglio","commissione","autorita","direzione","centro",
    "ufficio","servizio","stato","statale","nazionale","italiana","italiano",
    "polo","amministrazione","professione","comprensivo","superiore",
    "secondaria","primaria","generale","direzione",
}


def _name_tokens(name: str) -> set[str]:
    """Token significativi del nome ente: lowercase, no diacritici, len>=5."""
    if not name:
        return set()
    import unicodedata, re as _re
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    parts = _re.split(r"[\s\.,;:'\"\-\(\)\/\d]+", n)
    return {p for p in parts if p and p not in _NAME_NOISE and len(p) >= 5}


def _email_fallback_gate(candidate_dom: str, ente_name: str) -> bool:
    """Decide if `candidate_dom` (un dominio non-PEC estratto da Mail* del
    record IndicePA) può essere accettato come dominio PRIMARIO dell'ente
    quando manca il Sito_istituzionale.

    Regola: scartiamo se PEC; altrimenti accettiamo solo se un token
    significativo del nome ente è uguale a / contenuto in / contiene un
    meaningful_label del dominio. Niente fuzzy qui — l'is_legit completo
    con fuzzy gira in recover_it_unknowns sui domain_fallbacks; qui ci
    serve essere conservativi al massimo perché alimentiamo il SEED, da
    cui il dominio si propaga ovunque.
    """
    from mail_sovereignty.scrape_validator import meaningful_labels, PEC_PROVIDERS
    s = (candidate_dom or "").lower().strip().rstrip(".")
    if not s:
        return False
    for pec in PEC_PROVIDERS:
        if s == pec or s.endswith("." + pec):
            return False
    nt = _name_tokens(ente_name)
    if not nt:
        return False
    dl = {l for l in meaningful_labels(s) if len(l) >= 5}
    if not dl:
        return False
    if nt & dl:
        return True
    for nts in nt:
        for lbl in dl:
            if (len(nts) > 4 and nts in lbl) or (len(lbl) > 4 and lbl in nts):
                return True
    return False


def extract_domain_fallbacks(row: dict[str, Any], primary_domain: str | None) -> list[str]:
    """Extract non-PEC email-derived domains for use when the primary website
    domain has no MX. Order: Mail1 first, Mail5 last. Dedupes, excludes primary.

    PEC domains are NEVER included (per docs/countries/ITALY.md). Italian PEC
    is dominated by 5-6 providers and doesn't represent the office email
    infrastructure we want to classify.
    """
    out: list[str] = []
    seen: set[str] = set()
    if primary_domain:
        seen.add(primary_domain.lower().lstrip("www."))
    for n in range(1, 6):
        addr = (row.get(f"Mail{n}") or "").strip()
        kind = (row.get(f"Tipo_Mail{n}") or "").strip().lower()
        if not addr or kind == "pec":
            continue
        if "@" not in addr:
            continue
        host = addr.rsplit("@", 1)[1].strip().lower().rstrip(".")
        if host.startswith("www."):
            host = host[4:]
        if not host or not HOSTNAME_RE.match(host):
            continue
        if host in seen:
            continue
        seen.add(host)
        out.append(host)
    return out


# Esclusioni L6 — popolato a runtime da is_territorial() per i casi
# rigettati da is_real_comune. Scaricato a fine fetch in
# data/reports/l6_exclusions.json per audit manuale.
_L6_EXCLUSIONS_LOG: list[dict] = []


def is_territorial(name: str, codice_categoria: str,
                    codice_ipa: str | None = None,
                    codice_comune_istat: str | None = None) -> bool:
    """Return True solo per entità territoriali al livello giusto.

    L4/L5/L45: positive name pattern (instabile in IndicePA ma per queste
    categorie funziona ad oggi — vedi note in LEVEL_NAME_RE).
    L6: NIENTE name pattern. Delega a is_real_comune() che usa ISTAT
    come fonte autoritativa (codice_comune_ISTAT + denominazione).
    """
    if not name:
        return False

    # L6: nuova logica ISTAT-based, sostituisce il vecchio name regex
    # che falliva su "ROMA CAPITALE" (Roma) e simili.
    if codice_categoria == "L6":
        ok = is_real_comune(name, codice_ipa or "", codice_comune_istat or "")
        if not ok:
            # Logga l'esclusione per il report manuale.
            _L6_EXCLUSIONS_LOG.append({
                "codice_ipa": (codice_ipa or "").strip(),
                "codice_comune_istat": (codice_comune_istat or "").strip(),
                "name": name.strip(),
            })
        return ok

    # L4/L5/L45: positive name pattern (legacy, lasciato come è)
    pos = LEVEL_NAME_RE.get(codice_categoria)
    if pos is None:
        return False
    if not pos.match(name):
        return False
    return True


def write_l6_exclusions_report() -> None:
    """Scrive data/reports/l6_exclusions.json/csv col registro completo
    delle L6 escluse da is_real_comune. Per audit manuale e revisione."""
    if not _L6_EXCLUSIONS_LOG:
        return
    import csv
    out_dir = ROOT / "data" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    # JSON dettagliato
    out_json = out_dir / "l6_exclusions.json"
    out_json.write_text(json.dumps({
        "_meta": {
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "n_excluded": len(_L6_EXCLUSIONS_LOG),
            "explanation": (
                "Enti IndicePA categorizzati L6 (Comune) ma rifiutati come "
                "veri comuni da is_real_comune(). Cross-validation ISTAT: "
                "codice_comune_ISTAT è presente in ISTAT ma il nome IndicePA "
                "non corrisponde alla denominazione ufficiale. Sono enti con "
                "SEDE in quel comune (UNCEM, ANCI, ATS, Patrimonio Mobilita, "
                "consorzi, ecc.) mal-categorizzati upstream da IndicePA. "
                "Riassegnati a IT-CONS-{codice_ipa} per non collidere con "
                "i veri comuni nella vista comuni della mappa."
            ),
            "for_manual_review": (
                "Se trovi qui un VERO comune erroneamente escluso, è un "
                "bug di is_real_comune() o un caso ISTAT mancante. "
                "Procedure: docs/SEED_VALIDATION.md §6.2 / §6.3"
            ),
        },
        "items": _L6_EXCLUSIONS_LOG,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV per audit veloce
    out_csv = out_dir / "l6_exclusions.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["codice_ipa", "codice_comune_istat", "name"])
        for r in _L6_EXCLUSIONS_LOG:
            w.writerow([r["codice_ipa"], r["codice_comune_istat"], r["name"]])

    print(f"L6 exclusions: {len(_L6_EXCLUSIONS_LOG)} enti -> {out_json.name}, {out_csv.name}")


def build_id(prefix: str, codice_istat: Any, codice_comune_istat: Any) -> str | None:
    """Compose the mxmap entity id from IPA's ISTAT codes.

    For Regioni/Province: use Codice_ISTAT.
    For Comuni / Città Metropolitane: use Codice_comune_ISTAT (6-digit padded).
    """
    if prefix in ("IT-REG", "IT-PRO"):
        if codice_istat in (None, ""):
            return None
        return f"{prefix}-{str(codice_istat).strip().zfill(2 if prefix == 'IT-REG' else 3)}"
    # IT-COM, IT-CMM
    if codice_comune_istat in (None, ""):
        return None
    return f"{prefix}-{str(codice_comune_istat).strip().zfill(6)}"


def load_crosswalk() -> dict[str, Any] | None:
    """Load data/it_istat_osm_crosswalk.json if present; return None otherwise."""
    if not CROSSWALK_PATH.exists():
        return None
    with open(CROSSWALK_PATH, encoding="utf-8") as f:
        return json.load(f)


def lookup_osm(
    crosswalk: dict[str, Any] | None,
    *,
    codice_ipa: str | None,
    codice_categoria: str,
    codice_istat: str | None,
    codice_comune_istat: str | None,
) -> int | None:
    """Resolve osm_relation_id from the crosswalk per level-specific strategy.

    L6 (comuni): IPA key (Wikidata P6832) → ISTAT comune (6-digit) fallback.
    L5 (province): Codice_comune_ISTAT[:3] → by_istat_province (Italian ISTAT
        comune codes are PPP+CCC; first 3 digits are the province code).
    L45 (città metropolitane): same as L5 — CMs share the province ISTAT
        code-space; their OSM relation is at admin_level=6.
    L4 (regioni): hand-curated REGIONI_IPA_TO_ISTAT2 → by_istat_region.
        Province autonome (p_bz, p_TN) are looked up as province (admin_level=6).
    """
    if crosswalk is None:
        return None

    if codice_categoria == "L6":
        # Codice_IPA → P6832 join (preferred); ISTAT comune fallback.
        if codice_ipa:
            v = crosswalk.get("by_ipa", {}).get(codice_ipa)
            if v is not None:
                return int(v)
        if codice_comune_istat:
            v = crosswalk.get("by_istat_comune", {}).get(str(codice_comune_istat).strip().zfill(6))
            if v is not None:
                return int(v)
        return None

    if codice_categoria in ("L5", "L45"):
        if codice_comune_istat:
            prov_code = str(codice_comune_istat).strip().zfill(6)[:3]
            v = crosswalk.get("by_istat_province", {}).get(prov_code)
            if v is not None:
                return int(v)
        return None

    if codice_categoria == "L4":
        if codice_ipa in PROV_AUTONOME_IPA_TO_PROVINCE_ISTAT:
            prov_code = PROV_AUTONOME_IPA_TO_PROVINCE_ISTAT[codice_ipa]
            v = crosswalk.get("by_istat_province", {}).get(prov_code)
            if v is not None:
                return int(v)
            return None
        if codice_ipa in REGIONI_IPA_TO_ISTAT2:
            istat2 = REGIONI_IPA_TO_ISTAT2[codice_ipa]
            v = crosswalk.get("by_istat_region", {}).get(istat2)
            if v is not None:
                return int(v)
        return None

    return None


def transform(
    row: dict[str, Any],
    codice_categoria: str,
    crosswalk: dict[str, Any] | None,
    *,
    territorial_filter: bool = True,
) -> dict[str, Any] | None:
    """Map an IndicePA row to mxmap seed format. Returns None if filtered out.

    territorial_filter=True applies the strict territorial rules (drop
    consorzi/associazioni/unioni for L4/L5/L45/L6). When False (the
    --include-others branch), only `in liquidazione` and missing-domain
    drops apply — every other ente of every category is kept.
    """
    if (row.get("Ente_in_liquidazione") or "").strip().upper() == "S":
        return None
    name = (row.get("Denominazione_ente") or "").strip()
    if not name:
        return None
    # Territorial-vs-non-territorial split: previously we DROPPED consorzi/
    # associazioni/unioni/comunità-montane in L4/L5/L45/L6 because they
    # don't have a clean province/comune polygon. V1.1 keeps them in the
    # seed but reassigns the ID prefix to IT-CONS-* so the territorial
    # topo never tries to match a polygon for them. They're still
    # classified, still aggregated into citizen-friendly clusters.
    is_terr_for_id = True
    if territorial_filter and codice_categoria in LEVEL_MAP:
        if not is_territorial(name, codice_categoria,
                              codice_ipa=row.get("Codice_IPA"),
                              codice_comune_istat=str(row.get("Codice_comune_ISTAT") or "")):
            is_terr_for_id = False
    domain = extract_domain(row.get("Sito_istituzionale"))
    domain_source = "sito_istituzionale" if domain else None

    # Manual override hook — applies when IndicePA's Sito_istituzionale is
    # wrong/defunct and the recovery flow can't reach the right domain.
    # See IT_MANUAL_DOMAIN_OVERRIDES at the top of this file.
    codice_ipa_for_override = (row.get("Codice_IPA") or "").strip().lower()
    domain_override_source: str | None = None
    if codice_ipa_for_override in IT_MANUAL_DOMAIN_OVERRIDES:
        # Tier 1 — hardcoded human-verified manual overrides (highest priority).
        override = IT_MANUAL_DOMAIN_OVERRIDES[codice_ipa_for_override]
        if override and HOSTNAME_RE.match(override.lower()):
            domain = override.lower()
            domain_source = "manual_override"
            domain_override_source = "manual_override"
    elif codice_ipa_for_override in _MANUAL_LLM_ENRICHMENT:
        # Tier 2 — manual LLM enrichment (committed JSON, human-curated).
        # See scripts/generate_llm_enrichment_prompt.py for the workflow.
        domain = _MANUAL_LLM_ENRICHMENT[codice_ipa_for_override]
        domain_source = "manual_llm_enrichment"
        domain_override_source = "manual_llm_enrichment"
    elif codice_ipa_for_override in _PEC_ENRICHMENT:
        # Tier 3 — automated PEC-only enrichment (Wikidata + DuckDuckGo).
        # Applied for enti with no Sito_istituzionale and only PEC emails.
        domain = _PEC_ENRICHMENT[codice_ipa_for_override]
        domain_source = "pec_enrichment"
        domain_override_source = "pec_enrichment"

    # Email-fallback at seed-time: if Sito_istituzionale is missing/invalid,
    # derive the primary domain from the first non-PEC Mail{1..5} entry.
    # GATED by name-token check: il 72% di questo path produceva storicamente
    # misattribuzioni (gmail/libero/virgilio dell'impiegato, oppure dominio
    # di altro ente). Accettiamo solo se ALMENO UN token significativo del
    # nome ente intersecta (o è substring di) un meaningful_label del dominio
    # candidato. Vedi scripts/_test_email_non_pec_fallback_gating.py.
    if not domain:
        fb = extract_domain_fallbacks(row, primary_domain=None)
        for cand in fb:
            if _email_fallback_gate(cand, row.get("Denominazione_ente", "")):
                domain = cand
                domain_source = "email_non_pec_fallback"
                break

    # Tier 6 — AOO+UO derived non-PEC emails (passed through is_legit).
    # Only fires when nothing above gave us a domain. Most useful for PA
    # centrali (gov.it sites) whose enti record has only PEC but whose
    # AOO sub-units expose dirigenti emails on the real institutional
    # domain (interno.gov.it -> interno.it via mail_resp).
    if not domain and codice_ipa_for_override in _AOO_UO_EXTENSION:
        cands = _AOO_UO_EXTENSION[codice_ipa_for_override]
        if cands:
            domain = cands[0]
            domain_source = "aoo_uo_email_fallback"

    # NOTE: a previous attempt added a "pec_email_fallback" third tier here
    # (using the first PEC email host when neither Sito_istituzionale nor
    # non-PEC email gave a domain). It was REVERTED because PEC providers
    # don't reflect the ente's real email infrastructure — Italian PEC is
    # dominated by ~5 providers (Aruba PEC, legalmail, postecert, asmepec).
    # The chosen strategy for the ~620 PEC-only enti is enrichment: a
    # separate scripts/enrich_pec_only.py runs before fetch_indicepa to
    # discover the real website / non-PEC email via Wikidata P856, search
    # engines, and LLM prompting, and writes IT_ENRICHMENT_OVERRIDES which
    # are loaded here just like IT_MANUAL_DOMAIN_OVERRIDES.

    if not domain:
        return None
    # Build entity ID. Territorial L4/L5/L45/L6 entities get the standard
    # IT-REG/PRO/CMM/COM prefix; consorzi/unioni/associazioni in those
    # category codes (NOT real territorial entities) get IT-CONS-{ipa} so
    # the frontend never tries to match them to a province/comune polygon.
    # All other categories (L17, L33, etc.) get IT-{cat}-{ipa}.
    if codice_categoria in LEVEL_MAP and is_terr_for_id:
        prefix, _label = LEVEL_MAP[codice_categoria]
        entity_id = build_id(prefix, row.get("Codice_ISTAT"), row.get("Codice_comune_ISTAT"))
    else:
        codice_ipa_clean = (row.get("Codice_IPA") or "").strip()
        if not codice_ipa_clean:
            return None
        if codice_categoria in LEVEL_MAP and not is_terr_for_id:
            # Consorzio/unione/associazione miscategorized as territorial in IPA
            entity_id = f"IT-CONS-{codice_ipa_clean}"
        else:
            entity_id = f"IT-{codice_categoria}-{codice_ipa_clean}"
    if entity_id is None:
        return None

    codice_ipa = (row.get("Codice_IPA") or "").strip() or None
    codice_istat_str = str(row.get("Codice_ISTAT") or "").strip() or None
    codice_comune_istat_str = str(row.get("Codice_comune_ISTAT") or "").strip() or None
    osm_id = lookup_osm(
        crosswalk,
        codice_ipa=codice_ipa,
        codice_categoria=codice_categoria,
        codice_istat=codice_istat_str,
        codice_comune_istat=codice_comune_istat_str,
    )
    # CRITICAL: solo entry territoriali (IT-REG/PRO/CMM/COM) possono avere
    # osm_relation_id assegnato a un polygon. Le entry non-territoriali
    # (IT-CONS-* e IT-{C*|L33|L34|...}-*) NON DEVONO avere osm_relation_id
    # perché il frontend matcha le entry ai polygons per quel campo: se
    # UNCEM Lazio (IT-CONS-*) avesse osm_relation_id=41485 (= relazione
    # OSM di Roma, perché ipa_codice_comune_istat=058091 mappa a Roma),
    # il polygon di Roma nella vista comuni mostrerebbe UNCEM invece del
    # vero Comune di Roma. Storia: bug osservato in produzione il 2026-05-29.
    if not (codice_categoria in LEVEL_MAP and is_terr_for_id):
        osm_id = None

    domain_fallbacks = extract_domain_fallbacks(row, domain)

    # Region name: derive from ISTAT comune-3-digit prefix via the
    # ISTAT_PROVINCE_TO_REGION table. Used by the frontend's
    # matchGroupFeature() to join comuni to region polygons by name.
    region_name = istat_to_region(codice_comune_istat_str) if codice_categoria == "L6" else None
    if region_name is None and codice_categoria == "L4":
        # For regioni entries, use the entity's own Codice_ISTAT (2-digit) as
        # an alternative path — though we may want to set region to its own name.
        # Easiest: set region == name itself for L4/L5/L45 territorial entities.
        region_name = name

    # District name (= OSM province name) for IT-COM entries — used by the
    # frontend's district-level aggregation. Falls back to region for non-comuni.
    district_name = istat_to_province_name(codice_comune_istat_str) if codice_categoria == "L6" else None

    seed: dict[str, Any] = {
        "id": entity_id,
        "name": name,
        "country": "IT",
        "region": region_name,
        "district": district_name,
        "domain": domain,
        "osm_relation_id": osm_id,
        # mxmap.it Italian extension: ordered list of non-PEC email-derived
        # hostnames. Used by scripts/recover_it_unknowns.py when primary domain
        # has no MX (e.g., comune.albianodivrea.to.it has no MX, but Mail2 is
        # albiano.divrea@ruparpiemonte.it — recovery picks up ruparpiemonte.it).
        # NEVER includes PEC domains.
        "domain_fallbacks": domain_fallbacks,
        # IndicePA bookkeeping (kept for downstream joins / audits — mxmap will
        # ignore unknown keys)
        "ipa_codice_ipa": codice_ipa,
        "ipa_codice_categoria": codice_categoria,
        "ipa_codice_istat": codice_istat_str,
        "ipa_codice_comune_istat": codice_comune_istat_str,
    }
    if domain_source:
        seed["domain_source"] = domain_source
    if domain_override_source:
        seed["domain_override_source"] = domain_override_source
    return seed


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-others", action="store_true",
                    help="Also fetch every non-territorial IndicePA category "
                         "(schools, healthcare, universities, ministries, "
                         "professional orders, procurement, etc.) "
                         "with looser filtering. Default: territorial only.")
    args = ap.parse_args()

    raw_counts: dict[str, int] = {}
    kept_counts: dict[str, int] = {}
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    global _PEC_ENRICHMENT, _MANUAL_LLM_ENRICHMENT, _AOO_UO_EXTENSION
    _PEC_ENRICHMENT = load_pec_enrichment()
    if _PEC_ENRICHMENT:
        print(f"Loaded {len(_PEC_ENRICHMENT)} PEC-only enrichments from "
              f"{IT_PEC_ENRICHMENT_PATH.name}")
    _MANUAL_LLM_ENRICHMENT = load_manual_llm_enrichment()
    if _MANUAL_LLM_ENRICHMENT:
        print(f"Loaded {len(_MANUAL_LLM_ENRICHMENT)} manual-LLM enrichments "
              f"from {IT_MANUAL_LLM_ENRICHMENT_PATH.name}")
    _AOO_UO_EXTENSION = load_aoo_uo_extension()
    if _AOO_UO_EXTENSION:
        n_doms = sum(len(v) for v in _AOO_UO_EXTENSION.values())
        print(f"Loaded {len(_AOO_UO_EXTENSION)} enti enriched via AOO+UO "
              f"({n_doms} non-PEC domains, all is_legit-validated)")

    crosswalk = load_crosswalk()
    if crosswalk is None:
        print(f"WARNING: {CROSSWALK_PATH} not found — osm_relation_id will be null.")
        print("         Run scripts/build_istat_osm_crosswalk.py first for full data.\n")
    else:
        print(f"Loaded crosswalk: "
              f"{len(crosswalk.get('by_istat_region', {}))} regioni, "
              f"{len(crosswalk.get('by_istat_province', {}))} province, "
              f"{len(crosswalk.get('by_istat_comune', {}))} comuni, "
              f"{len(crosswalk.get('by_ipa', {}))} IPA-keyed")

    # Phase 1: territorial categories (strict filtering)
    for codice_categoria, (prefix, label) in LEVEL_MAP.items():
        print(f"\n=== {codice_categoria} — {label} ({prefix}) ===")
        rows = fetch_category(codice_categoria)
        raw_counts[codice_categoria] = len(rows)
        print(f"  Raw rows: {len(rows)}")

        kept = 0
        dropped_dup = 0
        with_osm = 0
        for row in rows:
            entity = transform(row, codice_categoria, crosswalk, territorial_filter=True)
            if entity is None:
                continue
            if entity["id"] in seen_ids:
                dropped_dup += 1
                continue
            seen_ids.add(entity["id"])
            entries.append(entity)
            kept += 1
            if entity.get("osm_relation_id") is not None:
                with_osm += 1
        kept_counts[codice_categoria] = kept
        print(
            f"  Kept: {kept}  with_osm: {with_osm}  "
            f"dropped(filter): {len(rows) - kept - dropped_dup}  duplicates: {dropped_dup}"
        )

    # Phase 2 (optional): non-territorial categories (looser filtering)
    if args.include_others:
        all_categories = fetch_all_categories()
        territorial = set(LEVEL_MAP)
        other_categories = [c for c in all_categories if c not in territorial]
        print(f"\n=== --include-others: {len(other_categories)} non-territorial categories ===")
        for codice_categoria in other_categories:
            rows = fetch_category(codice_categoria)
            raw_counts[codice_categoria] = len(rows)
            kept = 0
            dropped_dup = 0
            for row in rows:
                entity = transform(row, codice_categoria, crosswalk, territorial_filter=False)
                if entity is None:
                    continue
                if entity["id"] in seen_ids:
                    dropped_dup += 1
                    continue
                seen_ids.add(entity["id"])
                entries.append(entity)
                kept += 1
            kept_counts[codice_categoria] = kept
            if rows:
                print(f"  {codice_categoria:<5} raw={len(rows):>5}  kept={kept:>5}  "
                      f"dropped={len(rows)-kept-dropped_dup:>4}  dup={dropped_dup:>3}")

    out_path = DATA / "municipalities_it.json"
    DATA.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    # Scrivi report L6 esclusioni (per audit manuale — vedi
    # docs/SEED_VALIDATION.md §6).
    write_l6_exclusions_report()

    total_with_osm = sum(1 for e in entries if e.get("osm_relation_id") is not None)
    print("\n=== Summary ===")
    for code, (prefix, label) in LEVEL_MAP.items():
        print(f"  {code} {label:<32} raw={raw_counts.get(code, 0):>6}  kept={kept_counts.get(code, 0):>6}")
    print(f"  TOTAL kept={len(entries):>6}  with_osm={total_with_osm:>6}")
    print(f"\nWritten: {out_path}")
    if crosswalk is None:
        print("Note: osm_relation_id is null — run scripts/build_istat_osm_crosswalk.py and re-run this script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
