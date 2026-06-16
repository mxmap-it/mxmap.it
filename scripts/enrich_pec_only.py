#!/usr/bin/env python3
"""Enrichment pipeline for PEC-only IndicePA enti.

~620 entities in IndicePA have NO Sito_istituzionale and ONLY PEC emails
(no non-PEC). The standard fetch_indicepa drops them at seed-time because
PEC providers (Aruba PEC, legalmail, postecert, asmepec) are dominated by
~5 entities and don't represent the ente's real email infrastructure.

This script tries to discover the real website / non-PEC email domain via:

  Tier 1: Wikidata SPARQL — query P6832 (IndicePA code) -> P856 (website)
  Tier 2: DuckDuckGo HTML search (no API key required) for "<ente_name>"
          + heuristic filter (.it/.gov.it/.eu, valid hostname, has MX)
  Tier 3: TODO — Claude API LLM prompt (skipped if ANTHROPIC_API_KEY absent)

Output:  data/enrichment_pec_only.json
  {
    "codice_ipa": {
      "domain": "comune-x.it",
      "source": "wikidata|duckduckgo|llm",
      "name": "Comune di X",
      "verified_mx": true
    },
    ...
  }

`fetch_indicepa.py` loads this file via load_pec_enrichment() and applies
each entry as a second-priority override (after IT_MANUAL_DOMAIN_OVERRIDES).
The seed marks domain_source='pec_enrichment_<source>' for audit.

Usage:
  uv run python3 scripts/enrich_pec_only.py [--limit N] [--rebuild]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT_FILE = DATA / "enrichment_pec_only.json"

CKAN_BASE = "https://indicepa.gov.it/ipa-dati/api/3/action"
RESOURCE_ID = "d09adf99-dc10-4349-8c53-27b1e5aa97b6"
PAGE_SIZE = 5000
USER_AGENT = "mxmap.it-pec-enrichment/0.1 (+https://github.com/mxmap-it/mxmap.it)"

WD_SPARQL = "https://query.wikidata.org/sparql"

HOSTNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$")

# Skip these "fake" PEC-derived results — popular Italian PEC providers.
SKIP_PEC_PROVIDER_HOSTS = {
    "pec.it", "legalmail.it", "postecert.it", "arubapec.it", "aruba.it",
    "asmepec.it", "conafpec.it", "notariato.it", "fnofi.it",
    "sicurezzapostale.it", "pec.aruba.it", "kpec.it", "namirial.it",
}

# Acceptable Italian/EU TLDs for results
GOOD_TLD_RE = re.compile(r"\.(it|gov\.it|edu\.it|eu|com|org|net)$", re.IGNORECASE)


def http_get(url: str, *, headers: dict[str, str] | None = None,
             retries: int = 2, sleep_s: float = 1.0,
             data: bytes | None = None, timeout: int = 15) -> str:
    """GET (or POST when data set) with simple retry on transient failures.
    Aggressive timeout (15s default) so a single hung mirror doesn't stall
    the loop indefinitely."""
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=data,
                                         headers={"User-Agent": USER_AGENT, **(headers or {})})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(sleep_s); sleep_s *= 1.5
    raise RuntimeError(f"GET {url} failed after {retries} attempts: {last_err}")


# ---------- IndicePA loader ----------

def fetch_pec_only_candidates() -> list[dict[str, Any]]:
    """Return all IndicePA rows that have NO Sito_istituzionale (or syntactically
    invalid) AND only PEC emails (no non-PEC Mail{1..5} entry)."""
    print("Fetching all IndicePA rows (paginated)…")
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {"resource_id": RESOURCE_ID, "limit": PAGE_SIZE, "offset": offset}
        url = f"{CKAN_BASE}/datastore_search?{urllib.parse.urlencode(params)}"
        body = http_get(url)
        data = json.loads(body)
        recs = data["result"]["records"]
        rows.extend(recs)
        if len(recs) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.4)
    print(f"  total IndicePA rows: {len(rows)}")

    candidates: list[dict[str, Any]] = []
    for r in rows:
        if (r.get("Ente_in_liquidazione") or "").strip().upper() == "S":
            continue
        sito = (r.get("Sito_istituzionale") or "").strip()
        # accept candidate if no sito OR sito is syntactically broken
        if sito:
            s = sito if "://" in sito else "//" + sito
            try:
                from urllib.parse import urlparse
                host = (urlparse(s).hostname or "").lower().lstrip("www.")
            except Exception:
                host = ""
            if host and HOSTNAME_RE.match(host):
                continue  # has a usable website — skip
        # Now check that NO non-PEC email exists
        has_non_pec = False
        has_pec = False
        for n in range(1, 6):
            addr = (r.get(f"Mail{n}") or "").strip()
            kind = (r.get(f"Tipo_Mail{n}") or "").strip().lower()
            if not addr or "@" not in addr:
                continue
            if kind == "pec":
                has_pec = True
            else:
                has_non_pec = True
        if has_non_pec or not has_pec:
            continue
        candidates.append(r)
    print(f"  PEC-only candidates: {len(candidates)}")
    return candidates


# ---------- Tier 1: Wikidata ----------

def wikidata_lookup_by_ipa(codice_ipa: str) -> str | None:
    """Query Wikidata for an entity with P6832=codice_ipa, return its P856
    (official website) host if present."""
    q = (
        "SELECT ?ente ?website WHERE { "
        f'?ente wdt:P6832 "{codice_ipa}". '
        "OPTIONAL { ?ente wdt:P856 ?website. } "
        "} LIMIT 5"
    )
    url = f"{WD_SPARQL}?query={urllib.parse.quote(q)}&format=json"
    try:
        body = http_get(url, headers={"Accept": "application/sparql-results+json"})
    except RuntimeError:
        return None
    try:
        d = json.loads(body)
    except Exception:
        return None
    for b in d.get("results", {}).get("bindings", []):
        site = b.get("website", {}).get("value")
        if site:
            return _extract_host(site)
    return None


def _extract_host(url: str) -> str | None:
    s = url.strip()
    if not s:
        return None
    if "://" not in s:
        s = "//" + s
    try:
        from urllib.parse import urlparse
        host = (urlparse(s).hostname or "").lower().lstrip(".")
    except Exception:
        return None
    if host.startswith("www."):
        host = host[4:]
    if not host or not HOSTNAME_RE.match(host):
        return None
    return host


# ---------- Tier 2: Wikipedia opensearch + page parse ----------

EXTERNAL_LINK_RE = re.compile(r'\[(https?://[^\s\]]+)', re.IGNORECASE)
INFOBOX_WEBSITE_RE = re.compile(
    r"\|\s*(?:sito[\s_]?(?:web|internet|ufficiale)|website)\s*=\s*\[?(https?://\S+|[a-z0-9][a-z0-9.-]+\.[a-z]{2,})",
    re.IGNORECASE,
)


def wikipedia_opensearch(query: str) -> str | None:
    """Use Italian Wikipedia opensearch API to find a likely page title for
    the query. Returns title or None."""
    api = ("https://it.wikipedia.org/w/api.php"
           f"?action=opensearch&format=json&limit=1&search={urllib.parse.quote(query)}")
    try:
        body = http_get(api)
    except RuntimeError:
        return None
    try:
        d = json.loads(body)
    except Exception:
        return None
    titles = d[1] if isinstance(d, list) and len(d) > 1 else []
    return titles[0] if titles else None


def wikipedia_page_website(title: str) -> str | None:
    """Fetch the Italian Wikipedia article wikitext and extract the
    "sito web|website" infobox parameter or first http://... external link
    that looks like an Italian PA domain."""
    api = ("https://it.wikipedia.org/w/api.php"
           "?action=query&format=json&prop=revisions&rvslots=main&rvprop=content"
           f"&titles={urllib.parse.quote(title)}")
    try:
        body = http_get(api)
        d = json.loads(body)
    except Exception:
        return None
    pages = d.get("query", {}).get("pages", {})
    text = ""
    for _pid, p in pages.items():
        revs = p.get("revisions", [])
        if revs and "slots" in revs[0]:
            text = revs[0]["slots"]["main"].get("*", "")
            break
    if not text:
        return None
    # Try infobox |sito web= / |website= first
    m = INFOBOX_WEBSITE_RE.search(text)
    if m:
        host = _extract_host(m.group(1))
        if host and host not in SKIP_PEC_PROVIDER_HOSTS and GOOD_TLD_RE.search(host):
            return host
    # Fall back: scan external links for plausible PA domain
    for m in EXTERNAL_LINK_RE.finditer(text):
        host = _extract_host(m.group(1))
        if not host:
            continue
        if host in SKIP_PEC_PROVIDER_HOSTS:
            continue
        if any(host.endswith(s) for s in
               (".facebook.com", ".instagram.com", ".linkedin.com",
                ".wikipedia.org", ".wikidata.org", ".commons.wikimedia.org",
                ".youtube.com", ".twitter.com", "x.com",
                ".indicepa.gov.it", "indicepa.gov.it",
                ".google.com", "maps.google.com")):
            continue
        if not GOOD_TLD_RE.search(host):
            continue
        return host
    return None


def wikipedia_lookup(name: str) -> str | None:
    """Combined: opensearch -> page -> website. None if nothing found."""
    title = wikipedia_opensearch(name)
    if not title:
        return None
    return wikipedia_page_website(title)


# ---------- Verification: MX lookup ----------

def has_mx_records(host: str) -> bool:
    """Light MX check via system resolver (fallback: skip on import failure)."""
    try:
        import dns.resolver
    except ImportError:
        return True  # don't reject if dnspython missing
    try:
        answers = dns.resolver.resolve(host, "MX", lifetime=5)
        return len(list(answers)) > 0
    except Exception:
        return False


# ---------- Main loop ----------

def enrich_one(row: dict[str, Any]) -> dict[str, Any] | None:
    codice_ipa = (row.get("Codice_IPA") or "").strip()
    name = (row.get("Denominazione_ente") or "").strip()
    if not codice_ipa or not name:
        return None

    # Tier 1: Wikidata
    host = wikidata_lookup_by_ipa(codice_ipa)
    src = "wikidata" if host else None

    # Tier 2: IT Wikipedia opensearch + page parse (replaces DDG which is
    # rate-limited / IP-blocked from the Scaleway server)
    if not host:
        host = wikipedia_lookup(name)
        src = "wikipedia" if host else None

    if not host:
        return None

    return {
        "codice_ipa": codice_ipa,
        "name": name,
        "domain": host,
        "source": src,
        "verified_mx": has_mx_records(host),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="enrich only first N candidates (for testing)")
    ap.add_argument("--rebuild", action="store_true",
                    help="discard existing enrichment file and start over")
    ap.add_argument("--skip-existing", action="store_true",
                    help="(default) only enrich entries not yet in the output file")
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict[str, Any]] = {}
    if OUT_FILE.exists() and not args.rebuild:
        existing = json.loads(OUT_FILE.read_text(encoding="utf-8"))
        print(f"Loaded {len(existing)} existing enrichments from {OUT_FILE}")

    candidates = fetch_pec_only_candidates()
    if args.limit:
        candidates = candidates[: args.limit]

    enriched = dict(existing)
    n_wd, n_ddg, n_fail = 0, 0, 0
    for i, row in enumerate(candidates, 1):
        codice_ipa = (row.get("Codice_IPA") or "").strip()
        if not codice_ipa:
            continue
        if codice_ipa in enriched and not args.rebuild:
            continue
        try:
            res = enrich_one(row)
        except Exception as e:
            print(f"  [{i}/{len(candidates)}] {codice_ipa}: ERROR {e!r}")
            res = None
        if res:
            enriched[codice_ipa] = res
            if res["source"] == "wikidata":   n_wd += 1
            else:                             n_ddg += 1  # now wikipedia
            print(f"  [{i}/{len(candidates)}] {codice_ipa}  {res['name'][:40]:<40} "
                  f"-> {res['domain']:<35}  [{res['source']}]"
                  f"{' MX✓' if res['verified_mx'] else ' MX✗'}", flush=True)
        else:
            n_fail += 1
            if i % 25 == 0:
                print(f"  [{i}/{len(candidates)}] (still searching… {n_fail} failures so far)")
        # Periodic checkpoint every 50 candidates
        if i % 50 == 0:
            OUT_FILE.write_text(json.dumps(enriched, ensure_ascii=False, indent=2),
                                encoding="utf-8")
        time.sleep(random.uniform(0.5, 1.5))

    OUT_FILE.write_text(json.dumps(enriched, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print()
    print(f"Wrote {OUT_FILE}")
    print(f"Total enrichments: {len(enriched)}  (Wikidata: {n_wd}  DDG: {n_ddg}  failed: {n_fail})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
