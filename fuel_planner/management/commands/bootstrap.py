from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run migrations and load the bundled fuel-station fixture."

    def handle(self, *args: Any, **options: Any) -> None:
        source = Path(settings.BASE_DIR) / "data" / "fuel_stations.csv"
        call_command("migrate", interactive=False)
        call_command("import_fuel_stations", source=source)
