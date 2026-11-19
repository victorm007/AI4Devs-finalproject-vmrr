"""Producción: servidor del hogar y VPS (readme, sección 2.4).

HB-04 agrega aquí los ajustes de HTTPS detrás de nginx.
"""

from .base import *  # noqa: F403

DEBUG = False  # nunca True en producción, aunque .env diga otra cosa
