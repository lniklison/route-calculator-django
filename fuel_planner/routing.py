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
UNSUPPORTED_STATES = {"AK", "HI"}


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
    def __init__(self) -> None:
        self.base_url = str(settings.OPENROUTESERVICE_BASE_URL).rstrip("/")
        self.api_key = str(settings.OPENROUTESERVICE_API_KEY)

    def geocode(self, query: str) -> ResolvedLocation:
        cache_key = f"ors:geocode:{_hash(query.strip().casefold())}"
        cached = _cache_get(cache_key)
        if isinstance(cached, dict):
            return ResolvedLocation(**cached)

        if not self.api_key:
            raise RoutingServiceUnavailable("OPENROUTESERVICE_API_KEY is not configured.")

        try:
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
        except (httpx.HTTPError, TypeError, ValueError) as error:
            raise RoutingServiceUnavailable() from error

        if not features:
            raise LocationNotFound(f'No location found for "{query}".')

        feature = features[0]
        properties = feature.get("properties", {})
        coordinates = feature.get("geometry", {}).get("coordinates", [])
        country = properties.get("country_a")
        state = str(properties.get("region_a", "")).upper()
        if country != "USA" or state in UNSUPPORTED_STATES:
            raise UnsupportedLocation()
        if len(coordinates) < 2 or not state:
            raise LocationNotFound(f'No supported US location found for "{query}".')

        location = ResolvedLocation(
            label=str(properties.get("label", query)),
            longitude=float(coordinates[0]),
            latitude=float(coordinates[1]),
            state=state,
        )
        _cache_set(cache_key, location.__dict__, GEOCODE_CACHE_SECONDS)
        return location

    def route(self, start: ResolvedLocation, finish: ResolvedLocation) -> Route:
        coordinate_key = (
            f"{start.longitude:.6f},{start.latitude:.6f}:"
            f"{finish.longitude:.6f},{finish.latitude:.6f}"
        )
        cache_key = f"ors:route:{_hash(coordinate_key)}"
        cached = _cache_get(cache_key)
        if isinstance(cached, dict):
            return _route_from_feature(cached)

        if not self.api_key:
            raise RoutingServiceUnavailable("OPENROUTESERVICE_API_KEY is not configured.")

        try:
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
            feature = features[0]
            route = _route_from_feature(feature)
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise RoutingServiceUnavailable() from error

        _cache_set(cache_key, feature, ROUTE_CACHE_SECONDS)
        return route


def _route_from_feature(feature: dict[str, Any]) -> Route:
    summary = feature["properties"]["summary"]
    return Route(
        feature=feature,
        distance_meters=float(summary["distance"]),
        duration_seconds=float(summary["duration"]),
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _cache_get(key: str) -> Any:
    try:
        return cache.get(key)
    except Exception:
        return None


def _cache_set(key: str, value: Any, timeout: int) -> None:
    try:
        cache.set(key, value, timeout)
    except Exception:
        pass
