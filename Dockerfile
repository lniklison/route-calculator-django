FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y binutils gdal-bin libproj-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

CMD ["gunicorn", "route_optimizer.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]

FROM base AS development
RUN pip install --no-cache-dir ".[dev]"

FROM base AS production
RUN pip install --no-cache-dir "."
