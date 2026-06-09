from datetime import date

from flightmon.models import FareQuote
from flightmon.store import Store


def _quote(price: float, provider: str = "ryanair") -> FareQuote:
    return FareQuote(
        origin="BSL",
        destination="CPH",
        depart_date=date(2026, 3, 4),
        return_date=date(2026, 3, 7),
        nights=3,
        price=price,
        currency="EUR",
        provider=provider,
    )


def test_historic_low_tracks_minimum():
    store = Store(":memory:")
    assert store.historic_low("BSL-CPH") is None

    store.record(_quote(80))
    store.record(_quote(60))
    store.record(_quote(95))
    assert store.historic_low("BSL-CPH") == 60


def test_alert_dedup_within_window():
    store = Store(":memory:")
    q = _quote(50)
    assert store.already_alerted(q) is False

    store.record_alert(q)
    # Same itinerary at the same price within the window -> suppressed.
    assert store.already_alerted(q) is True
    # A cheaper price for the same itinerary should still alert.
    assert store.already_alerted(_quote(40)) is False
