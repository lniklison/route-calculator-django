import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "development-only-secret")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [
    host
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host
]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.gis",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "fuel_planner",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "route_optimizer.urls"
WSGI_APPLICATION = "route_optimizer.wsgi.application"
ASGI_APPLICATION = "route_optimizer.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {},
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.getenv("POSTGRES_DB", "route_planner"),
        "USER": os.getenv("POSTGRES_USER", "route_planner"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "route_planner"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "fuel_planner.errors.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Route Fuel Planner API",
    "DESCRIPTION": "Find cost-effective fuel stops along a US driving route.",
    "VERSION": "1.0.0",
}

OPENROUTESERVICE_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY", "")
OPENROUTESERVICE_BASE_URL = os.getenv(
    "OPENROUTESERVICE_BASE_URL", "https://api.openrouteservice.org"
)
TANK_CAPACITY_GALLONS = os.getenv("TANK_CAPACITY_GALLONS", "50")
FUEL_EFFICIENCY_MPG = os.getenv("FUEL_EFFICIENCY_MPG", "10")
ROUTE_CORRIDOR_MILES = os.getenv("ROUTE_CORRIDOR_MILES", "10")
