from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from flight_tracker.models import FlightOffer
from flight_tracker.validation import validate_travel_class


class MockFlightProvider:
    """Predictable local provider used for tests and early pipeline work."""

    name = "mock"

    def __init__(self, prices: list[Decimal] | None = None) -> None:
        # Tests can pass exact prices; otherwise the provider uses simple defaults.
        self._prices = prices or [Decimal("250.00"), Decimal("265.00")]
        self._search_count = 0

    def search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        travel_class: str = "economy",
    ) -> list[FlightOffer]:
        validate_travel_class(travel_class)

        # Each search advances the price so repeated collection creates history.
        price = self._prices[self._search_count % len(self._prices)]
        self._search_count += 1

        # Keep mock flight times deterministic: same route/date always has same times.
        departure_time = datetime.combine(
            departure_date, time(hour=9), tzinfo=timezone.utc
        )
        arrival_time = departure_time + timedelta(hours=3)

        return [
            FlightOffer(
                origin=origin,
                destination=destination,
                departure_time=departure_time,
                arrival_time=arrival_time,
                price_amount=price,
                currency="USD",
                airline="Mock Air",
                stops=0,
                provider=self.name,
                travel_class=travel_class,
            )
        ]
