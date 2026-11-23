"""Rutas del proyecto. Cada app agrega las suyas en su ticket."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="login")),  # TK-03 la apunta a existencias
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),  # solo POST
    path("admin/", admin.site.urls),
]
