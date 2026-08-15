## validation and data modeling for flight offers, search runs, and price observations

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from flight_tracker.validation import (
    validate_airport_code,
    validate_aware_datetime,
    validate_currency,
    validate_travel_class,
)


@dataclass(frozen=True)
class FlightOffer:
    """One flight or itinerary returned by a provider."""

    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    price_amount: Decimal
    currency: str
    airline: str
    stops: int
    provider: str
    travel_class: str = "economy"

    def __post_init__(self) -> None:
        # __post_init__ runs right after dataclass creation, so bad data fails early.
        origin = validate_airport_code(self.origin, "origin")
        destination = validate_airport_code(self.destination, "destination")
        if origin == destination:
            raise ValueError("origin and destination must be different")

        departure_time = validate_aware_datetime(self.departure_time, "departure_time")
        arrival_time = validate_aware_datetime(self.arrival_time, "arrival_time")
        if arrival_time <= departure_time:
            raise ValueError("arrival_time must be after departure_time")

        if self.price_amount < Decimal("0"):
            raise ValueError("price_amount cannot be negative")
        if not self.airline:
            raise ValueError("airline is required")
        if self.stops < 0:
            raise ValueError("stops cannot be negative")
        if not self.provider:
            raise ValueError("provider is required")

        validate_currency(self.currency)
        validate_travel_class(self.travel_class)


@dataclass(frozen=True)
class SearchRun:
    """One attempt to search a route and departure date."""

    origin: str
    destination: str
    departure_date: date
    provider: str
    started_at: datetime
    travel_class: str = "economy"
    cohort_id: str | None = None
    scheduled_lead_time_days: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        # A search run records when and where we looked, even if no offers appear.
        origin = validate_airport_code(self.origin, "origin")
        destination = validate_airport_code(self.destination, "destination")
        if origin == destination:
            raise ValueError("origin and destination must be different")
        if not self.provider:
            raise ValueError("provider is required")
        if self.cohort_id == "":
            raise ValueError("cohort_id cannot be blank")
        if (
            self.scheduled_lead_time_days is not None
            and self.scheduled_lead_time_days < 0
        ):
            raise ValueError("scheduled_lead_time_days cannot be negative")
        validate_aware_datetime(self.started_at, "started_at")
        validate_travel_class(self.travel_class)


@dataclass(frozen=True)
class PriceObservation:
    """The price seen for one offer at one specific observation time."""

    offer: FlightOffer
    observed_at: datetime
    search_run_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        # The observation time is what lets us build price history over time.
        validate_aware_datetime(self.observed_at, "observed_at")
