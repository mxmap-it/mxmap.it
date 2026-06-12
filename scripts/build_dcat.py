#!/usr/bin/env python3
"""Genera i metadati DCAT-AP_IT del dataset (F5) → history/dcat.jsonld.

DCAT-AP_IT è il profilo italiano (AgID) di DCAT-AP, lo standard con cui
dati.gov.it harvesta automaticamente i dataset opendata della PA. Esporre un
dcat.jsonld valido rende l'Osservatorio harvestabile nel catalogo nazionale.

Descrive il dataset (titolo, descrizione, publisher, licenza, frequenza
giornaliera, temi, keyword) e le sue distribuzioni (CSV/JSON/XLSX + snapshot
storici). Letto da data.json/runs.jsonl per i numeri correnti.

Uso: python3 scripts/build_dcat.py [--base-url https://fpietrosanti.github.io/mxmap.it]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_DEFAULT = "https://fpietrosanti.github.io/mxmap.it"

CONTEXT = {
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "vcard": "http://www.w3.org/2006/vcard/ns#",
    "dcatapit": "http://dati.gov.it/onto/dcatapit#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
}


def _distribution(base: str, path: str, fmt: str, title: str, media: str) -> dict:
    return {
        "@type": ["dcat:Distribution", "dcatapit:Distribution"],
        "dct:title": {"@value": title, "@language": "it"},
        "dct:format": {"@id": f"http://publications.europa.eu/resource/authority/file-type/{fmt}"},
        "dcat:mediaType": media,
        "dcat:accessURL": {"@id": f"{base}/{path}"},
        "dcat:downloadURL": {"@id": f"{base}/{path}"},
        "dct:license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=BASE_DEFAULT)
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # numeri correnti (per la descrizione)
    n_it = 0
    if args.data.exists():
        d = json.loads(args.data.read_text(encoding="utf-8"))
        muns = d.get("municipalities", d)
        n_it = sum(1 for v in muns.values() if (v.get("country") or "").upper() == "IT")

    dataset = {
        "@context": CONTEXT,
        "@type": ["dcat:Dataset", "dcatapit:Dataset"],
        "@id": f"{base}/history/dcat.jsonld#dataset",
        "dct:identifier": "mxmap-it-pa-email-sovereignty",
        "dct:title": {
            "@value": "Sovranità digitale della posta elettronica della PA italiana",
            "@language": "it",
        },
        "dct:description": {
            "@value": (
                f"Per ciascuno dei ~{n_it} enti della Pubblica Amministrazione "
                "italiana (IndicePA), il provider di posta elettronica reale "
                "classificato via analisi DNS pubblica (MX, SPF, DKIM, CNAME), "
                "con la sovranità (IT/estero, CLOUD Act), il livello di "
                "confidenza e lo storico dei cambiamenti. Aggiornato "
                "quotidianamente."
            ),
            "@language": "it",
        },
        "dct:modified": {"@value": now, "@type": "http://www.w3.org/2001/XMLSchema#date"},
        # frequenza: giornaliera (EU authority accrual-periodicity)
        "dct:accrualPeriodicity": {
            "@id": "http://publications.europa.eu/resource/authority/frequency/DAILY"
        },
        # tema: Governo e settore pubblico (EU data theme)
        "dcat:theme": [
            {"@id": "http://publications.europa.eu/resource/authority/data-theme/GOVE"}
        ],
        "dcat:keyword": [
            "pubblica amministrazione",
            "posta elettronica",
            "sovranità digitale",
            "CLOUD Act",
            "IndicePA",
            "DNS",
        ],
        "dct:publisher": {
            "@type": ["foaf:Agent", "dcatapit:Agent"],
            "@id": f"{base}#publisher",
            "foaf:name": "Osservatorio sulla Sovranità Digitale della Posta Elettronica della PA Italiana",
        },
        "dct:rightsHolder": {
            "@type": ["foaf:Agent", "dcatapit:Agent"],
            "foaf:name": "Osservatorio Sovranità Digitale PA",
        },
        "dct:language": {"@id": "http://publications.europa.eu/resource/authority/language/ITA"},
        # licenze: dati ODbL, contenuti CC-BY
        "dct:license": {"@id": "https://opendatacommons.org/licenses/odbl/1-0/"},
        "dcat:landingPage": {"@id": base},
        "dcat:distribution": [
            _distribution(base, "dist/mxmap_it_dataset.csv", "CSV", "Dataset completo (CSV)", "text/csv"),
            _distribution(base, "dist/mxmap_it_dataset.json", "JSON", "Dataset completo (JSON)", "application/json"),
            _distribution(base, "dist/mxmap_it_dataset.xlsx", "XLSX", "Dataset completo (XLSX)", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            _distribution(base, "history/runs.jsonl", "JSON", "Indice dei run storici (JSONL)", "application/jsonl"),
            _distribution(base, "history/snapshots/", "JSON", "Snapshot storici compatti (JSONL.gz)", "application/gzip"),
        ],
    }

    out = ROOT / "history" / "dcat.jsonld"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DCAT-AP_IT -> {out} ({len(dataset['dcat:distribution'])} distribuzioni, {n_it} enti IT)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
