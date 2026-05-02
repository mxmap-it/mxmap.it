#!/usr/bin/env python3
"""Fetch Italian public-administration seed data from IndicePA.

Pulls only territorial entities (Regioni / Province / Città Metropolitane /
Comuni) from the IndicePA `enti` dataset via CKAN's datastore_search JSON API.

Filtering rules per docs/countries/ITALY.md:
- Drop Ente_in_liquidazione = "S"
- Drop rows without a usable Sito_istituzionale (any TLD accepted)
- Drop consorzi/associazioni/unioni/comunità montane via name regex
- Encode level in the `id` prefix (IT-REG / IT-PRO / IT-CMM / IT-COM)

osm_relation_id is left null in this script — the ISTAT→OSM crosswalk is
built separately and patched in by a follow-up step.

Usage: uv run python3 scripts/fetch_indicepa.py
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

# Codice_Categoria → (level prefix, human-readable label)
LEVEL_MAP = {
    "L4": ("IT-REG", "Regione / Provincia Autonoma"),
    "L5": ("IT-PRO", "Provincia"),
    "L45": ("IT-CMM", "Città Metropolitana"),
    "L6": ("IT-COM", "Comune"),
}

# Names matching this regex are consorzi / associazioni / unioni — no polygon,
# excluded from v1 scope. Case-insensitive.
NON_TERRITORIAL_NAME_RE = re.compile(
    r"\b(consorzio|associazione|unione\s+(?:dei|di|del)\s+comuni|"
    r"unione\s+montana|unione\s+territoriale|"
    r"comunit[aà]\s+montana|comunit[aà]\s+collinare|comunit[aà]\s+isolana)\b",
    re.IGNORECASE,
)

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


def is_territorial(name: str) -> bool:
    """Return False if the name looks like a consorzio/associazione/unione."""
    if not name:
        return False
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


def transform(row: dict[str, Any], codice_categoria: str) -> dict[str, Any] | None:
    """Map an IndicePA row to mxmap seed format. Returns None if filtered out."""
    if (row.get("Ente_in_liquidazione") or "").strip().upper() == "S":
        return None
    name = (row.get("Denominazione_ente") or "").strip()
    if not name:
        return None
    if not is_territorial(name):
        return None
    domain = extract_domain(row.get("Sito_istituzionale"))
    if not domain:
        return None
    prefix, _label = LEVEL_MAP[codice_categoria]
    entity_id = build_id(prefix, row.get("Codice_ISTAT"), row.get("Codice_comune_ISTAT"))
    if entity_id is None:
        return None
    return {
        "id": entity_id,
        "name": name,
        "country": "IT",
        # `region` is filled in a later pass once we have the ISTAT region table;
        # leaving as None here keeps this script free of external lookups.
        "region": None,
        "domain": domain,
        "osm_relation_id": None,  # filled by the ISTAT→OSM crosswalk script
        # IndicePA bookkeeping (kept for downstream joins / audits — mxmap will
        # ignore unknown keys)
        "ipa_codice_ipa": (row.get("Codice_IPA") or "").strip() or None,
        "ipa_codice_categoria": codice_categoria,
        "ipa_codice_istat": (str(row.get("Codice_ISTAT") or "").strip() or None),
        "ipa_codice_comune_istat": (str(row.get("Codice_comune_ISTAT") or "").strip() or None),
    }


def main() -> int:
    raw_counts: dict[str, int] = {}
    kept_counts: dict[str, int] = {}
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for codice_categoria, (prefix, label) in LEVEL_MAP.items():
        print(f"\n=== {codice_categoria} — {label} ({prefix}) ===")
        rows = fetch_category(codice_categoria)
        raw_counts[codice_categoria] = len(rows)
        print(f"  Raw rows: {len(rows)}")

        kept = 0
        dropped_dup = 0
        for row in rows:
            entity = transform(row, codice_categoria)
            if entity is None:
                continue
            if entity["id"] in seen_ids:
                dropped_dup += 1
                continue
            seen_ids.add(entity["id"])
            entries.append(entity)
            kept += 1
        kept_counts[codice_categoria] = kept
        print(f"  Kept: {kept}  Dropped (filter): {len(rows) - kept - dropped_dup}  Duplicates: {dropped_dup}")

    out_path = DATA / "municipalities_it.json"
    DATA.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print("\n=== Summary ===")
    for code, (prefix, label) in LEVEL_MAP.items():
        print(f"  {code} {label:<32} raw={raw_counts.get(code, 0):>6}  kept={kept_counts.get(code, 0):>6}")
    print(f"  TOTAL                              kept={len(entries):>6}")
    print(f"\nWritten: {out_path}")
    print("Note: osm_relation_id is null — run the ISTAT→OSM crosswalk script next.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
