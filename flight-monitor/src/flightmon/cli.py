"""Command-line entry point: ``flightmon once`` and ``flightmon watch``."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

from .alerts import Alerter
from .config import load_config
from .monitor import run_once
from .providers import build_providers
from .store import Store


def _run(args) -> int:
    config = load_config(args.config)
    providers = build_providers(config.providers, config)
    if not providers:
        print("No usable providers configured. Aborting.", file=sys.stderr)
        return 2
    store = Store(config.db_path)
    alerter = Alerter(config.alerts)
    try:
        return run_once(config, providers, store, alerter)
    finally:
        store.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="flightmon",
        description="Monitor Nordic budget flights for flexible 3-4 day trips.",
    )
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="path to config.yaml"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("once", help="run a single scan and exit")

    watch = sub.add_parser("watch", help="scan repeatedly on an interval")
    watch.add_argument(
        "--interval",
        type=int,
        default=60,
        help="minutes between scans (default: 60)",
    )

    args = parser.parse_args(argv)

    if args.command == "once":
        return 0 if _run(args) >= 0 else 1

    if args.command == "watch":
        print(f"[watch] every {args.interval} min — Ctrl-C to stop")
        while True:
            print(f"[watch] scan at {datetime.now():%Y-%m-%d %H:%M}")
            try:
                _run(args)
            except Exception as exc:  # noqa: BLE001 - keep the loop alive
                print(f"[watch] scan error: {exc}")
            time.sleep(args.interval * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
