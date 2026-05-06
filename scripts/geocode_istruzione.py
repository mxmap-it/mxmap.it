#!/usr/bin/env python3
"""Geocode the ~8.405 Italian education entities (cluster Istruzione:
L33+L17+L43+L15+L28) to lat/lng via OSM Nominatim.

Output: data/it_istruzione_points.json
{
  "generated": "...",
  "total": 8405,
  "geocoded": 8312,
  "points": {
    "<codice_ipa>": {
      "name": "...",
      "categoria": "L33",
      "lat": 45.4642, "lon": 9.1900,
      "comune_istat": "015146",
      "comune_name": "Milano",
      "address_used": "Via X, 12, 20121 Milano MI",
      "geocode_source": "nominatim",   // or "comune_centroid_fallback"
      "comune_lat": 45.4642, "comune_lon": 9.1900   // for reference
    },
    ...
  }
}

Idempotent: existing entries in the output file are NOT re-geocoded
unless --refresh is passed. The file is committed to git so running
the pipeline from a fresh clone reuses the cached lat/lng without
hitting Nominatim again. Re-run only when:
  - new IndicePA enti appear that aren't yet in the cache
  - manual deletion of the cache file (--refresh)

Nominatim policy:
  - 1 request/second max (we use 1.1s for safety margin)
  - Provide a real User-Agent + email contact

Usage:
  uv run python3 scripts/geocode_istruzione.py [--limit N] [--refresh]
  uv run python3 scripts/geocode_istruzione.py --limit 100   # smoke test
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SEED_FILE = DATA / "municipalities_it.json"
OUT_FILE = DATA / "it_istruzione_points.json"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "mxmap.it-geocode/0.1 (+https://github.com/fpietrosanti/mxmap.it; contact: github)"
NOMINATIM_DELAY_S = 1.1  # >1 req/s violates the policy

ISTRUZIONE_CATS = {"L33", "L17", "L43", "L15", "L28"}


def fetch_indicepa_addresses(codici_ipa: list[str]) -> dict[str, dict]:
    """Pull Indirizzo/CAP/Comune fields for the given IPA codes via CKAN
    datastore_search. Returns {codice_ipa: {indirizzo, cap, comune, provincia}}.

    IndicePA CKAN supports filtering by Codice_IPA but only one at a time, so
    we paginate the full enti dataset and join in-process — much faster for
    8K codes than 8K filter queries.
    """
    print("  Loading IndicePA addresses (paginated full dataset)…")
    by_ipa: dict[str, dict] = {}
    offset = 0
    page = 5000
    target = set(codici_ipa)
    while True:
        url = (f"https://indicepa.gov.it/ipa-dati/api/3/action/datastore_search"
               f"?resource_id=d09adf99-dc10-4349-8c53-27b1e5aa97b6"
               f"&limit={page}&offset={offset}")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode("utf-8"))
        recs = d["result"]["records"]
        for rec in recs:
            cod = (rec.get("Codice_IPA") or "").strip()
            if cod in target:
                by_ipa[cod] = {
                    "indirizzo": (rec.get("Indirizzo") or "").strip(),
                    "cap": (rec.get("CAP") or "").strip(),
                    "comune": (rec.get("Comune") or "").strip(),
                    "provincia": (rec.get("Provincia") or "").strip(),
                    "denominazione": (rec.get("Denominazione_ente") or "").strip(),
                }
        if len(recs) < page:
            break
        offset += page
        time.sleep(0.4)
    print(f"  Joined: {len(by_ipa)}/{len(codici_ipa)} addresses found in IndicePA")
    return by_ipa


def nominatim_geocode(query: str) -> tuple[float, float] | None:
    """Single Nominatim query. Returns (lat, lon) or None."""
    params = {
        "q": query,
        "format": "json",
        "limit": "1",
        "countrycodes": "it",
        "addressdetails": "0",
    }
    url = f"{NOMINATIM_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        if isinstance(data, list) and data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="cap geocode requests (testing)")
    ap.add_argument("--refresh", action="store_true",
                    help="ignore existing cache and re-geocode everything")
    args = ap.parse_args()

    if not SEED_FILE.exists():
        print(f"FATAL: {SEED_FILE} missing — run fetch_indicepa first")
        return 1

    seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    istr_enti = [e for e in seed if e.get("ipa_codice_categoria") in ISTRUZIONE_CATS]
    print(f"Istruzione enti in seed: {len(istr_enti)}")

    cache: dict[str, Any] = {}
    if OUT_FILE.exists() and not args.refresh:
        existing = json.loads(OUT_FILE.read_text(encoding="utf-8"))
        cache = existing.get("points", {})
        print(f"Loaded cache: {len(cache)} previously-geocoded points")

    # Identify what still needs geocoding
    todo: list[dict] = []
    for e in istr_enti:
        ipa = (e.get("ipa_codice_ipa") or "").strip()
        if not ipa:
            continue
        if ipa in cache and not args.refresh:
            continue
        todo.append(e)
    print(f"To geocode: {len(todo)} (will skip {len(istr_enti) - len(todo)} cached)")
    if args.limit:
        todo = todo[: args.limit]
        print(f"  Limited to first {len(todo)} for this run")
    if not todo:
        print("Nothing to do — cache is complete.")
        # still re-write to refresh the meta header
        out = {
            "generated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total": len(istr_enti),
            "geocoded": len(cache),
            "points": cache,
        }
        OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        return 0

    # Fetch addresses
    addresses = fetch_indicepa_addresses([e["ipa_codice_ipa"] for e in todo])

    # Build comune-centroid fallback from seed
    comune_by_istat: dict[str, dict] = {}
    for e in seed:
        if e.get("ipa_codice_categoria") == "L6":
            i = (e.get("ipa_codice_comune_istat") or "").zfill(6)
            if i:
                comune_by_istat[i] = {"name": e.get("name", "")}

    geocoded = 0
    fallback = 0
    failed = 0
    for i, e in enumerate(todo, 1):
        ipa = e["ipa_codice_ipa"]
        cat = e.get("ipa_codice_categoria", "?")
        name = e.get("name", "")
        addr = addresses.get(ipa, {})
        comune_istat = (e.get("ipa_codice_comune_istat") or "").zfill(6)

        # Build query string: prefer full address, then comune+CAP, then comune
        q_full = ", ".join(filter(None, [
            addr.get("indirizzo"), addr.get("cap"),
            addr.get("comune"), addr.get("provincia"), "Italia"
        ]))
        q_comune = ", ".join(filter(None, [
            addr.get("comune"), addr.get("provincia"), "Italia"
        ]))

        coords = None
        source = None
        for q in (q_full, q_comune):
            if not q:
                continue
            coords = nominatim_geocode(q)
            time.sleep(NOMINATIM_DELAY_S)
            if coords:
                source = "nominatim"
                break

        if not coords:
            # last resort: comune centroid via Nominatim (very basic)
            failed += 1
            print(f"  [{i:>4}/{len(todo)}] {ipa:<10} {cat:<5} {name[:40]:<40}  FAIL")
            continue

        if source == "nominatim" and addr.get("indirizzo"):
            geocoded += 1
        else:
            fallback += 1

        cache[ipa] = {
            "name": name,
            "categoria": cat,
            "lat": coords[0],
            "lon": coords[1],
            "comune_istat": comune_istat,
            "comune_name": addr.get("comune", ""),
            "address_used": q_full or q_comune,
            "geocode_source": source,
        }
        if i % 20 == 0:
            kind = "ok" if source == "nominatim" else source
            print(f"  [{i:>4}/{len(todo)}] {ipa:<10} {cat:<5} {name[:38]:<38}  ({kind}) lat={coords[0]:.4f}, lon={coords[1]:.4f}")
        # Periodic checkpoint write
        if i % 50 == 0:
            out = {
                "generated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "total": len(istr_enti),
                "geocoded": len(cache),
                "points": cache,
            }
            OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                encoding="utf-8")

    out = {
        "generated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(istr_enti),
        "geocoded": len(cache),
        "points": cache,
    }
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print()
    print(f"Wrote {OUT_FILE}")
    print(f"Total cached: {len(cache)}  (added: {geocoded + fallback}, failed: {failed})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
