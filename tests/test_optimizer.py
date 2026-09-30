from decimal import Decimal

import pytest

from fuel_planner.optimizer import (
    CandidateStation,
    NoFeasibleFuelPlan,
    create_fuel_plan,
)


def test_short_trip_needs_no_fuel_stop() -> None:
    plan = create_fuel_plan(
        route_distance_miles=Decimal("400"),
        tank_capacity_gallons=Decimal("50"),
        fuel_efficiency_mpg=Decimal("10"),
        stations=[],
    )

    assert plan.stops == ()
    assert plan.fuel_consumed_gallons == Decimal("40.000")
    assert plan.fuel_purchased_gallons == Decimal("0.000")
    assert plan.trip_fuel_cost == Decimal("0.00")


def test_buys_only_the_fuel_needed_after_the_starting_tank() -> None:
    plan = create_fuel_plan(
        route_distance_miles=Decimal("600"),
        tank_capacity_gallons=Decimal("50"),
        fuel_efficiency_mpg=Decimal("10"),
        stations=[station("450", "3.000", 1)],
    )

    assert len(plan.stops) == 1
    assert plan.stops[0].station.opis_id == 1
    assert plan.stops[0].gallons_purchased == Decimal("10.000")
    assert plan.fuel_purchased_gallons == Decimal("10.000")
    assert plan.trip_fuel_cost == Decimal("30.00")


def test_skips_expensive_station_and_buys_less_when_cheaper_fuel_is_ahead() -> None:
    plan = create_fuel_plan(
        route_distance_miles=Decimal("1000"),
        tank_capacity_gallons=Decimal("50"),
        fuel_efficiency_mpg=Decimal("10"),
        stations=[
            station("400", "4.000", 1),
            station("450", "3.000", 2),
            station("800", "2.000", 3),
        ],
    )

    assert [stop.station.opis_id for stop in plan.stops] == [2, 3]
    assert [stop.gallons_purchased for stop in plan.stops] == [
        Decimal("30"),
        Decimal("20"),
    ]
    assert plan.trip_fuel_cost == Decimal("130.00")


def test_reports_the_route_gap_when_no_fuel_plan_is_possible() -> None:
    with pytest.raises(NoFeasibleFuelPlan) as error:
        create_fuel_plan(
            route_distance_miles=Decimal("1100"),
            tank_capacity_gallons=Decimal("50"),
            fuel_efficiency_mpg=Decimal("10"),
            stations=[station("400", "3.000", 1)],
        )

    assert error.value.route_mile == Decimal("400")
    assert error.value.maximum_reachable_mile == Decimal("900")


def test_hypothetical_large_tank_can_cover_the_route_without_stopping() -> None:
    plan = create_fuel_plan(
        route_distance_miles=Decimal("800"),
        tank_capacity_gallons=Decimal("500"),
        fuel_efficiency_mpg=Decimal("10"),
        stations=[],
    )

    assert plan.stops == ()
    assert plan.fuel_consumed_gallons == Decimal("80.000")
    assert plan.trip_fuel_cost == Decimal("0.00")


def station(mile: str, price: str, opis_id: int) -> CandidateStation:
    return CandidateStation(
        opis_id=opis_id,
        name=f"Station {opis_id}",
        route_mile=Decimal(mile),
        distance_from_route_miles=Decimal("1"),
        price_per_gallon=Decimal(price),
        latitude=Decimal("35"),
        longitude=Decimal("-100"),
        coordinate_precision="locality",
    )
