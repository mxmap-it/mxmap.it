"""Command-line entry point: ``flightmon once`` and ``flightmon watch``."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime, timedelta

from .alerts import Alerter
from .chains import Chain, find_cheapest_chains
from .config import load_config
from .corridor import ADJACENCY, AIRPORTS
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


def _fmt_delta(td: timedelta) -> str:
    mins = int(td.total_seconds() // 60)
    return f"{mins // 60}h{mins % 60:02d}m"


def _render_chain(chain: Chain, idx: int) -> str:
    route = " → ".join(chain.route)
    lines = [
        f"#{idx}  {chain.total_price:.0f} {chain.currency}  "
        f"| {chain.hops} voli | {route}"
    ]
    layovers = chain.layovers()
    for i, leg in enumerate(chain.legs):
        dep = leg.depart_dt.strftime("%d/%m %H:%M")
        arr = leg.arrive_dt.strftime("%d/%m %H:%M")
        lines.append(
            f"   {leg.origin} {dep} → {leg.destination} {arr}  "
            f"{leg.carrier:<3} {leg.price:>6.0f} {leg.currency}"
        )
        if i < len(layovers):
            hub = AIRPORTS.get(leg.destination)
            note = f"  [{hub.transit_note}]" if hub and hub.transit_note else ""
            lines.append(
                f"      ↳ scalo {leg.destination} {_fmt_delta(layovers[i])}{note}"
            )

    visas = [
        AIRPORTS[c].city
        for c in chain.route[1:-1]
        if c in AIRPORTS and AIRPORTS[c].needs_transit_visa
    ]
    if visas:
        lines.append(f"   ⚠️  visto di transito necessario: {', '.join(visas)}")
    dest = AIRPORTS.get(chain.route[-1])
    if dest and dest.transit_note:
        lines.append(f"   🛬 {dest.city}: {dest.transit_note}")
    return "\n".join(lines)


def _chain(args) -> int:
    origins = [o.strip().upper() for o in args.origins.split(",") if o.strip()]
    base = (
        date.fromisoformat(args.depart)
        if args.depart
        else date.today() + timedelta(days=30)
    )
    depart_days = [base + timedelta(days=i) for i in range(max(1, args.days))]

    if args.mock:
        from .demo import build_demo_pricer

        pricer = build_demo_pricer(base)
    else:
        try:
            from .pricer import AmadeusPricer

            pricer = AmadeusPricer(currency=args.currency)
        except Exception as exc:  # noqa: BLE001
            print(
                f"Pricer Amadeus non disponibile: {exc}\n"
                "Imposta AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET, "
                "oppure prova l'esempio offline con --mock.",
                file=sys.stderr,
            )
            return 2

    print(
        f"Cerco catene {','.join(origins)} → {args.to} "
        f"(dal {base}, finestra {args.days}g, max {args.max_legs} scali)…"
    )
    chains = find_cheapest_chains(
        pricer,
        origins,
        args.to.upper(),
        ADJACENCY,
        depart_days,
        min_connection_hours=args.min_connection,
        max_layover_hours=args.max_layover,
        max_legs=args.max_legs,
        top_n=args.top,
    )
    if not chains:
        print("Nessuna catena trovata con questi vincoli.")
        return 0
    print(f"\nTrovate {len(chains)} catene (ordinate per prezzo):\n")
    for i, chain in enumerate(chains, 1):
        print(_render_chain(chain, i))
        print()
    return 0


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

    chain = sub.add_parser(
        "chain",
        help="compose the cheapest multi-stop self-transfer chain",
    )
    chain.add_argument("--to", default="CMB", help="destination IATA (default CMB)")
    chain.add_argument(
        "--from",
        dest="origins",
        default="FCO,NAP",
        help="comma-separated origin IATAs (default FCO,NAP)",
    )
    chain.add_argument("--depart", help="earliest departure date YYYY-MM-DD")
    chain.add_argument(
        "--days", type=int, default=1, help="departure window in days (default 1)"
    )
    chain.add_argument(
        "--max-legs", type=int, default=5, dest="max_legs",
        help="maximum number of flights (default 5)",
    )
    chain.add_argument(
        "--min-connection", type=float, default=3.0, dest="min_connection",
        help="minimum self-transfer layover, hours (default 3)",
    )
    chain.add_argument(
        "--max-layover", type=float, default=30.0, dest="max_layover",
        help="maximum layover, hours — allows overnight (default 30)",
    )
    chain.add_argument("--top", type=int, default=5, help="how many chains to show")
    chain.add_argument("--currency", default="EUR")
    chain.add_argument(
        "--mock", action="store_true", help="use offline demo fares (no API key)"
    )

    args = parser.parse_args(argv)

    if args.command == "chain":
        return _chain(args)

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
