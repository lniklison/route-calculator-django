# Preserve approximate station coordinates with their provenance

The supplied fuel-price data has no coordinates and mostly describes highway exits rather than geocodable street addresses. We will attempt one offline Census batch match, fall back to a pinned GeoNames locality coordinate, and store the source and precision with every coordinate. This keeps imports reproducible and route requests fast without presenting city-level fallback points as exact truck-stop locations.
