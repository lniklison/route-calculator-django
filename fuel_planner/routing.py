import hashlib
from dataclasses import dataclass
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache

from fuel_planner.errors import (
    LocationNotFound,
    RoutingServiceUnavailable,
    UnsupportedLocation,
)

GEOCODE_CACHE_SECONDS = 30 * 24 * 60 * 60
ROUTE_CACHE_SECONDS = 24 * 60 * 60
CONTIGUOUS_US_REGIONS = {
    "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "IA", "ID",
    "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO", "MS",
    "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR",
    "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV",
    "WY",
}


@dataclass(frozen=True)
class ResolvedLocation:
    label: str
    longitude: float
    latitude: float
    state: str


@dataclass(frozen=True)
class Route:
    feature: dict[str, Any]
    distance_meters: float
    duration_seconds: float


class OpenRouteService:
    def __init__(self, api_key: str | None = None) -> None:
        self.base_url = str(settings.OPENROUTESERVICE_BASE_URL).rstrip("/")
        self.api_key = api_key or str(settings.OPENROUTESERVICE_API_KEY)

    def get_geocode(self, query: str) -> ResolvedLocation:
        cache_key = f"ors:geocode:{_hash(query.strip().casefold())}"
        cached = _get_from_cache(cache_key)
        if isinstance(cached, dict):
            return ResolvedLocation(**cached)

        self._require_api_key()

        try:
            feature = self._request_geocode_feature(query)
            location = _location_from_geocode(feature, query)
        except (LocationNotFound, UnsupportedLocation):
            raise
        except _PROVIDER_ERRORS as error:
            raise RoutingServiceUnavailable() from error

        _set_cache(cache_key, location.__dict__, GEOCODE_CACHE_SECONDS)
        return location

    def generate_route(self, start: ResolvedLocation, finish: ResolvedLocation) -> Route:
        coordinate_key = (
            f"{start.longitude:.6f},{start.latitude:.6f}:"
            f"{finish.longitude:.6f},{finish.latitude:.6f}"
        )
        cache_key = f"ors:route:{_hash(coordinate_key)}"
        cached = _get_from_cache(cache_key)
        if isinstance(cached, dict):
            return _route_from_raw_geojson(cached)

        self._require_api_key()

        try:
            raw_route = self._get_geojson_route(start, finish)
            route = _route_from_raw_geojson(raw_route)
        except _PROVIDER_ERRORS as error:
            raise RoutingServiceUnavailable() from error

        _set_cache(cache_key, raw_route, ROUTE_CACHE_SECONDS)
        return route

    def _require_api_key(self) -> None:
        if not self.api_key:
            raise RoutingServiceUnavailable(
                "OPENROUTESERVICE_API_KEY is not configured."
            )

    def _request_geocode_feature(self, query: str) -> dict[str, Any]:
        response = httpx.get(
            f"{self.base_url}/geocode/search",
            params={
                "api_key": self.api_key,
                "text": query,
                "boundary.country": "US",
                "size": 1,
            },
            timeout=10,
        )
        response.raise_for_status()
        features = response.json().get("features", [])
        if not features:
            raise LocationNotFound(f'No location found for "{query}".')
        return features[0]

    def _get_geojson_route(
        self,
        start: ResolvedLocation,
        finish: ResolvedLocation,
    ) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/v2/directions/driving-car/geojson",
            headers={"Authorization": self.api_key},
            json={
                "coordinates": [
                    [start.longitude, start.latitude],
                    [finish.longitude, finish.latitude],
                ],
                "instructions": False,
                "options": {"avoid_borders": "all"},
            },
            timeout=20,
        )
        response.raise_for_status()
        features = response.json().get("features", [])
        if not features:
            raise ValueError("The routing response contained no route.")
        return features[0]


_PROVIDER_ERRORS = (
    httpx.HTTPError,
    AttributeError,
    IndexError,
    KeyError,
    TypeError,
    ValueError,
)


def _location_from_geocode(feature: dict[str, Any], query: str) -> ResolvedLocation:
    properties = feature["properties"]
    coordinates = feature["geometry"]["coordinates"]
    country = properties["country_a"]
    state = str(properties["region_a"]).upper()
    if country != "USA" or state not in CONTIGUOUS_US_REGIONS:
        raise UnsupportedLocation()

    longitude = float(coordinates[0])
    latitude = float(coordinates[1])
    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        raise ValueError("The geocoder returned invalid coordinates.")
    return ResolvedLocation(
        label=str(properties.get("label", query)),
        longitude=longitude,
        latitude=latitude,
        state=state,
    )


def _route_from_raw_geojson(feature: dict[str, Any]) -> Route:
    summary = feature["properties"]["summary"]
    return Route(
        feature=feature,
        distance_meters=float(summary["distance"]),
        duration_seconds=float(summary["duration"]),
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _get_from_cache(key: str) -> Any:
    try:
        return cache.get(key)
    except Exception:
        return None


def _set_cache(key: str, value: Any, timeout: int) -> None:
    try:
        cache.set(key, value, timeout)
    except Exception:
        pass
