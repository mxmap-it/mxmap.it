#!/usr/bin/env python3
"""Fetch Italian admin boundaries at all 3 levels from Overpass.

Generates:
  topo/it_region.topo.json       (admin_level=4, ~22 regioni + prov.aut.)
  topo/it_province.topo.json     (admin_level=6, ~107 province + CM)
  topo/it_municipality.topo.json (admin_level=8, ~7,900 comuni)

Stored in mxmap's manifest under the existing 3-slot schema (region /
district / municipality) where "district" holds the province file.

Run on the server (fast network, fewer Overpass timeouts):
    uv run python3 scripts/fetch_it_boundaries.py

Requires mapshaper + osmtogeojson on PATH.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_boundaries import (  # noqa: E402
    DATA_DIR,
    TOPO_DIR,
    annotate_geojson,
    create_topojson,
    osm_to_geojson,
    overpass_query,
)

# Italy mainland + islands bounding box (Pantelleria/Lampedusa to South Tyrol).
IT_BBOX = [6.6, 35.4, 18.6, 47.1]

# admin_level -> mxmap level slot (matching the frontend's region/district/
# municipality 3-button toggle). Province goes in "district" for the manifest;
# the frontend translation layer renames it to "Province" in the UI.
LEVELS = [
    (4, "region"),
    (6, "district"),       # output filename: it_district.topo.json
    (8, "municipality"),
]
# We override the filename for level=6 to be "it_province.topo.json" so the
# file is self-documenting; the manifest still maps it under the "district"
# slot.
FILENAME_OVERRIDE = {6: "it_province.topo.json"}


def fetch_at_level(admin_level: int) -> dict | None:
    """Overpass query for all IT relations at the given admin_level."""
    query = f"""
[out:json][timeout:900];
area["ISO3166-1"="IT"]->.country;
(
  relation["boundary"="administrative"]["admin_level"="{admin_level}"](area.country);
);
out body;
>;
out skel qt;
"""
    print(f"  Overpass query for admin_level={admin_level} ...")
    return overpass_query(query)


def update_manifest(sizes: dict[str, int]) -> None:
    """Write the IT entry into topo/manifest.json with all three levels."""
    manifest_path = TOPO_DIR / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    region_file = "it_region.topo.json"
    district_file = "it_province.topo.json"
    muni_file = "it_municipality.topo.json"

    manifest["IT"] = {
        "levels": ["region", "district", "municipality"],
        "files": {
            "region": region_file,
            "district": district_file,
            "municipality": muni_file,
        },
        "sizes": {k: v for k, v in sizes.items() if v > 0},
        "bbox": IT_BBOX,
    }

    sorted_manifest = dict(sorted(manifest.items()))
    with open(manifest_path, "w") as f:
        json.dump(sorted_manifest, f, indent=2)
    print(f"  Updated manifest: IT -> 3 levels, bbox {IT_BBOX}")


def main() -> int:
    seed_path = DATA_DIR / "municipalities_it.json"
    with open(seed_path) as f:
        seed_data = json.load(f)
    print(f"Loaded {len(seed_data)} entries from {seed_path.name}")
    print(f"  with osm_relation_id: {sum(1 for e in seed_data if e.get('osm_relation_id'))}")

    TOPO_DIR.mkdir(parents=True, exist_ok=True)

    sizes: dict[str, int] = {}

    for admin_level, level_slot in LEVELS:
        out_filename = FILENAME_OVERRIDE.get(admin_level, f"it_{level_slot}.topo.json")
        print(f"\n=== admin_level={admin_level} -> {out_filename} ===")
        with tempfile.TemporaryDirectory() as tmpdir:
            osm_data = fetch_at_level(admin_level)
            if not osm_data:
                print("  ERROR: Overpass returned no data")
                continue
            relations = [e for e in osm_data.get("elements", []) if e["type"] == "relation"]
            print(f"  Overpass returned {len(relations)} relations")
            if not relations:
                print("  ERROR: no relations in response")
                continue

            geo_path = osm_to_geojson(osm_data, tmpdir)
            with open(geo_path) as f:
                geo = json.load(f)
            n_features = len(geo.get("features", []))
            print(f"  GeoJSON: {n_features} features")
            if n_features == 0:
                print("  ERROR: zero features after conversion")
                continue

            annotated_path = annotate_geojson(geo_path, "IT", seed_data)

            # Use the existing helper, but override the output filename for
            # province (admin_level=6) since create_topojson hardcodes "{cc}_{level}".
            if admin_level == 6:
                # Replicate create_topojson but with our preferred filename.
                out_path = str(TOPO_DIR / "it_province.topo.json")
                cmd = [
                    "mapshaper", annotated_path,
                    "-simplify", "10%", "keep-shapes",
                    "-o", out_path, "format=topojson quantization=5000",
                ]
                subprocess.run(cmd, check=True, capture_output=True)
            else:
                out_path = create_topojson(annotated_path, "IT", level_slot)

            size = Path(out_path).stat().st_size
            sizes[out_filename] = size
            print(f"  -> {Path(out_path).name} ({size:,} bytes)")

        time.sleep(10)  # polite to Overpass between levels

    update_manifest(sizes)

    print("\n=== Summary ===")
    for filename, size in sizes.items():
        print(f"  {filename:<35} {size:>12,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
