from decimal import Decimal

from rest_framework import serializers


class FuelPlanRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=300, trim_whitespace=True)
    finish = serializers.CharField(max_length=300, trim_whitespace=True)
    tank_capacity_gallons = serializers.DecimalField(
        max_digits=9,
        decimal_places=3,
        min_value=Decimal("0.001"),
        required=False,
    )


class FuelPlanSummarySerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    duration_minutes = serializers.FloatField()
    fuel_consumed_gallons = serializers.DecimalField(max_digits=12, decimal_places=3)
    fuel_purchased_gallons = serializers.DecimalField(max_digits=12, decimal_places=3)
    trip_fuel_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    tank_capacity_gallons = serializers.DecimalField(max_digits=9, decimal_places=3)
    fuel_efficiency_mpg = serializers.DecimalField(max_digits=9, decimal_places=3)
    maximum_range_miles = serializers.DecimalField(max_digits=15, decimal_places=3)


class FuelPlanResponseSerializer(serializers.Serializer):
    route = serializers.JSONField()
    fuel_stops = serializers.ListField(child=serializers.JSONField())
    summary = FuelPlanSummarySerializer()
    warnings = serializers.ListField(child=serializers.CharField())
