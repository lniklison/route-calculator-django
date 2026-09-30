from django.contrib.gis.db import models


class FuelDataImport(models.Model):
    source_file = models.CharField(max_length=255)
    source_sha256 = models.CharField(max_length=64, unique=True)
    imported_at = models.DateTimeField(auto_now_add=True)


class FuelStation(models.Model):
    class CoordinatePrecision(models.TextChoices):
        ADDRESS_RANGE = "address_range", "Address range"
        LOCALITY = "locality", "Locality"

    opis_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField()
    price_per_gallon = models.DecimalField(max_digits=6, decimal_places=3)
    location = models.PointField(geography=True, srid=4326)
    coordinate_source = models.CharField(max_length=50)
    coordinate_precision = models.CharField(
        max_length=20,
        choices=CoordinatePrecision.choices,
    )
    source_import = models.ForeignKey(
        FuelDataImport,
        on_delete=models.PROTECT,
        related_name="stations",
    )

    class Meta:
        ordering = ["opis_id"]

