from datetime import date

from flightmon.dates import departure_window, pair_round_trips, return_window
from flightmon.models import TripParams


def test_departure_and_return_windows():
    params = TripParams(
        min_nights=3, max_nights=4, earliest_days_ahead=3, search_horizon_days=90
    )
    today = date(2026, 1, 1)
    dep_start, dep_end = departure_window(params, today)
    assert dep_start == date(2026, 1, 4)
    assert dep_end == date(2026, 4, 1)

    ret_start, ret_end = return_window(params, today)
    assert ret_start == date(2026, 1, 7)   # dep_start + 3 nights
    assert ret_end == date(2026, 4, 5)     # dep_end + 4 nights


def test_pair_round_trips_matches_only_valid_nights():
    outbound = {date(2026, 1, 10): 20.0, date(2026, 1, 11): 15.0}
    inbound = {
        date(2026, 1, 13): 25.0,   # 3 nights from the 10th
        date(2026, 1, 14): 30.0,   # 4 nights from the 10th / 3 from the 11th
        date(2026, 1, 20): 10.0,   # too far -> no pairing
    }
    trips = list(pair_round_trips(outbound, inbound, 3, 4))

    totals = {(d, r): t for d, r, n, t in trips}
    assert totals[(date(2026, 1, 10), date(2026, 1, 13))] == 45.0
    assert totals[(date(2026, 1, 10), date(2026, 1, 14))] == 50.0
    assert totals[(date(2026, 1, 11), date(2026, 1, 14))] == 45.0
    # No 5+ night pairings, and the 20th is never reachable in 3-4 nights.
    assert all(3 <= n <= 4 for _, _, n, _ in trips)
    assert date(2026, 1, 20) not in {r for _, r, _, _ in trips}
