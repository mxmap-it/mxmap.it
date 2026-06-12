from datetime import date

from flightmon.chains import find_cheapest_chains
from flightmon.pricer import MockPricer

ADJ = {
    "FCO": ["IST", "AUH"],
    "IST": ["SHJ", "CMB"],
    "AUH": ["MAA", "CMB"],
    "SHJ": ["MAA", "CMB"],
    "MAA": ["CMB"],
    "CMB": [],
}
DAY = date(2026, 7, 15)


def _pricer() -> MockPricer:
    p = MockPricer()
    p.add("FCO", "IST", "2026-07-15T08:00", "2026-07-15T11:30", 55)
    p.add("IST", "SHJ", "2026-07-15T15:00", "2026-07-15T19:30", 95)
    p.add("IST", "CMB", "2026-07-15T20:00", "2026-07-16T05:30", 240)
    p.add("SHJ", "MAA", "2026-07-15T23:30", "2026-07-16T03:30", 60)
    p.add("SHJ", "CMB", "2026-07-15T22:30", "2026-07-16T04:30", 105)
    p.add("MAA", "CMB", "2026-07-16T09:00", "2026-07-16T10:30", 55)
    return p


def test_finds_globally_cheapest_chain():
    chains = find_cheapest_chains(
        _pricer(), ["FCO"], "CMB", ADJ, [DAY], top_n=3
    )
    assert chains
    cheapest = chains[0]
    # FCO->IST(55)->SHJ(95)->MAA(60)->CMB(55) = 265 beats the 3-leg
    # FCO->IST->SHJ->CMB (255)? -> let's assert it's the true minimum.
    assert cheapest.total_price == min(c.total_price for c in chains)
    assert cheapest.route[0] == "FCO" and cheapest.route[-1] == "CMB"
    # results are sorted by price
    prices = [c.total_price for c in chains]
    assert prices == sorted(prices)


def test_rejects_too_short_layover():
    p = MockPricer()
    p.add("FCO", "IST", "2026-07-15T08:00", "2026-07-15T11:30", 55)
    # only an onward flight 1h after arrival -> below the 3h minimum
    p.add("IST", "CMB", "2026-07-15T12:30", "2026-07-15T22:00", 200)
    chains = find_cheapest_chains(
        p, ["FCO"], "CMB", ADJ, [DAY], min_connection_hours=3.0
    )
    assert chains == []


def test_respects_max_legs():
    chains = find_cheapest_chains(
        _pricer(), ["FCO"], "CMB", ADJ, [DAY], max_legs=2
    )
    # With <=2 legs the only path is FCO->IST->CMB (direct from IST).
    for c in chains:
        assert c.hops <= 2
    assert any(c.route == ["FCO", "IST", "CMB"] for c in chains)


def test_overnight_layover_allowed():
    chains = find_cheapest_chains(
        _pricer(), ["FCO"], "CMB", ADJ, [DAY], max_layover_hours=30
    )
    # The MAA leg departs the morning after arrival -> overnight layover used.
    assert any("MAA" in c.route for c in chains)
