#!/usr/bin/env python3
"""Check: quanti L6 NON inizierebbero con regex 'Comune di/del/della/...'"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
seed = json.load(open(ROOT / "data/municipalities_it.json", encoding="utf-8"))
l6 = [e for e in seed if (e.get("ipa_codice_categoria") or "").upper() == "L6"]

# Positive regex per veri comuni
COMUNE_RE = re.compile(
    r"^\s*comune\s+(di|del|della|degli|delle|dei|dell['']|d['']).*",
    re.IGNORECASE
)

print(f"Totale L6: {len(l6)}")
not_comune = [e for e in l6 if not COMUNE_RE.match(e.get("name") or "")]
print(f"L6 che NON matchano 'Comune di/del/della/...': {len(not_comune)}")
print()
print("--- Anomalie da catturare con il filtro stretto ---")
for e in not_comune[:50]:
    name = (e.get("name") or "")[:65]
    ipa = e.get("ipa_codice_ipa") or ""
    istat = e.get("ipa_codice_comune_istat") or ""
    print(f"  ipa={ipa:<14}  istat={istat:<8}  name={name}")
print(f"\n... +{max(0,len(not_comune)-50)} altri (tot {len(not_comune)})")
