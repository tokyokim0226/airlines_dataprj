from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from flight_tracker.cohorts import TripCohort
from flight_tracker.validation import validate_travel_class


LEAD_TIME_CHECKPOINT_DAYS = (180, 120, 90, 60, 28, 21, 14, 7)
TRAVEL_CLASSES = ("economy", "business")


@dataclass(frozen=True)
class ScheduledObservation:
    """One planned cohort observation for a lead-time checkpoint and cabin class."""

    cohort_id: str
    scheduled_lead_time_days: int
    scheduled_observation_date: date
    travel_class: str

    def __post_init__(self) -> None:
        if not self.cohort_id:
            raise ValueError("cohort_id is required")
        if self.scheduled_lead_time_days not in LEAD_TIME_CHECKPOINT_DAYS:
            raise ValueError("scheduled_lead_time_days must be an accepted checkpoint")
        validate_travel_class(self.travel_class)

    def is_due_on(self, check_date: date) -> bool:
        return self.scheduled_observation_date == check_date


def build_observation_schedule(
    cohort: TripCohort,
    travel_classes: tuple[str, ...] = TRAVEL_CLASSES,
) -> tuple[ScheduledObservation, ...]:
    """Build all planned observations for a cohort and requested cabin classes."""

    observations: list[ScheduledObservation] = []
    for travel_class in travel_classes:
        validate_travel_class(travel_class)
        for lead_time_days in LEAD_TIME_CHECKPOINT_DAYS:
            observations.append(
                ScheduledObservation(
                    cohort_id=cohort.cohort_id,
                    scheduled_lead_time_days=lead_time_days,
                    scheduled_observation_date=cohort.departure_date
                    - timedelta(days=lead_time_days),
                    travel_class=travel_class,
                )
            )
    return tuple(observations)


def due_observations(
    cohort: TripCohort,
    check_date: date,
    travel_classes: tuple[str, ...] = TRAVEL_CLASSES,
) -> tuple[ScheduledObservation, ...]:
    """Return scheduled observations for a cohort that are due on check_date."""

    return tuple(
        observation
        for observation in build_observation_schedule(cohort, travel_classes)
        if observation.is_due_on(check_date)
    )
