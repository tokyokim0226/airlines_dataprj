from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from flight_tracker.validation import validate_aware_datetime


COHORT_TYPES = ("baseline", "event", "personal")
BASELINE_TRIP_DURATION_DAYS = 7


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
            raise ValueError("baseline cohorts must use a 7-day trip duration")
        if self.created_at is not None:
            validate_aware_datetime(self.created_at, "created_at")
