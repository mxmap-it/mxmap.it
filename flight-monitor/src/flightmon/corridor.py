"""Airport metadata and the hub graph for composing self-transfer chains.

The adjacency below is deliberately *generous*: any plausible low-cost
corridor edge from Italy toward Colombo is included. Non-existent routes are
pruned automatically at pricing time (the pricer returns no nonstop offer, so
the edge is never used). ``transit_note`` flags layover visa requirements for
an EU/Italian (or Swiss) passport.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Airport:
    code: str
    city: str
    country: str
    transit_note: str = ""        # visa/transit caveat for a self-transfer
    needs_transit_visa: bool = False


AIRPORTS: dict[str, Airport] = {
    # --- Italian origins -------------------------------------------------
    "FCO": Airport("FCO", "Roma Fiumicino", "IT"),
    "CIA": Airport("CIA", "Roma Ciampino", "IT"),
    "NAP": Airport("NAP", "Napoli", "IT"),
    # --- Turkey ----------------------------------------------------------
    "IST": Airport("IST", "Istanbul", "TR", "Senza visto (passaporto UE/CH)"),
    "SAW": Airport("SAW", "Istanbul Sabiha", "TR", "Senza visto (UE/CH)"),
    # --- Gulf ------------------------------------------------------------
    "AUH": Airport("AUH", "Abu Dhabi", "AE", "Visto gratis all'arrivo"),
    "DXB": Airport("DXB", "Dubai", "AE", "Visto gratis all'arrivo"),
    "SHJ": Airport("SHJ", "Sharjah", "AE", "Visto gratis all'arrivo"),
    "RKT": Airport("RKT", "Ras Al Khaimah", "AE", "Visto gratis all'arrivo"),
    "DOH": Airport("DOH", "Doha", "QA", "Senza visto 90gg"),
    "BAH": Airport("BAH", "Bahrein", "BH", "eVisa consigliato"),
    "KWI": Airport("KWI", "Kuwait", "KW", "eVisa richiesto", True),
    "MCT": Airport("MCT", "Muscat", "OM", "eVisa / transito"),
    # --- Saudi Arabia ----------------------------------------------------
    "JED": Airport("JED", "Jeddah", "SA", "eVisa / stopover"),
    "RUH": Airport("RUH", "Riyadh", "SA", "eVisa / stopover"),
    # --- South India (la tratta finale low-cost) -------------------------
    "MAA": Airport("MAA", "Chennai", "IN", "e-Visa OBBLIGATORIO per self-transfer", True),
    "TRZ": Airport("TRZ", "Tiruchirappalli", "IN", "e-Visa OBBLIGATORIO", True),
    "BLR": Airport("BLR", "Bengaluru", "IN", "e-Visa OBBLIGATORIO", True),
    "COK": Airport("COK", "Kochi", "IN", "e-Visa OBBLIGATORIO", True),
    "BOM": Airport("BOM", "Mumbai", "IN", "e-Visa OBBLIGATORIO", True),
    "DEL": Airport("DEL", "Delhi", "IN", "e-Visa OBBLIGATORIO", True),
    # --- Destination -----------------------------------------------------
    "CMB": Airport("CMB", "Colombo", "LK", "ETA obbligatorio"),
}

_GULF = ["AUH", "DXB", "SHJ", "RKT", "DOH", "BAH", "KWI", "MCT"]
_INDIA = ["MAA", "TRZ", "BLR", "COK", "BOM", "DEL"]
_SAUDI = ["JED", "RUH"]

# Directed corridor graph: airport -> reachable next hops.
ADJACENCY: dict[str, list[str]] = {
    # Italy -> Turkey / Gulf / Saudi bridges
    **{
        o: ["IST", "SAW", *_GULF, *_SAUDI]
        for o in ("FCO", "CIA", "NAP")
    },
    # Istanbul -> Gulf / Saudi / India / direct Colombo
    **{
        t: [*_GULF, *_SAUDI, *_INDIA, "CMB"]
        for t in ("IST", "SAW")
    },
    # Gulf -> India / Colombo
    **{g: [*_INDIA, "CMB"] for g in _GULF},
    # Saudi -> India / Colombo
    **{s: [*_INDIA, "CMB"] for s in _SAUDI},
    # India -> Colombo (cheapest final hop)
    **{i: ["CMB"] for i in _INDIA},
    "CMB": [],
}


def describe(code: str) -> str:
    a = AIRPORTS.get(code)
    return f"{code} ({a.city})" if a else code
