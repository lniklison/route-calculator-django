from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.conf import settings

from fuel_planner.errors import NoFeasiblePlan
from fuel_planner.optimizer import (
    CandidateStation,
    FuelPlan,
    FuelStop,
    NoFeasibleFuelPlan,
    create_fuel_plan,
)
from fuel_planner.routing import OpenRouteService, Route
from fuel_planner.stations import find_stations_near_route

METERS_PER_MILE = Decimal("1609.344")


@dataclass(frozen=True)
class _VehicleProfile:
    tank_capacity_gallons: Decimal
    fuel_efficiency_mpg: Decimal


@dataclass(frozen=True)
class _TripRoute:
    route: Route
    distance_miles: Decimal
    candidate_stations: list[CandidateStation]


def build_fuel_plan(
    start_query: str,
    finish_query: str,
    tank_capacity_gallons: Decimal | None,
    routing_api_key: str | None = None,
) -> dict[str, Any]:
    vehicle = _generate_vehicle_profile(tank_capacity_gallons)
    trip_route = _prepare_trip_route(start_query, finish_query, routing_api_key)
    fuel_plan = _optimize_fuel_plan(trip_route, vehicle)
    return _generate_fuel_plan_response(trip_route, fuel_plan, vehicle)


def _generate_vehicle_profile(tank_capacity_gallons: Decimal | None) -> _VehicleProfile:
    tank_capacity = tank_capacity_gallons or Decimal(
        str(settings.TANK_CAPACITY_GALLONS)
    )
    return _VehicleProfile(
        tank_capacity_gallons=tank_capacity,
        fuel_efficiency_mpg=Decimal(str(settings.FUEL_EFFICIENCY_MPG)),
    )


def _prepare_trip_route(
    start_query: str,
    finish_query: str,
    routing_api_key: str | None,
) -> _TripRoute:
    corridor_miles = Decimal(str(settings.ROUTE_CORRIDOR_MILES))

    routing = OpenRouteService(api_key=routing_api_key)
    start = routing.get_geocode(start_query)
    finish = routing.get_geocode(finish_query)
    route = routing.generate_route(start, finish)
    distance_miles = Decimal(str(route.distance_meters)) / METERS_PER_MILE
    candidate_stations = find_stations_near_route(
        route.feature,
        distance_miles,
        corridor_miles,
    )
    return _TripRoute(route, distance_miles, candidate_stations)


def _optimize_fuel_plan(
    trip_route: _TripRoute,
    vehicle: _VehicleProfile,
) -> FuelPlan:
    try:
        return create_fuel_plan(
            route_distance_miles=trip_route.distance_miles,
            tank_capacity_gallons=vehicle.tank_capacity_gallons,
            fuel_efficiency_mpg=vehicle.fuel_efficiency_mpg,
            stations=trip_route.candidate_stations,
        )
    except NoFeasibleFuelPlan as error:
        gap = error.maximum_reachable_mile - error.route_mile
        raise NoFeasiblePlan(
            f"No station can bridge the route after mile {error.route_mile:.1f}; "
            f"the vehicle can travel {gap:.1f} more miles."
        ) from error


def _generate_fuel_plan_response(
    trip_route: _TripRoute,
    fuel_plan: FuelPlan,
    vehicle: _VehicleProfile,
) -> dict[str, Any]:
    return {
        "route": trip_route.route.feature,
        "fuel_stops": [_stop_feature(stop) for stop in fuel_plan.stops],
        "summary": _trip_summary(trip_route, fuel_plan, vehicle),
        "warnings": _warnings(fuel_plan.stops),
    }


def _trip_summary(
    trip_route: _TripRoute,
    fuel_plan: FuelPlan,
    vehicle: _VehicleProfile,
) -> dict[str, Any]:
    duration_minutes = Decimal(str(trip_route.route.duration_seconds)) / Decimal("60")
    maximum_range = vehicle.tank_capacity_gallons * vehicle.fuel_efficiency_mpg
    return {
        "distance_miles": float(trip_route.distance_miles.quantize(Decimal("0.1"))),
        "duration_minutes": float(duration_minutes.quantize(Decimal("0.1"))),
        "fuel_consumed_gallons": str(fuel_plan.fuel_consumed_gallons),
        "fuel_purchased_gallons": str(fuel_plan.fuel_purchased_gallons),
        "trip_fuel_cost": str(fuel_plan.trip_fuel_cost),
        "tank_capacity_gallons": _compact_decimal(vehicle.tank_capacity_gallons),
        "fuel_efficiency_mpg": _compact_decimal(vehicle.fuel_efficiency_mpg),
        "maximum_range_miles": _compact_decimal(maximum_range),
    }


def _stop_feature(stop: FuelStop) -> dict[str, Any]:
    station = stop.station
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [float(station.longitude), float(station.latitude)],
        },
        "properties": {
            "opis_id": station.opis_id,
            "name": station.name,
            "price_per_gallon": str(station.price_per_gallon),
            "gallons_purchased": str(
                stop.gallons_purchased.quantize(
                    Decimal("0.001"), rounding=ROUND_HALF_UP
                )
            ),
            "cost": str(stop.cost),
            "route_mile": float(station.route_mile.quantize(Decimal("0.1"))),
            "distance_from_route_miles": float(
                station.distance_from_route_miles.quantize(Decimal("0.1"))
            ),
            "coordinate_precision": station.coordinate_precision,
        },
    }


def _warnings(stops: tuple[FuelStop, ...]) -> list[str]:
    warnings = [
        "The vehicle starts with a full tank; the cost of that fuel is excluded.",
        "Fuel-station detour mileage is not included in range or cost calculations.",
        "Prices are assumed to be USD per gallon; fuel grade and effective date are unknown.",
    ]
    if any(stop.station.coordinate_precision == "locality" for stop in stops):
        warnings.append("At least one fuel-stop coordinate is a locality-level approximation.")
    return warnings


def _compact_decimal(value: Decimal) -> str:
    return format(value.normalize(), "f")
