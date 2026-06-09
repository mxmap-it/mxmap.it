"""Load and validate YAML configuration into typed objects."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .models import Destination, TripParams


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


@dataclass
class EmailConfig:
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    sender: str = ""
    recipients: list[str] = field(default_factory=list)


@dataclass
class AlertConfig:
    console: bool = True
    csv_path: str = "deals.csv"
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    email: EmailConfig = field(default_factory=EmailConfig)


@dataclass
class Config:
    origins: list[str]
    destinations: list[Destination]
    trip: TripParams
    budget_eur: float
    currency: str = "EUR"
    providers: list[str] = field(default_factory=lambda: ["ryanair"])
    alerts: AlertConfig = field(default_factory=AlertConfig)
    db_path: str = "flightmon.db"

    def budget_for(self, destination: Destination) -> float:
        """Effective threshold for a destination (override or global default)."""
        return destination.budget_eur or self.budget_eur


def _env_or(value, env_key: str):
    """Allow secrets to come from the environment rather than the YAML file."""
    if value:
        return value
    return os.environ.get(env_key, "")


def load_config(path: str | Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text()) or {}

    destinations = [
        Destination(
            code=d["code"],
            city=d.get("city", d["code"]),
            country=d.get("country", ""),
            region=d.get("region", "nordic"),
            budget_eur=d.get("budget_eur"),
        )
        for d in raw.get("destinations", [])
    ]

    trip_raw = raw.get("trip", {})
    trip = TripParams(
        min_nights=trip_raw.get("min_nights", 3),
        max_nights=trip_raw.get("max_nights", 4),
        earliest_days_ahead=trip_raw.get("earliest_days_ahead", 3),
        search_horizon_days=trip_raw.get("search_horizon_days", 90),
    )

    a = raw.get("alerts", {})
    tg = a.get("telegram", {})
    em = a.get("email", {})
    alerts = AlertConfig(
        console=a.get("console", True),
        csv_path=a.get("csv_path", "deals.csv"),
        telegram=TelegramConfig(
            enabled=tg.get("enabled", False),
            bot_token=_env_or(tg.get("bot_token", ""), "FLIGHTMON_TG_TOKEN"),
            chat_id=_env_or(tg.get("chat_id", ""), "FLIGHTMON_TG_CHAT"),
        ),
        email=EmailConfig(
            enabled=em.get("enabled", False),
            smtp_host=em.get("smtp_host", ""),
            smtp_port=em.get("smtp_port", 587),
            username=_env_or(em.get("username", ""), "FLIGHTMON_SMTP_USER"),
            password=_env_or(em.get("password", ""), "FLIGHTMON_SMTP_PASS"),
            sender=em.get("sender", ""),
            recipients=em.get("recipients", []),
        ),
    )

    if not destinations:
        raise ValueError("config has no destinations")
    if not raw.get("origins"):
        raise ValueError("config has no origins")

    return Config(
        origins=list(raw["origins"]),
        destinations=destinations,
        trip=trip,
        budget_eur=float(raw.get("budget_eur", 100)),
        currency=raw.get("currency", "EUR"),
        providers=raw.get("providers", ["ryanair"]),
        alerts=alerts,
        db_path=raw.get("db_path", "flightmon.db"),
    )
