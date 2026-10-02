# Route Fuel Planner

A Django API that returns a US driving Route, cost-effective Fuel Stops, and the Trip Fuel Cost.

## Quick start

You need Docker Desktop or Docker Compose and a free OpenRouteService key.

1. Create a key at [OpenRouteService](https://openrouteservice.org/dev/#/signup).
2. Create your local environment file:

```bash
cp .env.example .env
```

3. Open `.env` and replace the placeholder with your key:

```env
OPENROUTESERVICE_API_KEY=your-real-key-here
```

4. Start the application:

```bash
docker compose up --build
```

Docker starts PostgreSQL/PostGIS, Redis, and Django. It also runs the migrations and imports 6,603 Fuel Stations.

The first build can take a few minutes. The API is ready at <http://localhost:8000> when the `web` container starts.

- API documentation: <http://localhost:8000/api/docs/>
- OpenAPI schema: <http://localhost:8000/api/schema/>

## Make a request

```bash
curl --request POST http://localhost:8000/api/v1/fuel-plans \
  --header "Content-Type: application/json" \
  --data '{
    "start": "Austin, TX",
    "finish": "Denver, CO",
    "tank_capacity_gallons": 50
  }'
```

`start` and `finish` accept free-form locations in the contiguous United States.

`tank_capacity_gallons` is optional and defaults to 50. Fuel efficiency is fixed at the assignment value of 10 MPG.

You can also send `routing_api_key` in the request body. When present, it replaces the server key for that request.

## Response

The response contains:

- the Route as a GeoJSON line;
- ordered Fuel Stops as GeoJSON points;
- the gallons purchased and cost at each Fuel Stop;
- Trip distance, duration, fuel use, purchased fuel, and Trip Fuel Cost;
- warnings about the planning assumptions and coordinate precision.

A Trip within the initial tank range has no Fuel Stops and a Trip Fuel Cost of `$0.000`.

## How planning works

OpenRouteService resolves the two locations and returns one driving Route. Redis caches locations for 30 days and Routes for 24 hours.

PostGIS finds Fuel Stations within 10 straight-line miles of the Route. These become Candidate Stations ordered by their position along the Route.

If cheaper fuel is reachable, the optimizer buys only enough fuel to reach it. Otherwise, it buys enough to continue to the best reachable Fuel Station.

## Assumptions and limitations

- The vehicle starts with a full tank. The cost of this Starting Fuel is excluded.
- The Supported Area is the contiguous United States. Alaska, Hawaii, territories, and Canada are excluded.
- Fuel Station detour distance is not included in range or cost calculations.
- Fuel Price is treated as USD per gallon and rounded to three decimal places.
- Fuel grade and price date are unknown.
- Duplicate OPIS station IDs use their lowest supplied Fuel Price.
- Most Fuel Station coordinates are locality-level approximations, not exact station locations.

## Errors

Every expected error uses the same shape:

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
- `404`: a location could not be resolved
- `422`: unsupported location or no feasible Fuel Plan
- `502`: OpenRouteService failed or no key is configured

## Development

Run the checks inside the application container:

```bash
docker compose run --rm web pytest
docker compose run --rm web mypy fuel_planner route_optimizer scripts tests
docker compose run --rm web ruff check .
```

Stop the application with:

```bash
docker compose down
```

## Data

The original assessment CSV is included because this repository is intended to remain private.

See [data/README.md](data/README.md) for source and licensing information. Domain terms are in [CONTEXT.md](CONTEXT.md). The coordinate decision is in [ADR 0001](docs/adr/0001-approximate-station-coordinates.md).
