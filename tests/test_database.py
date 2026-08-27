from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from flight_tracker.cohorts import build_monthly_baseline_cohort
from flight_tracker.database import FlightPriceDatabase
from flight_tracker.models import (
    FlightSegment,
    PriceObservation,
    TripOffer,
    RawProviderResponse,
    SearchRun,
)
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


def test_database_stores_raw_provider_responses(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")
    database.initialize()
    search_run = database.insert_search_run(
        SearchRun(
            origin="ICN",
            destination="LHR",
            departure_date=date(2027, 2, 12),
            return_date=date(2027, 2, 21),
            provider="mock",
            started_at=datetime(2026, 8, 16, 10, tzinfo=UTC),
            travel_class="business",
        )
    )

    stored = database.insert_raw_provider_response(
        RawProviderResponse(
            search_run_id=search_run.id or 0,
            provider="mock",
            captured_at=datetime(2026, 8, 16, 10, tzinfo=UTC),
            response_text='{"provider":"mock","offers":[]}',
        )
    )

    responses = database.get_raw_provider_responses(search_run.id)

    assert stored.id is not None
    assert len(responses) == 1
    assert responses[0].response_text == '{"provider":"mock","offers":[]}'
    assert responses[0].search_run_id == search_run.id


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
            return_date=departure_date + timedelta(days=7),
            provider="mock",
            started_at=datetime(2026, 7, 1, 10, tzinfo=UTC),
        )
    )

    later = PriceObservation(
        trip_offer=TripOffer(
            origin="LAX",
            destination="JFK",
            departure_date=departure_date,
            return_date=departure_date + timedelta(days=7),
            price_amount=Decimal("220.00"),
            currency="USD",
            provider="mock",
            airline_summary="Mock Air",
            segments=(
                FlightSegment(
                    direction="outbound",
                    segment_order=1,
                    origin="LAX",
                    destination="JFK",
                    departure_time=departure_time,
                    arrival_time=departure_time + timedelta(hours=5),
                    airline="Mock Air",
                    duration_minutes=300,
                ),
            ),
        ),
        observed_at=datetime(2026, 7, 2, 10, tzinfo=UTC),
        search_run_id=search_run.id,
    )
    earlier = PriceObservation(
        trip_offer=TripOffer(
            origin="LAX",
            destination="JFK",
            departure_date=departure_date,
            return_date=departure_date + timedelta(days=7),
            price_amount=Decimal("210.00"),
            currency="USD",
            provider="mock",
            airline_summary="Mock Air",
            segments=(
                FlightSegment(
                    direction="outbound",
                    segment_order=1,
                    origin="LAX",
                    destination="JFK",
                    departure_time=departure_time,
                    arrival_time=departure_time + timedelta(hours=5),
                    airline="Mock Air",
                    duration_minutes=300,
                ),
            ),
        ),
        observed_at=datetime(2026, 7, 1, 10, tzinfo=UTC),
        search_run_id=search_run.id,
    )

    database.insert_price_observation(later)
    database.insert_price_observation(earlier)

    history = database.get_price_history("LAX", "JFK", departure_date)

    assert [observation.trip_offer.price_amount for observation in history] == [
        Decimal("210.00"),
        Decimal("220.00"),
    ]
    assert len(history[0].trip_offer.segments) == 1
    assert history[0].trip_offer.segments[0].trip_offer_id == history[0].trip_offer.id
