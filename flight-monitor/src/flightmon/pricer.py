"""Per-leg fare pricing for the chain composer.

A ``Pricer`` answers a single question: what are the cheapest *nonstop*
options to fly O->D on a given day? Chains are built by the search in
``chains.py`` on top of this. The Amadeus implementation is real; the mock is
for tests and offline demos (the cloud sandbox here blocks live carriers)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from .chains import LegOffer


class Pricer(Protocol):
    def price_leg(self, origin: str, dest: str, day: date) -> list[LegOffer]:
        ...


class AmadeusPricer:
    """Prices each leg as a nonstop flight via Amadeus flight-offers.

    ``nonStop=true`` is essential: every chain edge must be a single real
    flight, otherwise we'd double-count Amadeus' own connections.
    """

    def __init__(self, currency: str = "EUR", max_offers: int = 5):
        from .amadeus_client import AmadeusClient

        self.client = AmadeusClient()
        self.currency = currency
        self.max_offers = max_offers
        self._cache: dict[tuple[str, str, str], list[LegOffer]] = {}

    def price_leg(self, origin: str, dest: str, day: date) -> list[LegOffer]:
        key = (origin, dest, day.isoformat())
        if key in self._cache:
            return self._cache[key]

        data = self.client.get(
            "/v2/shopping/flight-offers",
            {
                "originLocationCode": origin,
                "destinationLocationCode": dest,
                "departureDate": day.isoformat(),
                "adults": 1,
                "currencyCode": self.currency,
                "nonStop": "true",
                "max": self.max_offers,
            },
        )
        offers: list[LegOffer] = []
        for o in (data or {}).get("data", []):
            try:
                seg = o["itineraries"][0]["segments"][0]
                offers.append(
                    LegOffer(
                        origin=origin,
                        destination=dest,
                        depart_dt=datetime.fromisoformat(seg["departure"]["at"]),
                        arrive_dt=datetime.fromisoformat(seg["arrival"]["at"]),
                        price=float(o["price"]["grandTotal"]),
                        currency=o["price"].get("currency", self.currency),
                        carrier=seg.get("carrierCode", ""),
                    )
                )
            except (KeyError, IndexError, ValueError):
                continue
        offers.sort(key=lambda x: x.price)
        self._cache[key] = offers
        return offers


class MockPricer:
    """In-memory pricer for tests/offline demos.

    Seed it with ``add(origin, dest, depart_iso, arrive_iso, price)`` entries.
    Queries are matched by (origin, dest, day-of-departure).
    """

    def __init__(self, currency: str = "EUR"):
        self.currency = currency
        self._table: dict[tuple[str, str, str], list[LegOffer]] = {}

    def add(
        self,
        origin: str,
        dest: str,
        depart_iso: str,
        arrive_iso: str,
        price: float,
        carrier: str = "XX",
    ) -> None:
        dep = datetime.fromisoformat(depart_iso)
        offer = LegOffer(
            origin=origin,
            destination=dest,
            depart_dt=dep,
            arrive_dt=datetime.fromisoformat(arrive_iso),
            price=price,
            currency=self.currency,
            carrier=carrier,
        )
        self._table.setdefault(
            (origin, dest, dep.date().isoformat()), []
        ).append(offer)

    def price_leg(self, origin: str, dest: str, day: date) -> list[LegOffer]:
        offers = list(self._table.get((origin, dest, day.isoformat()), []))
        offers.sort(key=lambda x: x.price)
        return offers
