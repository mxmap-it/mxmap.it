#!/usr/bin/env python3
"""Build the Italian ISTAT/IndicePA → OSM-relation-ID crosswalk for mxmap.it.

Queries Wikidata for every Italian item that has both `P402` (OSM relation ID)
and `P635` (ISTAT ID), and optionally `P6832` (IndicePA ID). Partitions by
ISTAT code length:
- 2 digits → regione (incl. provincia autonoma)
- 3 digits → provincia / città metropolitana
- 6 digits → comune

Output: data/it_istat_osm_crosswalk.json
{
    "by_ipa": {"c_h501": 41485, ...},                  # IndicePA Codice_IPA → OSM
    "by_istat_region":   {"12": 40780, ...},
    "by_istat_province": {"058": 40784, ...},
    "by_istat_comune":   {"058091": 41485, ...},
    "metadata": {"generated_at": "...", "source": "Wikidata SPARQL"}
}

Consumed by scripts/patch_it_osm_ids.py to fill the `osm_relation_id` field
in data/municipalities_it.json.

Usage: uv run python3 scripts/build_istat_osm_crosswalk.py
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "mxmap.it-crosswalk-builder/0.1 (+https://github.com/fpietrosanti/mxmap.it)"

# All Italian items (P17=Q38) with both an OSM relation (P402) and an ISTAT ID
# (P635). Optionally include the IndicePA ID (P6832) when present.
QUERY = """
SELECT ?item ?itemLabel ?osm ?istat ?ipa WHERE {
  ?item wdt:P17 wd:Q38 ;
        wdt:P402 ?osm ;
        wdt:P635 ?istat .
  OPTIONAL { ?item wdt:P6832 ?ipa }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "it,en". }
}
"""


def sparql_query(query: str) -> list[dict[str, Any]]:
    """Run a SPARQL query against Wikidata Query Service."""
    url = f"{SPARQL_URL}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/sparql-results+json",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("results", {}).get("bindings", [])


def main() -> int:
    print("Querying Wikidata for Italian admin entities (P402 + P635)...")
    rows = sparql_query(QUERY)
    print(f"  Got {len(rows)} raw rows")

    by_ipa: dict[str, int] = {}
    by_region: dict[str, int] = {}
    by_province: dict[str, int] = {}
    by_comune: dict[str, int] = {}

    skipped_bad_osm = 0
    skipped_bad_istat = 0

    for r in rows:
        try:
            osm = int(r["osm"]["value"])
        except (KeyError, ValueError):
            skipped_bad_osm += 1
            continue
        istat = (r.get("istat", {}).get("value") or "").strip()
        if not istat or not istat.isdigit():
            skipped_bad_istat += 1
            continue

        # Partition by ISTAT length. Italian standard:
        #   region    = 2 digits
        #   province  = 3 digits
        #   comune    = 6 digits
        if len(istat) <= 2:
            by_region[istat.zfill(2)] = osm
        elif len(istat) <= 3:
            by_province[istat.zfill(3)] = osm
        elif len(istat) == 6:
            by_comune[istat] = osm
        else:
            # Some items have padded values (e.g. "0058091") — normalise.
            stripped = istat.lstrip("0")
            if len(stripped) <= 6:
                by_comune[stripped.zfill(6)] = osm
            else:
                # Unexpected length — record under a debug bucket
                # (don't silently drop)
                by_comune[istat] = osm

        # Bonus: IPA join key (P6832), when present
        ipa = (r.get("ipa", {}).get("value") or "").strip()
        if ipa:
            by_ipa[ipa] = osm

    out = {
        "by_ipa": by_ipa,
        "by_istat_region": by_region,
        "by_istat_province": by_province,
        "by_istat_comune": by_comune,
        "metadata": {
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "source": "Wikidata SPARQL (P17=Q38, P402, P635, optional P6832)",
            "raw_row_count": len(rows),
            "skipped_bad_osm": skipped_bad_osm,
            "skipped_bad_istat": skipped_bad_istat,
        },
    }

    out_path = DATA / "it_istat_osm_crosswalk.json"
    DATA.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=True)

    print()
    print("=== Summary ===")
    print(f"  Regioni     (2-digit ISTAT): {len(by_region):>6}  (expected ~22)")
    print(f"  Province    (3-digit ISTAT): {len(by_province):>6}  (expected ~107)")
    print(f"  Comuni      (6-digit ISTAT): {len(by_comune):>6}  (expected ~7900)")
    print(f"  IPA-keyed entries:           {len(by_ipa):>6}")
    print(f"  Skipped (bad OSM):           {skipped_bad_osm:>6}")
    print(f"  Skipped (bad ISTAT):         {skipped_bad_istat:>6}")
    print(f"\nWritten: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
