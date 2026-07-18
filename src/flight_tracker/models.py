from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


def _validate_airport_code(value: str, field_name: str) -> str:
    if len(value) != 3 or not value.isalpha() or not value.isupper():
        raise ValueError(f"{field_name} must be a 3-letter uppercase airport code")
    return value


def _validate_aware_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _validate_currency(value: str) -> str:
    if len(value) != 3 or not value.isalpha() or not value.isupper():
        raise ValueError("currency must be a 3-letter uppercase currency code")
    return value


@dataclass(frozen=True)
class FlightOffer:
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    price_amount: Decimal
    currency: str
    airline: str
    stops: int
    provider: str

    def __post_init__(self) -> None:
        origin = _validate_airport_code(self.origin, "origin")
        destination = _validate_airport_code(self.destination, "destination")
        if origin == destination:
            raise ValueError("origin and destination must be different")

        departure_time = _validate_aware_datetime(
            self.departure_time, "departure_time"
        )
        arrival_time = _validate_aware_datetime(self.arrival_time, "arrival_time")
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

        _validate_currency(self.currency)


@dataclass(frozen=True)
class SearchRun:
    origin: str
    destination: str
    departure_date: date
    provider: str
    started_at: datetime
    id: int | None = None

    def __post_init__(self) -> None:
        origin = _validate_airport_code(self.origin, "origin")
        destination = _validate_airport_code(self.destination, "destination")
        if origin == destination:
            raise ValueError("origin and destination must be different")
        if not self.provider:
            raise ValueError("provider is required")
        _validate_aware_datetime(self.started_at, "started_at")


@dataclass(frozen=True)
class PriceObservation:
    offer: FlightOffer
    observed_at: datetime
    search_run_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        _validate_aware_datetime(self.observed_at, "observed_at")
