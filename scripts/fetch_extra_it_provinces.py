#!/usr/bin/env python3
"""Fetch extra Italian province polygons that are missing from the standard
admin_level=6 Overpass result for area["ISO3166-1"="IT"].

Two known cases:

1. **Valle d'Aosta / Vallée d'Aoste** — single-province autonomous region.
   In OSM it exists only at admin_level=4 (relation 35394). For mxmap.it
   province-choropleth we copy that polygon into it_province.topo.json with
   name "Valle d'Aosta / Vallée d'Aoste" so comuni VdA (ISTAT 007*) have a
   province-level polygon to color.

2. **Provincia del Sud Sardegna** — created by the 2016 Sardinian reform
   (merger of Carbonia-Iglesias, Medio Campidano, Cagliari periphery).
   OSM relation 8829893. The standard L6 Overpass query sometimes misses
   it because of admin_level tagging inconsistencies.

This script:
  - Fetches the two relations from Overpass (with mirror rotation/backoff)
  - Converts each to GeoJSON (Python in-process, no osmtogeojson npm dep)
  - Merges them into topo/it_province.topo.json as additional features
  - Writes the updated topo back

Reproducible: idempotent — re-running just refreshes the polygons.

Usage:
  uv run python3 scripts/fetch_extra_it_provinces.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPO_PROVINCE = ROOT / "topo" / "it_province.topo.json"

# Each entry: (osm_relation_id, name to write into properties.name)
EXTRA_PROVINCES = [
    (35394,   "Valle d'Aosta / Vallée d'Aoste"),
    (8829893, "Sud Sardegna"),
]

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]
USER_AGENT = "mxmap.it-extra-provinces/0.1 (+https://github.com/fpietrosanti/mxmap.it)"


def overpass_query(rel_id: int, *, timeout: int = 90) -> dict:
    """Fetch full geometry of a single OSM relation, rotating mirrors on
    failure. Returns the parsed JSON response."""
    q = f"""[out:json][timeout:{timeout}];
relation({rel_id});
out body;
>;
out skel qt;"""
    last_err: Exception | None = None
    for url in OVERPASS_MIRRORS:
        try:
            data = q.encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"User-Agent": USER_AGENT, "Content-Type": "text/plain"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8")
            return json.loads(body)
        except Exception as e:
            last_err = e
            print(f"  mirror {url} failed: {e!r}; trying next…")
            time.sleep(5)
    raise RuntimeError(f"All Overpass mirrors failed for relation {rel_id}: {last_err}")


def overpass_to_geojson(elements: list[dict], rel_id: int, name: str) -> dict:
    """Convert an Overpass relation result (relation + ways + nodes) into a
    minimal GeoJSON Feature with multipolygon geometry. Only handles the
    outer/inner ring case, sufficient for admin boundary relations."""
    nodes_by_id: dict[int, tuple[float, float]] = {}
    ways_by_id: dict[int, list[int]] = {}
    rel: dict | None = None
    for el in elements:
        if el["type"] == "node":
            nodes_by_id[el["id"]] = (el["lon"], el["lat"])
        elif el["type"] == "way":
            ways_by_id[el["id"]] = el.get("nodes", [])
        elif el["type"] == "relation" and el["id"] == rel_id:
            rel = el
    if rel is None:
        raise RuntimeError(f"Relation {rel_id} not found in Overpass result")

    # Build outer rings by stitching way geometries together (best-effort).
    # For simplicity we keep each outer way as its own LineString and let
    # mapshaper post-process into clean polygons during topo merge.
    outer_lines: list[list[list[float]]] = []
    for member in rel.get("members", []):
        if member.get("type") != "way":
            continue
        if member.get("role") not in ("outer", "", None):
            continue
        coords = []
        for nid in ways_by_id.get(member["ref"], []):
            ll = nodes_by_id.get(nid)
            if ll:
                coords.append(list(ll))
        if len(coords) >= 2:
            outer_lines.append(coords)

    if not outer_lines:
        raise RuntimeError(f"No outer ways resolved for relation {rel_id}")

    # Stitch lines into closed rings (greedy join by endpoint match).
    rings: list[list[list[float]]] = []
    remaining = outer_lines[:]
    while remaining:
        ring = remaining.pop(0)[:]
        progress = True
        while progress and ring[0] != ring[-1]:
            progress = False
            for i, ln in enumerate(remaining):
                if ln[0] == ring[-1]:
                    ring.extend(ln[1:]); remaining.pop(i); progress = True; break
                if ln[-1] == ring[-1]:
                    ring.extend(list(reversed(ln))[1:]); remaining.pop(i); progress = True; break
                if ln[-1] == ring[0]:
                    ring = ln[:-1] + ring; remaining.pop(i); progress = True; break
                if ln[0] == ring[0]:
                    ring = list(reversed(ln))[:-1] + ring; remaining.pop(i); progress = True; break
        if ring[0] != ring[-1]:
            ring.append(ring[0])  # force-close
        rings.append(ring)

    return {
        "type": "Feature",
        "id": f"relation/{rel_id}",
        "properties": {
            "name": name,
            "country": "IT",
            "ISO3166-1": "IT",
            "osm_id": rel_id,
            "admin_level": 6,
        },
        "geometry": {
            "type": "MultiPolygon" if len(rings) > 1 else "Polygon",
            "coordinates": (
                [[ring] for ring in rings] if len(rings) > 1 else [rings[0]]
            ),
        },
    }


def topojson_inject_geometry(topo: dict, feature: dict) -> None:
    """Append a GeoJSON Feature into the first object's geometries list of an
    existing TopoJSON. NOTE: this writes raw lat/lng coordinates rather than
    quantized arcs, which is non-canonical TopoJSON but works because Leaflet
    consumes the geometries via topojson-client's `feature()` which handles
    both arcs and inline coordinates. For full correctness re-run mapshaper
    on the merged topo, but for 2 extra polygons this is acceptable."""
    objs = topo.get("objects", {})
    if not objs:
        raise RuntimeError("topo has no objects")
    obj_name = next(iter(objs))
    geoms = objs[obj_name].setdefault("geometries", [])
    # Skip if already present (idempotent re-run)
    target_id = feature["id"]
    geoms[:] = [g for g in geoms if g.get("id") != target_id]
    # Inject as an inline-coords geometry. TopoJSON spec allows "coordinates"
    # on Polygon/MultiPolygon geometries even outside arcs.
    geoms.append({
        "type": feature["geometry"]["type"],
        "id": target_id,
        "properties": feature["properties"],
        "coordinates": feature["geometry"]["coordinates"],
    })


def main() -> int:
    if not TOPO_PROVINCE.exists():
        print(f"FATAL: {TOPO_PROVINCE} not found. Run fetch_it_boundaries.py first.")
        return 1

    print(f"Loading existing topo: {TOPO_PROVINCE}")
    topo = json.loads(TOPO_PROVINCE.read_text(encoding="utf-8"))
    print(f"  current geometries: "
          f"{sum(len(o.get('geometries',[])) for o in topo.get('objects',{}).values())}")

    for rel_id, name in EXTRA_PROVINCES:
        print(f"\nFetching relation {rel_id} ({name})…")
        try:
            data = overpass_query(rel_id)
        except RuntimeError as e:
            print(f"  ERROR: {e}")
            continue
        feat = overpass_to_geojson(data["elements"], rel_id, name)
        print(f"  geometry: {feat['geometry']['type']} "
              f"with {sum(len(p) for p in feat['geometry']['coordinates'])} ring points")
        topojson_inject_geometry(topo, feat)
        print(f"  injected into topo")
        time.sleep(2)

    new_total = sum(len(o.get("geometries",[])) for o in topo.get("objects",{}).values())
    print(f"\nNew geometries total: {new_total}")
    TOPO_PROVINCE.write_text(json.dumps(topo, ensure_ascii=False, separators=(",", ":")),
                             encoding="utf-8")
    print(f"Wrote {TOPO_PROVINCE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
