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

# Each entry: (osm_relation_id, name to write into properties.name).
# OSM relation IDs verified via Wikidata P402 / Overpass name search.
EXTRA_PROVINCES = [
    (42004,    "Valle d'Aosta / Vallée d'Aoste"),  # Wikidata Q1280, P402=42004
    # NOTE: Sud Sardegna (Q23498165, claimed P402=17135059) has no boundary
    # relation in OSM — verified via name search 2026-05-05. Coverage is
    # handled instead by re-fetching the 2 pre-2016 provinces below and
    # renaming them to "Sud Sardegna" via fix_sardegna_legacy_provinces.py.
    (19166661, "Gallura Nord-Est Sardegna"),       # ex-Olbia-Tempio (rename->Tàttari/Sassari)
    (19621461, "Ogliastra"),                        # ex-Ogliastra    (rename->Nuoro)
]

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]
USER_AGENT = "mxmap.it-extra-provinces/0.1 (+https://github.com/mxmap-it/mxmap.it)"


def overpass_query(rel_id: int, *, timeout: int = 90) -> dict:
    """Fetch full geometry of a single OSM relation, rotating mirrors on
    failure. Returns the parsed JSON response.

    Uses `out geom` so each member way comes with inline lat/lon coordinates
    on its `geometry` field — no need for separate node lookup. Simpler and
    more reliable than the `>;out skel qt;` recursion pattern."""
    q = f"""[out:json][timeout:{timeout}];
relation({rel_id});
out geom;"""
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
    """Convert an Overpass relation result (with `out geom` inline coords)
    into a minimal GeoJSON Feature with multipolygon geometry. Each way
    member has a `geometry` field of [{lat, lon}, ...] from `out geom`."""
    rel: dict | None = None
    for el in elements:
        if el.get("type") == "relation" and el.get("id") == rel_id:
            rel = el
            break
    if rel is None:
        # Fallback: use first relation in the result
        for el in elements:
            if el.get("type") == "relation":
                rel = el
                break
    if rel is None:
        raise RuntimeError(f"Relation {rel_id} not found in Overpass result "
                           f"(got {len(elements)} elements, types: "
                           f"{set(e.get('type') for e in elements)})")

    # Pull outer ring geometries directly from each member way's `geometry`.
    outer_lines: list[list[list[float]]] = []
    for member in rel.get("members", []):
        if member.get("type") != "way":
            continue
        if member.get("role") not in ("outer", "", None):
            continue
        geom = member.get("geometry") or []
        coords = [[pt["lon"], pt["lat"]] for pt in geom if "lat" in pt and "lon" in pt]
        if len(coords) >= 2:
            outer_lines.append(coords)

    if not outer_lines:
        raise RuntimeError(f"No outer ways resolved for relation {rel_id}")

    # Stitch lines into closed rings using bi-directional greedy match.
    # Tries to merge at BOTH ring[-1] AND ring[0]; when nothing connects,
    # close current ring and start a fresh one (multi-island handling).
    rings: list[list[list[float]]] = []
    remaining = [ln[:] for ln in outer_lines]
    while remaining:
        ring = remaining.pop(0)
        while ring[0] != ring[-1]:
            extended = False
            for i, ln in enumerate(remaining):
                if ln[0] == ring[-1]:
                    ring.extend(ln[1:]); remaining.pop(i); extended = True; break
                if ln[-1] == ring[-1]:
                    ring.extend(reversed(ln[:-1])); remaining.pop(i); extended = True; break
                if ln[-1] == ring[0]:
                    ring = ln + ring[1:]; remaining.pop(i); extended = True; break
                if ln[0] == ring[0]:
                    ring = list(reversed(ln)) + ring[1:]; remaining.pop(i); extended = True; break
            if not extended:
                break
        if ring[0] != ring[-1]:
            ring.append(ring[0])
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


def _quantize_ring(ring: list[list[float]], transform: dict) -> list[list[int]]:
    sx, sy = transform["scale"]
    tx, ty = transform["translate"]
    abs_pts = [[round((p[0] - tx) / sx), round((p[1] - ty) / sy)] for p in ring]
    out = [abs_pts[0][:]]
    for i in range(1, len(abs_pts)):
        out.append([abs_pts[i][0] - abs_pts[i-1][0],
                    abs_pts[i][1] - abs_pts[i-1][1]])
    return out


def topojson_inject_geometry(topo: dict, feature: dict) -> None:
    """Append a GeoJSON Feature into the first object's geometries list of
    an existing TopoJSON, encoded as proper TopoJSON arcs (quantized + delta-
    encoded if topo.transform is present). Inline `coordinates` is invalid
    TopoJSON and is silently dropped by topojson-client — using this format
    previously caused the injected provinces (Valle d'Aosta + Sud Sardegna)
    to be invisible on the map."""
    objs = topo.get("objects", {})
    if not objs:
        raise RuntimeError("topo has no objects")
    obj_name = next(iter(objs))
    geoms = objs[obj_name].setdefault("geometries", [])
    target_id = feature["id"]
    # Idempotent: drop any existing entry with this id (and any legacy
    # inline-coords variant that was buggy).
    geoms[:] = [g for g in geoms if g.get("id") != target_id]

    transform = topo.get("transform")
    arcs = topo.setdefault("arcs", [])

    geom_type = feature["geometry"]["type"]
    coords = feature["geometry"]["coordinates"]
    # Normalize to list-of-rings (Polygon: 1 polygon; MultiPolygon: many)
    if geom_type == "Polygon":
        polys = [coords]
    else:
        polys = coords
    # Each polygon is [outer_ring, hole_ring, ...]; here we only handle outer.
    poly_arcs = []
    for poly in polys:
        ring_arcs = []
        for ring in poly:
            arc = _quantize_ring(ring, transform) if transform else [p[:] for p in ring]
            arcs.append(arc)
            ring_arcs.append(len(arcs) - 1)
        poly_arcs.append([[idx] for idx in ring_arcs])

    if geom_type == "Polygon":
        new_geom = {
            "type": "Polygon",
            "id": target_id,
            "properties": feature["properties"],
            "arcs": poly_arcs[0],
        }
    else:
        new_geom = {
            "type": "MultiPolygon",
            "id": target_id,
            "properties": feature["properties"],
            "arcs": poly_arcs,
        }
    geoms.append(new_geom)


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
        try:
            feat = overpass_to_geojson(data["elements"], rel_id, name)
        except RuntimeError as e:
            print(f"  PARSE ERROR: {e}")
            continue
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
