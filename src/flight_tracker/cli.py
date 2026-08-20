from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from flight_tracker.analysis import get_price_history
from flight_tracker.collector import collect_due_prices, collect_prices
from flight_tracker.database import FlightPriceDatabase
from flight_tracker.mock_provider import MockFlightProvider
from flight_tracker.seed import seed_baseline_schedule
from flight_tracker.serpapi_client import (
    build_serpapi_google_flights_url,
    default_google_flights_fixture_request,
    fetch_serpapi_google_flights_fixture,
    load_serpapi_api_key_from_environment,
    save_serpapi_fixture,
)


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

    collect_due_parser = subparsers.add_parser(
        "collect-due",
        help="Collect local mock prices for scheduled observations due on a date.",
    )
    collect_due_parser.add_argument("--date", default=date.today().isoformat())

    serpapi_fixture_parser = subparsers.add_parser(
        "fetch-serpapi-fixture",
        help="Fetch exactly one SerpAPI Google Flights fixture JSON response.",
    )
    serpapi_fixture_parser.add_argument(
        "--output",
        default="tests/fixtures/serpapi_google_flights_icn_lhr_2027_02_12_economy.json",
    )
    serpapi_fixture_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the request URL without calling SerpAPI.",
    )

    collect_parser = subparsers.add_parser(
        "collect",
        help="Collect one local mock route/date search and print its history.",
    )
    collect_parser.add_argument("--origin", default="LAX")
    collect_parser.add_argument("--destination", default="JFK")
    collect_parser.add_argument("--departure-date", default=date.today().isoformat())
    collect_parser.add_argument(
        "--travel-class",
        choices=("economy", "business"),
        default="economy",
    )

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

    if args.command == "fetch-serpapi-fixture":
        fixture_request = default_google_flights_fixture_request()
        if args.dry_run:
            print(build_serpapi_google_flights_url(fixture_request, "REDACTED"))
            return

        api_key = load_serpapi_api_key_from_environment()
        payload = fetch_serpapi_google_flights_fixture(fixture_request, api_key)
        output_path = save_serpapi_fixture(payload, Path(args.output))
        print(f"Saved SerpAPI fixture to {output_path}.")
        return

    provider = MockFlightProvider()

    if args.command == "collect-due":
        due_date = date.fromisoformat(args.date)
        observations = collect_due_prices(
            provider=provider,
            database=database,
            due_date=due_date,
        )
        print(f"Collected {len(observations)} price observations for {due_date}.")
        return

    departure_date = date.fromisoformat(args.departure_date)

    collect_prices(
        provider=provider,
        database=database,
        origin=args.origin,
        destination=args.destination,
        departure_date=departure_date,
        travel_class=args.travel_class,
    )
    history = get_price_history(database, args.origin, args.destination, departure_date)

    # Print the full history after this collection so the CLI shows accumulation.
    for observation in history:
        offer = observation.offer
        print(
            f"{observation.observed_at.isoformat()} "
            f"{offer.origin}->{offer.destination} "
            f"{offer.departure_time.date().isoformat()} "
            f"{offer.airline} {offer.travel_class} "
            f"{offer.price_amount} {offer.currency}"
        )


if __name__ == "__main__":
    main()
