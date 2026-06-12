"""Amadeus Self-Service provider (optional).

Covers airlines Ryanair can't (Icelandair/PLAY into KEF, Air Greenland to
GOH, SAS/Finnair, etc.). Requires free credentials from
https://developers.amadeus.com -- set ``AMADEUS_CLIENT_ID`` and
``AMADEUS_CLIENT_SECRET`` in the environment.

Amadeus charges per request and requires concrete dates, so rather than
sweeping every day we sample candidate departure dates (default: every
Wednesday in the horizon -- statistically the cheapest day) and price the
3- and 4-night returns for each. Set ``AMADEUS_HOST=production`` to hit live
data instead of the test sandbox.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from datetime import date, timedelta

from ..amadeus_client import AmadeusClient
from ..dates import departure_window
from ..models import Destination, FareQuote, TripParams


class AmadeusProvider:
    name = "amadeus"

    def __init__(self, currency: str = "EUR", sample_weekday: int = 2):
        self.client = AmadeusClient()
        self.currency = currency
        self.sample_weekday = sample_weekday  # 0=Mon .. 2=Wed

    def _candidate_departures(self, trip: TripParams) -> list[date]:
        start, end = departure_window(trip)
        d = start
        while d.weekday() != self.sample_weekday:
            d += timedelta(days=1)
        out = []
        while d <= end:
            out.append(d)
            d += timedelta(days=7)
        return out

    def _price(
        self, origin: str, dest: str, depart: date, ret: date
    ) -> float | None:
        data = self.client.get(
            "/v2/shopping/flight-offers",
            {
                "originLocationCode": origin,
                "destinationLocationCode": dest,
                "departureDate": depart.isoformat(),
                "returnDate": ret.isoformat(),
                "adults": 1,
                "currencyCode": self.currency,
                "max": 5,
                "nonStop": "false",
            },
        )
        if data is None:
            return None
        offers = data.get("data", [])
        prices = [float(o["price"]["grandTotal"]) for o in offers]
        return min(prices) if prices else None

    def search(
        self,
        origins: list[str],
        destinations: list[Destination],
        trip: TripParams,
    ) -> Iterable[FareQuote]:
        departures = self._candidate_departures(trip)
        for origin in origins:
            for dest in destinations:
                best: tuple[date, date, int, float] | None = None
                for depart in departures:
                    for nights in range(trip.min_nights, trip.max_nights + 1):
                        ret = depart + timedelta(days=nights)
                        try:
                            total = self._price(origin, dest.code, depart, ret)
                        except Exception as exc:  # noqa: BLE001
                            print(f"[amadeus] {origin}->{dest.code} {exc}")
                            total = None
                        time.sleep(0.3)
                        if total is not None and (
                            best is None or total < best[3]
                        ):
                            best = (depart, ret, nights, total)
                if best is None:
                    continue
                depart, ret, nights, total = best
                yield FareQuote(
                    origin=origin,
                    destination=dest.code,
                    depart_date=depart,
                    return_date=ret,
                    nights=nights,
                    price=round(total, 2),
                    currency=self.currency,
                    provider=self.name,
                )
