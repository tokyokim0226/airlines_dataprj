from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any, Protocol

from flight_tracker.database import FlightPriceDatabase
from flight_tracker.models import (
    FlightOffer,
    PriceObservation,
    RawProviderResponse,
    SearchRun,
)
from flight_tracker.parser import parse_mock_flight_response
from flight_tracker.routes import Route
from flight_tracker.scheduling import ScheduledObservation


class FlightProvider(Protocol):
    """The small interface any flight data provider must follow."""

    name: str

    def raw_search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        travel_class: str = "economy",
    ) -> dict[str, Any]: ...

    def search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        travel_class: str = "economy",
    ) -> list[FlightOffer]: ...


def collect_prices(
    provider: FlightProvider,
    database: FlightPriceDatabase,
    origin: str,
    destination: str,
    departure_date: date,
    observed_at: datetime | None = None,
    travel_class: str = "economy",
    cohort_id: str | None = None,
    scheduled_lead_time_days: int | None = None,
) -> list[PriceObservation]:
    # Make the collector safe to call even before the database file exists.
    database.initialize()

    # Tests can pass observed_at for predictable history; real runs use now.
    collected_at = observed_at or datetime.now(UTC)

    # A SearchRun records this collection attempt before we store its results.
    search_run = database.insert_search_run(
        SearchRun(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            provider=provider.name,
            started_at=collected_at,
            travel_class=travel_class,
            cohort_id=cohort_id,
            scheduled_lead_time_days=scheduled_lead_time_days,
        )
    )

    raw_response = provider.raw_search(
        origin, destination, departure_date, travel_class
    )
    database.insert_raw_provider_response(
        RawProviderResponse(
            search_run_id=_require_search_run_id(search_run),
            provider=provider.name,
            captured_at=collected_at,
            response_text=json.dumps(raw_response, sort_keys=True),
        )
    )

    observations: list[PriceObservation] = []
    for offer in _parse_provider_response(provider.name, raw_response):
        # Wrap the provider's offer with the time we observed its price.
        observation = PriceObservation(
            offer=offer,
            observed_at=collected_at,
            search_run_id=search_run.id,
        )
        observations.append(database.insert_price_observation(observation))

    return observations


def collect_due_prices(
    provider: FlightProvider,
    database: FlightPriceDatabase,
    due_date: date,
    observed_at: datetime | None = None,
) -> list[PriceObservation]:
    """Collect mock prices for all scheduled observations due on one date."""

    database.initialize()
    collected_at = observed_at or datetime.now(UTC)
    observations: list[PriceObservation] = []

    for scheduled_observation in database.get_scheduled_observations_due_on(due_date):
        cohort = database.get_trip_cohort(scheduled_observation.cohort_id)
        if cohort is None:
            raise ValueError(f"cohort not found: {scheduled_observation.cohort_id}")

        route = database.get_route(cohort.route_id)
        if route is None:
            raise ValueError(f"route not found: {cohort.route_id}")

        origin, destination = _primary_airport_pair(route)
        observations.extend(
            _collect_scheduled_observation(
                provider=provider,
                database=database,
                scheduled_observation=scheduled_observation,
                origin=origin,
                destination=destination,
                departure_date=cohort.departure_date,
                observed_at=collected_at,
            )
        )

    return observations


def _collect_scheduled_observation(
    provider: FlightProvider,
    database: FlightPriceDatabase,
    scheduled_observation: ScheduledObservation,
    origin: str,
    destination: str,
    departure_date: date,
    observed_at: datetime,
) -> list[PriceObservation]:
    return collect_prices(
        provider=provider,
        database=database,
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        observed_at=observed_at,
        travel_class=scheduled_observation.travel_class,
        cohort_id=scheduled_observation.cohort_id,
        scheduled_lead_time_days=scheduled_observation.scheduled_lead_time_days,
    )


def _primary_airport_pair(route: Route) -> tuple[str, str]:
    # Minimal local prototype: one airport pair per city route.
    # Later we can expand to all airport combinations after checking API quota cost.
    return route.origin_airports[0], route.destination_airports[0]


def _parse_provider_response(
    provider_name: str,
    raw_response: dict[str, Any],
) -> list[FlightOffer]:
    if provider_name == "mock":
        return parse_mock_flight_response(raw_response)
    raise ValueError(f"unsupported provider parser: {provider_name}")


def _require_search_run_id(search_run: SearchRun) -> int:
    if search_run.id is None:
        raise ValueError("search_run id is required before storing raw response")
    return search_run.id
