#!/usr/bin/env python3
"""Probe AOO + UO IndicePA datasets to see how much MORE non-PEC email
data they expose vs the bare `enti` dataset, and whether the union
solves the gov.it / PA-centrale recovery problem without scraping."""
import json
import sys
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from collections import Counter

BASE = "https://indicepa.gov.it/ipa-dati/api/3/action/datastore_search"
ENTI_RES = "d09adf99-dc10-4349-8c53-27b1e5aa97b6"
AOO_RES  = "2566e791-80cd-45c7-b3c9-df914b91649a"

UO_RES = "b0aa1f6c-f135-4c8a-b416-396fed4e1a5d"  # Unità Organizzative


def fetch(resource_id, filters=None, limit=5000):
    params = {"resource_id": resource_id, "limit": limit}
    if filters:
        params["filters"] = json.dumps(filters)
    req = Request(BASE + "?" + urlencode(params),
                  headers={"User-Agent": "mxmap-aoo-probe/0.1"})
    return json.loads(urlopen(req, timeout=120).read())["result"]["records"]


def email_domains_from_record(rec, pec_only=False):
    """Return set of (kind, host) tuples for ALL email fields in record."""
    found = set()
    for k, v in rec.items():
        if not v or not isinstance(v, str) or "@" not in v:
            continue
        host = v.split("@", 1)[1].strip().lower().rstrip(".")
        # Determine kind
        kind_field = None
        for tk in ("Tipo_" + k, "Tipo_mail", "Tipo_Mail"):
            if tk in rec and rec[tk]:
                kind_field = rec[tk]
                break
        is_pec = (kind_field or "").strip().lower() == "pec" or "pec" in host
        if pec_only and not is_pec:
            continue
        if not pec_only and is_pec:
            continue
        found.add(host)
    return found


# 1. Min Interno via enti
print("=== Step 1: enti record for Codice_IPA=m_it ===")
enti_recs = fetch(ENTI_RES, {"Codice_IPA": "m_it"})
print(f"  records: {len(enti_recs)}")
non_pec_enti = set()
pec_enti = set()
for r in enti_recs:
    non_pec_enti |= email_domains_from_record(r, pec_only=False)
    pec_enti |= email_domains_from_record(r, pec_only=True)
print(f"  non-PEC email-domains: {non_pec_enti or '(none)'}")
print(f"  PEC email-domains:     {pec_enti or '(none)'}")

# 2. AOO records linked to m_it
print()
print("=== Step 2: AOO records linked to m_it ===")
aoo_recs = fetch(AOO_RES, {"Codice_ipa": "m_it"})
print(f"  AOO count: {len(aoo_recs)}")
non_pec_aoo = set()
pec_aoo = set()
for r in aoo_recs:
    non_pec_aoo |= email_domains_from_record(r, pec_only=False)
    pec_aoo |= email_domains_from_record(r, pec_only=True)
print(f"  non-PEC email-domains across AOOs: {len(non_pec_aoo)}")
for h in sorted(non_pec_aoo)[:15]:
    print(f"    - {h}")
print(f"  PEC email-domains: {len(pec_aoo)}")
for h in sorted(pec_aoo)[:5]:
    print(f"    - {h}")

# 3. UO records linked to m_it
print()
print("=== Step 3: UO records linked to m_it ===")
try:
    # UO endpoint may use different field name
    uo_recs = fetch(UO_RES, {"Codice_ipa": "m_it"})
except Exception:
    uo_recs = fetch(UO_RES, {"Codice_IPA": "m_it"})
print(f"  UO count: {len(uo_recs)}")
non_pec_uo = set()
for r in uo_recs:
    non_pec_uo |= email_domains_from_record(r, pec_only=False)
print(f"  non-PEC email-domains across UOs: {len(non_pec_uo)}")
for h in sorted(non_pec_uo)[:20]:
    print(f"    - {h}")

# 4. Union summary
print()
print("=== Step 4: union of non-PEC domains for Codice_IPA=m_it ===")
all_non_pec = non_pec_enti | non_pec_aoo | non_pec_uo
print(f"  TOTAL distinct non-PEC email-domains: {len(all_non_pec)}")
for h in sorted(all_non_pec):
    print(f"    - {h}")

# 5. Histogram of contributions
print()
print("=== Step 5: source contribution ===")
print(f"  enti: {len(non_pec_enti)}")
print(f"  AOO:  {len(non_pec_aoo)}")
print(f"  UO:   {len(non_pec_uo)}")
print(f"  union additional from AOO/UO: {len((non_pec_aoo | non_pec_uo) - non_pec_enti)}")
