from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from fuel_planner.serializers import (
    FuelPlanRequestSerializer,
    FuelPlanResponseSerializer,
)
from fuel_planner.service import build_fuel_plan


class FuelPlanView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        request=FuelPlanRequestSerializer,
        responses={200: FuelPlanResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = FuelPlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = build_fuel_plan(
            start_query=serializer.validated_data["start"],
            finish_query=serializer.validated_data["finish"],
            tank_capacity_gallons=serializer.validated_data.get(
                "tank_capacity_gallons"
            ),
            routing_api_key=serializer.validated_data.get("routing_api_key"),
        )
        return Response(result)
