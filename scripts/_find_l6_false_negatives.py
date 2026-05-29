#!/usr/bin/env python3
"""Trova VERI comuni filtrati erroneamente a IT-CONS-* dal filtro L6
positivo (nome che non inizia per 'Comune'). Identifica i casi da
aggiungere a L6_NAME_EXCEPTIONS."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
seed = json.load(open(ROOT / "data/municipalities_it.json", encoding="utf-8"))

# Veri comuni hanno codice_ipa nel pattern c_<catastale>
CATASTALE_RE = re.compile(r"^c_[a-z][a-z0-9]{3}$", re.IGNORECASE)

sus = []
for e in seed:
    if not e.get("id", "").startswith("IT-CONS-"):
        continue
    if (e.get("ipa_codice_categoria") or "").upper() != "L6":
        continue
    ipa = (e.get("ipa_codice_ipa") or "").lower()
    if CATASTALE_RE.match(ipa):
        sus.append(e)

print(f"VERI COMUNI filtrati erroneamente a IT-CONS-* (codice IPA c_<catastale>): {len(sus)}")
print()
for e in sus:
    name = (e.get("name") or "")[:60]
    ipa = e.get("ipa_codice_ipa") or ""
    istat = e.get("ipa_codice_comune_istat") or ""
    print(f"  ipa={ipa:<12} istat={istat:<8} name={name}")
