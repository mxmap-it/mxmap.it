#!/usr/bin/env python3
"""Submit site URLs to IndexNow — scheduled, slow, page-by-page (rolling slices).

IndexNow is today's standard "ping" protocol: ONE POST to api.indexnow.org
shares the submitted URLs with ALL participating engines (Bing, Yandex,
Seznam, Naver, Yep — they exchange submissions with each other). Google does
NOT participate (and retired its sitemap-ping endpoint in 2023): for Google
the levers remain the maintained sitemap (<lastmod> from kpi.json), internal
linking and authority — no per-page ping exists there.

Strategy ("schedulato e con calma"): read the LIVE sitemap index + children,
sort the full URL list, split it into chunks of ``--per-day`` and submit only
today's chunk, chosen by days-since-epoch modulo the number of chunks. The
whole site is thus (re)submitted on a rolling cycle — ~1 month at 1000/day
for ~30k URLs — without ever bursting, then cycles again (URLs re-signal
freshness after each nightly data refresh).

The IndexNow key is PUBLIC by design: it lives in a world-readable
``https://mxmap.it/<key>.txt`` (committed at repo root) that the engines use
to verify we own the host. No secret handling needed.

Run:  python3 scripts/indexnow_submit.py [--per-day 1000] [--dry-run]
Wired into ``.github/workflows/indexnow.yml`` (daily cron + dispatch).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import date

BASE = "https://mxmap.it"
HOST = "mxmap.it"
KEY = "2cfe36c7b58ae96308ab27e9c6b8b185410f8b5c1768f7ee"
KEY_LOCATION = f"{BASE}/{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"
UA = "mxmap.it-indexnow/1.0 (+https://mxmap.it)"


def fetch(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


def collect_urls() -> list[str]:
    """All page URLs from the live sitemap (index + children, or flat urlset)."""
    root = fetch(f"{BASE}/sitemap.xml")
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", root)
    if "<sitemapindex" in root:
        pages: list[str] = []
        for child in locs:
            try:
                pages += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", fetch(child))
            except Exception as e:  # noqa: BLE001 — un figlio rotto non blocca il giro
                print(f"::warning::figlio sitemap illeggibile {child}: {e}")
        return sorted(set(pages))
    return sorted(set(locs))


def todays_slice(urls: list[str], per_day: int) -> tuple[int, int, list[str]]:
    chunks = max(1, -(-len(urls) // per_day))  # ceil
    idx = date.today().toordinal() % chunks
    return idx, chunks, urls[idx * per_day : (idx + 1) * per_day]


def submit(urls: list[str]) -> int:
    payload = json.dumps(
        {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}
    ).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": UA},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-day", type=int, default=1000)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    urls = collect_urls()
    if not urls:
        sys.exit("::error::sitemap vuoto o irraggiungibile — niente da sottomettere")
    idx, chunks, batch = todays_slice(urls, args.per_day)
    print(
        f"[indexnow] URL nel sitemap: {len(urls)} | fetta {idx + 1}/{chunks} "
        f"({len(batch)} URL): {batch[0]} … {batch[-1]}"
    )
    if args.dry_run:
        print("[indexnow] dry-run: nessuna submission")
        return

    status = submit(batch)
    if status in (200, 202):
        print(
            f"[indexnow] OK http={status} — fetta accettata (condivisa con tutti i motori IndexNow)"
        )
    elif status in (400, 403, 422):
        # 400 = payload malformato, 403 = chiave non valida, 422 = URL/host mismatch:
        # sono errori di CONFIGURAZIONE → devono rendere rosso il run.
        # ECCEZIONE NOTA (cold-start): nei primi minuti dopo la pubblicazione di
        # una chiave NUOVA il validatore può ancora vedere il 404 in cache → 403
        # transitorio. Osservato al primo run (2026-09-17): riprovato dopo pochi
        # minuti → 200. Se il 403 appare subito dopo una rotazione della chiave,
        # riprova prima di debuggare.
        sys.exit(
            f"::error::IndexNow http={status} — configurazione da correggere (chiave/host/payload)"
        )
    else:
        # 429 / 5xx: transiente — domani il cron ritenta da solo (la fetta persa
        # verrà comunque ri-sottomessa al prossimo ciclo mensile).
        print(
            f"::warning::IndexNow http={status} (transiente) — si riprova al prossimo giro"
        )


if __name__ == "__main__":
    main()
