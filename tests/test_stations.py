from django.contrib.gis.geos import LineString, Point

from fuel_planner.stations import _geodesic_route_fraction


def test_route_fraction_uses_distance_instead_of_degrees() -> None:
    route = LineString((-100, 25), (-100, 45), (-90, 45), srid=4326)

    fraction = _geodesic_route_fraction(route, Point(-95, 45, srid=4326))

    assert 0.86 < fraction < 0.88
