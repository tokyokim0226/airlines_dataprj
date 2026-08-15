import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from flight_tracker.parser import parse_mock_flight_response


def test_parse_mock_flight_response_from_fixture() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "mock_flight_response.json"
    response = json.loads(fixture_path.read_text())

    offers = parse_mock_flight_response(response)

    assert len(offers) == 1
    assert offers[0].origin == "ICN"
    assert offers[0].destination == "LHR"
    assert offers[0].departure_time == datetime.fromisoformat(
        "2027-02-12T09:00:00+00:00"
    )
    assert offers[0].price_amount == Decimal("1500.00")
    assert offers[0].travel_class == "business"


def test_parse_mock_flight_response_requires_offers_list() -> None:
    with pytest.raises(ValueError, match="offers"):
        parse_mock_flight_response({"provider": "mock"})
