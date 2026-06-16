"""Minimal URL conf for the test suite."""
from django.urls import path

from djangordf.admin import rdf_admin_site


urlpatterns = [
    path("admin/rdf/", rdf_admin_site.urls),
]
