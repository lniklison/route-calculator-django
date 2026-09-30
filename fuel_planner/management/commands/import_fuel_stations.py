import csv
import hashlib
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from fuel_planner.models import FuelDataImport, FuelStation

CONTIGUOUS_US_STATES = {
    "AL",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
}
PRICE_PRECISION = Decimal("0.001")


@dataclass(frozen=True)
class StationRow:
    opis_id: int
    name: str
    address: str
    city: str
    state: str
    rack_id: int
    price: Decimal
    latitude: float
    longitude: float
    coordinate_source: str
    coordinate_precision: str


class Command(BaseCommand):
    help = "Import the enriched fuel-station CSV into PostgreSQL."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--source", type=Path, required=True)

    def handle(self, *args: Any, **options: Any) -> None:
        source: Path = options["source"]
        if not source.is_file():
            raise CommandError(f"Fuel-station source does not exist: {source}")

        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        active_hash = FuelStation.objects.values_list(
            "source_import__source_sha256", flat=True
        ).first()
        if active_hash == source_hash:
            self.stdout.write("Fuel-station data is already imported.")
            return

        stations = _read_stations(source)
        with transaction.atomic():
            data_import, _ = FuelDataImport.objects.get_or_create(
                source_sha256=source_hash,
                defaults={"source_file": source.name},
            )
            FuelStation.objects.all().delete()
            FuelStation.objects.bulk_create(
                [
                    FuelStation(
                        opis_id=row.opis_id,
                        name=row.name,
                        address=row.address,
                        city=row.city,
                        state=row.state,
                        rack_id=row.rack_id,
                        price_per_gallon=row.price,
                        location=Point(row.longitude, row.latitude, srid=4326),
                        coordinate_source=row.coordinate_source,
                        coordinate_precision=row.coordinate_precision,
                        source_import=data_import,
                    )
                    for row in stations.values()
                ],
                batch_size=1000,
            )

        self.stdout.write(self.style.SUCCESS(f"Imported {len(stations)} fuel stations."))


def _read_stations(source: Path) -> dict[int, StationRow]:
    stations: dict[int, StationRow] = {}
    with source.open(newline="", encoding="utf-8-sig") as csv_file:
        for raw in csv.DictReader(csv_file):
            row = _parse_row(raw)
            if row.state not in CONTIGUOUS_US_STATES:
                continue
            existing = stations.get(row.opis_id)
            if existing is None or row.price < existing.price:
                stations[row.opis_id] = row
    return stations


def _parse_row(raw: dict[str, str]) -> StationRow:
    try:
        precision = raw["Coordinate Precision"].strip()
        valid_precisions = {choice for choice, _ in FuelStation.CoordinatePrecision.choices}
        if precision not in valid_precisions:
            raise ValueError(f"Unknown coordinate precision: {precision}")
        return StationRow(
            opis_id=int(raw["OPIS Truckstop ID"]),
            name=raw["Truckstop Name"].strip(),
            address=raw["Address"].strip(),
            city=raw["City"].strip(),
            state=raw["State"].strip().upper(),
            rack_id=int(raw["Rack ID"]),
            price=Decimal(raw["Retail Price"]).quantize(
                PRICE_PRECISION, rounding=ROUND_HALF_UP
            ),
            latitude=float(raw["Latitude"]),
            longitude=float(raw["Longitude"]),
            coordinate_source=raw["Coordinate Source"].strip(),
            coordinate_precision=precision,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CommandError(f"Invalid fuel-station row: {error}") from error
