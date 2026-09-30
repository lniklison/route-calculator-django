from typing import Any

from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class LocationNotFound(APIException):
    status_code = 404
    default_code = "location_not_found"
    default_detail = "The location could not be resolved."


class UnsupportedLocation(APIException):
    status_code = 422
    default_code = "unsupported_location"
    default_detail = "The location is outside the contiguous United States."


class NoFeasiblePlan(APIException):
    status_code = 422
    default_code = "no_feasible_fuel_plan"


class RoutingServiceUnavailable(APIException):
    status_code = 502
    default_code = "routing_service_unavailable"
    default_detail = "The routing provider could not complete the request."


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        return None
    code = "invalid_request" if response.status_code == 400 else getattr(
        exc, "default_code", "request_failed"
    )
    return Response(
        {
            "error": {
                "code": code,
                "message": _message_from(response.data),
                "details": response.data if isinstance(response.data, dict) else {},
            }
        },
        status=response.status_code,
        headers=response.headers,
    )


def _message_from(data: Any) -> str:
    if isinstance(data, dict):
        detail = data.get("detail")
        if detail is not None:
            return str(detail)
        return "The request is invalid."
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data)
