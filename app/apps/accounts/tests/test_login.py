"""Inicio de sesión, cierre de sesión, sesiones y bloqueo por intentos fallidos (sección 2.5).

HB-08. Capa HTTP: URL + vista + plantilla con el cliente de pruebas de Django. Antes de TK-01
no hay mock: el usuario de prueba es "prueba.operador", del grupo "Lectura y escritura", que
crea la migración 0003_grupos.

Los usuarios nunca entran con client.login(): no pasa la petición al backend de django-axes y
falla. Se usa client.force_login(usuario) o un POST al login.

Se comprueban fuera de pytest:
- "Login a 390 px y sin violaciones de CSP" (criterio 6): en el navegador, en
  https://localhost/accounts/login/, en escritorio y a 390 px (no hay Playwright hasta TK-03).
- "djLint sin cambios ni errores" (criterio 7): con python scripts/verificar.py, el mismo
  verificador del job lint.
"""

import re
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.http]
CLAVE = "Prueba-operador-2026"
CLAVE_INCORRECTA = "Prueba-equivocada-1"


@pytest.fixture
def operador():
    usuario = get_user_model().objects.create_user("prueba.operador", password=CLAVE, is_staff=True)
    usuario.groups.add(Group.objects.get(name="Lectura y escritura"))
    return usuario


def entrar(client, usuario, clave):
    return client.post(reverse("login"), {"username": usuario, "password": clave})


def plantillas(respuesta):
    return {plantilla.name for plantilla in respuesta.templates}


def test_la_pagina_de_login_no_usa_recursos_externos(client):
    # Scenario: Recursos propios y etiquetas (HB-08, criterio 6)
    respuesta = client.get(reverse("login"))
    # Sin el valor del token CSRF: es aleatorio y, en minúsculas, podría contener "cdn" y
    # hacer fallar el test de vez en cuando. Django lo escribe siempre con este formato
    html = re.sub(
        r'name="csrfmiddlewaretoken" value="[^"]*"',
        'name="csrfmiddlewaretoken"',
        respuesta.content.decode(),
    )
    assert respuesta.status_code == 200
    assert reverse("login") == "/accounts/login/"
    assert {"base.html", "registration/login.html"} <= plantillas(respuesta)
    assert "css/vendor/bootstrap.min.css" in html
    assert "cdn" not in html.lower() and "<script>" not in html
    assert 'for="id_username"' in html and 'for="id_password"' in html  # <label> en cada campo
    # Ningún <script> sin src (JavaScript en línea), aunque lleve otros atributos
    for etiqueta in re.findall(r"<script\b[^>]*>", html):
        assert "src=" in etiqueta, etiqueta
    # Sin estilos en línea: ni el atributo style ni un elemento <style>
    assert " style=" not in html
    assert "<style" not in html.lower()
    # La misma política CSP que nginx (HB-04)
    assert respuesta.headers["Content-Security-Policy"] == settings.CONTENT_SECURITY_POLICY


def test_login_correcto_lleva_al_panel(client, operador):
    # Scenario: Credenciales correctas (HB-08, criterio 1)
    respuesta = entrar(client, "prueba.operador", CLAVE)
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("admin:index")
    # La sesión quedó iniciada con ese usuario
    assert client.session["_auth_user_id"] == str(operador.pk)


def test_login_incorrecto_muestra_el_error(client, operador):
    # Scenario: Credenciales incorrectas (HB-08, criterio 1)
    respuesta = entrar(client, "prueba.operador", CLAVE_INCORRECTA)
    assert respuesta.status_code == 200
    assert "Usuario o contraseña incorrectos." in respuesta.content.decode()
    assert "_auth_user_id" not in client.session


def test_la_raiz_lleva_al_login(client):
    # Scenario: La raíz lleva al login (HB-08, criterio 1)
    respuesta = client.get("/")
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("login")


def test_sin_sesion_el_panel_pide_login(client):
    # Scenario: Sin sesión, el panel pide iniciarla (HB-08, regresión)
    # De regresión: nace en verde, porque el panel de Django ya redirige a su login. Protege
    # contra un LOGIN_URL o una ruta que dejen /admin/ abierto sin sesión
    respuesta = client.get("/admin/")
    assert respuesta.status_code == 302
    assert respuesta.url.startswith("/admin/login/")


def test_cerrar_sesion_solo_con_post(client, operador):
    # Scenario: Cerrar sesión solo con POST (HB-08, descripción técnica)
    client.force_login(operador)
    assert client.get(reverse("logout")).status_code == 405
    # Control: el GET no cerró la sesión
    assert client.session["_auth_user_id"] == str(operador.pk)
    respuesta = client.post(reverse("logout"))
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("login")
    assert "_auth_user_id" not in client.session


def test_4_intentos_fallidos_no_bloquean_la_cuenta(client, operador):
    # Scenario: El sexto intento responde 429 (HB-08, criterio 5)
    # Control del bloqueo: con un intento fallido menos que el límite, la contraseña correcta
    # todavía entra; el bloqueo no llega antes de tiempo
    for _ in range(settings.AXES_FAILURE_LIMIT - 1):
        assert entrar(client, "prueba.operador", CLAVE_INCORRECTA).status_code == 200
    respuesta = entrar(client, "prueba.operador", CLAVE)
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("admin:index")


def test_5_intentos_fallidos_bloquean_la_cuenta(client, operador):
    # Scenario: El sexto intento responde 429 (HB-08, criterio 5)
    for _ in range(settings.AXES_FAILURE_LIMIT):
        entrar(client, "prueba.operador", CLAVE_INCORRECTA)
    respuesta = entrar(client, "prueba.operador", CLAVE)  # ni con la contraseña correcta
    assert respuesta.status_code == 429
    assert "bloqueada" in respuesta.content.decode()
    assert "registration/bloqueado.html" in plantillas(respuesta)
    assert "_auth_user_id" not in client.session


def test_el_bloqueo_dura_15_minutos_y_se_cuenta_por_usuario():
    # Scenario: Configuración del bloqueo y de la sesión (HB-08, descripción técnica)
    assert settings.AXES_FAILURE_LIMIT == 5
    assert settings.AXES_COOLOFF_TIME == timedelta(minutes=15)
    assert settings.AXES_LOCKOUT_PARAMETERS == ["username"]


def test_la_sesion_expira_tras_30_minutos_de_inactividad():
    # Scenario: Configuración del bloqueo y de la sesión (HB-08, descripción técnica)
    # Ninguno de los 3 valores es el de Django por defecto (1209600, False y False): no pasa
    # sin la configuración de este ticket
    assert settings.SESSION_COOKIE_AGE == 1800
    assert settings.SESSION_SAVE_EVERY_REQUEST and settings.SESSION_EXPIRE_AT_BROWSER_CLOSE
