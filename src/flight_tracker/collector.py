from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Protocol

from flight_tracker.database import FlightPriceDatabase
from flight_tracker.models import FlightOffer, PriceObservation, SearchRun


class FlightProvider(Protocol):
    name: str

    def search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
    ) -> list[FlightOffer]:
        ...


def collect_prices(
    provider: FlightProvider,
    database: FlightPriceDatabase,
    origin: str,
    destination: str,
    departure_date: date,
    observed_at: datetime | None = None,
) -> list[PriceObservation]:
    database.initialize()
    collected_at = observed_at or datetime.now(UTC)

    search_run = database.insert_search_run(
        SearchRun(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            provider=provider.name,
            started_at=collected_at,
        )
    )

    observations: list[PriceObservation] = []
    for offer in provider.search(origin, destination, departure_date):
        observation = PriceObservation(
            offer=offer,
            observed_at=collected_at,
            search_run_id=search_run.id,
        )
        observations.append(database.insert_price_observation(observation))

    return observations
