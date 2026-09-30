from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

THREE_DECIMALS = Decimal("0.001")


@dataclass(frozen=True)
class CandidateStation:
    opis_id: int
    name: str
    route_mile: Decimal
    distance_from_route_miles: Decimal
    price_per_gallon: Decimal
    latitude: Decimal
    longitude: Decimal
    coordinate_precision: str


@dataclass(frozen=True)
class FuelStop:
    station: CandidateStation
    gallons_purchased: Decimal
    cost: Decimal


@dataclass(frozen=True)
class FuelPlan:
    stops: tuple[FuelStop, ...]
    fuel_consumed_gallons: Decimal
    fuel_purchased_gallons: Decimal
    trip_fuel_cost: Decimal


class NoFeasibleFuelPlan(Exception):
    def __init__(self, route_mile: Decimal, maximum_reachable_mile: Decimal) -> None:
        self.route_mile = route_mile
        self.maximum_reachable_mile = maximum_reachable_mile
        super().__init__(
            f"No station can be reached after route mile {route_mile}; "
            f"maximum reachable mile is {maximum_reachable_mile}."
        )


@dataclass(frozen=True)
class _Destination:
    route_mile: Decimal
    price_per_gallon: Decimal = Decimal("-1")


RoutePoint = CandidateStation | _Destination


def create_fuel_plan(
    *,
    route_distance_miles: Decimal,
    tank_capacity_gallons: Decimal,
    fuel_efficiency_mpg: Decimal,
    stations: list[CandidateStation],
) -> FuelPlan:
    fuel_consumed = route_distance_miles / fuel_efficiency_mpg
    if fuel_consumed <= tank_capacity_gallons:
        return FuelPlan(
            stops=(),
            fuel_consumed_gallons=fuel_consumed.quantize(
                THREE_DECIMALS, rounding=ROUND_HALF_UP
            ),
            fuel_purchased_gallons=Decimal("0.000"),
            trip_fuel_cost=Decimal("0.000"),
        )

    maximum_range = tank_capacity_gallons * fuel_efficiency_mpg
    destination = _Destination(route_mile=route_distance_miles)
    candidate_stations = sorted(
        (
            station
            for station in stations
            if Decimal("0") < station.route_mile < route_distance_miles
        ),
        key=lambda station: (
            station.route_mile,
            station.price_per_gallon,
            station.distance_from_route_miles,
            station.opis_id,
        ),
    )
    route_points: list[RoutePoint] = list(candidate_stations)
    route_points.append(destination)

    current_mile = Decimal("0")
    current_station: CandidateStation | None = None
    current_price = Decimal("0")
    fuel_in_tank = tank_capacity_gallons
    stops: list[FuelStop] = []

    while current_mile < route_distance_miles:
        reachable = [
            point
            for point in route_points
            if current_mile < point.route_mile <= current_mile + maximum_range
        ]
        if not reachable:
            raise NoFeasibleFuelPlan(current_mile, current_mile + maximum_range)

        cheaper_point = next(
            (point for point in reachable if point.price_per_gallon < current_price),
            None,
        )
        if cheaper_point is not None:
            next_point = cheaper_point
            desired_fuel = (next_point.route_mile - current_mile) / fuel_efficiency_mpg
        else:
            next_point = min(
                reachable,
                key=lambda point: (
                    point.price_per_gallon,
                    -point.route_mile,
                    getattr(point, "distance_from_route_miles", Decimal("0")),
                ),
            )
            desired_fuel = tank_capacity_gallons

        if current_station is not None:
            gallons_purchased = max(Decimal("0"), desired_fuel - fuel_in_tank)
            if gallons_purchased > 0:
                stops.append(
                    FuelStop(
                        station=current_station,
                        gallons_purchased=gallons_purchased,
                        cost=(gallons_purchased * current_price).quantize(
                            THREE_DECIMALS, rounding=ROUND_HALF_UP
                        ),
                    )
                )
                fuel_in_tank += gallons_purchased

        fuel_needed = (next_point.route_mile - current_mile) / fuel_efficiency_mpg
        fuel_in_tank -= fuel_needed
        current_mile = next_point.route_mile
        route_points = [
            point for point in route_points if point.route_mile > current_mile
        ]

        if isinstance(next_point, _Destination):
            break
        current_station = next_point
        current_price = next_point.price_per_gallon

    purchased = sum((stop.gallons_purchased for stop in stops), Decimal("0"))
    cost = sum((stop.cost for stop in stops), Decimal("0"))
    return FuelPlan(
        stops=tuple(stops),
        fuel_consumed_gallons=fuel_consumed.quantize(
            THREE_DECIMALS, rounding=ROUND_HALF_UP
        ),
        fuel_purchased_gallons=purchased.quantize(
            THREE_DECIMALS, rounding=ROUND_HALF_UP
        ),
        trip_fuel_cost=cost.quantize(THREE_DECIMALS, rounding=ROUND_HALF_UP),
    )
