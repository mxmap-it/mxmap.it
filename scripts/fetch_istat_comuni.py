#!/usr/bin/env python3
"""Fetch dell'elenco ufficiale dei comuni italiani da ISTAT.

Source: https://www.istat.it/it/archivio/6789
Direct URL: https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv

Normalizza i campi e salva in data/istat_comuni.json — committato come
snapshot per il regression test tests/test_seed_invariants.py. Il file
viene rigenerato manualmente quando ISTAT pubblica una nuova edizione
(in genere semestrale, dopo variazioni amministrative).

Schema output:
{
  "_meta": {"generated": "ISO8601", "source_url": "...", "n_comuni": 7896},
  "comuni": [
    {
      "codice_istat": "001001",   # 6 cifre paddate
      "codice_catastale": "A074",  # 4 caratteri (catasto)
      "denominazione_it": "Agliè",
      "denominazione_full": "Agliè",   # incluso nome bilingue se diverso
      "codice_regione": "01",
      "codice_provincia": "001",
      "sigla_auto": "TO",
      "codice_nuts3_2024": "ITC11",
      "capoluogo": False
    },
    ...
  ]
}
"""
from __future__ import annotations
import argparse
import csv
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ISTAT_URL = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"
OUT_PATH = DATA / "istat_comuni.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=DATA / "istat_raw" / "comuni.csv",
                    help="Cache CSV path (default: data/istat_raw/comuni.csv)")
    ap.add_argument("--refresh", action="store_true",
                    help="Re-scarica anche se la cache esiste")
    args = ap.parse_args()

    args.cache.parent.mkdir(parents=True, exist_ok=True)
    if args.refresh or not args.cache.exists():
        print(f"Downloading ISTAT comuni list from {ISTAT_URL}...")
        req = urllib.request.Request(ISTAT_URL, headers={
            "User-Agent": "mxmap.it-istat-fetcher/1.0 (+https://github.com/fpietrosanti/mxmap.it)"
        })
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        args.cache.write_bytes(data)
        print(f"  saved {args.cache} ({len(data):,} bytes)")
    else:
        print(f"Using cached {args.cache}")

    print("Parsing CSV...")
    out = []
    with open(args.cache, encoding="iso-8859-1") as f:
        rdr = csv.DictReader(f, delimiter=";")
        for row in rdr:
            codice_istat = row.get("Codice Comune formato alfanumerico", "").strip()
            if not codice_istat:
                continue
            den_it = row.get("Denominazione in italiano", "").strip()
            den_full = row.get("Denominazione (Italiana e straniera)", "").strip() or den_it
            codice_cat = row.get("Codice Catastale del comune", "").strip()
            codice_reg = row.get("Codice Regione", "").strip()
            codice_prov = row.get("Codice Provincia (Storico)(1)", "").strip()
            sigla = row.get("Sigla automobilistica", "").strip()
            nuts3 = row.get("Codice NUTS3 2024", "").strip()
            capoluogo = row.get(
                "Flag Comune capoluogo di provincia/citt\xe0 metropolitana/libero consorzio",
                "").strip() == "1"
            out.append({
                "codice_istat": codice_istat,
                "codice_catastale": codice_cat,
                "denominazione_it": den_it,
                "denominazione_full": den_full,
                "codice_regione": codice_reg,
                "codice_provincia": codice_prov,
                "sigla_auto": sigla,
                "codice_nuts3_2024": nuts3,
                "capoluogo": capoluogo,
            })

    payload = {
        "_meta": {
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_url": ISTAT_URL,
            "n_comuni": len(out),
        },
        "comuni": out,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"\nWrote {OUT_PATH} with {len(out)} comuni.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
