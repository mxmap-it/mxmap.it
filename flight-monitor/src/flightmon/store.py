"""SQLite-backed price history and alert de-duplication."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import FareQuote

_SCHEMA = """
CREATE TABLE IF NOT EXISTS fares (
    route       TEXT NOT NULL,
    origin      TEXT NOT NULL,
    destination TEXT NOT NULL,
    depart_date TEXT NOT NULL,
    return_date TEXT NOT NULL,
    nights      INTEGER NOT NULL,
    price       REAL NOT NULL,
    currency    TEXT NOT NULL,
    provider    TEXT NOT NULL,
    seen_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fares_route ON fares(route);

CREATE TABLE IF NOT EXISTS alerts (
    signature   TEXT NOT NULL,
    price       REAL NOT NULL,
    alerted_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alerts_sig ON alerts(signature);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str = "flightmon.db"):
        self.path = path
        new = path == ":memory:" or not Path(path).exists()
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        if new or path == ":memory:":
            self.conn.executescript(_SCHEMA)
        else:
            self.conn.executescript(_SCHEMA)  # idempotent

    def close(self) -> None:
        self.conn.close()

    # -- price history ----------------------------------------------------
    def historic_low(self, route: str) -> float | None:
        """Lowest price ever recorded for a route, or None if never seen."""
        row = self.conn.execute(
            "SELECT MIN(price) AS m FROM fares WHERE route = ?", (route,)
        ).fetchone()
        return row["m"] if row and row["m"] is not None else None

    def record(self, quote: FareQuote) -> None:
        self.conn.execute(
            "INSERT INTO fares (route, origin, destination, depart_date, "
            "return_date, nights, price, currency, provider, seen_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                quote.route,
                quote.origin,
                quote.destination,
                quote.depart_date.isoformat(),
                quote.return_date.isoformat(),
                quote.nights,
                quote.price,
                quote.currency,
                quote.provider,
                _now(),
            ),
        )
        self.conn.commit()

    # -- alert de-duplication --------------------------------------------
    def already_alerted(
        self, quote: FareQuote, within_hours: int = 24
    ) -> bool:
        """True if we alerted on this exact itinerary at the same-or-lower
        price within the cooldown window (avoids spamming repeat scans)."""
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=within_hours)
        ).isoformat()
        row = self.conn.execute(
            "SELECT MIN(price) AS m FROM alerts "
            "WHERE signature = ? AND alerted_at >= ?",
            (quote.signature, cutoff),
        ).fetchone()
        prev = row["m"] if row else None
        return prev is not None and quote.price >= prev

    def record_alert(self, quote: FareQuote) -> None:
        self.conn.execute(
            "INSERT INTO alerts (signature, price, alerted_at) VALUES (?,?,?)",
            (quote.signature, quote.price, _now()),
        )
        self.conn.commit()
