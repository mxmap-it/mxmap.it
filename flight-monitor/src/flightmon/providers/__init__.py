"""Flight-fare data providers."""

from __future__ import annotations

from .base import Provider


def build_providers(names, config) -> list[Provider]:
    """Instantiate the requested providers, skipping any that fail to load
    (e.g. Amadeus without credentials) with a warning rather than crashing."""
    providers: list[Provider] = []
    for name in names:
        key = name.lower()
        try:
            if key == "ryanair":
                from .ryanair import RyanairProvider

                providers.append(RyanairProvider(currency=config.currency))
            elif key == "amadeus":
                from .amadeus import AmadeusProvider

                providers.append(AmadeusProvider(currency=config.currency))
            else:
                print(f"[providers] unknown provider '{name}', skipping")
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"[providers] could not init '{name}': {exc}")
    return providers
