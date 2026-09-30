from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command

from fuel_planner.models import FuelStation

HEADER = (
    "OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price,"
    "Latitude,Longitude,Coordinate Source,Coordinate Precision\n"
)


@pytest.mark.django_db
def test_import_uses_the_cheapest_price_for_each_us_station(tmp_path: Path) -> None:
    source = tmp_path / "stations.csv"
    source.write_text(
        HEADER
        + "7,Example Stop,Exit 1,Austin,TX,100,3.7894,30.2672,-97.7431,geonames_city,locality\n"
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


@pytest.mark.django_db
def test_import_can_restore_a_previously_imported_dataset(tmp_path: Path) -> None:
    first_source = tmp_path / "first.csv"
    second_source = tmp_path / "second.csv"
    first_source.write_text(
        HEADER
        + "1,First Stop,Exit 1,Austin,TX,100,3.000,30.2,-97.7,geonames_city,locality\n",
        encoding="utf-8",
    )
    second_source.write_text(
        HEADER
        + "2,Second Stop,Exit 2,Denver,CO,101,4.000,39.7,-105.0,geonames_city,locality\n",
        encoding="utf-8",
    )

    call_command("import_fuel_stations", source=first_source)
    call_command("import_fuel_stations", source=second_source)
    call_command("import_fuel_stations", source=first_source)

    assert list(FuelStation.objects.values_list("opis_id", flat=True)) == [1]
