"""Producción: servidor del hogar y VPS (readme, sección 2.4).

Detrás de nginx (HB-04): nginx termina HTTPS, redirige 80 -> 443 y envía HSTS, así que
Django no lo repite. El resto de la configuración de HTTPS es común y está en base.py.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False  # nunca True en producción, aunque .env diga otra cosa

# Nombre del Hogar (HB-06): sin valor por defecto, como SECRET_KEY. La migración
# entidades/0003_hogar lo crea una sola vez y no se renombra desde la aplicación, así que el
# servidor del hogar no arranca sin haberlo elegido.
HOGAR_NOMBRE = os.environ.get("HOGAR_NOMBRE", "").strip()
if not HOGAR_NOMBRE:
    raise ImproperlyConfigured(
        "Falta HOGAR_NOMBRE en .env: en producción el Hogar debe tener su nombre real "
        "(o el de la demo, si es la demo)."
    )

# nginx ya redirige 80 -> 443 y envía HSTS: Django no los repite
# (dos cabeceras HSTS distintas confunden a los navegadores).
SECURE_SSL_REDIRECT = False
SILENCED_SYSTEM_CHECKS = [
    "security.W004",  # SECURE_HSTS_SECONDS: lo pone nginx
    "security.W008",  # SECURE_SSL_REDIRECT: lo hace nginx
]
