from typing import Any

import httpx
import pytest
import respx
from django.contrib.gis.geos import Point
from django.test import override_settings
from rest_framework.test import APIClient

from fuel_planner.models import FuelDataImport, FuelStation

GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
DIRECTIONS_URL = (
    "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
)


def geocode_response(longitude: float, latitude: float, state: str) -> dict[str, Any]:
    return {
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
                "properties": {
                    "country_a": "USA",
                    "region_a": state,
                    "label": f"Resolved location, {state}",
                },
            }
        ]
    }


@pytest.mark.django_db
@override_settings(OPENROUTESERVICE_API_KEY="test-key")
@respx.mock
def test_creates_a_geojson_fuel_plan_for_free_form_locations() -> None:
    respx.get(GEOCODE_URL).mock(
        side_effect=[
            httpx.Response(200, json=geocode_response(-97.7431, 30.2672, "TX")),
            httpx.Response(200, json=geocode_response(-104.9903, 39.7392, "CO")),
        ]
    )
    route = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[-97.7431, 30.2672], [-104.9903, 39.7392]],
        },
        "properties": {"summary": {"distance": 643737.6, "duration": 36000}},
    }
    respx.post(DIRECTIONS_URL).mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": [route]})
    )

    response = APIClient().post(
        "/api/v1/fuel-plans",
        {"start": "Austin, TX", "finish": "Denver, CO"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["route"] == route
    assert response.json()["fuel_stops"] == []
    assert response.json()["summary"] == {
        "distance_miles": 400.0,
        "duration_minutes": 600.0,
        "fuel_consumed_gallons": "40.000",
        "fuel_purchased_gallons": "0.000",
        "trip_fuel_cost": "0.00",
        "tank_capacity_gallons": "50",
        "fuel_efficiency_mpg": "10",
        "maximum_range_miles": "500",
    }


@pytest.mark.django_db
def test_rejects_a_non_positive_tank_capacity() -> None:
    response = APIClient().post(
        "/api/v1/fuel-plans",
        {
            "start": "Austin, TX",
            "finish": "Denver, CO",
            "tank_capacity_gallons": 0,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"
    assert "tank_capacity_gallons" in response.json()["error"]["details"]


@pytest.mark.django_db
@override_settings(OPENROUTESERVICE_API_KEY="test-key")
@respx.mock
def test_reports_a_location_that_cannot_be_resolved() -> None:
    respx.get(GEOCODE_URL).mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )

    response = APIClient().post(
        "/api/v1/fuel-plans",
        {"start": "Nowhere, ZZ", "finish": "Denver, CO"},
        format="json",
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "location_not_found"


@pytest.mark.django_db
@override_settings(OPENROUTESERVICE_API_KEY="test-key")
@respx.mock
def test_returns_an_affordable_station_along_a_long_route() -> None:
    data_import = FuelDataImport.objects.create(
        source_file="test.csv",
        source_sha256="a" * 64,
    )
    FuelStation.objects.create(
        opis_id=7,
        name="Midway Fuel",
        address="I-10, Exit 1",
        city="Midway",
        state="TX",
        rack_id=100,
        price_per_gallon="3.000",
        location=Point(-95, 30, srid=4326),
        coordinate_source="geonames_city",
        coordinate_precision="locality",
        source_import=data_import,
    )
    respx.get(GEOCODE_URL).mock(
        side_effect=[
            httpx.Response(200, json=geocode_response(-100, 30, "TX")),
            httpx.Response(200, json=geocode_response(-90, 30, "TX")),
        ]
    )
    route = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[-100, 30], [-90, 30]]},
        "properties": {"summary": {"distance": 965606.4, "duration": 50000}},
    }
    respx.post(DIRECTIONS_URL).mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": [route]})
    )

    response = APIClient().post(
        "/api/v1/fuel-plans",
        {"start": "Origin, TX", "finish": "Finish, TX"},
        format="json",
    )

    assert response.status_code == 200
    assert len(response.json()["fuel_stops"]) == 1
    properties = response.json()["fuel_stops"][0]["properties"]
    assert properties["opis_id"] == 7
    assert properties["gallons_purchased"] == "10.000"
    assert response.json()["summary"]["trip_fuel_cost"] == "30.00"
