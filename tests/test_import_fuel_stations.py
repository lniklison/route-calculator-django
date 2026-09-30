from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command

from fuel_planner.models import FuelStation


@pytest.mark.django_db
def test_import_uses_the_cheapest_price_for_each_us_station(tmp_path: Path) -> None:
    source = tmp_path / "stations.csv"
    source.write_text(
        "OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price,"
        "Latitude,Longitude,Coordinate Source,Coordinate Precision\n"
        "7,Example Stop,Exit 1,Austin,TX,100,3.7894,30.2672,-97.7431,geonames_city,locality\n"
        "7,Example Stop,Exit 1,Austin,TX,100,3.4564,30.2672,-97.7431,geonames_city,locality\n"
        "8,Canadian Stop,Exit 2,Toronto,ON,101,2.000,43.6532,-79.3832,geonames_city,locality\n",
        encoding="utf-8",
    )

    call_command("import_fuel_stations", source=source)

    station = FuelStation.objects.get()
    assert station.opis_id == 7
    assert station.price_per_gallon == Decimal("3.456")
    assert station.city == "Austin"
    assert station.coordinate_precision == "locality"
