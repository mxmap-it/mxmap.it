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
USER_AGENT = "mxmap.it-missing-comuni/0.1 (+https://github.com/fpietrosanti/mxmap.it)"


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


def overpass_to_polygon(elements: list[dict], rel_id: int, name: str) -> dict | None:
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
    # Close any open lines + assemble naive polygon
    rings = []
    remaining = outer_lines[:]
    while remaining:
        ring = remaining.pop(0)[:]
        progress = True
        while progress and ring[0] != ring[-1] and remaining:
            progress = False
            for i, ln in enumerate(remaining):
                if ln[0] == ring[-1]:
                    ring.extend(ln[1:]); remaining.pop(i); progress = True; break
                if ln[-1] == ring[-1]:
                    ring.extend(list(reversed(ln))[1:]); remaining.pop(i); progress = True; break
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        rings.append(ring)
    return {
        "type": "MultiPolygon" if len(rings) > 1 else "Polygon",
        "id": f"relation/{rel_id}",
        "properties": {"name": name, "country": "IT", "osm_id": rel_id},
        "coordinates": [[ring] for ring in rings] if len(rings) > 1 else [rings[0]],
    }


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

    # Collect existing osm_ids in topo
    obj_name = next(iter(topo.get("objects", {})))
    geoms = topo["objects"][obj_name].setdefault("geometries", [])
    existing_osm = set()
    for g in geoms:
        gid = g.get("id", "")
        if isinstance(gid, str) and gid.startswith("relation/"):
            try:
                existing_osm.add(int(gid.split("/", 1)[1]))
            except ValueError:
                pass
    print(f"  topo has {len(existing_osm)} relation features (out of {len(geoms)} total)")

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
        feat = overpass_to_polygon(data.get("elements", []), rel_id, name)
        if not feat:
            print("PARSE FAIL")
            failed += 1
            continue
        geoms.append(feat)
        existing_osm.add(rel_id)
        fetched += 1
        print(f"OK ({feat['type']})")
        # Periodic checkpoint write — protects against process kill mid-run
        if i % 20 == 0:
            TOPO.write_text(json.dumps(topo, ensure_ascii=False, separators=(",", ":")),
                            encoding="utf-8")
        time.sleep(1.2)  # be polite to Overpass

    TOPO.write_text(json.dumps(topo, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    print()
    print(f"Done. Fetched={fetched}, failed={failed}")
    print(f"Topo now has {len(existing_osm)} relation features.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
