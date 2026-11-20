"""Producción: servidor del hogar y VPS (readme, sección 2.4).

Detrás de nginx (HB-04): nginx termina HTTPS, redirige 80 -> 443 y envía HSTS, así que
Django no lo repite. El resto de la configuración de HTTPS es común y está en base.py.
"""

from .base import *  # noqa: F403

DEBUG = False  # nunca True en producción, aunque .env diga otra cosa

# nginx ya redirige 80 -> 443 y envía HSTS: Django no los repite
# (dos cabeceras HSTS distintas confunden a los navegadores).
SECURE_SSL_REDIRECT = False
SILENCED_SYSTEM_CHECKS = [
    "security.W004",  # SECURE_HSTS_SECONDS: lo pone nginx
    "security.W008",  # SECURE_SSL_REDIRECT: lo hace nginx
]
