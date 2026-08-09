from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from flight_tracker.models import (
    FlightOffer,
    PriceObservation,
    Route,
    build_fixed_routes,
)


def make_offer(**overrides: object) -> FlightOffer:
    departure_time = datetime(2026, 8, 1, 9, tzinfo=UTC)
    values = {
        "origin": "LAX",
        "destination": "JFK",
        "departure_time": departure_time,
        "arrival_time": departure_time + timedelta(hours=5),
        "price_amount": Decimal("199.99"),
        "currency": "USD",
        "airline": "Mock Air",
        "stops": 0,
        "provider": "mock",
    }
    values.update(overrides)
    return FlightOffer(**values)


def test_valid_flight_offer() -> None:
    offer = make_offer()

    assert offer.origin == "LAX"
    assert offer.price_amount == Decimal("199.99")


def test_invalid_airport_code_is_rejected() -> None:
    with pytest.raises(ValueError, match="origin"):
        make_offer(origin="la")


def test_same_origin_and_destination_is_rejected() -> None:
    with pytest.raises(ValueError, match="different"):
        make_offer(destination="LAX")


def test_negative_price_is_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        make_offer(price_amount=Decimal("-1.00"))


def test_arrival_before_departure_is_rejected() -> None:
    departure_time = datetime(2026, 8, 1, 9, tzinfo=UTC)

    with pytest.raises(ValueError, match="arrival_time"):
        make_offer(
            departure_time=departure_time,
            arrival_time=departure_time - timedelta(minutes=1),
        )


def test_observed_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="observed_at"):
        PriceObservation(offer=make_offer(), observed_at=datetime(2026, 8, 1, 12))


def test_valid_route_configuration() -> None:
    route = Route(
        route_id="SEOUL_TO_LONDON",
        origin_city="Seoul",
        destination_city="London",
        origin_airports=("ICN", "GMP"),
        destination_airports=("LHR", "LGW"),
    )

    assert route.origin_city == "Seoul"
    assert route.destination_airports == ("LHR", "LGW")
    assert route.active is True


def test_route_rejects_empty_airport_group() -> None:
    with pytest.raises(ValueError, match="origin_airports"):
        Route(
            route_id="SEOUL_TO_LONDON",
            origin_city="Seoul",
            destination_city="London",
            origin_airports=(),
            destination_airports=("LHR", "LGW"),
        )


def test_route_rejects_invalid_airport_code() -> None:
    with pytest.raises(ValueError, match="destination_airports"):
        Route(
            route_id="SEOUL_TO_LONDON",
            origin_city="Seoul",
            destination_city="London",
            origin_airports=("ICN", "GMP"),
            destination_airports=("lhr",),
        )


def test_route_rejects_same_origin_and_destination_city() -> None:
    with pytest.raises(ValueError, match="different"):
        Route(
            route_id="SEOUL_TO_SEOUL",
            origin_city="Seoul",
            destination_city="Seoul",
            origin_airports=("ICN", "GMP"),
            destination_airports=("ICN", "GMP"),
        )


def test_build_fixed_routes_returns_twelve_directional_routes() -> None:
    routes = build_fixed_routes()

    assert len(routes) == 12
    assert len({route.route_id for route in routes}) == 12
    assert {route.origin_city for route in routes} == {
        "Seoul",
        "London",
        "Tokyo",
        "Kuala Lumpur",
    }
    assert ("Seoul", "London") in {
        (route.origin_city, route.destination_city) for route in routes
    }
    assert ("London", "Seoul") in {
        (route.origin_city, route.destination_city) for route in routes
    }
    assert all(route.origin_city != route.destination_city for route in routes)
