import pytest

from flight_tracker.routes import Route, build_fixed_routes


def test_valid_route_configuration() -> None:
    route = Route(
        route_id="SEOUL_TO_LONDON",
        origin_city="Seoul",
        destination_city="London",
        origin_airports=("ICN", "GMP"),
        destination_airports=("LHR", "LGW"),
    )

    assert route.origin_city == "Seoul"
    assert route.destination_airports == ("LHR", "LGW")
    assert route.active is True


def test_route_rejects_empty_airport_group() -> None:
    with pytest.raises(ValueError, match="origin_airports"):
        Route(
            route_id="SEOUL_TO_LONDON",
            origin_city="Seoul",
            destination_city="London",
            origin_airports=(),
            destination_airports=("LHR", "LGW"),
        )


def test_route_rejects_invalid_airport_code() -> None:
    with pytest.raises(ValueError, match="destination_airports"):
        Route(
            route_id="SEOUL_TO_LONDON",
            origin_city="Seoul",
            destination_city="London",
            origin_airports=("ICN", "GMP"),
            destination_airports=("lhr",),
        )


def test_route_rejects_same_origin_and_destination_city() -> None:
    with pytest.raises(ValueError, match="different"):
        Route(
            route_id="SEOUL_TO_SEOUL",
            origin_city="Seoul",
            destination_city="Seoul",
            origin_airports=("ICN", "GMP"),
            destination_airports=("ICN", "GMP"),
        )


def test_build_fixed_routes_returns_twelve_directional_routes() -> None:
    routes = build_fixed_routes()

    assert len(routes) == 12
    assert len({route.route_id for route in routes}) == 12
    assert {route.origin_city for route in routes} == {
        "Seoul",
        "London",
        "Tokyo",
        "Kuala Lumpur",
    }
    assert ("Seoul", "London") in {
        (route.origin_city, route.destination_city) for route in routes
    }
    assert ("London", "Seoul") in {
        (route.origin_city, route.destination_city) for route in routes
    }
    assert all(route.origin_city != route.destination_city for route in routes)
