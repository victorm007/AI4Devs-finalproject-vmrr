"""Rutas del proyecto. Cada app agrega las suyas en su ticket."""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
