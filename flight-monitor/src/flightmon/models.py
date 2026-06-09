"""Core data structures shared across providers, store, and alerts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Destination:
    """A monitored arrival airport."""

    code: str
    city: str
    country: str
    region: str = "nordic"
    # Per-destination override of the round-trip alert threshold (EUR).
    budget_eur: float | None = None


@dataclass(frozen=True)
class TripParams:
    """Flexible-date trip constraints."""

    min_nights: int = 3
    max_nights: int = 4
    earliest_days_ahead: int = 3
    search_horizon_days: int = 90


@dataclass(frozen=True)
class FareQuote:
    """A concrete round-trip fare found by a provider."""

    origin: str
    destination: str
    depart_date: date
    return_date: date
    nights: int
    price: float
    currency: str
    provider: str
    outbound_flight: str = ""
    inbound_flight: str = ""
    deep_link: str = ""

    @property
    def route(self) -> str:
        """Stable route identifier used for price history grouping."""
        return f"{self.origin}-{self.destination}"

    @property
    def signature(self) -> str:
        """Identity of a specific itinerary, for alert de-duplication."""
        return f"{self.route}:{self.depart_date}:{self.return_date}:{self.provider}"


@dataclass
class Opportunity:
    """A fare that beat a threshold and/or set a historic low."""

    quote: FareQuote
    threshold_eur: float | None
    under_budget: bool
    historic_low: bool
    previous_low: float | None = None
    reasons: list[str] = field(default_factory=list)
