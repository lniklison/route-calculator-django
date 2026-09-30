#!/usr/bin/env python
import argparse
import csv
import hashlib
import json
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

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
OUTPUT_FIELDS = [
    "OPIS Truckstop ID",
    "Truckstop Name",
    "Address",
    "City",
    "State",
    "Rack ID",
    "Retail Price",
    "Latitude",
    "Longitude",
    "Coordinate Source",
    "Coordinate Precision",
]


@dataclass(frozen=True)
class Coordinate:
    latitude: str
    longitude: str
    population: int


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--geonames", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--census-results", type=Path)
    args = parser.parse_args()

    city_coordinates = load_geonames(args.geonames)
    census_coordinates = load_census_results(args.census_results)
    rows = cheapest_us_rows(args.source)
    enriched: list[dict[str, str]] = []
    unmatched: set[tuple[str, str]] = set()

    for opis_id, row in sorted(rows.items()):
        coordinate = census_coordinates.get(opis_id)
        source = "census_address"
        precision = "address_range"
        if coordinate is None:
            city_key = (normalize(row["City"]), row["State"].strip().upper())
            coordinate = city_coordinates.get(city_key)
            source = "geonames_city"
            precision = "locality"
        if coordinate is None:
            unmatched.add((row["City"].strip(), row["State"].strip().upper()))
            continue

        enriched.append(
            {
                **{field: row[field].strip() for field in OUTPUT_FIELDS[:6]},
                "Retail Price": str(
                    Decimal(row["Retail Price"]).quantize(
                        Decimal("0.001"), rounding=ROUND_HALF_UP
                    )
                ),
                "Latitude": coordinate.latitude,
                "Longitude": coordinate.longitude,
                "Coordinate Source": source,
                "Coordinate Precision": precision,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(enriched)

    metadata = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": args.source.name,
        "source_sha256": sha256(args.source),
        "geonames_download_url": "https://download.geonames.org/export/dump/US.zip",
        "geonames_file": args.geonames.name,
        "geonames_sha256": sha256(args.geonames),
        "census_results_sha256": (
            sha256(args.census_results)
            if args.census_results and args.census_results.exists()
            else None
        ),
        "census_confident_match_count": len(census_coordinates),
        "station_count": len(enriched),
        "unmatched_localities": [f"{city}, {state}" for city, state in sorted(unmatched)],
    }
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(enriched)} stations; skipped {len(unmatched)} unmatched localities.")


def cheapest_us_rows(source: Path) -> dict[int, dict[str, str]]:
    rows: dict[int, dict[str, str]] = {}
    with source.open(newline="", encoding="utf-8-sig") as source_file:
        for row in csv.DictReader(source_file):
            state = row["State"].strip().upper()
            if state not in CONTIGUOUS_US_STATES:
                continue
            opis_id = int(row["OPIS Truckstop ID"])
            existing = rows.get(opis_id)
            if existing is None or Decimal(row["Retail Price"]) < Decimal(
                existing["Retail Price"]
            ):
                rows[opis_id] = row
    return rows


def load_geonames(source: Path) -> dict[tuple[str, str], Coordinate]:
    coordinates: dict[tuple[str, str], Coordinate] = {}
    with zipfile.ZipFile(source) as archive:
        text_name = max(
            (entry for entry in archive.infolist() if entry.filename.endswith(".txt")),
            key=lambda entry: entry.file_size,
        ).filename
        with archive.open(text_name) as lines:
            for encoded_line in lines:
                fields = encoded_line.decode("utf-8").rstrip("\n").split("\t")
                if len(fields) < 19 or fields[6] != "P":
                    continue
                state = fields[10]
                if state not in CONTIGUOUS_US_STATES:
                    continue
                coordinate = Coordinate(
                    latitude=fields[4],
                    longitude=fields[5],
                    population=int(fields[14] or 0),
                )
                names = {fields[1], fields[2], *fields[3].split(",")}
                for name in names:
                    key = (normalize(name), state)
                    existing = coordinates.get(key)
                    if key[0] and (
                        existing is None or coordinate.population > existing.population
                    ):
                        coordinates[key] = coordinate
    return coordinates


def load_census_results(source: Path | None) -> dict[int, Coordinate]:
    if source is None or not source.exists():
        return {}
    coordinates: dict[int, Coordinate] = {}
    with source.open(newline="", encoding="utf-8-sig") as source_file:
        for row in csv.reader(source_file):
            if len(row) < 9 or row[5].strip().lower() != "match":
                continue
            longitude, latitude = row[8].split(",")
            coordinates[int(row[0])] = Coordinate(latitude, longitude, 0)
    return coordinates


def normalize(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
