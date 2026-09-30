from typing import Any

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def use_isolated_application_cache(settings: Any) -> None:
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
    cache.clear()
