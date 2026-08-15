from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from flight_tracker.cohorts import build_monthly_baseline_cohort
from flight_tracker.database import FlightPriceDatabase
from flight_tracker.models import FlightOffer, PriceObservation, SearchRun
from flight_tracker.routes import Route
from flight_tracker.scheduling import build_observation_schedule


def test_database_stores_and_returns_routes(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")
    database.initialize()
    route = Route(
        route_id="SEOUL_TO_LONDON",
        origin_city="Seoul",
        destination_city="London",
        origin_airports=("ICN", "GMP"),
        destination_airports=("LHR", "LGW"),
    )

    database.upsert_route(route)
    database.upsert_route(route)

    assert database.get_routes() == [route]


def test_database_stores_and_returns_trip_cohorts(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")
    database.initialize()
    route = Route(
        route_id="SEOUL_TO_LONDON",
        origin_city="Seoul",
        destination_city="London",
        origin_airports=("ICN", "GMP"),
        destination_airports=("LHR", "LGW"),
    )
    cohort = build_monthly_baseline_cohort(route, 2027, 2)

    database.upsert_route(route)
    database.upsert_trip_cohort(cohort)
    database.upsert_trip_cohort(cohort)

    assert database.get_trip_cohorts(route.route_id) == [cohort]


def test_database_stores_and_returns_scheduled_observations(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")
    database.initialize()
    route = Route(
        route_id="SEOUL_TO_LONDON",
        origin_city="Seoul",
        destination_city="London",
        origin_airports=("ICN", "GMP"),
        destination_airports=("LHR", "LGW"),
    )
    cohort = build_monthly_baseline_cohort(route, 2027, 2)
    schedule = build_observation_schedule(cohort, travel_classes=("economy",))

    database.upsert_route(route)
    database.upsert_trip_cohort(cohort)
    for observation in schedule:
        database.upsert_scheduled_observation(observation)
        database.upsert_scheduled_observation(observation)

    stored_schedule = database.get_scheduled_observations(cohort.cohort_id)

    assert stored_schedule == list(schedule)


def test_database_returns_scheduled_observations_due_on_date(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")
    database.initialize()
    route = Route(
        route_id="SEOUL_TO_LONDON",
        origin_city="Seoul",
        destination_city="London",
        origin_airports=("ICN", "GMP"),
        destination_airports=("LHR", "LGW"),
    )
    cohort = build_monthly_baseline_cohort(route, 2027, 2)

    database.upsert_route(route)
    database.upsert_trip_cohort(cohort)
    for observation in build_observation_schedule(cohort):
        database.upsert_scheduled_observation(observation)

    due = database.get_scheduled_observations_due_on(date(2026, 8, 16))

    assert len(due) == 2
    assert {observation.travel_class for observation in due} == {"economy", "business"}
    assert {observation.scheduled_lead_time_days for observation in due} == {180}


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
