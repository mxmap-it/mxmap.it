#!/usr/bin/env python3
"""Strip foreign (French / Swiss / Slovenian / etc.) admin polygons from
topo/it_*.topo.json.

Overpass `area["ISO3166-1"="IT"]` with admin_level=4/6/8 returns relations
whose area intersects the Italian boundary, INCLUDING cross-border foreign
admin units (e.g., Auvergne-Rhône-Alpes which contains Mont Blanc, partly
in Italy). The OSM data is correct; we just need to drop foreign features
when rendering the Italy-only map.

This script keeps:
  - Italian regions (admin_level=4): exact match against IT_REGION_NAMES
  - Italian provinces (admin_level=6): allowlist by Italian-province name
  - Italian comuni (admin_level=8): keep only features whose `country` tag
    is empty or "IT", or whose name matches an Italian comune in seed
    (best-effort).

Run after fetch_it_boundaries.py:
  uv run python3 scripts/strip_foreign_from_it_topo.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPO_DIR = ROOT / "topo"
DATA_DIR = ROOT / "data"

# Exact Italian region names as they appear in OSM admin_level=4 `name` tag.
IT_REGION_NAMES = frozenset({
    "Piemonte",
    "Valle d'Aosta / Vallée d'Aoste",
    "Lombardia",
    "Trentino-Alto Adige/Südtirol",
    "Veneto",
    "Friuli-Venezia Giulia",
    "Liguria",
    "Emilia-Romagna",
    "Toscana",
    "Umbria",
    "Marche",
    "Lazio",
    "Abruzzo",
    "Molise",
    "Campania",
    "Puglia",
    "Basilicata",
    "Calabria",
    "Sicilia",
    "Sardigna/Sardegna",
})


def load_seed_province_names() -> set[str]:
    """Italian province OSM names — derived from data/it_istat_osm_crosswalk.json
    crossed with the existing topo if present, OR fall back to seed-derived list."""
    seed_path = DATA_DIR / "municipalities_it.json"
    names: set[str] = set()
    if seed_path.exists():
        seed = json.loads(seed_path.read_text(encoding="utf-8"))
        for e in seed:
            if e.get("id", "").startswith(("IT-PRO-", "IT-CMM-")):
                # Strip common prefixes used by IndicePA names
                n = (e.get("name") or "").strip()
                # Keep multiple variants for matching
                names.add(n)
                for prefix in ["Provincia di ", "Provincia del ", "Provincia dell'",
                               "Provincia della ", "Città Metropolitana di ",
                               "Città Metropolitana di Roma Capitale", "Libero Consorzio Comunale di ",
                               "CITTA' METROPOLITANA DI ", "Citta' Metropolitana di "]:
                    if n.startswith(prefix):
                        names.add(n[len(prefix):])
    return names


def load_seed_comune_names() -> set[str]:
    """Italian comune OSM names from seed."""
    seed_path = DATA_DIR / "municipalities_it.json"
    names: set[str] = set()
    if seed_path.exists():
        seed = json.loads(seed_path.read_text(encoding="utf-8"))
        for e in seed:
            if e.get("id", "").startswith("IT-COM-"):
                n = (e.get("name") or "").strip()
                if n.startswith("Comune di "):
                    n = n[len("Comune di "):]
                if n.startswith("Comune dell'"):
                    n = n[len("Comune dell'"):]
                if n.startswith("Comune della "):
                    n = n[len("Comune della "):]
                names.add(n.lower())
    return names


def filter_topo(topo_path: Path, allowlist: set[str], *, trust_country_tag: bool = False,
                allow_country_iso: str = "IT", strict_allowlist: bool = False) -> tuple[int, int]:
    """Filter geometries.

    Strategy:
      - If feature.properties.country tag matches allow_country_iso ("IT"),
        ALWAYS keep (country tag is the strongest signal — annotate_geojson
        sets it from the seed which is Italy-only).
      - Else if country tag is set to a foreign value (FR, CH, AT, SI, …),
        ALWAYS drop.
      - Else (country tag empty/missing): use the name allowlist.
        - trust_country_tag=True bypasses the name check entirely
          (used for L8 comuni where the allowlist is too brittle to match
          ~7,900 Italian comuni reliably).
    """
    if not topo_path.exists():
        print(f"  {topo_path.name}: missing — skipping")
        return 0, 0
    topo = json.loads(topo_path.read_text(encoding="utf-8"))
    objs = topo.get("objects", {})
    total_kept = 0
    total_removed = 0
    removed_names: list[str] = []
    for obj_name, obj in objs.items():
        before = obj.get("geometries", [])
        after = []
        for f in before:
            props = f.get("properties") or {}
            name = (props.get("name") or "").strip()
            country = (props.get("country") or props.get("ISO3166-1") or "").strip().upper()
            # strict_allowlist: ignore the country tag entirely, only the name
            # allowlist matters. Used for L4 where annotate_geojson labels every
            # feature country=IT (including cross-border foreign relations like
            # Auvergne-Rhône-Alpes that intersect the Italian boundary).
            if strict_allowlist:
                if name in allowlist or any(name.lower() == a.lower() for a in allowlist):
                    after.append(f)
                    total_kept += 1
                else:
                    total_removed += 1
                    removed_names.append(f"{name} [{country or '-'}]")
                continue
            # Country tag matches IT -> keep
            if country == allow_country_iso:
                after.append(f)
                total_kept += 1
                continue
            # Country tag is explicitly foreign -> drop
            if country and country != allow_country_iso:
                total_removed += 1
                removed_names.append(f"{name} [{country}]")
                continue
            # Country tag empty: trust_country_tag=True keeps (assume IT-only seed annotation reliability)
            if trust_country_tag:
                after.append(f)
                total_kept += 1
                continue
            # Country tag empty + we don't fully trust the tag: name allowlist
            if name in allowlist:
                after.append(f)
                total_kept += 1
                continue
            if any(name.lower() == a.lower() for a in allowlist):
                after.append(f)
                total_kept += 1
                continue
            total_removed += 1
            removed_names.append(name)
        obj["geometries"] = after
    topo_path.write_text(json.dumps(topo, ensure_ascii=False, separators=(",", ":")),
                         encoding="utf-8")
    print(f"  {topo_path.name}: kept {total_kept}, removed {total_removed}")
    if removed_names:
        for rn in removed_names[:8]:
            print(f"    - removed: {rn!r}")
        if len(removed_names) > 8:
            print(f"    ... and {len(removed_names) - 8} more")
    return total_kept, total_removed


def main() -> int:
    print("=== Strip foreign features from IT topo files ===")
    print(f"\n[L4 region] keeping the 20 Italian regions:")
    filter_topo(TOPO_DIR / "it_region.topo.json", IT_REGION_NAMES, strict_allowlist=True)

    province_names = load_seed_province_names()
    # Augment seed-province allowlist with the topo-bilingual variants we
    # use in fetch_indicepa.py ISTAT3_TO_TOPO_NAME_MANUAL (Friuli bilingual,
    # Sardegna historical pre-2016 names). These don't appear in the seed
    # because seed.district mirrors the topo `name` tag, but the allowlist
    # is computed from seed `name` (without the "Provincia di " prefix
    # stripping logic). Adding them explicitly makes strip_foreign keep
    # these polygons reliably.
    province_names_topo = province_names | {
        "Udine / Udin / Videm",
        "Gorizia / Gurize / Gorica",
        "Aristanis/Oristano",
        "Casteddu/Cagliari",
        "Tàttari/Sassari",
        "Pordenone / Pordenon",
        "Nuoro",
        "Gallura Nord-Est Sardegna",
        "Ogliastra",
        "Medio Campidano",
        "Sulcis Iglesiente",
    }
    print(f"\n[L6 province] strict allowlist of {len(province_names_topo)} Italian provinces "
          f"(strips foreign cross-border features like Haute-Savoie):")
    filter_topo(TOPO_DIR / "it_province.topo.json", province_names_topo,
                strict_allowlist=True)

    # admin_level=8 (comuni) — too many entries to enumerate; rely on country tag
    # which annotate_geojson sets to "IT". Foreign comuni from cross-border
    # area get country=='' typically (no IT tag) and get dropped.
    comune_names = load_seed_comune_names()
    print(f"\n[L8 municipality] keeping comuni in seed ({len(comune_names)} names):")
    filter_topo(TOPO_DIR / "it_municipality.topo.json", comune_names)

    print("\nDone. Rebuild manifest if sizes changed: scripts/fetch_it_boundaries.py update_manifest()")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
