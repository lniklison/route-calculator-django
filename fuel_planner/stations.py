from decimal import Decimal
from typing import Any

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import LineString
from django.contrib.gis.measure import D

from fuel_planner.models import FuelStation
from fuel_planner.optimizer import CandidateStation


def stations_near_route(
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
        route_fraction = route_line.project(station.location) / route_line.length
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
