from __future__ import annotations

import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from flight_tracker.models import FlightOffer, PriceObservation, SearchRun


class FlightPriceDatabase:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS search_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    started_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS price_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_run_id INTEGER NOT NULL,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_time TEXT NOT NULL,
                    arrival_time TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    price_amount TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    airline TEXT NOT NULL,
                    stops INTEGER NOT NULL,
                    provider TEXT NOT NULL,
                    FOREIGN KEY (search_run_id) REFERENCES search_runs (id)
                )
                """
            )

    def insert_search_run(self, search_run: SearchRun) -> SearchRun:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO search_runs (
                    origin,
                    destination,
                    departure_date,
                    provider,
                    started_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    search_run.origin,
                    search_run.destination,
                    search_run.departure_date.isoformat(),
                    search_run.provider,
                    search_run.started_at.isoformat(),
                ),
            )

        return SearchRun(
            id=cursor.lastrowid,
            origin=search_run.origin,
            destination=search_run.destination,
            departure_date=search_run.departure_date,
            provider=search_run.provider,
            started_at=search_run.started_at,
        )

    def insert_price_observation(
        self, observation: PriceObservation
    ) -> PriceObservation:
        if observation.search_run_id is None:
            raise ValueError("search_run_id is required before storing an observation")

        offer = observation.offer
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO price_observations (
                    search_run_id,
                    origin,
                    destination,
                    departure_time,
                    arrival_time,
                    observed_at,
                    price_amount,
                    currency,
                    airline,
                    stops,
                    provider
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation.search_run_id,
                    offer.origin,
                    offer.destination,
                    offer.departure_time.isoformat(),
                    offer.arrival_time.isoformat(),
                    observation.observed_at.isoformat(),
                    str(offer.price_amount),
                    offer.currency,
                    offer.airline,
                    offer.stops,
                    offer.provider,
                ),
            )

        return PriceObservation(
            id=cursor.lastrowid,
            search_run_id=observation.search_run_id,
            offer=offer,
            observed_at=observation.observed_at,
        )

    def get_price_history(
        self,
        origin: str,
        destination: str,
        departure_date: date,
    ) -> list[PriceObservation]:
        start_of_day = datetime.combine(
            departure_date, datetime.min.time()
        ).date().isoformat()

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    search_run_id,
                    origin,
                    destination,
                    departure_time,
                    arrival_time,
                    observed_at,
                    price_amount,
                    currency,
                    airline,
                    stops,
                    provider
                FROM price_observations
                WHERE origin = ?
                    AND destination = ?
                    AND substr(departure_time, 1, 10) = ?
                ORDER BY observed_at ASC, id ASC
                """,
                (origin, destination, start_of_day),
            ).fetchall()

        return [self._row_to_observation(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _row_to_observation(row: sqlite3.Row | tuple[object, ...]) -> PriceObservation:
        (
            observation_id,
            search_run_id,
            origin,
            destination,
            departure_time,
            arrival_time,
            observed_at,
            price_amount,
            currency,
            airline,
            stops,
            provider,
        ) = row

        offer = FlightOffer(
            origin=str(origin),
            destination=str(destination),
            departure_time=datetime.fromisoformat(str(departure_time)),
            arrival_time=datetime.fromisoformat(str(arrival_time)),
            price_amount=Decimal(str(price_amount)),
            currency=str(currency),
            airline=str(airline),
            stops=int(stops),
            provider=str(provider),
        )

        return PriceObservation(
            id=int(observation_id),
            search_run_id=int(search_run_id),
            offer=offer,
            observed_at=datetime.fromisoformat(str(observed_at)),
        )
