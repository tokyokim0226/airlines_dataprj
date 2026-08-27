"""Validation and data models for trip prices, segments, and observations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from flight_tracker.validation import (
    validate_airport_code,
    validate_aware_datetime,
    validate_currency,
    validate_travel_class,
)


@dataclass(frozen=True)
class FlightSegment:
    """One physical flight leg inside a priced trip itinerary."""

    direction: str
    segment_order: int
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    airline: str
    flight_number: str | None = None
    aircraft: str | None = None
    duration_minutes: int | None = None
    id: int | None = None
    trip_offer_id: int | None = None

    def __post_init__(self) -> None:
        if self.direction not in {"outbound", "return"}:
            raise ValueError("direction must be outbound or return")
        if self.segment_order < 1:
            raise ValueError("segment_order must be at least 1")

        origin = validate_airport_code(self.origin, "origin")
        destination = validate_airport_code(self.destination, "destination")
        if origin == destination:
            raise ValueError("segment origin and destination must be different")

        departure_time = validate_aware_datetime(self.departure_time, "departure_time")
        arrival_time = validate_aware_datetime(self.arrival_time, "arrival_time")
        if arrival_time <= departure_time:
            raise ValueError("arrival_time must be after departure_time")

        if not self.airline:
            raise ValueError("airline is required")
        if self.duration_minutes is not None and self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")


@dataclass(frozen=True)
class TripOffer:
    """One priced itinerary returned by a provider, usually round trip."""

    origin: str
    destination: str
    departure_date: date
    return_date: date
    price_amount: Decimal
    currency: str
    provider: str
    travel_class: str = "economy"
    airline_summary: str = "Unknown"
    outbound_stops: int = 0
    return_stops: int = 0
    total_duration_minutes: int | None = None
    segments: tuple[FlightSegment, ...] = field(default_factory=tuple)
    id: int | None = None

    def __post_init__(self) -> None:
        # TripOffer is the main analysis grain: one priced trip seen in a search.
        origin = validate_airport_code(self.origin, "origin")
        destination = validate_airport_code(self.destination, "destination")
        if origin == destination:
            raise ValueError("origin and destination must be different")
        if self.return_date <= self.departure_date:
            raise ValueError("return_date must be after departure_date")
        if self.price_amount < Decimal("0"):
            raise ValueError("price_amount cannot be negative")
        if not self.provider:
            raise ValueError("provider is required")
        if not self.airline_summary:
            raise ValueError("airline_summary is required")
        if self.outbound_stops < 0:
            raise ValueError("outbound_stops cannot be negative")
        if self.return_stops < 0:
            raise ValueError("return_stops cannot be negative")
        if self.total_duration_minutes is not None and self.total_duration_minutes <= 0:
            raise ValueError("total_duration_minutes must be positive")

        validate_currency(self.currency)
        validate_travel_class(self.travel_class)


@dataclass(frozen=True)
class SearchRun:
    """One attempt to search a route and trip date pair."""

    origin: str
    destination: str
    departure_date: date
    return_date: date
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
        if self.return_date <= self.departure_date:
            raise ValueError("return_date must be after departure_date")
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
    """The price seen for one trip offer at one specific observation time."""

    trip_offer: TripOffer
    observed_at: datetime
    search_run_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        # The observation time is what lets us build price history over time.
        validate_aware_datetime(self.observed_at, "observed_at")


@dataclass(frozen=True)
class RawProviderResponse:
    """The unmodified provider payload captured for one search run."""

    search_run_id: int
    provider: str
    captured_at: datetime
    response_text: str
    id: int | None = None

    def __post_init__(self) -> None:
        if self.search_run_id <= 0:
            raise ValueError("search_run_id is required")
        if not self.provider:
            raise ValueError("provider is required")
        if not self.response_text:
            raise ValueError("response_text is required")
        validate_aware_datetime(self.captured_at, "captured_at")
