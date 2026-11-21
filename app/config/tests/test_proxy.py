"""Django detrás de nginx (readme, sección 2.4.1): HTTPS por cabecera, CSRF y CSP.

Va en config/tests/ porque prueba la configuración del proyecto, no las vistas de una
app: lleva el marcador infra (no http) y se corre sola con -m infra. Las pruebas con
curl contra nginx (redirección, cabeceras, estáticos y puertos) van en el PR.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client, RequestFactory

pytestmark = pytest.mark.infra

# BASE_DIR es app/: en el repositorio completo (CI) resuelve a nginx/default.conf de la
# raíz; dentro del contenedor web resuelve a /nginx/default.conf, que no existe.
NGINX_CONF = Path(settings.BASE_DIR).parent / "nginx" / "default.conf"


def test_reconoce_https_por_la_cabecera_de_nginx():
    # Scenario: HTTPS por la cabecera de nginx
    peticion = RequestFactory().get("/", HTTP_X_FORWARDED_PROTO="https")
    assert peticion.is_secure()


def test_sin_la_cabecera_la_peticion_no_es_https():
    # Scenario: Sin la cabecera no es HTTPS
    # Regresión: nace en verde, porque Django no considera HTTPS una petición sin la
    # cabecera. Protege contra un SECURE_PROXY_SSL_HEADER que acepte cualquier petición.
    assert not RequestFactory().get("/").is_secure()


def test_las_cookies_solo_viajan_por_https():
    # Scenario: Cookies solo por HTTPS
    assert settings.SESSION_COOKIE_SECURE
    assert settings.CSRF_COOKIE_SECURE


@pytest.mark.django_db
def test_acepta_formularios_desde_el_origen_de_nginx():
    # Scenario: Formulario desde el origen de nginx
    cliente = Client(enforce_csrf_checks=True)
    pagina = cliente.get("/admin/login/", secure=True)
    assert pagina.status_code == 200
    token = pagina.cookies["csrftoken"].value
    respuesta = cliente.post(
        "/admin/login/",
        {"username": "nadie", "password": "Prueba-no-existe", "csrfmiddlewaretoken": token},
        secure=True,
        HTTP_ORIGIN="https://localhost",
    )
    # Credenciales inválidas, pero el CSRF se acepta: el formulario vuelve con 200, no 403
    assert respuesta.status_code == 200


@pytest.mark.django_db
def test_rechaza_formularios_desde_otro_origen():
    # Scenario: Formulario desde otro origen
    # Regresión: nace en verde, porque Django ya rechaza un Origin que no es el suyo.
    # Protege contra un CSRF_TRUSTED_ORIGINS demasiado amplio. Control positivo: la
    # página carga y el token es válido, así que el 403 se debe solo al origen.
    cliente = Client(enforce_csrf_checks=True)
    pagina = cliente.get("/admin/login/", secure=True)
    assert pagina.status_code == 200
    token = pagina.cookies["csrftoken"].value
    assert token
    respuesta = cliente.post(
        "/admin/login/",
        {"username": "nadie", "password": "Prueba-no-existe", "csrfmiddlewaretoken": token},
        secure=True,
        HTTP_ORIGIN="https://sitio-malicioso.example",
    )
    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_django_envia_la_politica_csp():
    # Scenario: Django envía la política CSP
    # Una política vacía haría pasar la comparación sin proteger nada
    assert isinstance(settings.CONTENT_SECURITY_POLICY, str)
    assert settings.CONTENT_SECURITY_POLICY.strip()
    respuesta = Client().get("/admin/login/", secure=True)
    assert respuesta.status_code == 200
    assert respuesta.headers["Content-Security-Policy"] == settings.CONTENT_SECURITY_POLICY


def test_la_csp_de_django_es_la_misma_que_la_de_nginx():
    # Scenario: La misma política en Django y en nginx
    # En el contenedor web solo existe app/: el test corre en el CI, que tiene el
    # repositorio completo.
    if not NGINX_CONF.exists():
        pytest.skip("nginx/default.conf no está al alcance (contenedor web); lo comprueba el CI")
    politica = re.search(
        r'add_header Content-Security-Policy "([^"]+)"',
        NGINX_CONF.read_text(encoding="utf-8"),
    )
    assert politica, "nginx/default.conf no tiene add_header Content-Security-Policy"
    assert politica.group(1) == settings.CONTENT_SECURITY_POLICY
