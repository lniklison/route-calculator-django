# Fuel-station data

`source/fuel-prices-for-be-assessment.csv` is the assessment input supplied by the employer. It has no redistribution license and this repository must remain private.

`fuel_stations.csv` is the normalized import fixture. US Census address matches are preferred when available; otherwise a city-level coordinate from GeoNames is used and marked as `locality` precision. Coordinates are approximate and do not make the fuel prices current.

GeoNames data is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The fixture was derived from the US country dump published at <https://download.geonames.org/export/dump/US.zip>. Retrieval details and source hashes are in `fixture-metadata.json`.
