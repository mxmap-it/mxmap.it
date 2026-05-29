#!/usr/bin/env python3
"""Audit: enti categorizzati L6 (Comune) in IndicePA ma il cui ipa_codice_ipa
NON è un codice comunale (c_XXXX o codice ISTAT comune valido).

Questi sono FALSI COMUNI: enti che IndicePA ha mal-categorizzato come L6
ma che sono in realtà associazioni/delegazioni/consorzi. Esempio reale:
UNCEM Delegazione Regionale del Lazio, registrato come L6 con codice
ISTAT 058091 (= Roma Capitale) — collisione di id con il vero Comune di
Roma + poligono Roma riusato erroneamente."""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
seed = json.load(open(ROOT / "data/municipalities_it.json", encoding="utf-8"))

# 1. Collisioni istat
istat_to_enti = defaultdict(list)
for e in seed:
    istat = e.get("ipa_codice_comune_istat")
    if istat:
        istat_to_enti[istat].append(e)

print("=" * 80)
print("COLLISIONI di ipa_codice_comune_istat (più enti con stesso ISTAT comune)")
print("=" * 80)
collisions = {k: v for k, v in istat_to_enti.items() if len(v) > 1}
print(f"Codici ISTAT con >1 ente: {len(collisions)}")
for istat, enti in sorted(collisions.items(), key=lambda x: -len(x[1]))[:30]:
    print(f"\n  ISTAT {istat} → {len(enti)} enti:")
    for e in enti:
        print(f"    id={e['id']:<24}  cat={e.get('ipa_codice_categoria'):<5}  "
              f"ipa={(e.get('ipa_codice_ipa') or ''):<14}  name={e['name'][:50]}")

# 2. L6 con ipa_codice_ipa NON c_*
print()
print("=" * 80)
print("ENTI categorizzati L6 ma con ipa_codice_ipa NON c_XXXX (sospetti)")
print("=" * 80)
# Comuni veri hanno ipa_codice_ipa che inizia con "c_" seguito da codice catastale
# (es. c_a662 = Bari, c_f205 = Milano, c_h501 = Roma)
sus = [e for e in seed
       if (e.get("ipa_codice_categoria") or "").upper() == "L6"
       and not (e.get("ipa_codice_ipa") or "").lower().startswith("c_")]
print(f"Totale: {len(sus)}\n")
for e in sus[:50]:
    print(f"  ipa={(e.get('ipa_codice_ipa') or ''):<14}  istat={(e.get('ipa_codice_comune_istat') or '?'):<8}  name={e['name'][:55]}")
print(f"\n... +{max(0,len(sus)-50)} altri (totale {len(sus)})")
