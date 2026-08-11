from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from flight_tracker.models import FlightOffer, PriceObservation


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
