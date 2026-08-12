from datetime import datetime

import pytest

from flight_tracker.cohorts import TripCohort
from flight_tracker.scheduling import (
    LEAD_TIME_CHECKPOINT_DAYS,
    ScheduledObservation,
    build_observation_schedule,
    due_observations,
)


def make_cohort() -> TripCohort:
    return TripCohort(
        cohort_id="SEOUL_TO_LONDON_2027_02_BASELINE",
        route_id="SEOUL_TO_LONDON",
        cohort_type="baseline",
        departure_date=datetime(2027, 2, 12).date(),
        return_date=datetime(2027, 2, 21).date(),
        trip_duration_days=9,
    )


def test_build_observation_schedule_creates_checkpoints_for_both_travel_classes() -> (
    None
):
    schedule = build_observation_schedule(make_cohort())

    assert len(schedule) == len(LEAD_TIME_CHECKPOINT_DAYS) * 2
    assert {observation.travel_class for observation in schedule} == {
        "economy",
        "business",
    }
    assert {observation.scheduled_lead_time_days for observation in schedule} == set(
        LEAD_TIME_CHECKPOINT_DAYS
    )


def test_build_observation_schedule_calculates_dates_from_departure_date() -> None:
    schedule = build_observation_schedule(make_cohort(), travel_classes=("economy",))
    by_lead_time = {
        observation.scheduled_lead_time_days: observation.scheduled_observation_date
        for observation in schedule
    }

    assert by_lead_time[180] == datetime(2026, 8, 16).date()
    assert by_lead_time[120] == datetime(2026, 10, 15).date()
    assert by_lead_time[7] == datetime(2027, 2, 5).date()


def test_due_observations_returns_matching_checkpoint_for_each_requested_class() -> (
    None
):
    due = due_observations(make_cohort(), datetime(2026, 10, 15).date())

    assert len(due) == 2
    assert {observation.travel_class for observation in due} == {"economy", "business"}
    assert {observation.scheduled_lead_time_days for observation in due} == {120}


def test_due_observations_can_be_limited_to_one_travel_class() -> None:
    due = due_observations(
        make_cohort(),
        datetime(2026, 10, 15).date(),
        travel_classes=("business",),
    )

    assert len(due) == 1
    assert due[0].travel_class == "business"
    assert due[0].scheduled_lead_time_days == 120


def test_due_observations_returns_empty_when_no_checkpoint_is_due() -> None:
    due = due_observations(make_cohort(), datetime(2026, 10, 16).date())

    assert due == ()


def test_scheduled_observation_rejects_invalid_checkpoint() -> None:
    with pytest.raises(ValueError, match="scheduled_lead_time_days"):
        ScheduledObservation(
            cohort_id="SEOUL_TO_LONDON_2027_02_BASELINE",
            scheduled_lead_time_days=45,
            scheduled_observation_date=datetime(2026, 12, 29).date(),
            travel_class="economy",
        )


def test_scheduled_observation_rejects_invalid_travel_class() -> None:
    with pytest.raises(ValueError, match="travel_class"):
        ScheduledObservation(
            cohort_id="SEOUL_TO_LONDON_2027_02_BASELINE",
            scheduled_lead_time_days=60,
            scheduled_observation_date=datetime(2026, 12, 14).date(),
            travel_class="premium_economy",
        )
