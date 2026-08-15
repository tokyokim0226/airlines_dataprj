from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from flight_tracker.models import FlightOffer


def parse_mock_flight_response(response: Mapping[str, Any]) -> list[FlightOffer]:
    """Normalize the local mock provider raw response into FlightOffer records."""

    provider = _required_string(response, "provider")
    offers = response.get("offers")
    if not isinstance(offers, list):
        raise ValueError("response must include an offers list")

    parsed_offers: list[FlightOffer] = []
    for item in offers:
        if not isinstance(item, Mapping):
            raise ValueError("each offer must be an object")
        parsed_offers.append(_parse_mock_offer(item, provider))

    return parsed_offers


def _parse_mock_offer(item: Mapping[str, Any], provider: str) -> FlightOffer:
    return FlightOffer(
        origin=_required_string(item, "origin"),
        destination=_required_string(item, "destination"),
        departure_time=datetime.fromisoformat(_required_string(item, "departure_time")),
        arrival_time=datetime.fromisoformat(_required_string(item, "arrival_time")),
        price_amount=Decimal(_required_string(item, "price_amount")),
        currency=_required_string(item, "currency"),
        airline=_required_string(item, "airline"),
        stops=_required_int(item, "stops"),
        provider=provider,
        travel_class=_required_string(item, "travel_class"),
    )


def _required_string(data: Mapping[str, Any], field_name: str) -> str:
    value = data.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} is required")
    return value


def _required_int(data: Mapping[str, Any], field_name: str) -> int:
    value = data.get(field_name)
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value
