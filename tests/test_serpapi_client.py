import json
from datetime import date

import pytest

from flight_tracker.serpapi_client import (
    SERPAPI_TRAVEL_CLASS_CODES,
    SerpApiFixtureRequest,
    build_serpapi_google_flights_url,
    default_google_flights_fixture_request,
    save_serpapi_fixture,
)


def test_default_google_flights_fixture_request_matches_first_controlled_search() -> (
    None
):
    request = default_google_flights_fixture_request()

    assert request.departure_id == "ICN"
    assert request.arrival_id == "LHR"
    assert request.outbound_date == date(2027, 2, 12)
    assert request.return_date == date(2027, 2, 21)
    assert request.travel_class == "economy"


def test_serpapi_fixture_request_builds_google_flights_params() -> None:
    request = default_google_flights_fixture_request()

    params = request.to_query_params(api_key="secret")

    assert params["engine"] == "google_flights"
    assert params["type"] == "1"
    assert params["departure_id"] == "ICN"
    assert params["arrival_id"] == "LHR"
    assert params["outbound_date"] == "2027-02-12"
    assert params["return_date"] == "2027-02-21"
    assert params["travel_class"] == SERPAPI_TRAVEL_CLASS_CODES["economy"]
    assert params["currency"] == "USD"
    assert params["gl"] == "us"
    assert params["hl"] == "en"
    assert params["api_key"] == "secret"


def test_build_serpapi_google_flights_url_includes_expected_parameters() -> None:
    url = build_serpapi_google_flights_url(
        default_google_flights_fixture_request(),
        api_key="secret",
    )

    assert url.startswith("https://serpapi.com/search?")
    assert "engine=google_flights" in url
    assert "departure_id=ICN" in url
    assert "arrival_id=LHR" in url
    assert "travel_class=1" in url


def test_serpapi_fixture_request_rejects_unsupported_travel_class() -> None:
    with pytest.raises(ValueError, match="travel_class"):
        SerpApiFixtureRequest(
            departure_id="ICN",
            arrival_id="LHR",
            outbound_date=date(2027, 2, 12),
            return_date=date(2027, 2, 21),
            travel_class="first",
        )


def test_serpapi_fixture_request_rejects_return_before_outbound() -> None:
    with pytest.raises(ValueError, match="return_date"):
        SerpApiFixtureRequest(
            departure_id="ICN",
            arrival_id="LHR",
            outbound_date=date(2027, 2, 12),
            return_date=date(2027, 2, 11),
        )


def test_save_serpapi_fixture_writes_json(tmp_path) -> None:
    output_path = tmp_path / "fixtures" / "serpapi_fixture.json"

    saved_path = save_serpapi_fixture({"provider": "serpapi"}, output_path)

    assert saved_path == output_path
    assert json.loads(output_path.read_text()) == {"provider": "serpapi"}
