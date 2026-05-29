#!/usr/bin/env python3
"""Verifica post-fix: UNCEM Lazio + statistica id prefix."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
seed = json.load(open(ROOT / "data/municipalities_it.json", encoding="utf-8"))

# UNCEM Lazio
for e in seed:
    if "uncem" in (e.get("name", "") or "").lower() and \
       "lazio" in (e.get("name", "") or "").lower():
        print("UNCEM Lazio post-fix:")
        for k in ("id", "ipa_codice_ipa", "ipa_codice_categoria",
                 "ipa_codice_comune_istat", "name", "domain"):
            print(f"  {k}: {e.get(k)}")
        break

print()
prefs = Counter(e.get("id", "")[:7] for e in seed)
print("Distribuzione id prefix (top 10):")
for p, n in prefs.most_common(10):
    print(f"  {p:<10} {n}")
print(f"\nTotale seed: {len(seed)}")

# Esempi enti riassegnati IT-COM-* → IT-CONS-*
print()
print("Esempi di enti riassegnati (IT-CONS-) ex-falsi-comuni:")
ex = [e for e in seed if e.get("id", "").startswith("IT-CONS-")
      and (e.get("ipa_codice_categoria") or "").upper() == "L6"]
print(f"Totale L6 riassegnati a IT-CONS-: {len(ex)}")
for e in ex[:15]:
    print(f"  {e['id']:<26}  {(e.get('name') or '')[:60]}")
