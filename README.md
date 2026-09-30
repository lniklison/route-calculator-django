# Route Fuel Planner

A Django API that returns a driving route and a cost-effective fuel plan using the supplied truck-stop prices.

## Run it

1. Create a free [OpenRouteService API key](https://openrouteservice.org/dev/#/signup).
2. Copy `.env.example` to `.env` and set `OPENROUTESERVICE_API_KEY`.
3. Start the stack:

```bash
docker compose up --build
```

Docker starts PostgreSQL/PostGIS and Redis, runs migrations, imports 6,603 US fuel stations, and serves the API at `http://localhost:8000`.

Interactive API documentation is available at `http://localhost:8000/api/docs/`; the OpenAPI schema is at `/api/schema/`.

## Request

```bash
curl --request POST http://localhost:8000/api/v1/fuel-plans \
  --header 'Content-Type: application/json' \
  --data '{
    "start": "Austin, TX",
    "finish": "Denver, CO",
    "tank_capacity_gallons": 50,
    "routing_api_key": "optional-request-specific-key"
  }'
```

`tank_capacity_gallons` is optional and defaults to 50. Any positive value is accepted so hypothetical vehicles can be modelled. `routing_api_key` is also optional and overrides the server's OpenRouteService key for that request. Fuel efficiency is fixed at the assignment value of 10 MPG.

The response contains:

- the route as a GeoJSON `Feature`;
- selected fuel stops as ordered GeoJSON point features;
- gallons and cost at each stop;
- total distance, duration, fuel consumption, fuel purchases, and trip fuel cost;
- warnings describing assumptions and approximate coordinates.

## Important assumptions

- The vehicle starts with a full tank. Its previous purchase cost is unknown and excluded, so trips within the initial range cost `$0.000`.
- The route must remain in the contiguous United States. OpenRouteService is asked to avoid international borders.
- Stations within 10 straight-line miles of the route are considered. Their detour mileage is not added to range or cost.
- `Retail Price` is treated as USD per gallon and rounded to three decimals. Fuel grade and effective date are unknown.
- Duplicate OPIS station IDs use their lowest supplied price.
- Station addresses are mostly highway-exit descriptions. A Census batch attempt returned no confident matches, so the checked-in coordinates are GeoNames locality points and are labelled as approximate.

## How optimization works

Candidates are ordered by their projected mile along the route. At each selected station, the planner buys only enough fuel to reach the first cheaper reachable station. If no cheaper station is within range, it fills enough to reach the best-priced reachable station. This standard greedy strategy minimizes fuel-purchase cost on a fixed route; equal prices favor progress and fewer stops.

PostGIS performs the route-corridor query. Redis caches resolved locations for 30 days and routes for 24 hours. Cache failures are non-fatal, and failed provider responses are not cached.

## Errors

Errors use one shape:

```json
{
  "error": {
    "code": "no_feasible_fuel_plan",
    "message": "No station can bridge the route after mile 500.0.",
    "details": {}
  }
}
```

- `400`: invalid request data
- `404`: a free-form location could not be resolved
- `422`: unsupported location or no feasible fuel plan
- `502`: OpenRouteService failed or is not configured

## Development

Run all checks in the same container used by the application:

```bash
docker compose run --rm web pytest
docker compose run --rm web mypy fuel_planner route_optimizer scripts
docker compose run --rm web ruff check .
```

The source CSV is included because this assessment repository is intended to remain private. See [data/README.md](data/README.md) for provenance and licensing notes. Domain language and the coordinate decision are recorded in [CONTEXT.md](CONTEXT.md) and [ADR 0001](docs/adr/0001-approximate-station-coordinates.md).
