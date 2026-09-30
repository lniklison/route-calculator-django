#!/usr/bin/env python
import argparse
import csv
from pathlib import Path

from build_station_fixture import cheapest_us_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = cheapest_us_rows(args.source)
    with args.output.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        for opis_id, row in sorted(rows.items()):
            writer.writerow(
                [
                    opis_id,
                    row["Address"].strip(),
                    row["City"].strip(),
                    row["State"].strip(),
                    "",
                ]
            )

    print(f"Wrote {len(rows)} Census batch records.")


if __name__ == "__main__":
    main()
