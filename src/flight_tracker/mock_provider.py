from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from flight_tracker.models import TripOffer
from flight_tracker.parser import parse_mock_flight_response
from flight_tracker.validation import validate_travel_class


class MockFlightProvider:
    """Predictable local provider used for tests and early pipeline work."""

    name = "mock"

    def __init__(self, prices: list[Decimal] | None = None) -> None:
        # Tests can pass exact prices; otherwise the provider uses simple defaults.
        self._prices = prices or [Decimal("250.00"), Decimal("265.00")]
        self._search_count = 0

    def raw_search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: date,
        travel_class: str = "economy",
    ) -> dict[str, Any]:
        validate_travel_class(travel_class)
        if return_date <= departure_date:
            raise ValueError("return_date must be after departure_date")

        # Each search advances the price so repeated collection creates history.
        price = self._prices[self._search_count % len(self._prices)]
        self._search_count += 1

        outbound_departure = datetime.combine(
            departure_date, time(hour=9), tzinfo=timezone.utc
        )
        outbound_arrival = outbound_departure + timedelta(hours=3)
        return_departure = datetime.combine(
            return_date, time(hour=18), tzinfo=timezone.utc
        )
        return_arrival = return_departure + timedelta(hours=3)

        return {
            "provider": self.name,
            "query": {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date.isoformat(),
                "return_date": return_date.isoformat(),
                "travel_class": travel_class,
            },
            "trip_offers": [
                {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date.isoformat(),
                    "return_date": return_date.isoformat(),
                    "price_amount": str(price),
                    "currency": "USD",
                    "airline_summary": "Mock Air",
                    "outbound_stops": 0,
                    "return_stops": 0,
                    "total_duration_minutes": 360,
                    "travel_class": travel_class,
                    "segments": [
                        {
                            "direction": "outbound",
                            "segment_order": 1,
                            "origin": origin,
                            "destination": destination,
                            "departure_time": outbound_departure.isoformat(),
                            "arrival_time": outbound_arrival.isoformat(),
                            "airline": "Mock Air",
                            "flight_number": "MA 100",
                            "aircraft": "Mock 737",
                            "duration_minutes": 180,
                        },
                        {
                            "direction": "return",
                            "segment_order": 1,
                            "origin": destination,
                            "destination": origin,
                            "departure_time": return_departure.isoformat(),
                            "arrival_time": return_arrival.isoformat(),
                            "airline": "Mock Air",
                            "flight_number": "MA 101",
                            "aircraft": "Mock 737",
                            "duration_minutes": 180,
                        },
                    ],
                }
            ],
        }

    def search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: date,
        travel_class: str = "economy",
    ) -> list[TripOffer]:
        raw_response = self.raw_search(
            origin, destination, departure_date, return_date, travel_class
        )
        return parse_mock_flight_response(raw_response)
