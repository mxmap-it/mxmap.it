#!/usr/bin/env python3
"""Debug helper: inspect why a specific OSM relation fails to stitch
into closed rings. Pass the relation ID as argv[1]. Used to diagnose
the residual PARSE FAIL cases in fetch_missing_comuni_polygons.py."""
from __future__ import annotations
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_missing_comuni_polygons import overpass_to_polygon, stitch_rings  # noqa


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: _debug_polygon.py <relation_id>")
        return 1
    rel_id = int(sys.argv[1])
    mirrors = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.osm.ch/api/interpreter",
        "https://overpass.openstreetmap.fr/api/interpreter",
    ]
    q = f"[out:json];relation({rel_id});out geom;".encode("utf-8")
    d = None
    for m in mirrors:
        try:
            req = urllib.request.Request(m, data=q,
                                         headers={"User-Agent": "mxmap-debug",
                                                  "Content-Type": "text/plain"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8"))
            break
        except Exception as e:
            print(f"  mirror {m}: {e!r}")
    if d is None:
        print("all mirrors failed")
        return 1
    els = d.get("elements", [])
    print(f"elements: {len(els)}")
    for el in els:
        if el.get("type") != "relation":
            continue
        outer = []
        for m in el.get("members", []):
            if m.get("type") == "way" and m.get("role") in ("outer", "", None):
                geom = m.get("geometry") or []
                pts = [[p["lon"], p["lat"]] for p in geom if "lat" in p]
                if pts:
                    outer.append(pts)
        print(f"outer ways: {len(outer)}")
        for i, w in enumerate(outer):
            print(f"  way{i}: {len(w)} pts, start={w[0]}, end={w[-1]}")

        rings = stitch_rings(outer)
        print(f"stitched rings: {len(rings)}")
        for i, r in enumerate(rings):
            closed = r[0] == r[-1]
            print(f"  ring{i}: {len(r)} pts, closed={closed}")

    result = overpass_to_polygon(d.get("elements", []), rel_id, "debug")
    if result is None:
        print("overpass_to_polygon -> None (PARSE FAIL)")
    else:
        print(f"overpass_to_polygon -> {result.get('type')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
