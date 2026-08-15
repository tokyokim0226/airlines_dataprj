from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from flight_tracker.analysis import get_price_history
from flight_tracker.collector import collect_prices
from flight_tracker.database import FlightPriceDatabase
from flight_tracker.mock_provider import MockFlightProvider
from flight_tracker.seed import seed_baseline_schedule


def main() -> None:
    # argparse turns terminal flags into Python values.
    parser = argparse.ArgumentParser(description="Run the local flight price pipeline.")
    parser.add_argument("--database", default="flight_prices.sqlite3")

    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser(
        "seed-baseline",
        help="Seed Phase 1 routes, monthly baseline cohorts, and schedules.",
    )
    seed_parser.add_argument("--start-year", type=int, required=True)
    seed_parser.add_argument("--end-year", type=int, required=True)

    collect_parser = subparsers.add_parser(
        "collect",
        help="Collect one local mock route/date search and print its history.",
    )
    collect_parser.add_argument("--origin", default="LAX")
    collect_parser.add_argument("--destination", default="JFK")
    collect_parser.add_argument("--departure-date", default=date.today().isoformat())

    args = parser.parse_args()

    # The CLI wires concrete local pieces together: SQLite plus mock data.
    database = FlightPriceDatabase(Path(args.database))

    if args.command == "seed-baseline":
        result = seed_baseline_schedule(
            database=database,
            start_year=args.start_year,
            end_year=args.end_year,
        )
        print(
            "Seeded "
            f"{result.route_count} routes, "
            f"{result.cohort_count} cohorts, "
            f"{result.scheduled_observation_count} scheduled observations."
        )
        return

    departure_date = date.fromisoformat(args.departure_date)
    provider = MockFlightProvider()

    collect_prices(
        provider=provider,
        database=database,
        origin=args.origin,
        destination=args.destination,
        departure_date=departure_date,
    )
    history = get_price_history(database, args.origin, args.destination, departure_date)

    # Print the full history after this collection so the CLI shows accumulation.
    for observation in history:
        offer = observation.offer
        print(
            f"{observation.observed_at.isoformat()} "
            f"{offer.origin}->{offer.destination} "
            f"{offer.departure_time.date().isoformat()} "
            f"{offer.airline} {offer.price_amount} {offer.currency}"
        )


if __name__ == "__main__":
    main()
