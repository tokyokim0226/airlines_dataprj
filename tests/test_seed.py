from datetime import UTC, datetime

import pytest

from flight_tracker.database import FlightPriceDatabase
from flight_tracker.seed import seed_baseline_schedule
from flight_tracker.scheduling import LEAD_TIME_CHECKPOINT_DAYS, TRAVEL_CLASSES


def test_seed_baseline_schedule_creates_one_year_phase_one_plan(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")

    result = seed_baseline_schedule(
        database=database,
        start_year=2027,
        end_year=2027,
        created_at=datetime(2026, 8, 16, 10, tzinfo=UTC),
    )

    route_count = 12
    cohort_count = route_count * 12
    scheduled_observation_count = (
        cohort_count * len(LEAD_TIME_CHECKPOINT_DAYS) * len(TRAVEL_CLASSES)
    )

    assert result.route_count == route_count
    assert result.cohort_count == cohort_count
    assert result.scheduled_observation_count == scheduled_observation_count
    assert len(database.get_routes()) == route_count
    assert len(database.get_trip_cohorts()) == cohort_count
    assert len(database.get_scheduled_observations()) == scheduled_observation_count


def test_seed_baseline_schedule_is_idempotent(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")

    seed_baseline_schedule(database, 2027, 2027)
    seed_baseline_schedule(database, 2027, 2027)

    assert len(database.get_routes()) == 12
    assert len(database.get_trip_cohorts()) == 12 * 12
    assert len(database.get_scheduled_observations()) == (
        12 * 12 * len(LEAD_TIME_CHECKPOINT_DAYS) * len(TRAVEL_CLASSES)
    )


def test_seed_baseline_schedule_rejects_invalid_year_range(tmp_path) -> None:
    database = FlightPriceDatabase(tmp_path / "prices.sqlite3")

    with pytest.raises(ValueError, match="end_year"):
        seed_baseline_schedule(database, 2028, 2027)
