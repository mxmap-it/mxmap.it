from datetime import date

from flightmon.alerts import Alerter
from flightmon.config import AlertConfig
from flightmon.models import (
    Destination,
    FareQuote,
    TripParams,
)
from flightmon.monitor import evaluate, run_once
from flightmon.store import Store


def _quote(price: float, dest: str = "CPH") -> FareQuote:
    return FareQuote(
        origin="BSL",
        destination=dest,
        depart_date=date(2026, 3, 4),
        return_date=date(2026, 3, 7),
        nights=3,
        price=price,
        currency="EUR",
        provider="fake",
    )


def test_evaluate_under_budget():
    opp = evaluate(_quote(80), threshold=100, historic_low=None)
    assert opp is not None
    assert opp.under_budget
    assert "under €100" in opp.reasons


def test_evaluate_over_budget_no_history_is_silent():
    assert evaluate(_quote(150), threshold=100, historic_low=None) is None


def test_evaluate_historic_low_over_budget_still_alerts():
    opp = evaluate(_quote(120), threshold=100, historic_low=140)
    assert opp is not None
    assert opp.historic_low
    assert not opp.under_budget
    assert "historic low" in opp.reasons


def test_evaluate_first_sighting_not_a_historic_low():
    # No prior history -> not flagged as a "historic low".
    opp = evaluate(_quote(90), threshold=100, historic_low=None)
    assert opp is not None
    assert not opp.historic_low


class _FakeProvider:
    name = "fake"

    def __init__(self, quotes):
        self._quotes = quotes

    def search(self, origins, destinations, trip):
        yield from self._quotes


class _StubConfig:
    origins = ["BSL"]
    destinations = [Destination("CPH", "Copenhagen", "DK")]
    trip = TripParams()
    budget_eur = 100

    def budget_for(self, dest):
        return dest.budget_eur or self.budget_eur


def test_run_once_alerts_and_dedupes(tmp_path):
    store = Store(":memory:")
    alerter = Alerter(AlertConfig(console=False, csv_path=str(tmp_path / "d.csv")))
    config = _StubConfig()

    # First scan: 80 EUR is under budget -> one alert.
    provider = _FakeProvider([_quote(80)])
    assert run_once(config, [provider], store, alerter) == 1

    # Re-scan the same itinerary/price -> suppressed by dedup.
    provider = _FakeProvider([_quote(80)])
    assert run_once(config, [provider], store, alerter) == 0

    # A new historic low (60) -> alerts again.
    provider = _FakeProvider([_quote(60)])
    assert run_once(config, [provider], store, alerter) == 1
