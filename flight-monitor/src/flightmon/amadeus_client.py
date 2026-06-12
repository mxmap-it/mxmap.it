"""Shared Amadeus Self-Service client: OAuth token + JSON GET helper.

Used by both the round-trip provider and the chain pricer. Credentials come
from the environment:

    AMADEUS_CLIENT_ID, AMADEUS_CLIENT_SECRET
    AMADEUS_HOST = test (default) | production
"""

from __future__ import annotations

import os
import time

import requests

_HOSTS = {
    "test": "https://test.api.amadeus.com",
    "production": "https://api.amadeus.com",
}


class AmadeusClient:
    def __init__(self):
        self.client_id = os.environ.get("AMADEUS_CLIENT_ID", "")
        self.client_secret = os.environ.get("AMADEUS_CLIENT_SECRET", "")
        if not (self.client_id and self.client_secret):
            raise RuntimeError(
                "AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET not set"
            )
        self.base = _HOSTS.get(
            os.environ.get("AMADEUS_HOST", "test"), _HOSTS["test"]
        )
        self.session = requests.Session()
        self._token = ""
        self._token_exp = 0.0

    def token(self) -> str:
        if self._token and time.time() < self._token_exp - 30:
            return self._token
        resp = self.session.post(
            f"{self.base}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_exp = time.time() + data.get("expires_in", 1799)
        return self._token

    def get(self, path: str, params: dict) -> dict | None:
        """GET an Amadeus endpoint; returns parsed JSON or None on non-200."""
        resp = self.session.get(
            f"{self.base}{path}",
            headers={"Authorization": f"Bearer {self.token()}"},
            params=params,
            timeout=30,
        )
        if resp.status_code != 200:
            return None
        return resp.json()
