from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from fuel_planner.views import FuelPlanView

urlpatterns = [
    path("api/v1/fuel-plans", FuelPlanView.as_view(), name="fuel-plan"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
