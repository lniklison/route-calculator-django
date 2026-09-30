from decimal import Decimal
from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


@extend_schema_field(OpenApiTypes.DECIMAL)
class PositiveDecimalField(serializers.Field):
    default_error_messages = {
        "invalid": "Enter a valid decimal number.",
        "not_positive": "Ensure this value is greater than zero.",
    }

    def to_internal_value(self, data: Any) -> Decimal:
        try:
            value = Decimal(str(data))
        except (ValueError, TypeError, ArithmeticError):
            self.fail("invalid")
        if not value.is_finite():
            self.fail("invalid")
        if value <= 0:
            self.fail("not_positive")
        return value

    def to_representation(self, value: Any) -> str:
        return format(Decimal(str(value)), "f")


class FuelPlanRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=300, trim_whitespace=True)
    finish = serializers.CharField(max_length=300, trim_whitespace=True)
    tank_capacity_gallons = PositiveDecimalField(required=False)
    routing_api_key = serializers.CharField(
        max_length=500,
        required=False,
        trim_whitespace=True,
        write_only=True,
    )


class FuelPlanSummarySerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    duration_minutes = serializers.FloatField()
    fuel_consumed_gallons = serializers.DecimalField(max_digits=12, decimal_places=3)
    fuel_purchased_gallons = serializers.DecimalField(max_digits=12, decimal_places=3)
    trip_fuel_cost = serializers.DecimalField(max_digits=15, decimal_places=3)
    tank_capacity_gallons = serializers.CharField()
    fuel_efficiency_mpg = serializers.DecimalField(max_digits=9, decimal_places=3)
    maximum_range_miles = serializers.CharField()


class FuelPlanResponseSerializer(serializers.Serializer):
    route = serializers.JSONField()
    fuel_stops = serializers.ListField(child=serializers.JSONField())
    summary = FuelPlanSummarySerializer()
    warnings = serializers.ListField(child=serializers.CharField())
