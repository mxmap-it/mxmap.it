"""Date-window generation and round-trip pairing for flexible trips."""

from __future__ import annotations

from datetime import date, timedelta


def departure_window(
    params,
    today: date | None = None,
) -> tuple[date, date]:
    """Earliest/latest *departure* dates to scan, given the trip horizon."""
    today = today or date.today()
    start = today + timedelta(days=params.earliest_days_ahead)
    end = today + timedelta(days=params.search_horizon_days)
    return start, end


def return_window(params, today: date | None = None) -> tuple[date, date]:
    """Earliest/latest *return* dates (departure window shifted by max nights)."""
    start, end = departure_window(params, today)
    return start + timedelta(days=params.min_nights), end + timedelta(
        days=params.max_nights
    )


def pair_round_trips(
    outbound_by_date: dict[date, float],
    inbound_by_date: dict[date, float],
    min_nights: int,
    max_nights: int,
):
    """Pair cheapest outbound/inbound fares into valid 3-4 night itineraries.

    Yields ``(depart_date, return_date, nights, total_price)`` for every
    outbound date that has a matching inbound exactly ``nights`` later.
    """
    for depart, out_price in outbound_by_date.items():
        for nights in range(min_nights, max_nights + 1):
            ret = depart + timedelta(days=nights)
            in_price = inbound_by_date.get(ret)
            if in_price is None:
                continue
            yield depart, ret, nights, round(out_price + in_price, 2)
