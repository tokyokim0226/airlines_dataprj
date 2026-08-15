from datetime import UTC, datetime
from decimal import Decimal

from flight_tracker.cohorts import build_monthly_baseline_cohort
from flight_tracker.collector import collect_due_prices
from flight_tracker.database import FlightPriceDatabase
from flight_tracker.mock_provider import MockFlightProvider
from flight_tracker.routes import Route
from flight_tracker.scheduling import build_observation_schedule


def seed_one_due_cohort(database: FlightPriceDatabase) -> None:
    route = Route(
        route_id="SEOUL_TO_LONDON",
        origin_city="Seoul",
        destination_city="London",
        origin_airports=("ICN", "GMP"),
        destination_airports=("LHR", "LGW"),
    )
    cohort = build_monthly_baseline_cohort(route, 2027, 2)

    database.initialize()
    database.upsert_route(route)
    database.upsert_trip_cohort(cohort)
    for scheduled_observation in build_observation_schedule(cohort):
        if scheduled_observation.scheduled_lead_time_days == 180:
            database.upsert_scheduled_observation(scheduled_observation)


def test_collect_due_prices_collects_scheduled_observations(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")
    seed_one_due_cohort(database)
    provider = MockFlightProvider(prices=[Decimal("500.00"), Decimal("1500.00")])

    observations = collect_due_prices(
        provider=provider,
        database=database,
        due_date=datetime(2026, 8, 16).date(),
        observed_at=datetime(2026, 8, 16, 10, tzinfo=UTC),
    )

    assert len(observations) == 2
    assert {observation.offer.travel_class for observation in observations} == {
        "economy",
        "business",
    }
    assert {observation.offer.origin for observation in observations} == {"ICN"}
    assert {observation.offer.destination for observation in observations} == {"LHR"}
    assert {
        observation.offer.departure_time.date() for observation in observations
    } == {datetime(2027, 2, 12).date()}

    raw_responses = database.get_raw_provider_responses()

    assert len(raw_responses) == 2
    assert all(
        '"provider": "mock"' in response.response_text for response in raw_responses
    )


def test_collect_due_prices_is_append_only_when_run_repeatedly(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")
    seed_one_due_cohort(database)
    provider = MockFlightProvider(prices=[Decimal("500.00"), Decimal("550.00")])

    collect_due_prices(
        provider=provider,
        database=database,
        due_date=datetime(2026, 8, 16).date(),
        observed_at=datetime(2026, 8, 16, 10, tzinfo=UTC),
    )
    collect_due_prices(
        provider=provider,
        database=database,
        due_date=datetime(2026, 8, 16).date(),
        observed_at=datetime(2026, 8, 16, 11, tzinfo=UTC),
    )

    history = database.get_price_history(
        origin="ICN",
        destination="LHR",
        departure_date=datetime(2027, 2, 12).date(),
    )

    assert len(history) == 4
    assert len({observation.id for observation in history}) == 4
    assert [observation.observed_at.hour for observation in history] == [10, 10, 11, 11]


def test_collect_due_prices_returns_empty_when_nothing_is_due(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")
    seed_one_due_cohort(database)
    provider = MockFlightProvider()

    observations = collect_due_prices(
        provider=provider,
        database=database,
        due_date=datetime(2026, 8, 17).date(),
        observed_at=datetime(2026, 8, 17, 10, tzinfo=UTC),
    )

    assert observations == []
