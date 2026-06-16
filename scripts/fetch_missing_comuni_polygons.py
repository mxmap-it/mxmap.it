#!/usr/bin/env python3
"""Fetch comuni polygons that are present in the seed but missing from
topo/it_municipality.topo.json.

Symptom: white/uncolored polygons on the map, particularly in southern
Sardegna (provinces 091 Nuoro + 111 Cagliari) and isolated cases like
Veroli (FR). Per-province Overpass batching in fetch_it_boundaries.py
silently drops some relations when a chunk fails or when the Overpass
mirror returns partial results.

This script:
  1. Walks data/municipalities_it.json — collects all L6 entries with
     osm_relation_id set.
  2. Walks topo/it_municipality.topo.json — collects all relation/<id>
     features already present.
  3. For each missing osm_id (in seed but not in topo), fetches the
     relation from Overpass with `out geom` (rotated mirrors, retries)
     and injects a Polygon/MultiPolygon feature into the topo.
  4. Writes the topo back. Idempotent — re-run safe.

Reproducible: any future re-fetch from scratch can include this step
in scripts/server_autorun_full_pipeline.sh after fetch_it_boundaries.py.

Usage:
  uv run python3 scripts/fetch_missing_comuni_polygons.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPO = ROOT / "topo" / "it_municipality.topo.json"
SEED = ROOT / "data" / "municipalities_it.json"

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]
USER_AGENT = "mxmap.it-missing-comuni/0.1 (+https://github.com/mxmap-it/mxmap.it)"


def overpass_query(rel_id: int, *, timeout: int = 30) -> dict | None:
    q = f"[out:json][timeout:{timeout}];relation({rel_id});out geom;".encode("utf-8")
    last_err: Exception | None = None
    for url in OVERPASS_MIRRORS:
        try:
            req = urllib.request.Request(url, data=q,
                                         headers={"User-Agent": USER_AGENT,
                                                  "Content-Type": "text/plain"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            time.sleep(2)
    print(f"    all mirrors failed for relation {rel_id}: {last_err}")
    return None


def stitch_rings(lines: list[list[list[float]]]) -> list[list[list[float]]]:
    """Stitch unordered way segments into closed rings.

    Each input is an open polyline [[lon,lat], ...]. Endpoints from the same
    Overpass response are byte-identical, so plain == on point lists is
    reliable. We greedily merge segments at either end of the current ring
    (4 directions), then start a new ring when no segment connects.

    Improvements over the naive version: tries to extend at BOTH ring[0] AND
    ring[-1] (4 cases instead of 2), correctly handling complex multi-island
    boundaries (Aosta, Sauris, Sardegna 2016 splits, Friuli bilingual comuni).
    """
    rings: list[list[list[float]]] = []
    remaining = [ln[:] for ln in lines]
    while remaining:
        ring = remaining.pop(0)
        while ring[0] != ring[-1]:
            extended = False
            for i, ln in enumerate(remaining):
                # extend forward (append at end)
                if ln[0] == ring[-1]:
                    ring.extend(ln[1:]); remaining.pop(i); extended = True; break
                if ln[-1] == ring[-1]:
                    ring.extend(reversed(ln[:-1])); remaining.pop(i); extended = True; break
                # extend backward (prepend at start)
                if ln[-1] == ring[0]:
                    ring = ln + ring[1:]; remaining.pop(i); extended = True; break
                if ln[0] == ring[0]:
                    ring = list(reversed(ln)) + ring[1:]; remaining.pop(i); extended = True; break
            if not extended:
                break  # disjoint piece; force-close + start new ring
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        rings.append(ring)
    return rings


def overpass_to_rings(elements: list[dict], rel_id: int) -> list[list[list[float]]] | None:
    """Pull raw outer rings (each [[lon,lat],...]) from an Overpass relation."""
    rel = next((e for e in elements
                if e.get("type") == "relation" and e.get("id") == rel_id), None)
    if rel is None:
        return None
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
        return None
    rings = stitch_rings(outer_lines)
    return rings or None


def quantize_ring(ring: list[list[float]], transform: dict) -> list[list[int]]:
    """Convert raw [lon,lat] ring to TopoJSON quantized + delta-encoded arc.

    TopoJSON spec: each arc is a sequence of [x, y] pairs where the first
    pair is absolute (in quantized integer space), and subsequent pairs are
    delta-encoded relative to the previous pair. Quantization uses the
    topology's transform: x_q = round((lon - translate[0]) / scale[0]).
    """
    sx, sy = transform["scale"]
    tx, ty = transform["translate"]
    abs_pts = [[round((p[0] - tx) / sx), round((p[1] - ty) / sy)] for p in ring]
    out = [abs_pts[0][:]]
    for i in range(1, len(abs_pts)):
        out.append([abs_pts[i][0] - abs_pts[i-1][0],
                    abs_pts[i][1] - abs_pts[i-1][1]])
    return out


def append_polygon_to_topo(topo: dict, rel_id: int, name: str,
                            rings: list[list[list[float]]]) -> None:
    """Inject a Polygon/MultiPolygon feature into the first object's geometries
    list, encoded as TopoJSON arcs (quantized + delta-encoded) so topojson-client
    renders it correctly. Mixing inline `coordinates` with arc-based geometries
    in the same topology breaks rendering."""
    transform = topo.get("transform")
    arcs = topo.setdefault("arcs", [])
    obj_name = next(iter(topo.get("objects", {})))
    geoms = topo["objects"][obj_name].setdefault("geometries", [])

    geom_arcs: list[list[int]] = []  # one entry per ring, each = list of arc indexes
    for ring in rings:
        if transform:
            arc = quantize_ring(ring, transform)
        else:
            arc = [p[:] for p in ring]  # raw coords (no transform)
        arcs.append(arc)
        geom_arcs.append([len(arcs) - 1])

    if len(rings) > 1:
        geom = {
            "type": "MultiPolygon",
            "id": f"relation/{rel_id}",
            "properties": {"name": name, "country": "IT", "osm_id": rel_id},
            "arcs": [[ga] for ga in geom_arcs],  # MultiPolygon: list of polygons, each = list of rings
        }
    else:
        geom = {
            "type": "Polygon",
            "id": f"relation/{rel_id}",
            "properties": {"name": name, "country": "IT", "osm_id": rel_id},
            "arcs": geom_arcs,  # Polygon: list of rings
        }
    geoms.append(geom)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if not TOPO.exists() or not SEED.exists():
        print("FATAL: topo or seed missing")
        return 1

    print(f"Loading seed and topo…")
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    topo = json.loads(TOPO.read_text(encoding="utf-8"))

    # Collect existing osm_ids in topo. ALSO purge any features that use the
    # invalid inline `coordinates` schema (legacy bug — TopoJSON requires
    # `arcs`, the inline form is silently dropped by topojson-client and
    # invisible on the map). They get re-fetched below in the proper
    # quantized-arcs format.
    obj_name = next(iter(topo.get("objects", {})))
    geoms = topo["objects"][obj_name].setdefault("geometries", [])
    existing_osm: set[int] = set()
    purged = 0
    valid_geoms: list[dict] = []
    for g in geoms:
        gid = g.get("id", "")
        # Drop legacy inline-coordinates features
        if "coordinates" in g and "arcs" not in g:
            purged += 1
            continue
        valid_geoms.append(g)
        if isinstance(gid, str) and gid.startswith("relation/"):
            try:
                existing_osm.add(int(gid.split("/", 1)[1]))
            except ValueError:
                pass
    if purged:
        topo["objects"][obj_name]["geometries"] = valid_geoms
        geoms = valid_geoms
        print(f"  PURGED {purged} legacy inline-coordinate features (will re-fetch as arcs)")
    print(f"  topo has {len(existing_osm)} valid relation features (out of {len(geoms)} total)")

    # Collect needed osm_ids from seed
    needed: list[tuple[int, str]] = []
    for e in seed:
        if e.get("ipa_codice_categoria") != "L6":
            continue
        osm = e.get("osm_relation_id")
        if not osm:
            continue
        try:
            osm_int = int(osm)
        except (TypeError, ValueError):
            continue
        if osm_int in existing_osm:
            continue
        name = (e.get("name") or "").strip()
        for prefix in ("Comune di ", "Comune del ", "Comune della ",
                       "Comune dell'", "Comune dei "):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        needed.append((osm_int, name))

    print(f"  comuni in seed missing from topo: {len(needed)}")
    if args.limit:
        needed = needed[: args.limit]
    if not needed:
        print("  nothing to fetch — topo is complete.")
        return 0

    fetched = 0
    failed = 0
    for i, (rel_id, name) in enumerate(needed, 1):
        print(f"  [{i:>3}/{len(needed)}] relation/{rel_id}  {name[:42]:<42} …", end=" ", flush=True)
        data = overpass_query(rel_id)
        if not data:
            print("FETCH FAIL")
            failed += 1
            continue
        rings = overpass_to_rings(data.get("elements", []), rel_id)
        if not rings:
            print("PARSE FAIL")
            failed += 1
            continue
        append_polygon_to_topo(topo, rel_id, name, rings)
        existing_osm.add(rel_id)
        fetched += 1
        kind = "MultiPolygon" if len(rings) > 1 else "Polygon"
        print(f"OK ({kind}, {len(rings)} ring{'s' if len(rings)>1 else ''})")
        if i % 20 == 0:
            TOPO.write_text(json.dumps(topo, ensure_ascii=False, separators=(",", ":")),
                            encoding="utf-8")
        time.sleep(1.2)

    TOPO.write_text(json.dumps(topo, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    print()
    print(f"Done. Fetched={fetched}, failed={failed}")
    print(f"Topo now has {len(existing_osm)} relation features.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
