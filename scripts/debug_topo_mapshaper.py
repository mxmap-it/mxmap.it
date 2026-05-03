"""Reproduce the mapshaper failure at admin_level=4 with visible stderr."""
import sys
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_boundaries import (  # noqa: E402
    overpass_query,
    osm_to_geojson,
    annotate_geojson,
    TOPO_DIR,
    DATA_DIR,
)


def main() -> int:
    with open(DATA_DIR / "municipalities_it.json", encoding="utf-8") as f:
        seed = json.load(f)

    query = (
        '[out:json][timeout:600];'
        'area["ISO3166-1"="IT"]->.country;'
        '(relation["boundary"="administrative"]["admin_level"="4"](area.country););'
        'out body; >; out skel qt;'
    )
    print("Querying Overpass for admin_level=4 (regions)...")
    osm_data = overpass_query(query)
    relations = [e for e in osm_data.get("elements", []) if e["type"] == "relation"]
    print(f"Got {len(relations)} relations")

    with tempfile.TemporaryDirectory() as tmp:
        geo_path = osm_to_geojson(osm_data, tmp)
        with open(geo_path, encoding="utf-8") as f:
            geo = json.load(f)
        n = len(geo.get("features", []))
        print(f"GeoJSON features: {n}")
        if n == 0:
            print("ERROR: zero features")
            return 2
        annotated = annotate_geojson(geo_path, "IT", seed)
        print("Running mapshaper with stderr visible...")
        out_path = str(TOPO_DIR / "it_region.topo.json")
        # Try the same arg layout the existing helper uses (last token combines
        # format and quantization with a space separator).
        cmd1 = [
            "mapshaper", annotated,
            "-simplify", "8%", "keep-shapes",
            "-o", out_path, "format=topojson quantization=5000",
        ]
        print("CMD1 (joined arg):", cmd1)
        r1 = subprocess.run(cmd1, capture_output=True, text=True)
        print("r1.returncode =", r1.returncode)
        print("--- r1.stdout (first 2000 chars) ---")
        print(r1.stdout[:2000])
        print("--- r1.stderr (first 4000 chars) ---")
        print(r1.stderr[:4000])
        if r1.returncode != 0:
            print("\n--- Retrying with split args ---")
            cmd2 = [
                "mapshaper", annotated,
                "-simplify", "8%", "keep-shapes",
                "-o", out_path, "format=topojson", "quantization=5000",
            ]
            print("CMD2 (split args):", cmd2)
            r2 = subprocess.run(cmd2, capture_output=True, text=True)
            print("r2.returncode =", r2.returncode)
            print("--- r2.stdout (first 2000 chars) ---")
            print(r2.stdout[:2000])
            print("--- r2.stderr (first 4000 chars) ---")
            print(r2.stderr[:4000])
        return 0 if r1.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
