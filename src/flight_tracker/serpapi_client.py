from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


SERPAPI_GOOGLE_FLIGHTS_ENDPOINT = "https://serpapi.com/search"
SERPAPI_API_KEY_ENV_VAR = "SERPAPI_API_KEY"
# SerpAPI expects numeric cabin-class codes, while the rest of our app uses
# readable labels so analysis code never has to remember provider-specific numbers.
SERPAPI_TRAVEL_CLASS_CODES = {
    "economy": "1",
    "business": "3",
}


@dataclass(frozen=True)
class SerpApiFixtureRequest:
    """One controlled Google Flights request used to capture a parser fixture."""

    departure_id: str
    arrival_id: str
    outbound_date: date
    return_date: date
    travel_class: str = "economy"
    currency: str = "USD"
    gl: str = "us"
    hl: str = "en"

    def __post_init__(self) -> None:
        if self.travel_class not in SERPAPI_TRAVEL_CLASS_CODES:
            raise ValueError("travel_class must be economy or business")
        if self.return_date <= self.outbound_date:
            raise ValueError("return_date must be after outbound_date")

    def to_query_params(self, api_key: str) -> dict[str, str]:
        if not api_key:
            raise ValueError("api_key is required")

        # Keep this request deliberately narrow: one round-trip Google Flights
        # search used only to capture a real fixture for parser development.
        return {
            "engine": "google_flights",
            "type": "1",
            "departure_id": self.departure_id,
            "arrival_id": self.arrival_id,
            "outbound_date": self.outbound_date.isoformat(),
            "return_date": self.return_date.isoformat(),
            "travel_class": SERPAPI_TRAVEL_CLASS_CODES[self.travel_class],
            "currency": self.currency,
            "gl": self.gl,
            "hl": self.hl,
            "api_key": api_key,
        }


def default_google_flights_fixture_request() -> SerpApiFixtureRequest:
    """Return the first controlled fixture search aligned with the baseline cohort."""

    # Matches SEOUL_TO_LONDON_2027_02_BASELINE: second Friday to following Sunday.
    return SerpApiFixtureRequest(
        departure_id="ICN",
        arrival_id="LHR",
        outbound_date=date(2027, 2, 12),
        return_date=date(2027, 2, 21),
        travel_class="economy",
    )


def build_serpapi_google_flights_url(
    fixture_request: SerpApiFixtureRequest,
    api_key: str,
) -> str:
    query_string = urlencode(fixture_request.to_query_params(api_key))
    return f"{SERPAPI_GOOGLE_FLIGHTS_ENDPOINT}?{query_string}"


def fetch_serpapi_google_flights_fixture(
    fixture_request: SerpApiFixtureRequest,
    api_key: str,
) -> dict[str, Any]:
    """Execute one SerpAPI Google Flights request and return the decoded JSON."""

    url = build_serpapi_google_flights_url(fixture_request, api_key)
    # This is intentionally not used by normal tests; it spends one SerpAPI request
    # only when the user explicitly runs the fixture command.
    with urlopen(url, timeout=60) as response:  # noqa: S310 - controlled CLI API call
        response_body = response.read().decode("utf-8")
    payload = json.loads(response_body)
    if not isinstance(payload, dict):
        raise ValueError("SerpAPI response must be a JSON object")
    return payload


def save_serpapi_fixture(payload: dict[str, Any], output_path: Path) -> Path:
    # Save the raw JSON exactly as the parser fixture we will inspect next.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return output_path


def load_serpapi_api_key_from_environment(env_file: Path = Path(".env")) -> str:
    api_key = os.environ.get(SERPAPI_API_KEY_ENV_VAR, "")
    if api_key:
        return api_key

    # Fall back to a local .env file so you do not need to export the key every
    # time. .env is ignored by git, so the real key should stay local.
    api_key = _load_value_from_env_file(env_file, SERPAPI_API_KEY_ENV_VAR)
    if api_key:
        return api_key

    raise RuntimeError(f"{SERPAPI_API_KEY_ENV_VAR} is required")


def _load_value_from_env_file(env_file: Path, key: str) -> str:
    if not env_file.exists():
        return ""

    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        env_key, env_value = line.split("=", 1)
        if env_key.strip() == key:
            return env_value.strip().strip('"').strip("'")

    return ""
