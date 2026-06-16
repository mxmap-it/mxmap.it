#!/usr/bin/env python3
"""Enrich the IndicePA seed by harvesting non-PEC email domains from
the AOO + Unita Organizzative auxiliary datasets, filtered through
src/mail_sovereignty/scrape_validator.is_legit_email_domain so we
never inherit a sub-unit's email that doesn't actually belong to the
parent ente.

Why this matters: the bare `enti` dataset only has Mail{1..5} which is
overwhelmingly PEC. AOO and UO records carry per-sub-unit responsabili
emails (mail_resp, mail1/2/3) that are MOSTLY non-PEC (working office
emails). For PA centrali like Min. Interno, the enti record exposes
zero non-PEC, while AOO has hundreds (281 AOO for m_it -> domains:
interno.it, vigilfuoco.it).

Output: data/indicepa_extended_emails.json
{
  "_meta": {...},
  "by_ipa": {
    "m_it": {
      "non_pec_domains": ["interno.it", "vigilfuoco.it"],
      "source_record_count": 283,
      "filtered_out": [
        {"dom": "comune.roma.it", "reason": "no_label_intersection"},
        ...
      ]
    },
    ...
  }
}

Usage: uv run python3 scripts/enrich_from_aoo_uo.py [--refresh]
Idempotent — caches downloaded TXT files under data/indicepa_raw/.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys as _sys
csv.field_size_limit(min(_sys.maxsize, 2**31 - 1))
import json
import sys
import time
import urllib.request
from pathlib import Path
from collections import defaultdict, Counter
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))
from mail_sovereignty.scrape_validator import is_legit_email_domain  # noqa

DATA = ROOT / "data"
RAW = DATA / "indicepa_raw"
RAW.mkdir(parents=True, exist_ok=True)
OUT = DATA / "indicepa_extended_emails.json"

USER_AGENT = "mxmap.it-aoo-uo-enrichment/0.1 (+https://github.com/mxmap-it/mxmap.it)"

# Discovered via package_show; cached here for clarity.
DATASETS = {
    "aoo": {
        "url": "https://indicepa.gov.it/ipa-dati/dataset/d813fced-2e40-43d2-bb51-b393ccb0c714/resource/2566e791-80cd-45c7-b3c9-df914b91649a/download/aoo.txt",
        "key_field": "cod_amm",
        "id_field": "cod_aoo",
        "name_field": "des_aoo",
        # Email columns + their type-tag column (or None if always non-PEC)
        "email_cols": [
            ("mail_resp", None),         # responsabile — overwhelmingly non-PEC
            ("mail1", "tipo_mail1"),
            ("mail2", "tipo_mail2"),
            ("mail3", "tipo_mail3"),
        ],
    },
    "uo": {
        # UO is only published as XLSX; fall back to CKAN datastore_search
        # API (paginated) and synthesize a TSV cache in the same column
        # shape as AOO so the parser path below is uniform.
        "ckan_resource_id": "b0aa1f6c-f135-4c8a-b416-396fed4e1a5d",
        "ckan_total_estimate": 130000,
        "ckan_field_map": {
            "Codice_IPA": "cod_amm",
            "Codice_uni_uo": "cod_ou",
            "Descrizione_uo": "des_ou",
            "Mail_responsabile": "mail_resp",
            "Mail1": "mail1",
            "Tipo_Mail1": "tipo_mail1",
            "Mail2": "mail2",
            "Tipo_Mail2": "tipo_mail2",
            "Mail3": "mail3",
            "Tipo_Mail3": "tipo_mail3",
        },
        "key_field": "cod_amm",
        "id_field": "cod_ou",
        "name_field": "des_ou",
        "email_cols": [
            ("mail_resp", None),
            ("mail1", "tipo_mail1"),
            ("mail2", "tipo_mail2"),
            ("mail3", "tipo_mail3"),
        ],
    },
}

HOSTNAME_OK = lambda h: h and "." in h and len(h) < 256


def download_if_needed(name: str, url: str) -> Path:
    out = RAW / f"{name}.txt"
    if out.exists() and out.stat().st_size > 0:
        return out
    print(f"  Downloading {name} from IndicePA…")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
    out.write_bytes(data)
    print(f"    saved {out} ({out.stat().st_size:,} bytes)")
    return out


def synthesize_tsv_from_ckan(name: str, resource_id: str,
                              field_map: dict, page_size: int = 32000) -> Path:
    """Pull `resource_id` via CKAN datastore_search (paginated), rename
    the columns through `field_map`, and write a TSV at RAW/{name}.txt
    with the same shape as the TXT downloads. Idempotent — caches."""
    out = RAW / f"{name}.txt"
    if out.exists() and out.stat().st_size > 0:
        return out
    print(f"  Pulling {name} via CKAN datastore_search (paginated)…")
    base = ("https://indicepa.gov.it/ipa-dati/api/3/action/datastore_search"
            f"?resource_id={resource_id}")
    offset = 0
    rows: list[dict] = []
    while True:
        url = f"{base}&limit={page_size}&offset={offset}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=300) as r:
            payload = json.loads(r.read())
        recs = payload["result"]["records"]
        if not recs:
            break
        rows.extend(recs)
        offset += len(recs)
        print(f"    fetched {len(rows):,} / total≈{payload['result'].get('total','?')}")
        if len(recs) < page_size:
            break
    # Write TSV in target column shape
    cols = list(field_map.values())
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("\t".join(cols) + "\n")
        for rec in rows:
            f.write("\t".join(
                str(rec.get(src, "") or "").replace("\t", " ").replace("\n", " ")
                for src in field_map.keys()
            ) + "\n")
    print(f"    saved {out} ({out.stat().st_size:,} bytes, {len(rows):,} rows)")
    return out


def extract_email_domains(rec: dict, email_cols: list, ipa_field: str) -> dict:
    """For one record, return {non_pec_doms: set, pec_doms: set}.
    PEC emails are recognized by Tipo_mail*=Pec or 'pec' in domain
    substring (defensive)."""
    non_pec: set[str] = set()
    pec: set[str] = set()
    for col, tipo_col in email_cols:
        addr = (rec.get(col) or "").strip()
        if not addr or addr.lower() == "null" or "@" not in addr:
            continue
        host = addr.rsplit("@", 1)[1].strip().lower().rstrip(".")
        if not HOSTNAME_OK(host):
            continue
        # Skip purely PEC providers
        is_pec = False
        if tipo_col:
            kind = (rec.get(tipo_col) or "").strip().lower()
            if kind == "pec":
                is_pec = True
        # Conservative: also flag pec.* prefix or known PEC suffixes
        if (host.startswith("pec.") or host.startswith("cert.")
                or "pec." in host[:8] or host.endswith(".pec.it")
                or host in {"pec.it", "legalmail.it", "postecert.it",
                            "arubapec.it", "asmepec.it", "notariato.it"}):
            is_pec = True
        if is_pec:
            pec.add(host)
        else:
            non_pec.add(host)
    return {"non_pec": non_pec, "pec": pec}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="redownload AOO/UO even if cached")
    args = ap.parse_args()

    # Step 1: download both datasets
    print("=== Step 1: download AOO + UO ===")
    files = {}
    for name, ds in DATASETS.items():
        if args.refresh:
            (RAW / f"{name}.txt").unlink(missing_ok=True)
        if "url" in ds:
            files[name] = download_if_needed(name, ds["url"])
        elif "ckan_resource_id" in ds:
            files[name] = synthesize_tsv_from_ckan(
                name, ds["ckan_resource_id"], ds["ckan_field_map"])
        else:
            raise ValueError(f"dataset {name} has no source")

    # Step 2: build a map codice_ipa -> ente_domain (from seed)
    seed_path = DATA / "municipalities_it.json"
    if not seed_path.exists():
        print("FATAL: seed missing — run fetch_indicepa first")
        return 1
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    ipa_to_ente_domain = {}
    for e in seed:
        ipa = (e.get("ipa_codice_ipa") or "").strip().lower()
        if ipa and e.get("domain"):
            ipa_to_ente_domain[ipa] = e["domain"]

    # Step 3: walk AOO + UO records, extract emails, filter through validator
    print()
    print("=== Step 2: parse AOO + UO and harvest non-PEC emails ===")
    by_ipa: dict[str, dict] = defaultdict(
        lambda: {"non_pec_domains": set(), "filtered_out": [],
                 "source_record_count": 0})

    for name, ds in DATASETS.items():
        path = files[name]
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            rdr = csv.DictReader(f, delimiter="\t")
            n_total = n_with_email = 0
            for rec in rdr:
                n_total += 1
                ipa = (rec.get(ds["key_field"]) or "").strip().lower()
                if not ipa:
                    continue
                ente_domain = ipa_to_ente_domain.get(ipa)
                if not ente_domain:
                    continue   # we don't have this ente in our seed
                hits = extract_email_domains(rec, ds["email_cols"], ds["key_field"])
                if not hits["non_pec"]:
                    continue
                n_with_email += 1
                by_ipa[ipa]["source_record_count"] += 1
                for dom in hits["non_pec"]:
                    ok, reason = is_legit_email_domain(dom, ente_domain,
                                                       codice_ipa=ipa)
                    if ok:
                        by_ipa[ipa]["non_pec_domains"].add(dom)
                    else:
                        by_ipa[ipa]["filtered_out"].append({
                            "dom": dom, "reason": reason,
                        })
            print(f"  {name}: parsed {n_total} records, "
                  f"{n_with_email} had at least one non-PEC email matching "
                  f"a seed-ente codice_IPA")

    # Step 4: dedupe filtered_out (same dom can appear many times)
    for ipa in by_ipa:
        seen = set()
        unique = []
        for fo in by_ipa[ipa]["filtered_out"]:
            key = (fo["dom"], fo["reason"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(fo)
        by_ipa[ipa]["filtered_out"] = unique[:20]   # cap audit trail
        by_ipa[ipa]["non_pec_domains"] = sorted(by_ipa[ipa]["non_pec_domains"])

    # Step 5: stats
    n_enriched = sum(1 for v in by_ipa.values() if v["non_pec_domains"])
    n_total_doms = sum(len(v["non_pec_domains"]) for v in by_ipa.values())
    print()
    print(f"=== Step 3: stats ===")
    print(f"  enti enriched with at least one non-PEC domain: {n_enriched}")
    print(f"  total distinct non-PEC domains harvested:        {n_total_doms}")
    rejected = Counter()
    for v in by_ipa.values():
        for fo in v["filtered_out"]:
            rejected[fo["reason"]] += 1
    print(f"  filtered out (per reason, top 10):")
    for r, n in rejected.most_common(10):
        print(f"    {r:<30} {n}")

    # Step 6: write output
    payload = {
        "_meta": {
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_datasets": list(DATASETS.keys()),
            "n_enriched": n_enriched,
            "n_total_domains": n_total_doms,
        },
        "by_ipa": dict(by_ipa),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
