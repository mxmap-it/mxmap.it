#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
seed = json.loads((ROOT / "data" / "municipalities_it.json").read_text(encoding="utf-8"))

ISTR = {
    "L33": "Scuole statali",
    "L17": "Università pubbliche",
    "L43": "Istituzioni AFAM",
    "L15": "Diritto allo studio universitario",
    "L28": "Consorzi interuniversitari di ricerca",
}

istr_enti = [e for e in seed if e.get("ipa_codice_categoria") in ISTR]
print(f"=== Cluster ISTRUZIONE: {len(istr_enti)} enti totali ===")
print()
for cat, label in ISTR.items():
    enti = [e for e in seed if e.get("ipa_codice_categoria") == cat]
    with_istat = sum(1 for e in enti if e.get("ipa_codice_comune_istat"))
    print(f"  {cat:<5} {label:<42} {len(enti):>5}  con ISTAT comune: {with_istat}")

# Schools choropleth
istr_data = json.loads((ROOT / "data" / "it_istruzione_by_comune.json").read_text(encoding="utf-8"))
total_schools = istr_data["total_schools"]
comuni_with = istr_data["comuni_with_schools"]
print()
print(f"Schools choropleth: {total_schools} scuole aggregate su {comuni_with} comuni")
print()

# Polygon coverage
topo = json.loads((ROOT / "topo" / "it_municipality.topo.json").read_text(encoding="utf-8"))
muni_osm: set = set()
for o in topo.get("objects", {}).values():
    for f in o.get("geometries", []):
        fid = f.get("id", "")
        if isinstance(fid, str) and fid.startswith("relation/"):
            try:
                muni_osm.add(int(fid.split("/", 1)[1]))
            except ValueError:
                pass

istat_to_osm: dict = {}
for e in seed:
    if e.get("ipa_codice_categoria") == "L6":
        i = e.get("ipa_codice_comune_istat")
        if i and e.get("osm_relation_id"):
            istat_to_osm[str(i).zfill(6)] = e.get("osm_relation_id")

matched = 0
unmatched = 0
no_istat = 0
istat_no_osm = 0
for e in istr_enti:
    i = e.get("ipa_codice_comune_istat")
    if not i:
        no_istat += 1
        unmatched += 1
        continue
    osm = istat_to_osm.get(str(i).zfill(6))
    if osm and osm in muni_osm:
        matched += 1
    else:
        istat_no_osm += 1
        unmatched += 1

print(f"Polygon coverage (via host comune): {matched}/{len(istr_enti)} matched ({matched/len(istr_enti)*100:.1f}%)")
print(f"  - mancano per: {no_istat} senza ISTAT comune, {istat_no_osm} ISTAT senza polygon")

print()
print("=== Conclusione ===")
print(f"Polygon dedicati per i singoli enti istruzione: NESSUNO (le scuole sono punti, non poligoni)")
print(f"Polygon comune-aggregato (host comune del singolo ente): {matched}/{len(istr_enti)}")
