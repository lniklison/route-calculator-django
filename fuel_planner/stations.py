import math
from decimal import Decimal
from typing import Any

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import LineString
from django.contrib.gis.measure import D

from fuel_planner.models import FuelStation
from fuel_planner.optimizer import CandidateStation


def find_stations_near_route(
    route_feature: dict[str, Any],
    route_distance_miles: Decimal,
    corridor_miles: Decimal,
) -> list[CandidateStation]:
    coordinates = route_feature["geometry"]["coordinates"]
    route_line = LineString(*coordinates, srid=4326)
    if route_line.length == 0:
        return []

    stations = FuelStation.objects.filter(
        location__distance_lte=(route_line, D(mi=float(corridor_miles)))
    ).annotate(distance_from_route=Distance("location", route_line))

    candidates = []
    for station in stations:
        route_fraction = _geodesic_route_fraction(route_line, station.location)
        candidates.append(
            CandidateStation(
                opis_id=station.opis_id,
                name=station.name,
                route_mile=route_distance_miles * Decimal(str(route_fraction)),
                distance_from_route_miles=Decimal(
                    str(station.distance_from_route.mi)
                ),
                price_per_gallon=station.price_per_gallon,
                latitude=Decimal(str(station.location.y)),
                longitude=Decimal(str(station.location.x)),
                coordinate_precision=station.coordinate_precision,
            )
        )
    return candidates


def _geodesic_route_fraction(route: LineString, point: Any) -> float:
    projected_route = route.clone()
    projected_point = point.clone()
    projected_route.transform(5070)
    projected_point.transform(5070)
    position = projected_route.project(projected_point)

    route_coordinates = list(route.coords)
    projected_coordinates = list(projected_route.coords)
    geodesic_lengths = [
        _great_circle_distance(start, finish)
        for start, finish in zip(route_coordinates, route_coordinates[1:], strict=False)
    ]
    total_length = sum(geodesic_lengths)
    if total_length == 0:
        return 0

    travelled = 0.0
    remaining_position = position
    for index, (start, finish) in enumerate(
        zip(projected_coordinates, projected_coordinates[1:], strict=False)
    ):
        segment_length = math.dist(start, finish)
        if remaining_position >= segment_length:
            travelled += geodesic_lengths[index]
            remaining_position -= segment_length
            continue
        if segment_length > 0:
            travelled += geodesic_lengths[index] * remaining_position / segment_length
        break

    return min(1.0, max(0.0, travelled / total_length))


def _great_circle_distance(start: tuple[float, ...], finish: tuple[float, ...]) -> float:
    start_longitude, start_latitude = map(math.radians, start[:2])
    finish_longitude, finish_latitude = map(math.radians, finish[:2])
    latitude_difference = finish_latitude - start_latitude
    longitude_difference = finish_longitude - start_longitude
    haversine = (
        math.sin(latitude_difference / 2) ** 2
        + math.cos(start_latitude)
        * math.cos(finish_latitude)
        * math.sin(longitude_difference / 2) ** 2
    )
    return 2 * math.asin(math.sqrt(haversine))
