from __future__ import annotations

from dataclasses import dataclass

from flight_tracker.validation import validate_airport_group


CITY_AIRPORTS: dict[str, tuple[str, ...]] = {
    "Seoul": ("ICN", "GMP"),
    "London": ("LHR", "LGW"),
    "Tokyo": ("HND", "NRT"),
    "Kuala Lumpur": ("KUL",),
}


def _route_id(origin_city: str, destination_city: str) -> str:
    origin = origin_city.upper().replace(" ", "_")
    destination = destination_city.upper().replace(" ", "_")
    return f"{origin}_TO_{destination}"


@dataclass(frozen=True)
class Route:
    """One directional city market, such as Seoul -> London."""

    route_id: str
    origin_city: str
    destination_city: str
    origin_airports: tuple[str, ...]
    destination_airports: tuple[str, ...]
    active: bool = True

    def __post_init__(self) -> None:
        if not self.route_id:
            raise ValueError("route_id is required")
        if not self.origin_city:
            raise ValueError("origin_city is required")
        if not self.destination_city:
            raise ValueError("destination_city is required")
        if self.origin_city == self.destination_city:
            raise ValueError("origin_city and destination_city must be different")

        validate_airport_group(self.origin_airports, "origin_airports")
        validate_airport_group(self.destination_airports, "destination_airports")


def build_fixed_routes() -> tuple[Route, ...]:
    """Build the twelve directional routes for the Phase 1 city family."""

    routes: list[Route] = []
    city_names = tuple(CITY_AIRPORTS)
    for origin_city in city_names:
        for destination_city in city_names:
            if origin_city == destination_city:
                continue
            routes.append(
                Route(
                    route_id=_route_id(origin_city, destination_city),
                    origin_city=origin_city,
                    destination_city=destination_city,
                    origin_airports=CITY_AIRPORTS[origin_city],
                    destination_airports=CITY_AIRPORTS[destination_city],
                )
            )
    return tuple(routes)
