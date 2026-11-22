"""registrar_residente: supertipo y subtipo en una sola transacción, como app_user (HB-06).

Corren como app_owner, salvo el último, que actúa como app_user con SET LOCAL ROLE dentro de la
transacción del test (el fixture como_app_user llega en TK-01). Antes de TK-01 no hay mock: el
Residente de prueba es Ana Ruiz, con los datos mínimos de la guía.
"""

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import connection

from apps.entidades.models import Entidad, Residente
from apps.entidades.services import registrar_residente

pytestmark = pytest.mark.django_db

MENSAJE_FECHAS = "Revisa las fechas: el ingreso no puede ser anterior al nacimiento."


def nuevo(**cambios):
    datos = dict(
        primer_nombre="Ana",
        primer_apellido="Ruiz",
        fecha_nacimiento=date(1940, 3, 1),
        fecha_ingreso=date(2026, 1, 5),
    )
    return Residente(**(datos | cambios))


def _conteos():
    return Entidad.objects.count(), Residente.objects.count()


def test_crea_la_entidad_y_el_residente_activo():
    # Scenario: Alta correcta (HB-06, criterio 5)
    entidades, residentes = _conteos()
    residente = registrar_residente(nuevo())
    assert residente.entidad.tipo == Entidad.Tipo.RESIDENTE
    assert residente.estado == Residente.Estado.ACTIVO
    assert residente.fecha_baja is None
    # Quedaron guardados en la base, uno de cada uno
    assert _conteos() == (entidades + 1, residentes + 1)
    guardado = Residente.objects.select_related("entidad").get(pk=residente.pk)
    assert guardado.entidad.tipo == Entidad.Tipo.RESIDENTE
    assert guardado.entidad.nombre is None
    assert guardado.primer_nombre == "Ana"
    assert guardado.primer_apellido == "Ruiz"
    assert guardado.estado == Residente.Estado.ACTIVO
    assert guardado.fecha_baja is None


def test_el_alta_siempre_queda_activa_y_sin_fecha_de_baja():
    # Scenario: Alta correcta (HB-06, criterio 5): el servicio fuerza ACTIVO y sin fecha de baja,
    # aunque el Residente llegue con otro estado
    residente = registrar_residente(nuevo(estado="EGRESADO", fecha_baja=date(2026, 2, 1)))
    guardado = Residente.objects.get(pk=residente.pk)
    assert guardado.estado == Residente.Estado.ACTIVO
    assert guardado.fecha_baja is None


def test_con_datos_invalidos_no_crea_nada():
    # Scenario: Datos inválidos no dejan una Entidad suelta (HB-06, criterio 5)
    antes = _conteos()
    with pytest.raises(ValidationError, match="ingreso no puede ser anterior") as error:
        registrar_residente(nuevo(fecha_ingreso=date(1930, 1, 1)))
    assert MENSAJE_FECHAS in error.value.messages
    assert _conteos() == antes


def test_no_registra_dos_veces_al_mismo_residente():
    # Scenario: No se registra dos veces (HB-06, descripción técnica)
    residente = registrar_residente(nuevo())
    # Control: el primer registro sí lo guardó
    assert Residente.objects.filter(pk=residente.pk).exists()
    antes = _conteos()
    with pytest.raises(ValueError):
        registrar_residente(residente)
    assert _conteos() == antes


def test_funciona_con_los_permisos_de_la_aplicacion():
    # Scenario: Alta como app_user (HB-06, criterio 5)
    # Control: el Residente no existía antes del alta
    assert not Residente.objects.filter(primer_nombre="Prueba").exists()
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL ROLE app_user")
        # Control: la sesión de verdad actúa como app_user, no como app_owner
        cursor.execute("SELECT current_user")
        assert cursor.fetchone() == ("app_user",)
    registrar_residente(nuevo(primer_nombre="Prueba"))
    with connection.cursor() as cursor:
        cursor.execute("RESET ROLE")
    assert Residente.objects.filter(primer_nombre="Prueba").exists()
