from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from flight_tracker.database import FlightPriceDatabase
from flight_tracker.models import FlightOffer, PriceObservation, SearchRun


def test_database_returns_price_history_in_chronological_order(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")
    database.initialize()
    departure_date = date(2026, 8, 1)
    departure_time = datetime(2026, 8, 1, 9, tzinfo=UTC)
    search_run = database.insert_search_run(
        SearchRun(
            origin="LAX",
            destination="JFK",
            departure_date=departure_date,
            provider="mock",
            started_at=datetime(2026, 7, 1, 10, tzinfo=UTC),
        )
    )

    later = PriceObservation(
        offer=FlightOffer(
            origin="LAX",
            destination="JFK",
            departure_time=departure_time,
            arrival_time=departure_time + timedelta(hours=5),
            price_amount=Decimal("220.00"),
            currency="USD",
            airline="Mock Air",
            stops=0,
            provider="mock",
        ),
        observed_at=datetime(2026, 7, 2, 10, tzinfo=UTC),
        search_run_id=search_run.id,
    )
    earlier = PriceObservation(
        offer=FlightOffer(
            origin="LAX",
            destination="JFK",
            departure_time=departure_time,
            arrival_time=departure_time + timedelta(hours=5),
            price_amount=Decimal("210.00"),
            currency="USD",
            airline="Mock Air",
            stops=0,
            provider="mock",
        ),
        observed_at=datetime(2026, 7, 1, 10, tzinfo=UTC),
        search_run_id=search_run.id,
    )

    database.insert_price_observation(later)
    database.insert_price_observation(earlier)

    history = database.get_price_history("LAX", "JFK", departure_date)

    assert [observation.offer.price_amount for observation in history] == [
        Decimal("210.00"),
        Decimal("220.00"),
    ]
