#!/usr/bin/env python3
"""Lookup ASN organization names via RIPE Stat for the top ASNs of
'independent'-classified IT enti, to identify Italian providers we
should catalogue in LOCAL_ISP_ASNS or ITALIAN_PROVIDER_ASN_OVERRIDES."""
import json
import sys
import time
import urllib.request

ASNS = [16509, 24994, 44920, 52030, 31034, 21056, 35110, 60087, 47242,
        12874, 16633, 43054, 31403, 8660, 16276, 198045, 396982, 15691,
        3302, 20746, 12445, 31638, 6882, 202675, 200760, 47217, 3242,
        50178, 201333, 34758, 20912]

UA = "mxmap.it-asn-lookup/0.1"

for asn in ASNS:
    url = f"https://stat.ripe.net/data/as-overview/data.json?resource=AS{asn}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8"))
        info = d.get("data", {}).get("holder", "?")
        country = d.get("data", {}).get("country_code", "?")
        print(f"  AS{asn:<8} {country:<3} {info}")
    except Exception as e:
        print(f"  AS{asn:<8} ERROR {e!r}")
    time.sleep(0.5)
