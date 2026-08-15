from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from flight_tracker.cohorts import build_monthly_baseline_cohort
from flight_tracker.database import FlightPriceDatabase
from flight_tracker.routes import build_fixed_routes
from flight_tracker.scheduling import build_observation_schedule


@dataclass(frozen=True)
class SeedResult:
    """Counts for the planned route/cohort/schedule rows created by seeding."""

    route_count: int
    cohort_count: int
    scheduled_observation_count: int


def seed_baseline_schedule(
    database: FlightPriceDatabase,
    start_year: int,
    end_year: int,
    created_at: datetime | None = None,
) -> SeedResult:
    """Seed fixed Phase 1 routes, monthly baseline cohorts, and schedules."""

    if end_year < start_year:
        raise ValueError("end_year must be greater than or equal to start_year")

    database.initialize()
    seeded_at = created_at or datetime.now(UTC)

    route_count = 0
    cohort_count = 0
    scheduled_observation_count = 0

    for route in build_fixed_routes():
        database.upsert_route(route)
        route_count += 1

        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                cohort = build_monthly_baseline_cohort(
                    route=route,
                    year=year,
                    month=month,
                    created_at=seeded_at,
                )
                database.upsert_trip_cohort(cohort)
                cohort_count += 1

                for observation in build_observation_schedule(cohort):
                    database.upsert_scheduled_observation(observation)
                    scheduled_observation_count += 1

    return SeedResult(
        route_count=route_count,
        cohort_count=cohort_count,
        scheduled_observation_count=scheduled_observation_count,
    )
