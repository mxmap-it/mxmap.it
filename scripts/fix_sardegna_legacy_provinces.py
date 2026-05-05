#!/usr/bin/env python3
"""Fix the 4 historical (pre-2016 reform) Sardinian province polygons in
topo/it_province.topo.json so the Province view doesn't show white blanks
in southern Sardegna.

Background: the 2016 Sardinian reform abolished 4 provinces:
  - Olbia-Tempio  -> merged into Sassari (ISTAT 090)
  - Ogliastra     -> merged into Nuoro   (ISTAT 091)
  - Medio Campidano  ┐
  - Carbonia-Iglesias┴-> merged into Sud Sardegna (ISTAT 092, no OSM polygon)

OSM still carries the old polygons under names "Gallura Nord-Est Sardegna",
"Ogliastra", "Medio Campidano", "Sulcis Iglesiente". Our IndicePA seed has
no comuni with the old ISTAT codes — they all use the post-reform codes.
Result: 4 white blanks where comuni-province aggregation has nothing to
match against.

Fix:
  1. DROP the 2 polygons whose territory is now fully covered by an
     existing modern province (Gallura -> Sassari, Ogliastra -> Nuoro).
  2. RENAME both Medio Campidano + Sulcis Iglesiente to "Sud Sardegna".
     The frontend's matchGroupFeature() looks up by exact `name` property,
     so both topo features render with the same group's style/color when
     the user is at Province view, effectively reconstructing the Sud
     Sardegna territory as a 2-piece colored area.

Idempotent — re-run safe (drop-then-rename based on current names).

Run after fetch_extra_it_provinces / strip_foreign in the topo build chain:
  uv run python3 scripts/fix_sardegna_legacy_provinces.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPO = ROOT / "topo" / "it_province.topo.json"

DROP_NAMES = {
    "Gallura Nord-Est Sardegna",  # now part of Sassari (090)
    "Ogliastra",                   # now part of Nuoro (091)
}

RENAME_TO_SUD_SARDEGNA = {
    "Medio Campidano",      # 092 part 1
    "Sulcis Iglesiente",    # 092 part 2
}


def main() -> int:
    if not TOPO.exists():
        print(f"FATAL: {TOPO} missing")
        return 1

    topo = json.loads(TOPO.read_text(encoding="utf-8"))
    obj_name = next(iter(topo.get("objects", {})))
    geoms = topo["objects"][obj_name].setdefault("geometries", [])

    kept = []
    dropped = []
    renamed = []
    for g in geoms:
        props = g.get("properties") or {}
        name = (props.get("name") or "").strip()
        if name in DROP_NAMES:
            dropped.append(name)
            continue
        if name in RENAME_TO_SUD_SARDEGNA:
            props["name"] = "Sud Sardegna"
            props["original_name"] = name  # keep for audit
            g["properties"] = props
            renamed.append(name)
        kept.append(g)

    topo["objects"][obj_name]["geometries"] = kept
    TOPO.write_text(json.dumps(topo, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")

    print(f"Province topo: dropped {len(dropped)}, renamed {len(renamed)}")
    for n in dropped:  print(f"  drop:   {n}")
    for n in renamed:  print(f"  rename: {n} -> Sud Sardegna")
    print(f"Total province features: {len(kept)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
