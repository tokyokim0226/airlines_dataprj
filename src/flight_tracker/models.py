## validation and data modeling for routes, flight offers, search runs, and price observations

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


CITY_AIRPORTS: dict[str, tuple[str, ...]] = {
    "Seoul": ("ICN", "GMP"),
    "London": ("LHR", "LGW"),
    "Tokyo": ("HND", "NRT"),
    "Kuala Lumpur": ("KUL",),
}


def _validate_airport_code(value: str, field_name: str) -> str:
    # Keep airport codes in one predictable format, like "LAX" or "JFK".
    if len(value) != 3 or not value.isalpha() or not value.isupper():
        raise ValueError(f"{field_name} must be a 3-letter uppercase airport code")
    return value


def _validate_aware_datetime(value: datetime, field_name: str) -> datetime:
    # Timezone-aware datetimes prevent confusing local-time comparisons later.
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _validate_currency(value: str) -> str:
    # Currency codes follow the common 3-letter format, like "USD" or "KRW".
    if len(value) != 3 or not value.isalpha() or not value.isupper():
        raise ValueError("currency must be a 3-letter uppercase currency code")
    return value


def _validate_airport_group(values: tuple[str, ...], field_name: str) -> None:
    if not values:
        raise ValueError(f"{field_name} must include at least one airport")
    for airport_code in values:
        _validate_airport_code(airport_code, field_name)


def _route_id(origin_city: str, destination_city: str) -> str:
    origin = origin_city.upper().replace(" ", "_")
    destination = destination_city.upper().replace(" ", "_")
    return f"{origin}_TO_{destination}"


@dataclass(frozen=True)
class Route:
    """One directional city market, such as Seoul -> London."""

    route_id: str
    origin_city: str
    destination_city: str
    origin_airports: tuple[str, ...]
    destination_airports: tuple[str, ...]
    active: bool = True

    def __post_init__(self) -> None:
        if not self.route_id:
            raise ValueError("route_id is required")
        if not self.origin_city:
            raise ValueError("origin_city is required")
        if not self.destination_city:
            raise ValueError("destination_city is required")
        if self.origin_city == self.destination_city:
            raise ValueError("origin_city and destination_city must be different")

        _validate_airport_group(self.origin_airports, "origin_airports")
        _validate_airport_group(self.destination_airports, "destination_airports")


def build_fixed_routes() -> tuple[Route, ...]:
    """Build the twelve directional routes for the Phase 1 city family."""

    routes: list[Route] = []
    city_names = tuple(CITY_AIRPORTS)
    for origin_city in city_names:
        for destination_city in city_names:
            if origin_city == destination_city:
                continue
            routes.append(
                Route(
                    route_id=_route_id(origin_city, destination_city),
                    origin_city=origin_city,
                    destination_city=destination_city,
                    origin_airports=CITY_AIRPORTS[origin_city],
                    destination_airports=CITY_AIRPORTS[destination_city],
                )
            )
    return tuple(routes)


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

    def __post_init__(self) -> None:
        # __post_init__ runs right after dataclass creation, so bad data fails early.
        origin = _validate_airport_code(self.origin, "origin")
        destination = _validate_airport_code(self.destination, "destination")
        if origin == destination:
            raise ValueError("origin and destination must be different")

        departure_time = _validate_aware_datetime(self.departure_time, "departure_time")
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
    """One attempt to search a route and departure date."""

    origin: str
    destination: str
    departure_date: date
    provider: str
    started_at: datetime
    id: int | None = None

    def __post_init__(self) -> None:
        # A search run records when and where we looked, even if no offers appear.
        origin = _validate_airport_code(self.origin, "origin")
        destination = _validate_airport_code(self.destination, "destination")
        if origin == destination:
            raise ValueError("origin and destination must be different")
        if not self.provider:
            raise ValueError("provider is required")
        _validate_aware_datetime(self.started_at, "started_at")


@dataclass(frozen=True)
class PriceObservation:
    """The price seen for one offer at one specific observation time."""

    offer: FlightOffer
    observed_at: datetime
    search_run_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        # The observation time is what lets us build price history over time.
        _validate_aware_datetime(self.observed_at, "observed_at")
