"""Scan orchestration: fetch quotes, evaluate, record history, alert."""

from __future__ import annotations

from .alerts import Alerter
from .config import Config
from .models import Destination, FareQuote, Opportunity
from .store import Store


def evaluate(
    quote: FareQuote,
    threshold: float | None,
    historic_low: float | None,
) -> Opportunity | None:
    """Decide whether a quote is an opportunity worth alerting on.

    Triggers when the fare is at/under its threshold OR beats every price
    previously seen for that route. ``historic_low`` is the prior minimum
    (None if the route has never been recorded).
    """
    under_budget = threshold is not None and quote.price <= threshold
    is_low = historic_low is None or quote.price < historic_low

    reasons: list[str] = []
    if under_budget:
        reasons.append(f"under €{threshold:.0f}")
    # Only flag a "historic low" once there is prior history to beat.
    new_low = is_low and historic_low is not None
    if new_low:
        reasons.append("historic low")

    if not reasons:
        return None

    return Opportunity(
        quote=quote,
        threshold_eur=threshold,
        under_budget=under_budget,
        historic_low=new_low,
        previous_low=historic_low,
        reasons=reasons,
    )


def run_once(config: Config, providers, store: Store, alerter: Alerter) -> int:
    """Run a single scan across all providers. Returns the number of alerts."""
    by_code: dict[str, Destination] = {d.code: d for d in config.destinations}
    alerts_sent = 0

    for provider in providers:
        print(f"[scan] provider={provider.name}")
        for quote in provider.search(
            config.origins, config.destinations, config.trip
        ):
            dest = by_code.get(quote.destination)
            threshold = config.budget_for(dest) if dest else config.budget_eur
            prior_low = store.historic_low(quote.route)

            opp = evaluate(quote, threshold, prior_low)
            store.record(quote)  # always record for price history

            if opp is None:
                continue
            if store.already_alerted(quote):
                continue

            alerter.emit(opp)
            store.record_alert(quote)
            alerts_sent += 1

    print(f"[scan] done, {alerts_sent} alert(s)")
    return alerts_sent
