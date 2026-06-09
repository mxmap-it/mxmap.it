"""Ryanair provider.

Uses the unofficial ``ryanair-py`` library, which wraps Ryanair's public
cheapest-fare endpoints. No API key required. Ryanair only serves mainland
Nordic airports (DK/SE/NO/FI) -- it does not fly to Iceland or Greenland, so
KEF/GOH destinations are simply skipped here (use Amadeus for those).
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from datetime import date

from ..dates import departure_window, pair_round_trips, return_window
from ..models import Destination, FareQuote, TripParams
from .base import Provider

# Airports Ryanair cannot serve -> skip without a wasted API call.
_UNSUPPORTED = {"KEF", "GOH", "RKV", "SFJ"}


def _to_date(value) -> date:
    """Normalise the library's departureTime (datetime) to a date."""
    return value.date() if hasattr(value, "date") else value


class RyanairProvider(Provider):
    name = "ryanair"

    def __init__(self, currency: str = "EUR", request_delay: float = 0.4):
        from ryanair import Ryanair  # imported lazily so tests can stub it

        self._api = Ryanair(currency=currency)
        self.currency = currency
        self.request_delay = request_delay

    def _cheapest_by_date(
        self, origin: str, dest: str, start: date, end: date
    ) -> dict[date, float]:
        """Map each available date to its cheapest one-way fare."""
        flights = self._api.get_cheapest_flights(
            origin, start, end, destination_airport=dest
        )
        out: dict[date, float] = {}
        for f in flights:
            d = _to_date(f.departureTime)
            price = float(f.price)
            if d not in out or price < out[d]:
                out[d] = price
        return out

    def search(
        self,
        origins: list[str],
        destinations: list[Destination],
        trip: TripParams,
    ) -> Iterable[FareQuote]:
        dep_start, dep_end = departure_window(trip)
        ret_start, ret_end = return_window(trip)

        for origin in origins:
            for dest in destinations:
                if dest.code in _UNSUPPORTED:
                    continue
                try:
                    outbound = self._cheapest_by_date(
                        origin, dest.code, dep_start, dep_end
                    )
                    time.sleep(self.request_delay)
                    inbound = self._cheapest_by_date(
                        dest.code, origin, ret_start, ret_end
                    )
                    time.sleep(self.request_delay)
                except Exception as exc:  # noqa: BLE001
                    print(f"[ryanair] {origin}->{dest.code} failed: {exc}")
                    continue

                trips = list(
                    pair_round_trips(
                        outbound, inbound, trip.min_nights, trip.max_nights
                    )
                )
                if not trips:
                    continue

                depart, ret, nights, total = min(trips, key=lambda t: t[3])
                yield FareQuote(
                    origin=origin,
                    destination=dest.code,
                    depart_date=depart,
                    return_date=ret,
                    nights=nights,
                    price=total,
                    currency=self.currency,
                    provider=self.name,
                    deep_link="https://www.ryanair.com/",
                )
