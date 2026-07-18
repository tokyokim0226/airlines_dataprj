from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from flight_tracker.models import FlightOffer


class MockFlightProvider:
    """Predictable local provider used for tests and early pipeline work."""

    name = "mock"

    def __init__(self, prices: list[Decimal] | None = None) -> None:
        self._prices = prices or [Decimal("250.00"), Decimal("265.00")]
        self._search_count = 0

    def search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
    ) -> list[FlightOffer]:
        price = self._prices[self._search_count % len(self._prices)]
        self._search_count += 1

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
            )
        ]
