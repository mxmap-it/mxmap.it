#!/usr/bin/env python3
"""Tabella di tutti gli enti UNKNOWN che hanno SIA un Sito_istituzionale
nel seed SIA almeno un domain_fallback (mail non-PEC IndicePA).

Per ciascun fallback, mostra anche la motivazione di rigetto del validatore
(rule passa/fallisce), per capire se il caso richiede una nuova regola o
un override manuale.

Scrive CSV completo in data/reports/unknown_with_fallback.csv + stampa
i primi 80 a stdout.
"""
from __future__ import annotations
import csv, json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))
from mail_sovereignty.scrape_validator import is_legit_email_domain

DATA = ROOT / "data"
seed = json.load(open(DATA / "municipalities_it.json", encoding="utf-8"))
seed_by_id = {e["id"]: e for e in seed}
data = json.load(open(ROOT / "data.json", encoding="utf-8"))
muns = data.get("municipalities") or data

rows = []
for k, m in muns.items():
    if (m.get("country") or "").upper() != "IT":
        continue
    if m.get("provider") != "unknown":
        continue
    se = seed_by_id.get(k)
    if not se:
        continue
    primary = (se.get("domain") or "").strip().lower()
    fbs = se.get("domain_fallbacks") or []
    if not primary or not fbs:
        continue
    ipa = se.get("ipa_codice_ipa", "")
    name = se.get("name", "")
    cat = se.get("ipa_codice_categoria", "")
    # ragione del rigetto per ciascun fallback
    fb_reasons = []
    for fb in fbs:
        ok, why = is_legit_email_domain(fb, primary, codice_ipa=ipa)
        fb_reasons.append(f"{fb}={'OK' if ok else 'NO'}:{why}")
    rows.append({
        "id": k,
        "codice_ipa": ipa,
        "categoria": cat,
        "name": name,
        "seed_domain": primary,
        "fallbacks": ";".join(fbs),
        "n_fallbacks": len(fbs),
        "fb_validator_reasons": " | ".join(fb_reasons),
    })

# write CSV
out = DATA / "reports" / "unknown_with_fallback.csv"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                       ["id","codice_ipa","categoria","name","seed_domain",
                        "fallbacks","n_fallbacks","fb_validator_reasons"])
    w.writeheader()
    w.writerows(rows)

# table to stdout
print(f"Totale enti UNKNOWN con seed_domain + fallback non-PEC: {len(rows)}\n")
print(f"Per categoria IndicePA:")
for c, n in Counter(r["categoria"] for r in rows).most_common(20):
    print(f"  {c:<6} {n}")
print()
print(f"=== Primi 80 (vedi {out.relative_to(ROOT)} per la lista completa) ===")
print(f"{'codice_ipa':<14}{'cat':<5}{'ente':<46}{'seed_domain':<32}{'fallback (validator)'}")
print("-" * 140)
for r in rows[:80]:
    fb_short = r["fb_validator_reasons"][:60]
    name = (r["name"] or "")[:44]
    print(f"{r['codice_ipa']:<14}{r['categoria']:<5}{name:<46}{r['seed_domain'][:30]:<32}{fb_short}")
print(f"\n...{max(0, len(rows)-80)} altri in {out.name}")
