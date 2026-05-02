#!/usr/bin/env python3
"""Fetch Italian public-administration seed data from IndicePA.

Pulls only territorial entities (Regioni / Province / Città Metropolitane /
Comuni) from the IndicePA `enti` dataset via CKAN's datastore_search JSON API.

Filtering rules per docs/countries/ITALY.md:
- Drop Ente_in_liquidazione = "S"
- Drop rows without a usable Sito_istituzionale (any TLD accepted)
- Drop consorzi/associazioni/unioni/comunità montane via name regex
- Encode level in the `id` prefix (IT-REG / IT-PRO / IT-CMM / IT-COM)

If `data/it_istat_osm_crosswalk.json` exists (built by
`scripts/build_istat_osm_crosswalk.py`), `osm_relation_id` is populated by
joining first on Codice_IPA (P6832 in Wikidata) and falling back to the
ISTAT code. Otherwise the field is left null.

Usage:
    uv run python3 scripts/build_istat_osm_crosswalk.py   # one-time, before
    uv run python3 scripts/fetch_indicepa.py
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
    "L6":  None,  # no positive filter; NON_TERRITORIAL_NAME_RE handles drops
}

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


def is_territorial(name: str, codice_categoria: str) -> bool:
    """Return True only for territorial entities at the right level.

    L4/L5/L45 use a positive name pattern (must start with "Regione" /
    "Provincia" / "Città Metropolitana") so that interregional consortia,
    regional agencies, and other non-territorial enti sharing the category
    are dropped.
    L6 uses a negative pattern (drop consorzi/unioni/comunità montane).
    """
    if not name:
        return False
    pos = LEVEL_NAME_RE.get(codice_categoria)
    if pos is not None:
        return bool(pos.match(name))
    # L6 fallback: negative match
    return NON_TERRITORIAL_NAME_RE.search(name) is None


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
) -> dict[str, Any] | None:
    """Map an IndicePA row to mxmap seed format. Returns None if filtered out."""
    if (row.get("Ente_in_liquidazione") or "").strip().upper() == "S":
        return None
    name = (row.get("Denominazione_ente") or "").strip()
    if not name:
        return None
    if not is_territorial(name, codice_categoria):
        return None
    domain = extract_domain(row.get("Sito_istituzionale"))
    if not domain:
        return None
    prefix, _label = LEVEL_MAP[codice_categoria]
    entity_id = build_id(prefix, row.get("Codice_ISTAT"), row.get("Codice_comune_ISTAT"))
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

    return {
        "id": entity_id,
        "name": name,
        "country": "IT",
        # `region` is filled in a later pass once we have the ISTAT region table;
        # leaving as None here keeps this script free of external lookups.
        "region": None,
        "domain": domain,
        "osm_relation_id": osm_id,
        # IndicePA bookkeeping (kept for downstream joins / audits — mxmap will
        # ignore unknown keys)
        "ipa_codice_ipa": codice_ipa,
        "ipa_codice_categoria": codice_categoria,
        "ipa_codice_istat": codice_istat_str,
        "ipa_codice_comune_istat": codice_comune_istat_str,
    }


def main() -> int:
    raw_counts: dict[str, int] = {}
    kept_counts: dict[str, int] = {}
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

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

    for codice_categoria, (prefix, label) in LEVEL_MAP.items():
        print(f"\n=== {codice_categoria} — {label} ({prefix}) ===")
        rows = fetch_category(codice_categoria)
        raw_counts[codice_categoria] = len(rows)
        print(f"  Raw rows: {len(rows)}")

        kept = 0
        dropped_dup = 0
        with_osm = 0
        for row in rows:
            entity = transform(row, codice_categoria, crosswalk)
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

    out_path = DATA / "municipalities_it.json"
    DATA.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

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
