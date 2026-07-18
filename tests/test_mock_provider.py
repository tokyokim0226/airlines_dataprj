from datetime import date
from decimal import Decimal

from flight_tracker.mock_provider import MockFlightProvider


def test_mock_provider_returns_valid_flight_offer() -> None:
    provider = MockFlightProvider(prices=[Decimal("300.00")])

    offers = provider.search("LAX", "JFK", date(2026, 8, 1))

    assert len(offers) == 1
    assert offers[0].origin == "LAX"
    assert offers[0].destination == "JFK"
    assert offers[0].price_amount == Decimal("300.00")
    assert offers[0].departure_time.tzinfo is not None


def test_mock_provider_cycles_prices() -> None:
    provider = MockFlightProvider(prices=[Decimal("300.00"), Decimal("310.00")])

    first = provider.search("LAX", "JFK", date(2026, 8, 1))[0]
    second = provider.search("LAX", "JFK", date(2026, 8, 1))[0]
    third = provider.search("LAX", "JFK", date(2026, 8, 1))[0]

    assert first.price_amount == Decimal("300.00")
    assert second.price_amount == Decimal("310.00")
    assert third.price_amount == Decimal("300.00")
