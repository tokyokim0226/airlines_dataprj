from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from flight_tracker.routes import Route
from flight_tracker.validation import validate_aware_datetime


COHORT_TYPES = ("baseline", "event", "personal")
BASELINE_TRIP_DURATION_DAYS = 9


@dataclass(frozen=True)
class TripCohort:
    """One fixed round-trip travel period monitored repeatedly over time."""

    cohort_id: str
    route_id: str
    cohort_type: str
    departure_date: date
    return_date: date
    trip_duration_days: int
    label: str | None = None
    active: bool = True
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.cohort_id:
            raise ValueError("cohort_id is required")
        if not self.route_id:
            raise ValueError("route_id is required")
        if self.cohort_type not in COHORT_TYPES:
            raise ValueError("cohort_type must be baseline, event, or personal")
        if self.return_date <= self.departure_date:
            raise ValueError("return_date must be after departure_date")

        actual_duration = (self.return_date - self.departure_date).days
        if self.trip_duration_days != actual_duration:
            raise ValueError("trip_duration_days must match departure and return dates")
        if (
            self.cohort_type == "baseline"
            and actual_duration != BASELINE_TRIP_DURATION_DAYS
        ):
            raise ValueError(
                "baseline cohorts must use the second-Friday-to-following-Sunday duration"
            )
        if self.created_at is not None:
            validate_aware_datetime(self.created_at, "created_at")


def _second_friday(year: int, month: int) -> date:
    first_day = date(year, month, 1)
    days_until_first_friday = (4 - first_day.weekday()) % 7
    first_friday = first_day + timedelta(days=days_until_first_friday)
    return first_friday + timedelta(days=7)


def build_monthly_baseline_cohort(
    route: Route,
    year: int,
    month: int,
    created_at: datetime | None = None,
) -> TripCohort:
    """Build one monthly baseline cohort using the approved Friday-to-Sunday rule."""

    departure_date = _second_friday(year, month)
    return_date = departure_date + timedelta(days=BASELINE_TRIP_DURATION_DAYS)
    return TripCohort(
        cohort_id=f"{route.route_id}_{year}_{month:02d}_BASELINE",
        route_id=route.route_id,
        cohort_type="baseline",
        departure_date=departure_date,
        return_date=return_date,
        trip_duration_days=BASELINE_TRIP_DURATION_DAYS,
        created_at=created_at,
    )
