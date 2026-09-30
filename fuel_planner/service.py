from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.conf import settings

from fuel_planner.errors import NoFeasiblePlan
from fuel_planner.optimizer import NoFeasibleFuelPlan, create_fuel_plan
from fuel_planner.routing import OpenRouteService
from fuel_planner.stations import stations_near_route

METERS_PER_MILE = Decimal("1609.344")


def build_fuel_plan(
    start_query: str,
    finish_query: str,
    tank_capacity_gallons: Decimal | None,
    routing_api_key: str | None = None,
) -> dict[str, Any]:
    tank_capacity = tank_capacity_gallons or Decimal(
        str(settings.TANK_CAPACITY_GALLONS)
    )
    fuel_efficiency = Decimal(str(settings.FUEL_EFFICIENCY_MPG))
    corridor_miles = Decimal(str(settings.ROUTE_CORRIDOR_MILES))

    routing = OpenRouteService(api_key=routing_api_key)
    start = routing.geocode(start_query)
    finish = routing.geocode(finish_query)
    route = routing.route(start, finish)
    distance_miles = Decimal(str(route.distance_meters)) / METERS_PER_MILE
    candidates = stations_near_route(route.feature, distance_miles, corridor_miles)

    try:
        plan = create_fuel_plan(
            route_distance_miles=distance_miles,
            tank_capacity_gallons=tank_capacity,
            fuel_efficiency_mpg=fuel_efficiency,
            stations=candidates,
        )
    except NoFeasibleFuelPlan as error:
        gap = error.maximum_reachable_mile - error.route_mile
        raise NoFeasiblePlan(
            f"No station can bridge the route after mile {error.route_mile:.1f}; "
            f"the vehicle can travel {gap:.1f} more miles."
        ) from error

    return {
        "route": route.feature,
        "fuel_stops": [_stop_feature(stop) for stop in plan.stops],
        "summary": {
            "distance_miles": float(distance_miles.quantize(Decimal("0.1"))),
            "duration_minutes": float(
                (Decimal(str(route.duration_seconds)) / Decimal("60")).quantize(
                    Decimal("0.1")
                )
            ),
            "fuel_consumed_gallons": str(plan.fuel_consumed_gallons),
            "fuel_purchased_gallons": str(plan.fuel_purchased_gallons),
            "trip_fuel_cost": str(plan.trip_fuel_cost),
            "tank_capacity_gallons": _compact_decimal(tank_capacity),
            "fuel_efficiency_mpg": _compact_decimal(fuel_efficiency),
            "maximum_range_miles": _compact_decimal(
                tank_capacity * fuel_efficiency
            ),
        },
        "warnings": _warnings(plan.stops),
    }


def _stop_feature(stop: Any) -> dict[str, Any]:
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


def _warnings(stops: tuple[Any, ...]) -> list[str]:
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
