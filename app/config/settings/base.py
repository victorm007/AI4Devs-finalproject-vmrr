"""Configuración común a todos los entornos (readme, secciones 2.3 y 2.5).

Los valores sensibles o que cambian por entorno vienen de variables de entorno
(metodología 12-factor). Nunca escribas aquí una contraseña ni la SECRET_KEY.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # la carpeta app/


def lista_del_entorno(nombre: str, por_defecto: str = "") -> list[str]:
    """Lee una variable con valores separados por comas: "a, b" -> ["a", "b"]."""
    return [v.strip() for v in os.environ.get(nombre, por_defecto).split(",") if v.strip()]


SECRET_KEY = os.environ["SECRET_KEY"]  # sin valor por defecto: si falta, Django no arranca
DEBUG = os.environ.get("DEBUG", "False") == "True"
ALLOWED_HOSTS = lista_del_entorno("ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# DATABASES: lo agrega HB-03 (conexión como app_user con variables DB_*).
# Mientras tanto Django usa el backend "dummy" y no toca ninguna base.

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True  # fechas con hora en timestamptz (readme, sección 3)

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstatic escribe aquí; nginx (HB-04) lo sirve
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
