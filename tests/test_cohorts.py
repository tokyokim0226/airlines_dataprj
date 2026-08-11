from datetime import UTC, datetime

import pytest

from flight_tracker.cohorts import TripCohort, build_monthly_baseline_cohort
from flight_tracker.routes import Route


def test_valid_baseline_trip_cohort() -> None:
    cohort = TripCohort(
        cohort_id="SEOUL_TO_LONDON_2027_02_BASELINE",
        route_id="SEOUL_TO_LONDON",
        cohort_type="baseline",
        departure_date=datetime(2027, 2, 12).date(),
        return_date=datetime(2027, 2, 21).date(),
        trip_duration_days=9,
        created_at=datetime(2026, 8, 11, 10, tzinfo=UTC),
    )

    assert cohort.route_id == "SEOUL_TO_LONDON"
    assert cohort.cohort_type == "baseline"
    assert cohort.active is True


def test_trip_cohort_allows_event_and_personal_types() -> None:
    event = TripCohort(
        cohort_id="SEOUL_TO_LONDON_LUNAR_NEW_YEAR",
        route_id="SEOUL_TO_LONDON",
        cohort_type="event",
        departure_date=datetime(2027, 2, 5).date(),
        return_date=datetime(2027, 2, 12).date(),
        trip_duration_days=7,
        label="Lunar New Year",
    )
    personal = TripCohort(
        cohort_id="LONDON_TO_SEOUL_FAMILY_VISIT",
        route_id="LONDON_TO_SEOUL",
        cohort_type="personal",
        departure_date=datetime(2027, 4, 3).date(),
        return_date=datetime(2027, 4, 17).date(),
        trip_duration_days=14,
        label="family visit",
    )

    assert event.label == "Lunar New Year"
    assert personal.trip_duration_days == 14


def test_trip_cohort_rejects_invalid_type() -> None:
    with pytest.raises(ValueError, match="cohort_type"):
        TripCohort(
            cohort_id="SEOUL_TO_LONDON_BAD",
            route_id="SEOUL_TO_LONDON",
            cohort_type="holiday",
            departure_date=datetime(2027, 2, 10).date(),
            return_date=datetime(2027, 2, 21).date(),
            trip_duration_days=9,
        )


def test_trip_cohort_rejects_missing_route_id() -> None:
    with pytest.raises(ValueError, match="route_id"):
        TripCohort(
            cohort_id="SEOUL_TO_LONDON_2027_02_BASELINE",
            route_id="",
            cohort_type="baseline",
            departure_date=datetime(2027, 2, 10).date(),
            return_date=datetime(2027, 2, 21).date(),
            trip_duration_days=9,
        )


def test_trip_cohort_rejects_return_before_departure() -> None:
    with pytest.raises(ValueError, match="return_date"):
        TripCohort(
            cohort_id="SEOUL_TO_LONDON_BAD_DATES",
            route_id="SEOUL_TO_LONDON",
            cohort_type="baseline",
            departure_date=datetime(2027, 2, 17).date(),
            return_date=datetime(2027, 2, 10).date(),
            trip_duration_days=7,
        )


def test_trip_cohort_rejects_duration_mismatch() -> None:
    with pytest.raises(ValueError, match="trip_duration_days"):
        TripCohort(
            cohort_id="SEOUL_TO_LONDON_BAD_DURATION",
            route_id="SEOUL_TO_LONDON",
            cohort_type="baseline",
            departure_date=datetime(2027, 2, 10).date(),
            return_date=datetime(2027, 2, 21).date(),
            trip_duration_days=8,
        )


def test_baseline_trip_cohort_must_use_approved_duration() -> None:
    with pytest.raises(ValueError, match="baseline"):
        TripCohort(
            cohort_id="SEOUL_TO_LONDON_LONG_BASELINE",
            route_id="SEOUL_TO_LONDON",
            cohort_type="baseline",
            departure_date=datetime(2027, 2, 10).date(),
            return_date=datetime(2027, 2, 20).date(),
            trip_duration_days=10,
        )


def test_trip_cohort_created_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="created_at"):
        TripCohort(
            cohort_id="SEOUL_TO_LONDON_2027_02_BASELINE",
            route_id="SEOUL_TO_LONDON",
            cohort_type="baseline",
            departure_date=datetime(2027, 2, 12).date(),
            return_date=datetime(2027, 2, 21).date(),
            trip_duration_days=9,
            created_at=datetime(2026, 8, 11, 10),
        )


def test_build_monthly_baseline_cohort_uses_second_friday_to_following_sunday() -> None:
    route = Route(
        route_id="SEOUL_TO_LONDON",
        origin_city="Seoul",
        destination_city="London",
        origin_airports=("ICN", "GMP"),
        destination_airports=("LHR", "LGW"),
    )

    cohort = build_monthly_baseline_cohort(route, 2027, 2)

    assert cohort.cohort_id == "SEOUL_TO_LONDON_2027_02_BASELINE"
    assert cohort.departure_date == datetime(2027, 2, 12).date()
    assert cohort.return_date == datetime(2027, 2, 21).date()
    assert cohort.trip_duration_days == 9


def test_build_monthly_baseline_cohort_handles_month_starting_on_friday() -> None:
    route = Route(
        route_id="LONDON_TO_SEOUL",
        origin_city="London",
        destination_city="Seoul",
        origin_airports=("LHR", "LGW"),
        destination_airports=("ICN", "GMP"),
    )

    cohort = build_monthly_baseline_cohort(route, 2027, 1)

    assert cohort.departure_date == datetime(2027, 1, 8).date()
    assert cohort.return_date == datetime(2027, 1, 17).date()
