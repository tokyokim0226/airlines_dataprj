from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from flight_tracker.models import FlightSegment, TripOffer


def parse_mock_flight_response(response: Mapping[str, Any]) -> list[TripOffer]:
    """Normalize the local mock provider response into TripOffer records."""

    provider = _required_string(response, "provider")
    trip_offers = response.get("trip_offers")
    if not isinstance(trip_offers, list):
        raise ValueError("response must include a trip_offers list")

    parsed_offers: list[TripOffer] = []
    for item in trip_offers:
        if not isinstance(item, Mapping):
            raise ValueError("each trip offer must be an object")
        parsed_offers.append(_parse_mock_trip_offer(item, provider))

    return parsed_offers


def _parse_mock_trip_offer(item: Mapping[str, Any], provider: str) -> TripOffer:
    segments_data = item.get("segments", [])
    if not isinstance(segments_data, list):
        raise ValueError("segments must be a list")

    segments = tuple(
        _parse_mock_segment(segment)
        for segment in segments_data
        if isinstance(segment, Mapping)
    )
    if len(segments) != len(segments_data):
        raise ValueError("each segment must be an object")

    return TripOffer(
        origin=_required_string(item, "origin"),
        destination=_required_string(item, "destination"),
        departure_date=datetime.fromisoformat(
            _required_string(item, "departure_date")
        ).date(),
        return_date=datetime.fromisoformat(_required_string(item, "return_date")).date(),
        price_amount=Decimal(_required_string(item, "price_amount")),
        currency=_required_string(item, "currency"),
        provider=provider,
        travel_class=_required_string(item, "travel_class"),
        airline_summary=_required_string(item, "airline_summary"),
        outbound_stops=_required_int(item, "outbound_stops"),
        return_stops=_required_int(item, "return_stops"),
        total_duration_minutes=_optional_int(item, "total_duration_minutes"),
        segments=segments,
    )


def _parse_mock_segment(item: Mapping[str, Any]) -> FlightSegment:
    return FlightSegment(
        direction=_required_string(item, "direction"),
        segment_order=_required_int(item, "segment_order"),
        origin=_required_string(item, "origin"),
        destination=_required_string(item, "destination"),
        departure_time=datetime.fromisoformat(_required_string(item, "departure_time")),
        arrival_time=datetime.fromisoformat(_required_string(item, "arrival_time")),
        airline=_required_string(item, "airline"),
        flight_number=_optional_string(item, "flight_number"),
        aircraft=_optional_string(item, "aircraft"),
        duration_minutes=_optional_int(item, "duration_minutes"),
    )


def _required_string(data: Mapping[str, Any], field_name: str) -> str:
    value = data.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} is required")
    return value


def _optional_string(data: Mapping[str, Any], field_name: str) -> str | None:
    value = data.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _required_int(data: Mapping[str, Any], field_name: str) -> int:
    value = data.get(field_name)
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value


def _optional_int(data: Mapping[str, Any], field_name: str) -> int | None:
    value = data.get(field_name)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value
