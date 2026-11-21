"""Cabecera Content-Security-Policy desde Django (readme, sección 2.5).

Detrás de nginx, nginx oculta esta cabecera (proxy_hide_header) y envía la suya, que es
idéntica. Sin nginx (live_server de las pruebas de Playwright), es la única: así los e2e
detectan un script o un estilo en línea igual que el navegador en producción.
"""

from django.conf import settings


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        respuesta.headers.setdefault("Content-Security-Policy", settings.CONTENT_SECURITY_POLICY)
        return respuesta
