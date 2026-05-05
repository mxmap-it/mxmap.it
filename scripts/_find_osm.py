#!/usr/bin/env python3
"""Quick lookup helper: find OSM relation IDs by name."""
import json
import sys
import urllib.request

NAME_REGEX = sys.argv[1] if len(sys.argv) > 1 else "Sud Sardegna|Sud Sardigna"

q = (f'[out:json];relation["name"~"{NAME_REGEX}"]["admin_level"];out tags;')

req = urllib.request.Request("https://overpass-api.de/api/interpreter",
                              data=q.encode("utf-8"),
                              headers={"User-Agent": "mxmap-find-osm"})
with urllib.request.urlopen(req, timeout=30) as r:
    d = json.loads(r.read().decode("utf-8"))

els = d.get("elements", [])
print(f"found: {len(els)} matching {NAME_REGEX!r}")
for el in els:
    if el.get("type") != "relation":
        continue
    t = el.get("tags", {})
    rid = el["id"]
    name = t.get("name", "")
    al = t.get("admin_level", "")
    ty = t.get("type", "")
    print(f"  id={rid:>10}  admin_level={al:<4}  type={ty:<12}  name={name}")
