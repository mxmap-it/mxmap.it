#!/usr/bin/env python3
"""Discover member comuni for each IT-CONS-* entity (consorzi/unioni/
associazioni/comunità-montane preserved at seed-time by V1.1).

Strategy (in order, first hit wins):

  Tier 1: Wikidata P527 (has part) — for the entity discovered via P6832
          (codice IPA), enumerate has-part claims and resolve each part's
          P635 (ISTAT comune code). Most reliable for well-modelled
          unions in IT.wikipedia.

  Tier 2: Wikipedia article parse — if Wikidata has no P527 but the entity
          has an Italian Wikipedia article (sitelink itwiki), fetch the
          page wikitext and look for the standard `Comuni` infobox
          parameter or a `wikitable` listing member comuni names. Map
          names to ISTAT codes using the existing seed comuni file.

  Tier 3: TODO LLM — Claude API prompt "List comuni members of <X> with
          ISTAT codes". Gated on ANTHROPIC_API_KEY, defers to a later run.

Output: data/enrichment_consorzi_members.json
{
  "<codice_ipa_lower>": {
    "name": "Unione dei Comuni X",
    "ipa_codice_categoria": "L18",
    "members_istat": ["028001", "028002", ...],   // 6-digit ISTAT comune
    "source": "wikidata|wikipedia|llm",
    "wikidata_qid": "Q123",
    "confidence": 1.0
  },
  ...
}

Used downstream by scripts/build_topo_consorzi.py to dissolve member
polygons from it_municipality.topo.json into one synthetic consorzio
polygon, exposed in the frontend as a new 'Consorzi' level.

Usage:
  uv run python3 scripts/enrich_consorzi_membership.py [--limit N] [--rebuild]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT_FILE = DATA / "enrichment_consorzi_members.json"
SEED_FILE = DATA / "municipalities_it.json"

USER_AGENT = "mxmap.it-consorzi-enrichment/0.1 (+https://github.com/fpietrosanti/mxmap.it)"
WD_SPARQL = "https://query.wikidata.org/sparql"


def http_get(url: str, *, headers: dict | None = None, retries: int = 3,
             sleep_s: float = 2.0) -> str:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                       **(headers or {})})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(sleep_s); sleep_s *= 1.7
    raise RuntimeError(f"GET {url} failed: {last_err}")


# ---------- Build seed-comuni name index for Tier 2 lookup ----------

def load_seed_comuni_index() -> dict[str, str]:
    """Return {comune_name_lowercase: istat6}. Used to resolve Wikipedia-derived
    comune names back to their ISTAT codes."""
    seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for e in seed:
        if e.get("ipa_codice_categoria") != "L6":
            continue
        istat = (e.get("ipa_codice_comune_istat") or "").zfill(6)
        if not istat or len(istat) != 6:
            continue
        n = (e.get("name") or "").strip()
        # IndicePA names: "Comune di X", "Comune dell'X", "Comune della X"
        for prefix in ["Comune di ", "Comune dell'", "Comune dell’",
                       "Comune della ", "Comune del ", "Comune dei "]:
            if n.startswith(prefix):
                n = n[len(prefix):]
                break
        out[n.lower().strip()] = istat
    print(f"  loaded {len(out)} comuni from seed for name resolution")
    return out


# ---------- Tier 1: Wikidata SPARQL ----------

def wikidata_lookup_members(codice_ipa: str) -> tuple[str | None, list[str], str | None]:
    """Return (qid, members_istat[], itwiki_title|None) for the entity matched
    by P6832=codice_ipa. members_istat is filled from each P527 part's P635."""
    q = (
        "SELECT DISTINCT ?ente ?part ?istat ?itwiki WHERE { "
        f'?ente wdt:P6832 "{codice_ipa}". '
        "OPTIONAL { ?ente wdt:P527 ?part. OPTIONAL { ?part wdt:P635 ?istat. } } "
        "OPTIONAL { ?itwiki schema:about ?ente; schema:isPartOf <https://it.wikipedia.org/>. } "
        "} LIMIT 200"
    )
    url = f"{WD_SPARQL}?query={urllib.parse.quote(q)}&format=json"
    try:
        body = http_get(url, headers={"Accept": "application/sparql-results+json"})
        d = json.loads(body)
    except Exception:
        return None, [], None
    qid: str | None = None
    members: list[str] = []
    itwiki_title: str | None = None
    for b in d.get("results", {}).get("bindings", []):
        ente = b.get("ente", {}).get("value", "")
        if ente.startswith("http://www.wikidata.org/entity/") and qid is None:
            qid = ente.rsplit("/", 1)[1]
        istat = b.get("istat", {}).get("value")
        if istat:
            members.append(str(istat).zfill(6))
        wp = b.get("itwiki", {}).get("value")
        if wp and itwiki_title is None:
            # https://it.wikipedia.org/wiki/Title
            try:
                title = urllib.parse.unquote(wp.split("/wiki/", 1)[1])
                itwiki_title = title
            except Exception:
                pass
    return qid, sorted(set(members)), itwiki_title


# ---------- Tier 2: Wikipedia wikitext parse ----------

WIKITEXT_COMUNE_PATTERNS = [
    # Infobox unione: |Comuni= <list>
    re.compile(r"\|\s*Comuni\s*=\s*([^|}]+)", re.IGNORECASE),
    # Lista comuni section
    re.compile(r"==\s*Comuni\s*=+\s*\n+(.+?)(?=\n==|\Z)", re.IGNORECASE | re.DOTALL),
]

LINK_RE = re.compile(r"\[\[([^|\]]+)(?:\|[^\]]*)?\]\]")


def wikipedia_lookup_members(itwiki_title: str, comuni_index: dict[str, str]) -> list[str]:
    """Fetch the Italian Wikipedia article wikitext and extract comuni names
    from the standard infobox/section patterns. Map each to its ISTAT via
    comuni_index (built from seed)."""
    api = (
        "https://it.wikipedia.org/w/api.php"
        "?action=query&format=json&prop=revisions&rvslots=main&rvprop=content"
        f"&titles={urllib.parse.quote(itwiki_title)}"
    )
    try:
        body = http_get(api)
        d = json.loads(body)
    except Exception:
        return []
    pages = d.get("query", {}).get("pages", {})
    text = ""
    for _pid, p in pages.items():
        revs = p.get("revisions", [])
        if revs and "slots" in revs[0]:
            text = revs[0]["slots"]["main"].get("*", "")
            break
    if not text:
        return []

    # Try each pattern; collect all wikilink targets, intersect with seed names
    candidates: list[str] = []
    for pat in WIKITEXT_COMUNE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        block = m.group(1)
        for ln in LINK_RE.findall(block):
            candidates.append(ln.strip())

    members_istat: list[str] = []
    for cand in candidates:
        # Wikipedia comune titles: "Bologna", "Bologna (comune)", "X (provincia di Y)"
        base = re.sub(r"\s*\([^)]+\)\s*$", "", cand).strip()
        istat = comuni_index.get(base.lower()) or comuni_index.get(cand.lower())
        if istat:
            members_istat.append(istat)
    return sorted(set(members_istat))


# ---------- Main loop ----------

def load_consorzi_from_seed() -> list[dict[str, Any]]:
    """Return all IT-CONS-* entries from the seed."""
    seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    return [e for e in seed if (e.get("id") or "").startswith("IT-CONS-")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    if not SEED_FILE.exists():
        print(f"FATAL: {SEED_FILE} missing — run fetch_indicepa.py first.")
        return 1

    consorzi = load_consorzi_from_seed()
    print(f"Found {len(consorzi)} IT-CONS-* entries in seed")
    if args.limit:
        consorzi = consorzi[: args.limit]

    comuni_index = load_seed_comuni_index()

    enriched: dict[str, Any] = {}
    if OUT_FILE.exists() and not args.rebuild:
        enriched = json.loads(OUT_FILE.read_text(encoding="utf-8"))
        print(f"Loaded {len(enriched)} existing consorzio enrichments")

    n_wd, n_wp, n_fail = 0, 0, 0
    for i, ent in enumerate(consorzi, 1):
        codice_ipa = (ent.get("ipa_codice_ipa") or "").strip().lower()
        if not codice_ipa:
            continue
        if codice_ipa in enriched and not args.rebuild:
            continue
        name = ent.get("name", "")
        cat = ent.get("ipa_codice_categoria", "?")

        try:
            qid, members, itwiki = wikidata_lookup_members(codice_ipa)
        except Exception as e:
            print(f"  [{i}] {codice_ipa} Wikidata error: {e!r}")
            qid, members, itwiki = None, [], None

        source = "wikidata" if members else None

        # Tier 2: try Wikipedia parse if Wikidata gave us a sitelink but no P527 members
        if not members and itwiki:
            try:
                members = wikipedia_lookup_members(itwiki, comuni_index)
                if members:
                    source = "wikipedia"
            except Exception as e:
                pass

        if members:
            enriched[codice_ipa] = {
                "name": name,
                "ipa_codice_categoria": cat,
                "members_istat": members,
                "source": source,
                "wikidata_qid": qid,
                "confidence": 1.0 if source == "wikidata" else 0.7,
            }
            if source == "wikidata":  n_wd += 1
            else:                     n_wp += 1
            print(f"  [{i:>3}/{len(consorzi)}] {codice_ipa}  {name[:45]:<45} "
                  f"-> {len(members):>3} comuni  [{source}]")
        else:
            n_fail += 1
            if i % 20 == 0:
                print(f"  [{i:>3}/{len(consorzi)}] (still searching… {n_fail} no-result so far)")

        if i % 25 == 0:
            OUT_FILE.write_text(json.dumps(enriched, ensure_ascii=False, indent=2),
                                encoding="utf-8")
        time.sleep(1.0)  # be polite to Wikidata

    OUT_FILE.write_text(json.dumps(enriched, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print()
    print(f"Wrote {OUT_FILE}")
    print(f"Enriched: {len(enriched)} (Wikidata P527: {n_wd}, Wikipedia: {n_wp}, "
          f"no-result: {n_fail})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
