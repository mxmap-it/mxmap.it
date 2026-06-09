"""Provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from ..models import Destination, FareQuote, TripParams


class Provider(ABC):
    """A source of round-trip fare quotes."""

    name: str = "base"

    @abstractmethod
    def search(
        self,
        origins: list[str],
        destinations: list[Destination],
        trip: TripParams,
    ) -> Iterable[FareQuote]:
        """Yield the cheapest valid round-trip per (origin, destination)."""
        raise NotImplementedError
