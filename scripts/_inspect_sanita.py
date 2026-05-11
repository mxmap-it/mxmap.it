#!/usr/bin/env python3
"""Survey of all health-sector PA enti in the seed (current 'sanita'
cluster + adjacent categories) — to plan the Sanità section visualization."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
seed = json.loads((ROOT / "data" / "municipalities_it.json").read_text(encoding="utf-8"))

# Step 1: well-known health categories
KNOWN_HEALTH = {
    "L7":  "ASL — Aziende Sanitarie Locali",
    "L8":  "Aziende Ospedaliere / Policlinici universitari",
    "L22": "IRCCS (Istituti di Ricovero e Cura a Carattere Scientifico)",
    "C12": "Istituti Zooprofilattici Sperimentali",
}

# Step 2: scan ALL categories for health keywords in their entities
HEALTH_KEYWORDS = re.compile(
    r"\b(sanit|ospedal|salute|ospedaliera|asl\b|ats\b|ares\b|arsan\b|"
    r"agenas|aifa|iss|farmac|croce\s+rossa|emergenza|118|cri\b|trasfusion|"
    r"zooprofilattic|policlinic|fondazione\s+irccs|asp\b|aress|"
    r"dipartimento\s+salute|asur|aspsalute|sanitaria)",
    re.IGNORECASE,
)

# Roll up by category
by_cat: dict = defaultdict(list)
for e in seed:
    cat = e.get("ipa_codice_categoria", "?")
    by_cat[cat].append(e)

print(f"=== KNOWN health categories ===\n")
total_known = 0
for code, label in KNOWN_HEALTH.items():
    enti = by_cat.get(code, [])
    n = len(enti)
    total_known += n
    print(f"  {code:<5} {label:<55} {n:>5}")

print(f"\n  TOTAL known: {total_known}\n")

# Step 3: discover health-named entities in OTHER categories
print(f"=== Health-named enti in OTHER categories (keyword-matched) ===\n")
extra_by_cat: dict = defaultdict(list)
for cat, enti in by_cat.items():
    if cat in KNOWN_HEALTH:
        continue
    for e in enti:
        name = (e.get("name") or "")
        if HEALTH_KEYWORDS.search(name):
            extra_by_cat[cat].append(name[:70])
total_extra = sum(len(v) for v in extra_by_cat.values())
for cat, names in sorted(extra_by_cat.items(), key=lambda kv: -len(kv[1]))[:10]:
    print(f"  {cat:<5} {len(names):>4}  examples:")
    for n in names[:3]:
        print(f"        - {n}")
print(f"\n  total extra (keyword-only, unknown cat): {total_extra}")

# Step 4: polygon-availability hint per category
print(f"\n=== Polygon-territorial-coverage feasibility ===\n")
table = [
    ("L7  ASL",
     "115",
     "Sì — territorio amministrativo definito (provincia o sub-provincia). "
     "OSM ha alcuni boundary=health relations ma coverage parziale; "
     "alternative: open-data regionali (Lombardia, Toscana, Emilia, Veneto)."),
    ("L8  Aziende Osped./Policlinici",
     "101",
     "No — sono SEDI singole (edifici). Markers su lat/lng (geocoding "
     "Nominatim sull'indirizzo IndicePA, simile alle scuole)."),
    ("L22 IRCCS",
     "9",
     "No — sedi singole di ricerca. Markers."),
    ("C12 Istituti Zooprofilattici",
     "10",
     "Misto: ogni istituto copre 1-2 regioni (territorio amministrativo) "
     "ma è un'unica sede. Render come Markers + label col territorio coperto."),
]
for code_label, n, feasibility in table:
    print(f"  {code_label:<32} ({n})\n    {feasibility}\n")

print("\n=== Proposta strutturata ===\n")
print("  Strato 1 (poligoni):  ASL — confini territoriali (admin_level=health)")
print("                         da fetchare via Overpass; fallback dissolve")
print("                         dei comuni se la relation OSM manca.")
print()
print("  Strato 2 (marker):    L8 + L22 + C12 — sedi geocodificate via")
print("                         Nominatim (riusa scripts/geocode_*.py).")
print("                         Marker colorato per provider, popup con")
print("                         dettaglio MX/SPF/DKIM (come Scuole + Comuni).")
print()
print("  Categoria estesa?     Includere anche enti health-keyword in")
print(f"                         altre categorie ({total_extra} candidati)?")
print(f"                         Da decidere con l'utente caso-per-caso.")
