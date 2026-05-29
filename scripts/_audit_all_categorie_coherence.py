#!/usr/bin/env python3
"""Audit completo della coerenza categoria↔nome per TUTTE le categorie
IndicePA presenti nel seed.

Per ogni categoria documentata, valuta quanti enti hanno un nome che
NON corrisponde al pattern atteso (= anomalia categoria IndicePA simile
al bug UNCEM Lazio).

Anche se queste anomalie non causano collisioni di id come UNCEM (perché
le categorie non-territoriali non usano codice_comune_ISTAT come chiave),
sono comunque indicatori di qualità del dato IndicePA e potenziali bug
futuri.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
seed = json.load(open(ROOT / "data/municipalities_it.json", encoding="utf-8"))

# Pattern positivi attesi per categoria.
# Source: codici IndicePA + verifica manuale denominazioni ufficiali.
CATEGORIA_NAME_RE = {
    # === Territoriali ===
    "L4":  re.compile(r"^\s*(regione\b|provincia\s+autonoma\s+(di|del)\b)", re.IGNORECASE),
    "L5":  re.compile(r"^\s*(provincia\b|libero\s+consorzio\s+comunale\b)", re.IGNORECASE),
    "L45": re.compile(r"^\s*citt[aà]'?\s+metropolitana\b", re.IGNORECASE),
    "L6":  re.compile(r"^\s*comune\b", re.IGNORECASE),
    # === Non-territoriali con name pattern atteso ===
    "C1":  re.compile(r"^\s*(ministero|presidenza\s+del\s+consiglio|avvocatura)", re.IGNORECASE),
    "C13": re.compile(r"^\s*(automobile\s+club|aci)\b", re.IGNORECASE),
    # Per L33 scuole il pattern è eterogeneo (istituto/liceo/circolo/cpia/...)
    "L33": re.compile(r"^\s*(istituto|liceo|circolo|cpia|centro|scuola|polo|convitto|isi|aut)", re.IGNORECASE),
    # === Categorie con pattern NON deterministico — skip ===
    # C3 = Agenzie nazionali (Forestale, Demanio, ANPAL, ecc. — vari)
    # C7 = Enti di Assistenza
    # C8 = Stipendi
    # C10 = Agenzie fiscali
    # C11 = Forze ordine
    # C12 = IZS
    # C14 = Ordini professionali (tantissimi pattern)
    # L1 = Università/AFAM
    # L7-L8 = ASL/ospedali
    # L17 = AFAM/Università
    # L18 = Unioni di comuni
    # L34 = Comunità montane
    # L35 = Camere commercio
    # L36 = Enti parco
    # L37 = Aziende speciali comunali
    # L38 = Aziende sanitarie speciali
    # L42 = ATER edilizia
    # L43 = AFAM
    # L44 = ATO rifiuti
    # L47 = Commissari straordinari
}

# Conteggio per categoria
by_cat = defaultdict(list)
for e in seed:
    cat = (e.get("ipa_codice_categoria") or "").upper()
    by_cat[cat].append(e)

print(f"Totale seed: {len(seed)}")
print(f"Categorie distinte: {len(by_cat)}")
print()
print(f"{'cat':<6}{'totale':>8}  {'pattern atteso':<55}{'anomalie':>10}")
print("-" * 90)

for cat in sorted(by_cat, key=lambda c: -len(by_cat[c])):
    enti = by_cat[cat]
    n = len(enti)
    pattern = CATEGORIA_NAME_RE.get(cat)
    if pattern is None:
        print(f"{cat:<6}{n:>8}  (no pattern definito)                                          —")
        continue
    anomalies = [e for e in enti if not pattern.match(e.get("name") or "")]
    print(f"{cat:<6}{n:>8}  {pattern.pattern[:53]:<55}{len(anomalies):>10}")
    if anomalies and cat in ("L4", "L5", "L45", "C1", "C13"):
        for e in anomalies[:5]:
            name = (e.get("name") or "")[:60]
            ipa = e.get("ipa_codice_ipa") or ""
            print(f"        - ipa={ipa:<14}  {name}")
        if len(anomalies) > 5:
            print(f"        ... +{len(anomalies)-5} altri")
