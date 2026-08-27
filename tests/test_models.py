from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from flight_tracker.models import FlightSegment, PriceObservation, TripOffer


def make_segment(**overrides: object) -> FlightSegment:
    values = {
        "direction": "outbound",
        "segment_order": 1,
        "origin": "LAX",
        "destination": "JFK",
        "departure_time": datetime(2026, 8, 1, 9, tzinfo=UTC),
        "arrival_time": datetime(2026, 8, 1, 14, tzinfo=UTC),
        "airline": "Mock Air",
    }
    values.update(overrides)
    return FlightSegment(**values)


def make_trip_offer(**overrides: object) -> TripOffer:
    values = {
        "origin": "LAX",
        "destination": "JFK",
        "departure_date": date(2026, 8, 1),
        "return_date": date(2026, 8, 8),
        "price_amount": Decimal("199.99"),
        "currency": "USD",
        "provider": "mock",
        "airline_summary": "Mock Air",
        "segments": (make_segment(),),
    }
    values.update(overrides)
    return TripOffer(**values)


def test_valid_trip_offer() -> None:
    trip_offer = make_trip_offer()

    assert trip_offer.origin == "LAX"
    assert trip_offer.return_date == date(2026, 8, 8)
    assert trip_offer.price_amount == Decimal("199.99")


def test_valid_flight_segment() -> None:
    segment = make_segment()

    assert segment.direction == "outbound"
    assert segment.segment_order == 1


def test_trip_offer_rejects_invalid_airport_code() -> None:
    with pytest.raises(ValueError, match="origin"):
        make_trip_offer(origin="la")


def test_trip_offer_rejects_same_origin_and_destination() -> None:
    with pytest.raises(ValueError, match="different"):
        make_trip_offer(destination="LAX")


def test_trip_offer_rejects_return_date_before_departure_date() -> None:
    with pytest.raises(ValueError, match="return_date"):
        make_trip_offer(return_date=date(2026, 7, 31))


def test_trip_offer_rejects_negative_price() -> None:
    with pytest.raises(ValueError, match="price_amount"):
        make_trip_offer(price_amount=Decimal("-1.00"))


def test_flight_segment_requires_timezone_aware_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        make_segment(
            departure_time=datetime(2026, 8, 1, 9),
            arrival_time=datetime(2026, 8, 1, 14),
        )


def test_price_observation_requires_timezone_aware_observed_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        PriceObservation(
            trip_offer=make_trip_offer(), observed_at=datetime(2026, 8, 1, 12)
        )


def test_invalid_travel_class() -> None:
    with pytest.raises(ValueError, match="travel_class"):
        make_trip_offer(travel_class="first")


def test_segment_arrival_must_be_after_departure() -> None:
    with pytest.raises(ValueError, match="arrival_time"):
        make_segment(arrival_time=datetime(2026, 8, 1, 8, tzinfo=UTC))


def test_segment_rejects_invalid_direction() -> None:
    with pytest.raises(ValueError, match="direction"):
        make_segment(direction="sideways")


def test_trip_offer_rejects_non_positive_total_duration() -> None:
    with pytest.raises(ValueError, match="total_duration_minutes"):
        make_trip_offer(total_duration_minutes=0)


def test_segment_rejects_non_positive_duration() -> None:
    with pytest.raises(ValueError, match="duration_minutes"):
        make_segment(duration_minutes=0)


def test_trip_offer_accepts_multi_day_segment() -> None:
    segment = make_segment(
        departure_time=datetime(2026, 8, 1, 22, tzinfo=UTC),
        arrival_time=datetime(2026, 8, 2, 6, tzinfo=UTC),
        duration_minutes=480,
    )

    assert segment.arrival_time - segment.departure_time == timedelta(hours=8)
