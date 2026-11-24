"""Residentes en /admin/: permisos por grupo, alta con el servicio, egreso validado y búsqueda.

HB-09. Capa HTTP: el panel /admin/ con el cliente de pruebas de Django. admin_client es el
fixture de pytest-django: un superusuario (el Administrador) con sesión iniciada. Antes de
TK-01 no hay mock: la residente de prueba es María Guadalupe Hernández López, con los datos
mínimos de la guía, y los usuarios de prueba son "prueba.*", creados con create_user; los 2
grupos los crea la migración 0003_grupos de accounts.

Los usuarios de grupo entran con force_login, nunca con client.login(), que choca con
django-axes. operador usa el client de pytest-django y lector un Client propio, para poder
usar los 2 en el mismo test.

Cada 403 lleva un control positivo (la misma persona sí ve otra página del panel), y después
de un 403 de cambio o de borrado se comprueba que la residente sigue igual en la base.

Rojo esperado: antes de HB-09 Residente no está registrado en el panel, así que sus URL
responden 404 (el fixture maria falla en su POST de alta).

Las búsquedas cuentan los resultados con context["cl"].result_count además de buscar el texto,
porque el término buscado también se pinta en la página.

Ajustes de la revisión adversarial de HB-09 (hallazgos 1, 6 y 7): búsqueda por nombre y
apellido juntos y sin espacios sobrantes, el alta como app_user y la CSP (sin <script> en
línea, <style>, atributos style ni on*=) en el alta, la lista y el cambio. El alta como
app_user hace SET LOCAL ROLE app_user en línea, en la conexión del test (la misma que usa el
cliente de Django), después de force_login: el fixture como_app_user nace en TK-01.

Rojo esperado de los ajustes: "maria hernandez" y " hernandez " no encuentran nada. Los de
app_user y CSP son de regresión: pasan desde el inicio y protegen lo que HB-09 ya entregó.
"""

import re
from datetime import date

import pytest
from django.contrib import admin
from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import Client

from apps.entidades.models import Entidad, Residente

pytestmark = [pytest.mark.django_db, pytest.mark.http]
URL = "/admin/entidades/residente/"
# Lo que la CSP bloquearía: <script> sin src, <style>, atributos style y manejadores on*=
SCRIPT_EN_LINEA = re.compile(r"<script\b(?![^>]*\bsrc\s*=)[^>]*>", re.IGNORECASE)
SCRIPT_CON_SRC = re.compile(r"<script\b[^>]*\bsrc\s*=", re.IGNORECASE)
ETIQUETA_STYLE = re.compile(r"<style\b", re.IGNORECASE)
ATRIBUTO_STYLE = re.compile(r"<[^>]*\sstyle\s*=", re.IGNORECASE)
MANEJADOR_ON = re.compile(r"<[^>]*\son[a-z]+\s*=", re.IGNORECASE)
ALTA = {
    "primer_nombre": "María",
    "segundo_nombre": "Guadalupe",
    "primer_apellido": "Hernández",
    "segundo_apellido": "López",
    "fecha_nacimiento": "1938-04-12",
    "fecha_ingreso": "2023-02-01",
}
AVISO_SIN_FECHA = "La fecha de baja es obligatoria"
AVISO_FECHA_ANTERIOR = "La fecha de baja no puede ser anterior al ingreso."


def codigo_en_linea(html):
    """Las coincidencias de todos los patrones de código en línea."""
    return [
        coincidencia
        for patron in (SCRIPT_EN_LINEA, ETIQUETA_STYLE, ATRIBUTO_STYLE, MANEJADOR_ON)
        for coincidencia in patron.findall(html)
    ]


def rol_actual():
    """El rol con el que corre ahora la conexión del test (y la del cliente de Django)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        return cursor.fetchone()[0]


def con_sesion(cliente, nombre, grupo):
    usuario = get_user_model().objects.create_user(nombre, is_staff=True)
    usuario.groups.add(Group.objects.get(name=grupo))
    cliente.force_login(usuario)
    return cliente


@pytest.fixture
def operador(client):
    """Un usuario de Lectura y escritura con sesión iniciada."""
    return con_sesion(client, "prueba.operador", "Lectura y escritura")


@pytest.fixture
def lector():
    """Un usuario de Solo lectura con sesión iniciada, en su propio Client."""
    return con_sesion(Client(), "prueba.lector", "Solo lectura")


@pytest.fixture
def maria(operador):
    """María Guadalupe Hernández López, registrada desde el panel por el operador."""
    assert operador.post(f"{URL}add/", ALTA).status_code == 302
    return Residente.objects.get(primer_apellido="Hernández")


def test_solo_lectura_consulta_residentes(lector):
    # Scenario: Solo lectura consulta los residentes (HB-09, criterio 1)
    # Control: la lista responde 200; el 403 del alta no es por falta de sesión
    assert lector.get(URL).status_code == 200
    assert lector.get(f"{URL}add/").status_code == 403


def test_solo_lectura_no_cambia_un_residente(operador, lector, maria):
    # Scenario: Solo lectura no cambia un residente (HB-09, criterio 1)
    url = f"{URL}{maria.pk}/change/"
    # Control positivo del botón de guardar: en la página editable del operador sí aparece,
    # así que su ausencia de abajo se debe al modo de consulta
    editable = operador.get(url)
    assert editable.status_code == 200
    assert 'name="_save"' in editable.content.decode()
    consulta = lector.get(url)
    assert consulta.status_code == 200
    assert 'name="_save"' not in consulta.content.decode()
    datos = ALTA | {"estado": "EGRESADO", "fecha_baja": "2026-02-01"}
    assert lector.post(url, datos).status_code == 403
    # Sigue ACTIVO y sin fecha de baja
    maria.refresh_from_db()
    assert maria.estado == Residente.Estado.ACTIVO
    assert maria.fecha_baja is None


def test_el_alta_crea_la_entidad_y_el_residente_activo(operador):
    # Scenario: El alta crea la entidad y el residente activo (HB-09, criterio 6)
    # Control: la residente no existía antes del alta
    assert not Residente.objects.filter(primer_apellido="Hernández").exists()
    entidades = Entidad.objects.count()
    assert operador.post(f"{URL}add/", ALTA).status_code == 302
    maria = Residente.objects.select_related("entidad").get(primer_apellido="Hernández")
    assert maria.entidad.tipo == Entidad.Tipo.RESIDENTE
    assert maria.estado == Residente.Estado.ACTIVO
    assert maria.fecha_baja is None
    assert maria.primer_nombre == "María"
    assert maria.fecha_ingreso == date(2023, 2, 1)
    # Una sola entidad nueva: la de la residente
    assert Entidad.objects.count() == entidades + 1


def test_el_alta_no_pide_el_estado(operador):
    # Scenario: El alta no pide el estado (HB-09, descripción técnica)
    respuesta = operador.get(f"{URL}add/")
    assert respuesta.status_code == 200  # sin esto, un 404 también pasaría el test
    html = respuesta.content.decode()
    # Control: es el formulario de alta, con los campos del residente
    assert 'name="primer_apellido"' in html
    assert 'name="estado"' not in html
    assert 'name="fecha_baja"' not in html


def test_egresar_sin_fecha_de_baja_da_un_mensaje(operador, maria):
    # Scenario: Egresar sin fecha de baja da un mensaje (HB-09, criterio 3)
    respuesta = operador.post(f"{URL}{maria.pk}/change/", ALTA | {"estado": "EGRESADO"})
    assert respuesta.status_code == 200
    assert AVISO_SIN_FECHA in respuesta.content.decode()
    maria.refresh_from_db()
    assert maria.estado == Residente.Estado.ACTIVO


def test_fecha_de_baja_anterior_al_ingreso(operador, maria):
    # Scenario: Fecha de baja anterior al ingreso (readme, sección 5, "Validaciones incluidas")
    # Control: ingresó el 2023-02-01, un día después de la fecha de baja que se envía
    assert maria.fecha_ingreso == date(2023, 2, 1)
    datos = ALTA | {"estado": "EGRESADO", "fecha_baja": "2023-01-31"}
    respuesta = operador.post(f"{URL}{maria.pk}/change/", datos)
    assert respuesta.status_code == 200
    assert AVISO_FECHA_ANTERIOR in respuesta.content.decode()
    maria.refresh_from_db()
    assert maria.estado == Residente.Estado.ACTIVO
    assert maria.fecha_baja is None


@pytest.mark.parametrize("estado", ["EGRESADO", "FALLECIDO"])
def test_egresar_o_fallecer_con_fecha_de_baja(operador, maria, estado):
    # Scenario: Egreso o defunción con fecha de baja (HB-09, descripción técnica)
    # Control: antes del cambio, su entidad está activa
    assert Entidad.objects.get(pk=maria.pk).activa is True
    datos = ALTA | {"estado": estado, "fecha_baja": "2026-02-01"}
    assert operador.post(f"{URL}{maria.pk}/change/", datos).status_code == 302
    maria.refresh_from_db()
    assert maria.estado == estado
    assert maria.fecha_baja == date(2026, 2, 1)
    assert Entidad.objects.get(pk=maria.pk).activa is False


def test_la_busqueda_ignora_acentos(operador, maria):
    # Scenario: "hernandez" encuentra "Hernández" (HB-09, criterio 5)
    respuesta = operador.get(URL, {"q": "hernandez"})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 1
    assert "Hernández" in respuesta.content.decode()
    # Control negativo: otro apellido no la incluye
    respuesta = operador.get(URL, {"q": "torres"})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 0
    assert "Hernández" not in respuesta.content.decode()


def test_la_busqueda_por_nombre_y_apellido(operador, maria):
    # Scenario: Nombre y apellido juntos (revisión de HB-09, hallazgo 1)
    for termino in ("maria hernandez", " hernandez "):
        respuesta = operador.get(URL, {"q": termino})
        assert respuesta.status_code == 200
        assert respuesta.context["cl"].result_count == 1
        assert "Hernández" in respuesta.content.decode()
    # Una palabra que no coincide la deja fuera, aunque la otra sí coincida
    respuesta = operador.get(URL, {"q": "maria torres"})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 0
    assert "Hernández" not in respuesta.content.decode()


def test_alta_de_un_residente_como_app_user():
    # Scenario: Alta de un residente como app_user (revisión de HB-09, hallazgo 6)
    # Regresión: el alta de HB-09 ya funciona con los permisos de app_user. Protege que el
    # panel, registrar_residente() y el historial de cambios (django_admin_log) no necesiten
    # los de app_owner
    cliente = con_sesion(Client(), "prueba.alta", "Lectura y escritura")  # antes del rol
    # Control: los tests corren como app_owner hasta el SET LOCAL ROLE
    assert rol_actual() != "app_user"
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL ROLE app_user")
    assert rol_actual() == "app_user"
    assert not Residente.objects.filter(primer_apellido="Hernández").exists()
    entidades = Entidad.objects.count()
    assert cliente.post(f"{URL}add/", ALTA).status_code == 302
    # La petición corrió en la misma conexión, que sigue como app_user
    assert rol_actual() == "app_user"
    maria = Residente.objects.select_related("entidad").get(primer_apellido="Hernández")
    assert maria.entidad.tipo == Entidad.Tipo.RESIDENTE
    assert maria.estado == Residente.Estado.ACTIVO
    assert Entidad.objects.count() == entidades + 1
    assert LogEntry.objects.filter(
        content_type__model="residente",
        action_flag=ADDITION,
        object_id=str(maria.pk),
    ).exists()


@pytest.mark.parametrize("pagina", ["alta", "lista", "cambio"])
def test_las_paginas_de_residentes_no_tienen_codigo_en_linea(operador, maria, pagina):
    # Scenario: Alta, lista y cambio de residentes sin código en línea (revisión de HB-09,
    # hallazgo 7). Regresión: HB-09 ya cumple la CSP en estas páginas
    url, control = {
        "alta": (f"{URL}add/", 'name="primer_apellido"'),
        "lista": (URL, "Hernández"),
        "cambio": (f"{URL}{maria.pk}/change/", 'name="_save"'),
    }[pagina]
    respuesta = operador.get(url)
    assert respuesta.status_code == 200
    assert respuesta.headers.get("Content-Security-Policy")
    html = respuesta.content.decode()
    # Control: es la página de verdad (el formulario, la lista con María o el cambio editable)
    # y carga scripts externos; así, la ausencia de código en línea no se debe a una página vacía
    assert control in html
    assert SCRIPT_CON_SRC.search(html)
    assert codigo_en_linea(html) == []


@pytest.mark.parametrize("quien", ["administrador", "lectura-escritura"])
def test_nadie_borra_residentes(operador, admin_client, maria, quien):
    # Scenario: Nadie borra residentes (HB-09, criterio 4)
    cliente = admin_client if quien == "administrador" else operador
    url = f"{URL}{maria.pk}/"
    # Control: la misma persona sí abre la página de cambio de la residente
    assert cliente.get(f"{url}change/").status_code == 200
    assert cliente.get(f"{url}delete/").status_code == 403
    assert cliente.post(f"{url}delete/", {"post": "yes"}).status_code == 403
    # La residente y su entidad siguen en la base
    assert Residente.objects.filter(pk=maria.pk).exists()
    assert Entidad.objects.filter(pk=maria.pk).exists()


def test_el_hogar_no_se_edita_en_el_panel(admin_client):
    # Scenario: El Hogar no se edita en el panel (HB-09, descripción técnica)
    # La aserción central (Entidad fuera del registro) es de regresión: hoy ya pasa, porque
    # ningún admin.py registra Entidad. Protege que nadie la registre después. Los controles
    # de Residente hacen que el test nazca en rojo y que no pase con un panel vacío
    assert Residente in admin.site._registry
    assert Entidad not in admin.site._registry
    # Control: el Administrador sí abre la lista de residentes de la misma app
    assert admin_client.get(URL).status_code == 200
    assert admin_client.get("/admin/entidades/entidad/").status_code == 404
