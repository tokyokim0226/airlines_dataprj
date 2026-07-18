from datetime import UTC, date, datetime
from decimal import Decimal

from flight_tracker.analysis import get_price_history
from flight_tracker.collector import collect_prices
from flight_tracker.database import FlightPriceDatabase
from flight_tracker.mock_provider import MockFlightProvider


def test_repeated_collection_creates_multiple_historical_observations(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")
    provider = MockFlightProvider(prices=[Decimal("250.00"), Decimal("275.00")])
    departure_date = date(2026, 8, 1)

    collect_prices(
        provider=provider,
        database=database,
        origin="LAX",
        destination="JFK",
        departure_date=departure_date,
        observed_at=datetime(2026, 7, 1, 10, tzinfo=UTC),
    )
    collect_prices(
        provider=provider,
        database=database,
        origin="LAX",
        destination="JFK",
        departure_date=departure_date,
        observed_at=datetime(2026, 7, 2, 10, tzinfo=UTC),
    )

    history = get_price_history(database, "LAX", "JFK", departure_date)

    assert len(history) == 2
    assert [observation.offer.price_amount for observation in history] == [
        Decimal("250.00"),
        Decimal("275.00"),
    ]
    assert history[0].id != history[1].id
    assert history[0].observed_at < history[1].observed_at
