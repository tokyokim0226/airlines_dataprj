from __future__ import annotations

from datetime import date

from flight_tracker.database import FlightPriceDatabase
from flight_tracker.models import PriceObservation


def get_price_history(
    database: FlightPriceDatabase,
    origin: str,
    destination: str,
    departure_date: date,
) -> list[PriceObservation]:
    return database.get_price_history(origin, destination, departure_date)
