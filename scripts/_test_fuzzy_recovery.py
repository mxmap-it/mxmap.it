#!/usr/bin/env python3
"""Simula una settima regola del validatore: 'fuzzy similarity' tra label
significativi del dominio candidato e del dominio (o nome) dell'ente,
usando la distanza di Damerau-Levenshtein.

Quantifica quanti rejects attuali sarebbero recuperabili a diverse soglie
di distanza, su due popolazioni:
  POP-A: i 1.627 enti già rigettati da cleanup_invalid_mx_attributions
         (cross-tenant trovati nei path scrape / fallback / recover)
  POP-B: i 169 enti email_non_pec_fallback che verrebbero rigettati
         se applicassimo il gate del nome (test precedente)

Per ogni reject, calcola la minima distanza fra QUALSIASI coppia
(label significativo del dominio candidato, label significativo del
nome o seed-domain dell'ente). Solo label di lunghezza >= MIN_LEN.

Stampa istogramma per distanza, e per ciascuna soglia (1, 2, 3) i recuperi.
Mostra ANCHE 30 esempi a distanza 1-2 per ispezione manuale.
"""
from __future__ import annotations
import csv, json, re, sys, unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))
from mail_sovereignty.scrape_validator import meaningful_labels, PEC_PROVIDERS

MIN_LEN = 5   # solo label di almeno 5 caratteri (evita "roma" vs "noma" etc.)


def damerau_levenshtein(s1: str, s2: str) -> int:
    """Distanza Damerau-Levenshtein (sostituzione/inserimento/eliminazione/
    trasposizione adiacenti)."""
    if s1 == s2:
        return 0
    len1, len2 = len(s1), len(s2)
    if not len1: return len2
    if not len2: return len1
    # matrix
    d = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1): d[i][0] = i
    for j in range(len2 + 1): d[0][j] = j
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i-1] == s2[j-1] else 1
            d[i][j] = min(d[i-1][j] + 1, d[i][j-1] + 1, d[i-1][j-1] + cost)
            if (i > 1 and j > 1 and s1[i-1] == s2[j-2] and s1[i-2] == s2[j-1]):
                d[i][j] = min(d[i][j], d[i-2][j-2] + cost)
    return d[len1][len2]


def normalize(s: str) -> str:
    """lowercase, no diacritics, alfa+digit only — per normalizzare label."""
    n = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", n.lower())


# stop-tokens del nome (stessa lista del test precedente)
NAME_NOISE = {
    "di","del","della","dello","dei","delle","degli","da","dal","dalla",
    "in","con","su","per","tra","fra","ed","e","a","al","alla","i","la",
    "il","lo","gli","le","l","d","de",
    "comune","comuni","provincia","provincie","regione","municipio",
    "citta","metropolitana","ministero","istituto","istituzione",
    "scuola","scuole","liceo","circolo","didattico","ordine","collegio",
    "federazione","azienda","agenzia","ente","consorzio","unione",
    "consiglio","commissione","autorita","direzione","centro",
    "ufficio","servizio","stato","statale","nazionale","italiana","italiano",
    "polo","amministrazione","professione","comprensivo","superiore",
    "secondaria","primaria","generale","direzione","della","delle",
}


def name_tokens(name: str) -> set[str]:
    if not name:
        return set()
    n = unicodedata.normalize("NFKD", name).encode("ascii","ignore").decode().lower()
    parts = re.split(r"[\s\.,;:'\"\-\(\)\/\d]+", n)
    return {p for p in parts
            if p and p not in NAME_NOISE and len(p) >= MIN_LEN}


def min_fuzzy_distance(candidate_dom: str, reference_tokens: set[str]) -> tuple[int, str, str]:
    """Min DL distance fra ogni meaningful_label del dominio e ogni token
    di riferimento. Ritorna (dist, label_dom, token_ref)."""
    cand_labels = {normalize(l) for l in meaningful_labels(candidate_dom) if len(l) >= MIN_LEN}
    ref = {normalize(t) for t in reference_tokens if len(t) >= MIN_LEN}
    best = (999, "", "")
    for cl in cand_labels:
        for rl in ref:
            d = damerau_levenshtein(cl, rl)
            if d < best[0]:
                best = (d, cl, rl)
    return best


def is_pec(dom: str) -> bool:
    s = (dom or "").lower()
    for pec in PEC_PROVIDERS:
        if s == pec or s.endswith("." + pec):
            return True
    return False


def evaluate_population(label: str, rows: list[dict]) -> None:
    """rows è una lista di dict con almeno candidate_dom + reference_tokens (set)."""
    print()
    print(f"=== Popolazione: {label} ({len(rows)} entries) ===")
    dist_counter: Counter[int] = Counter()
    samples_by_d: dict[int, list] = {1: [], 2: [], 3: []}
    pec_skipped = 0
    for r in rows:
        if is_pec(r["candidate_dom"]):
            pec_skipped += 1
            continue
        d, lbl, ref = min_fuzzy_distance(r["candidate_dom"], r["reference_tokens"])
        if d >= 999:
            d = 99
        dist_counter[d] += 1
        if d in samples_by_d and len(samples_by_d[d]) < 12:
            samples_by_d[d].append((r["id"], r["name"], r["candidate_dom"], r["seed_domain"], lbl, ref, d))
    total = sum(dist_counter.values())
    print(f"  PEC scartati a priori: {pec_skipped}")
    print(f"  Distribuzione distanza DL minima (candidate vs reference tokens):")
    for d in sorted(dist_counter):
        n = dist_counter[d]
        pct = 100*n/total if total else 0
        marker = "  ←" if d <= 2 else ""
        print(f"    d={d:>3}    {n:>5}  ({pct:5.1f}%){marker}")
    print()
    for thr in (1, 2, 3):
        rec = sum(n for d, n in dist_counter.items() if 1 <= d <= thr)
        print(f"  Soglia DL <= {thr}: recupererebbe {rec} entries ({100*rec/total if total else 0:.1f}%)")
    print()
    for d in (1, 2):
        if not samples_by_d[d]: continue
        print(f"  --- Esempi a distanza {d} (potenziali recuperi) ---")
        for id_, name, cand, seed, lbl, ref, dist in samples_by_d[d]:
            print(f"    {(id_ or '')[:24]:<25} {(name or '')[:36]:<38}")
            print(f"      candidato:  {cand}    [label: {lbl}]")
            print(f"      ente seed:  {seed}    [token: {ref}]   d={dist}")


def main() -> int:
    # ---- POPOLAZIONE A: cleanup_invalid_mx_attributions.csv ----
    csv_path = ROOT / "data/reports/manual_review_rejections_full.csv"
    rows_a = []
    if csv_path.exists():
        for r in csv.DictReader(open(csv_path, encoding="utf-8")):
            rows_a.append({
                "id": r["id"],
                "name": r.get("name") or "",
                "candidate_dom": r["claimed_domain"],
                "seed_domain": r["seed_domain"],
                # come reference, sia il dominio seed sia il nome
                "reference_tokens": (set(meaningful_labels(r["seed_domain"]))
                                      | name_tokens(r.get("name") or "")),
            })
    evaluate_population("cleanup_invalid_mx_attributions (cross-tenant purgati)", rows_a)

    # ---- POPOLAZIONE B: enti su email_non_pec_fallback ----
    seed = json.loads((ROOT / "data/municipalities_it.json").read_text(encoding="utf-8"))
    rows_b = []
    # solo quelli che il gate del NOME farebbe diventare unknown
    # → riproduciamo qui la logica del simulate_gate semplificata
    for e in seed:
        if (e.get("domain_source") or "") != "email_non_pec_fallback":
            continue
        name_t = name_tokens(e.get("name") or "")
        dom = e.get("domain") or ""
        dom_labels = {l for l in meaningful_labels(dom) if len(l) >= MIN_LEN}
        # accept se intersezione semplice già attiva
        if name_t & dom_labels:
            continue
        # accept se substring (vedi test precedente) — saltali, non vanno recuperati
        substr_hit = False
        for nt in {n for n in name_t if len(n) > 4}:
            for lbl in dom_labels:
                if nt in lbl or lbl in nt:
                    substr_hit = True; break
            if substr_hit: break
        if substr_hit:
            continue
        rows_b.append({
            "id": e.get("ipa_codice_ipa"),
            "name": e.get("name") or "",
            "candidate_dom": dom,
            "seed_domain": "(none — solo email)",
            "reference_tokens": name_t,
        })
    evaluate_population("email_non_pec_fallback rejects (gate proposto)", rows_b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
