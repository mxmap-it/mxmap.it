"""Compose the cheapest self-transfer chain to a destination.

Models the corridor as a time-expanded graph and runs a Dijkstra search keyed
on cumulative price over states ``(airport, arrival_datetime)``. The first
time a destination state is popped it is the globally cheapest itinerary, so
results come out in price order regardless of how many stops they take.

Layover feasibility note: a connection always happens at a *single* airport,
so comparing the (local) arrival time of one leg with the (local) departure
time of the next is correct even though airports sit in different time zones.
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta


@dataclass(frozen=True)
class LegOffer:
    origin: str
    destination: str
    depart_dt: datetime
    arrive_dt: datetime
    price: float
    currency: str
    carrier: str = ""


@dataclass
class Chain:
    legs: list[LegOffer]

    @property
    def total_price(self) -> float:
        return round(sum(leg.price for leg in self.legs), 2)

    @property
    def currency(self) -> str:
        return self.legs[0].currency if self.legs else ""

    @property
    def hops(self) -> int:
        return len(self.legs)

    @property
    def route(self) -> list[str]:
        if not self.legs:
            return []
        return [self.legs[0].origin] + [leg.destination for leg in self.legs]

    @property
    def signature(self) -> tuple:
        return tuple(
            (leg.origin, leg.destination, leg.depart_dt.isoformat())
            for leg in self.legs
        )

    def layovers(self) -> list[timedelta]:
        """Wait time at each intermediate airport."""
        return [
            self.legs[i + 1].depart_dt - self.legs[i].arrive_dt
            for i in range(len(self.legs) - 1)
        ]


@dataclass(order=True)
class _State:
    price: float
    seq: int
    airport: str = field(compare=False)
    ready_dt: datetime = field(compare=False)
    legs: list = field(compare=False, default_factory=list)


def _candidate_days(ready_dt: datetime, hops: int):
    """Days to query for the next leg. First leg: the start day only; later
    legs may also depart the following day (overnight layover)."""
    if hops == 0:
        return [ready_dt.date()]
    return [ready_dt.date(), (ready_dt + timedelta(days=1)).date()]


def find_cheapest_chains(
    pricer,
    origins: list[str],
    destination: str,
    adjacency: dict[str, list[str]],
    depart_days: list,
    *,
    min_connection_hours: float = 3.0,
    max_layover_hours: float = 30.0,
    max_legs: int = 5,
    top_n: int = 5,
) -> list[Chain]:
    """Return up to ``top_n`` distinct cheapest chains, in price order."""
    min_conn = timedelta(hours=min_connection_hours)
    max_lay = timedelta(hours=max_layover_hours)
    counter = itertools.count()

    heap: list[_State] = []
    for origin in origins:
        for day in depart_days:
            heapq.heappush(
                heap,
                _State(0.0, next(counter), origin, datetime.combine(day, time.min), []),
            )

    best_at: dict[tuple[str, str], float] = {}
    results: list[Chain] = []
    seen_sigs: set[tuple] = set()

    while heap and len(results) < top_n:
        st = heapq.heappop(heap)
        hops = len(st.legs)

        if st.airport == destination and hops > 0:
            chain = Chain(list(st.legs))
            if chain.signature not in seen_sigs:
                seen_sigs.add(chain.signature)
                results.append(chain)
            continue

        if hops >= max_legs:
            continue

        for nxt in adjacency.get(st.airport, []):
            for day in _candidate_days(st.ready_dt, hops):
                for off in pricer.price_leg(st.airport, nxt, day):
                    if hops == 0:
                        if off.depart_dt < st.ready_dt:
                            continue
                    else:
                        layover = off.depart_dt - st.ready_dt
                        if layover < min_conn or layover > max_lay:
                            continue

                    new_price = st.price + off.price
                    key = (nxt, off.arrive_dt.isoformat())
                    if key in best_at and best_at[key] <= new_price:
                        continue
                    best_at[key] = new_price
                    heapq.heappush(
                        heap,
                        _State(
                            new_price,
                            next(counter),
                            nxt,
                            off.arrive_dt,
                            st.legs + [off],
                        ),
                    )

    return results
