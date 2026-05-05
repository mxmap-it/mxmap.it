#!/usr/bin/env python3
"""Quick lookup helper: find OSM relation IDs by name+admin_level via Overpass."""
import json
import sys
import urllib.request

QUERY = """[out:json];
relation["name"~"Gallura Nord-Est|Ogliastra"]["admin_level"];
out tags;"""

req = urllib.request.Request("https://overpass-api.de/api/interpreter",
                              data=QUERY.encode("utf-8"),
                              headers={"User-Agent": "mxmap-find-osm"})
with urllib.request.urlopen(req, timeout=30) as r:
    d = json.loads(r.read().decode("utf-8"))

for el in d.get("elements", []):
    if el.get("type") != "relation":
        continue
    t = el.get("tags", {})
    rid = el["id"]
    name = t.get("name", "")
    al = t.get("admin_level", "")
    ty = t.get("type", "")
    print(f"  id={rid:>8}  admin_level={al:<4}  type={ty:<10}  name={name}")
