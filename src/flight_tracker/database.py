from __future__ import annotations

import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from flight_tracker.cohorts import TripCohort
from flight_tracker.models import (
    FlightOffer,
    PriceObservation,
    RawProviderResponse,
    SearchRun,
)
from flight_tracker.routes import Route
from flight_tracker.scheduling import ScheduledObservation


class FlightPriceDatabase:
    def __init__(self, path: str | Path) -> None:
        # SQLite stores everything in one local file at this path.
        self.path = Path(path)

    def initialize(self) -> None:
        # Create tables if this is a brand-new local database file.
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS routes (
                    route_id TEXT PRIMARY KEY,
                    origin_city TEXT NOT NULL,
                    destination_city TEXT NOT NULL,
                    origin_airports TEXT NOT NULL,
                    destination_airports TEXT NOT NULL,
                    active INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trip_cohorts (
                    cohort_id TEXT PRIMARY KEY,
                    route_id TEXT NOT NULL,
                    cohort_type TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    return_date TEXT NOT NULL,
                    trip_duration_days INTEGER NOT NULL,
                    label TEXT,
                    active INTEGER NOT NULL,
                    created_at TEXT,
                    FOREIGN KEY (route_id) REFERENCES routes (route_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_observations (
                    cohort_id TEXT NOT NULL,
                    scheduled_lead_time_days INTEGER NOT NULL,
                    scheduled_observation_date TEXT NOT NULL,
                    travel_class TEXT NOT NULL,
                    PRIMARY KEY (
                        cohort_id,
                        scheduled_lead_time_days,
                        travel_class
                    ),
                    FOREIGN KEY (cohort_id) REFERENCES trip_cohorts (cohort_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS search_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    travel_class TEXT NOT NULL DEFAULT 'economy',
                    cohort_id TEXT,
                    scheduled_lead_time_days INTEGER
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_provider_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_run_id INTEGER NOT NULL,
                    provider TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    FOREIGN KEY (search_run_id) REFERENCES search_runs (id)
                )
                """
            )
            connection.execute(
                """
                -- Each row here is historical. We insert new rows instead of
                -- updating old rows so price changes can be analyzed later.
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
                    travel_class TEXT NOT NULL DEFAULT 'economy',
                    FOREIGN KEY (search_run_id) REFERENCES search_runs (id)
                )
                """
            )
            self._ensure_column(
                connection,
                table_name="search_runs",
                column_name="travel_class",
                column_definition="TEXT NOT NULL DEFAULT 'economy'",
            )
            self._ensure_column(
                connection,
                table_name="search_runs",
                column_name="cohort_id",
                column_definition="TEXT",
            )
            self._ensure_column(
                connection,
                table_name="search_runs",
                column_name="scheduled_lead_time_days",
                column_definition="INTEGER",
            )
            self._ensure_column(
                connection,
                table_name="price_observations",
                column_name="travel_class",
                column_definition="TEXT NOT NULL DEFAULT 'economy'",
            )

    def upsert_route(self, route: Route) -> Route:
        # Route config is stable metadata, so re-running setup should be idempotent.
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO routes (
                    route_id,
                    origin_city,
                    destination_city,
                    origin_airports,
                    destination_airports,
                    active
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(route_id) DO UPDATE SET
                    origin_city = excluded.origin_city,
                    destination_city = excluded.destination_city,
                    origin_airports = excluded.origin_airports,
                    destination_airports = excluded.destination_airports,
                    active = excluded.active
                """,
                (
                    route.route_id,
                    route.origin_city,
                    route.destination_city,
                    ",".join(route.origin_airports),
                    ",".join(route.destination_airports),
                    int(route.active),
                ),
            )
        return route

    def get_route(self, route_id: str) -> Route | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    route_id,
                    origin_city,
                    destination_city,
                    origin_airports,
                    destination_airports,
                    active
                FROM routes
                WHERE route_id = ?
                """,
                (route_id,),
            ).fetchone()

        return self._row_to_route(row) if row is not None else None

    def get_routes(self) -> list[Route]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    route_id,
                    origin_city,
                    destination_city,
                    origin_airports,
                    destination_airports,
                    active
                FROM routes
                ORDER BY route_id ASC
                """
            ).fetchall()

        return [self._row_to_route(row) for row in rows]

    def upsert_trip_cohort(self, cohort: TripCohort) -> TripCohort:
        # Cohorts define the trip periods we intend to observe repeatedly.
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO trip_cohorts (
                    cohort_id,
                    route_id,
                    cohort_type,
                    departure_date,
                    return_date,
                    trip_duration_days,
                    label,
                    active,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cohort_id) DO UPDATE SET
                    route_id = excluded.route_id,
                    cohort_type = excluded.cohort_type,
                    departure_date = excluded.departure_date,
                    return_date = excluded.return_date,
                    trip_duration_days = excluded.trip_duration_days,
                    label = excluded.label,
                    active = excluded.active,
                    created_at = excluded.created_at
                """,
                (
                    cohort.cohort_id,
                    cohort.route_id,
                    cohort.cohort_type,
                    cohort.departure_date.isoformat(),
                    cohort.return_date.isoformat(),
                    cohort.trip_duration_days,
                    cohort.label,
                    int(cohort.active),
                    cohort.created_at.isoformat() if cohort.created_at else None,
                ),
            )
        return cohort

    def get_trip_cohort(self, cohort_id: str) -> TripCohort | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    cohort_id,
                    route_id,
                    cohort_type,
                    departure_date,
                    return_date,
                    trip_duration_days,
                    label,
                    active,
                    created_at
                FROM trip_cohorts
                WHERE cohort_id = ?
                """,
                (cohort_id,),
            ).fetchone()

        return self._row_to_trip_cohort(row) if row is not None else None

    def get_trip_cohorts(self, route_id: str | None = None) -> list[TripCohort]:
        with self._connect() as connection:
            if route_id is None:
                rows = connection.execute(
                    """
                    SELECT
                        cohort_id,
                        route_id,
                        cohort_type,
                        departure_date,
                        return_date,
                        trip_duration_days,
                        label,
                        active,
                        created_at
                    FROM trip_cohorts
                    ORDER BY departure_date ASC, cohort_id ASC
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT
                        cohort_id,
                        route_id,
                        cohort_type,
                        departure_date,
                        return_date,
                        trip_duration_days,
                        label,
                        active,
                        created_at
                    FROM trip_cohorts
                    WHERE route_id = ?
                    ORDER BY departure_date ASC, cohort_id ASC
                    """,
                    (route_id,),
                ).fetchall()

        return [self._row_to_trip_cohort(row) for row in rows]

    def upsert_scheduled_observation(
        self, observation: ScheduledObservation
    ) -> ScheduledObservation:
        # Schedule rows say when a cohort should be collected for each travel class.
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO scheduled_observations (
                    cohort_id,
                    scheduled_lead_time_days,
                    scheduled_observation_date,
                    travel_class
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(
                    cohort_id,
                    scheduled_lead_time_days,
                    travel_class
                ) DO UPDATE SET
                    scheduled_observation_date = excluded.scheduled_observation_date
                """,
                (
                    observation.cohort_id,
                    observation.scheduled_lead_time_days,
                    observation.scheduled_observation_date.isoformat(),
                    observation.travel_class,
                ),
            )
        return observation

    def get_scheduled_observations(
        self, cohort_id: str | None = None
    ) -> list[ScheduledObservation]:
        with self._connect() as connection:
            if cohort_id is None:
                rows = connection.execute(
                    """
                    SELECT
                        cohort_id,
                        scheduled_lead_time_days,
                        scheduled_observation_date,
                        travel_class
                    FROM scheduled_observations
                    ORDER BY
                        cohort_id ASC,
                        travel_class ASC,
                        scheduled_lead_time_days DESC
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT
                        cohort_id,
                        scheduled_lead_time_days,
                        scheduled_observation_date,
                        travel_class
                    FROM scheduled_observations
                    WHERE cohort_id = ?
                    ORDER BY travel_class ASC, scheduled_lead_time_days DESC
                    """,
                    (cohort_id,),
                ).fetchall()

        return [self._row_to_scheduled_observation(row) for row in rows]

    def get_scheduled_observations_due_on(
        self, check_date: date
    ) -> list[ScheduledObservation]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    scheduled_observations.cohort_id,
                    scheduled_observations.scheduled_lead_time_days,
                    scheduled_observations.scheduled_observation_date,
                    scheduled_observations.travel_class
                FROM scheduled_observations
                JOIN trip_cohorts
                    ON trip_cohorts.cohort_id = scheduled_observations.cohort_id
                JOIN routes
                    ON routes.route_id = trip_cohorts.route_id
                WHERE scheduled_observations.scheduled_observation_date = ?
                    AND trip_cohorts.active = 1
                    AND routes.active = 1
                ORDER BY
                    scheduled_observations.cohort_id ASC,
                    scheduled_observations.travel_class ASC,
                    scheduled_observations.scheduled_lead_time_days DESC
                """,
                (check_date.isoformat(),),
            ).fetchall()

        return [self._row_to_scheduled_observation(row) for row in rows]

    def insert_search_run(self, search_run: SearchRun) -> SearchRun:
        # Store the collection attempt first so observations can point back to it.
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO search_runs (
                    origin,
                    destination,
                    departure_date,
                    provider,
                    started_at,
                    travel_class,
                    cohort_id,
                    scheduled_lead_time_days
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    search_run.origin,
                    search_run.destination,
                    search_run.departure_date.isoformat(),
                    search_run.provider,
                    search_run.started_at.isoformat(),
                    search_run.travel_class,
                    search_run.cohort_id,
                    search_run.scheduled_lead_time_days,
                ),
            )

        return SearchRun(
            id=cursor.lastrowid,
            origin=search_run.origin,
            destination=search_run.destination,
            departure_date=search_run.departure_date,
            provider=search_run.provider,
            started_at=search_run.started_at,
            travel_class=search_run.travel_class,
            cohort_id=search_run.cohort_id,
            scheduled_lead_time_days=search_run.scheduled_lead_time_days,
        )

    def insert_raw_provider_response(
        self, raw_response: RawProviderResponse
    ) -> RawProviderResponse:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO raw_provider_responses (
                    search_run_id,
                    provider,
                    captured_at,
                    response_text
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    raw_response.search_run_id,
                    raw_response.provider,
                    raw_response.captured_at.isoformat(),
                    raw_response.response_text,
                ),
            )

        return RawProviderResponse(
            id=cursor.lastrowid,
            search_run_id=raw_response.search_run_id,
            provider=raw_response.provider,
            captured_at=raw_response.captured_at,
            response_text=raw_response.response_text,
        )

    def get_raw_provider_responses(
        self, search_run_id: int | None = None
    ) -> list[RawProviderResponse]:
        with self._connect() as connection:
            if search_run_id is None:
                rows = connection.execute(
                    """
                    SELECT
                        id,
                        search_run_id,
                        provider,
                        captured_at,
                        response_text
                    FROM raw_provider_responses
                    ORDER BY captured_at ASC, id ASC
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT
                        id,
                        search_run_id,
                        provider,
                        captured_at,
                        response_text
                    FROM raw_provider_responses
                    WHERE search_run_id = ?
                    ORDER BY captured_at ASC, id ASC
                    """,
                    (search_run_id,),
                ).fetchall()

        return [self._row_to_raw_provider_response(row) for row in rows]

    def insert_price_observation(
        self, observation: PriceObservation
    ) -> PriceObservation:
        if observation.search_run_id is None:
            raise ValueError("search_run_id is required before storing an observation")

        offer = observation.offer
        # This is always an INSERT, never an UPDATE, to preserve old observations.
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
                    provider,
                    travel_class
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    offer.travel_class,
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
        # The departure_time column includes a full timestamp, so compare only
        # the YYYY-MM-DD date part when filtering for a departure date.
        start_of_day = (
            datetime.combine(departure_date, datetime.min.time()).date().isoformat()
        )

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
                    provider,
                    travel_class
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
        # SQLite requires this setting per connection for foreign keys to work.
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_definition: str,
    ) -> None:
        columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing_column_names = {str(column[1]) for column in columns}
        if column_name not in existing_column_names:
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
            )

    @staticmethod
    def _row_to_route(row: sqlite3.Row | tuple[object, ...]) -> Route:
        (
            route_id,
            origin_city,
            destination_city,
            origin_airports,
            destination_airports,
            active,
        ) = row

        return Route(
            route_id=str(route_id),
            origin_city=str(origin_city),
            destination_city=str(destination_city),
            origin_airports=tuple(str(origin_airports).split(",")),
            destination_airports=tuple(str(destination_airports).split(",")),
            active=bool(active),
        )

    @staticmethod
    def _row_to_trip_cohort(row: sqlite3.Row | tuple[object, ...]) -> TripCohort:
        (
            cohort_id,
            route_id,
            cohort_type,
            departure_date,
            return_date,
            trip_duration_days,
            label,
            active,
            created_at,
        ) = row

        return TripCohort(
            cohort_id=str(cohort_id),
            route_id=str(route_id),
            cohort_type=str(cohort_type),
            departure_date=date.fromisoformat(str(departure_date)),
            return_date=date.fromisoformat(str(return_date)),
            trip_duration_days=int(trip_duration_days),
            label=str(label) if label is not None else None,
            active=bool(active),
            created_at=datetime.fromisoformat(str(created_at))
            if created_at is not None
            else None,
        )

    @staticmethod
    def _row_to_scheduled_observation(
        row: sqlite3.Row | tuple[object, ...],
    ) -> ScheduledObservation:
        (
            cohort_id,
            scheduled_lead_time_days,
            scheduled_observation_date,
            travel_class,
        ) = row

        return ScheduledObservation(
            cohort_id=str(cohort_id),
            scheduled_lead_time_days=int(scheduled_lead_time_days),
            scheduled_observation_date=date.fromisoformat(
                str(scheduled_observation_date)
            ),
            travel_class=str(travel_class),
        )

    @staticmethod
    def _row_to_raw_provider_response(
        row: sqlite3.Row | tuple[object, ...],
    ) -> RawProviderResponse:
        (
            response_id,
            search_run_id,
            provider,
            captured_at,
            response_text,
        ) = row

        return RawProviderResponse(
            id=int(response_id),
            search_run_id=int(search_run_id),
            provider=str(provider),
            captured_at=datetime.fromisoformat(str(captured_at)),
            response_text=str(response_text),
        )

    @staticmethod
    def _row_to_observation(row: sqlite3.Row | tuple[object, ...]) -> PriceObservation:
        # SQLite returns basic values; convert them back into our model objects.
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
            travel_class,
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
            travel_class=str(travel_class),
        )

        return PriceObservation(
            id=int(observation_id),
            search_run_id=int(search_run_id),
            offer=offer,
            observed_at=datetime.fromisoformat(str(observed_at)),
        )
