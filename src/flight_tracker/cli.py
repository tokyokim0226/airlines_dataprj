from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from flight_tracker.analysis import get_price_history
from flight_tracker.collector import collect_prices
from flight_tracker.database import FlightPriceDatabase
from flight_tracker.mock_provider import MockFlightProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect local mock flight prices.")
    parser.add_argument("--database", default="flight_prices.sqlite3")
    parser.add_argument("--origin", default="LAX")
    parser.add_argument("--destination", default="JFK")
    parser.add_argument("--departure-date", default=date.today().isoformat())
    args = parser.parse_args()

    departure_date = date.fromisoformat(args.departure_date)
    database = FlightPriceDatabase(Path(args.database))
    provider = MockFlightProvider()

    collect_prices(
        provider=provider,
        database=database,
        origin=args.origin,
        destination=args.destination,
        departure_date=departure_date,
    )
    history = get_price_history(database, args.origin, args.destination, departure_date)

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
