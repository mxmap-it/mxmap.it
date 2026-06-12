"""Synthetic fare data for an offline demo of the chain composer.

Lets ``flightmon chain --mock`` produce a believable Italy->Colombo result
without live API access (the cloud sandbox blocks real carriers). Legs are
anchored to whatever base departure date you pass, so the demo works for any
``--depart``.
"""

from __future__ import annotations

from datetime import date, timedelta

from .pricer import MockPricer


def build_demo_pricer(base: date) -> MockPricer:
    d0 = base.isoformat()
    d1 = (base + timedelta(days=1)).isoformat()
    p = MockPricer(currency="EUR")

    # Italy -> Istanbul / Gulf
    p.add("FCO", "IST", f"{d0}T08:00", f"{d0}T11:30", 55, "PC")
    p.add("NAP", "IST", f"{d0}T07:30", f"{d0}T11:10", 62, "PC")
    p.add("FCO", "AUH", f"{d0}T10:00", f"{d0}T18:30", 185, "EY")
    # Istanbul -> Gulf / direct
    p.add("IST", "SHJ", f"{d0}T15:00", f"{d0}T19:30", 95, "G9")
    p.add("IST", "AUH", f"{d0}T15:30", f"{d0}T20:00", 110, "PC")
    p.add("IST", "CMB", f"{d0}T20:00", f"{d1}T05:30", 240, "TK")
    # Gulf -> India / Colombo
    p.add("SHJ", "CMB", f"{d0}T22:30", f"{d1}T04:30", 105, "G9")
    p.add("SHJ", "MAA", f"{d0}T23:30", f"{d1}T03:30", 60, "G9")
    p.add("AUH", "MAA", f"{d0}T22:00", f"{d1}T03:00", 70, "6E")
    p.add("AUH", "CMB", f"{d0}T23:00", f"{d1}T05:00", 150, "EY")
    # South India -> Colombo (cheap final hop)
    p.add("MAA", "CMB", f"{d1}T09:00", f"{d1}T10:30", 55, "UL")
    return p
