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

DROP_NAMES: set[str] = set()  # nothing dropped — every territory needs coverage

# Rename map: legacy name -> modern province name. Multiple legacy polygons
# can map to the same modern name; matchGroupFeature() takes the first match
# but all with that name get the same group's color, so the territories
# merge visually into one continuous district.
RENAME_MAP = {
    "Gallura Nord-Est Sardegna": "Tàttari/Sassari",  # 2016: Olbia-Tempio merged into Sassari (ISTAT 090)
    "Ogliastra":                  "Nuoro",            # 2016: Ogliastra merged into Nuoro (ISTAT 091)
    "Medio Campidano":            "Sud Sardegna",     # 2016: Medio Campidano merged into Sud Sardegna (092)
    "Sulcis Iglesiente":          "Sud Sardegna",     # 2016: Carbonia-Iglesias merged into Sud Sardegna (092)
}
# Back-compat: keep old name list for messaging
RENAME_TO_SUD_SARDEGNA = {k for k, v in RENAME_MAP.items() if v == "Sud Sardegna"}


def main() -> int:
    if not TOPO.exists():
        print(f"FATAL: {TOPO} missing")
        return 1

    topo = json.loads(TOPO.read_text(encoding="utf-8"))
    obj_name = next(iter(topo.get("objects", {})))
    geoms = topo["objects"][obj_name].setdefault("geometries", [])

    kept = []
    dropped: list[str] = []
    renamed: list[tuple[str, str]] = []
    for g in geoms:
        props = g.get("properties") or {}
        name = (props.get("name") or "").strip()
        if name in DROP_NAMES:
            dropped.append(name)
            continue
        if name in RENAME_MAP:
            new_name = RENAME_MAP[name]
            # If already renamed in a previous run (idempotency), skip messaging
            if (props.get("original_name") or name) != name or props.get("name") != new_name:
                pass
            props["name"] = new_name
            props["original_name"] = name  # for audit
            g["properties"] = props
            renamed.append((name, new_name))
        kept.append(g)

    topo["objects"][obj_name]["geometries"] = kept
    TOPO.write_text(json.dumps(topo, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")

    print(f"Province topo: dropped {len(dropped)}, renamed {len(renamed)}")
    for n in dropped:    print(f"  drop:   {n}")
    for old, new in renamed: print(f"  rename: {old} -> {new}")
    print(f"Total province features: {len(kept)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
