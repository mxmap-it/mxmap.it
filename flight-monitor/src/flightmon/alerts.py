"""Alert channels: console, CSV log, Telegram, email."""

from __future__ import annotations

import csv
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

import requests

from .config import AlertConfig
from .models import Opportunity

_CSV_HEADER = [
    "seen_at",
    "route",
    "origin",
    "destination",
    "depart_date",
    "return_date",
    "nights",
    "price",
    "currency",
    "provider",
    "threshold",
    "historic_low",
    "previous_low",
]


def format_opportunity(opp: Opportunity) -> str:
    q = opp.quote
    tags = " ".join(f"[{r}]" for r in opp.reasons)
    return (
        f"✈️  {q.origin}→{q.destination}  "
        f"{q.price:.0f} {q.currency}  {tags}\n"
        f"    {q.depart_date} → {q.return_date} ({q.nights} nights)  "
        f"via {q.provider}\n"
        f"    {q.deep_link or ''}".rstrip()
    )


class Alerter:
    def __init__(self, config: AlertConfig):
        self.config = config

    def emit(self, opp: Opportunity) -> None:
        if self.config.console:
            print(format_opportunity(opp))
        if self.config.csv_path:
            self._csv(opp)
        if self.config.telegram.enabled:
            self._telegram(opp)
        if self.config.email.enabled:
            self._email(opp)

    # -- channels ---------------------------------------------------------
    def _csv(self, opp: Opportunity) -> None:
        q = opp.quote
        path = Path(self.config.csv_path)
        exists = path.exists()
        with path.open("a", newline="") as fh:
            w = csv.writer(fh)
            if not exists:
                w.writerow(_CSV_HEADER)
            w.writerow(
                [
                    datetime.now(timezone.utc).isoformat(),
                    q.route,
                    q.origin,
                    q.destination,
                    q.depart_date.isoformat(),
                    q.return_date.isoformat(),
                    q.nights,
                    f"{q.price:.2f}",
                    q.currency,
                    q.provider,
                    "" if opp.threshold_eur is None else f"{opp.threshold_eur:.0f}",
                    opp.historic_low,
                    "" if opp.previous_low is None else f"{opp.previous_low:.2f}",
                ]
            )

    def _telegram(self, opp: Opportunity) -> None:
        tg = self.config.telegram
        try:
            requests.post(
                f"https://api.telegram.org/bot{tg.bot_token}/sendMessage",
                data={"chat_id": tg.chat_id, "text": format_opportunity(opp)},
                timeout=15,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[alert] telegram failed: {exc}")

    def _email(self, opp: Opportunity) -> None:
        em = self.config.email
        try:
            msg = EmailMessage()
            q = opp.quote
            msg["Subject"] = (
                f"Flight deal {q.origin}→{q.destination} "
                f"{q.price:.0f}{q.currency}"
            )
            msg["From"] = em.sender or em.username
            msg["To"] = ", ".join(em.recipients)
            msg.set_content(format_opportunity(opp))
            with smtplib.SMTP(em.smtp_host, em.smtp_port, timeout=20) as s:
                s.starttls()
                if em.username:
                    s.login(em.username, em.password)
                s.send_message(msg)
        except Exception as exc:  # noqa: BLE001
            print(f"[alert] email failed: {exc}")
