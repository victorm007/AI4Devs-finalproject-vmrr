"""registrar_residente: supertipo y subtipo en una sola transacción, como app_user (HB-06).

Corren como app_owner, salvo el de los permisos, que actúa como app_user con SET LOCAL ROLE
dentro de la transacción del test (el fixture como_app_user llega en TK-01). Antes de TK-01 no
hay mock: el Residente de prueba es Ana Ruiz, con los datos mínimos de la guía.

Ajustes de la revisión de HB-06: el servicio quita los espacios de los nombres antes de validar,
y si el alta falla deja el Residente recibido como estaba, para poder reintentar. El reintento
tras un fallo de escritura es el único test que inyecta una falla (monkeypatch sobre
Residente.save): la base sigue siendo PostgreSQL real (ADR-0023), porque con datos reales
save() no falla después de que full_clean los validó.
"""

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection

from apps.entidades.models import Entidad, Residente
from apps.entidades.services import registrar_residente

pytestmark = pytest.mark.django_db

MENSAJE_FECHAS = "Revisa las fechas: el ingreso no puede ser anterior al nacimiento."
MENSAJE_NOMBRES = "El primer nombre y el primer apellido no pueden quedar vacíos."


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
    # TODO(TK-01): usar el fixture como_app_user cuando exista
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


def test_quita_los_espacios_de_los_nombres_y_guarda_vacios_los_segundos():
    # Scenario: Nombres normalizados (revisión de HB-06, nit 6)
    residente = registrar_residente(
        nuevo(
            primer_nombre="  Ana ",
            primer_apellido=" Ruiz",
            segundo_nombre="",
            segundo_apellido="   ",
        )
    )
    # Leído de la base: lo que importa es lo que quedó guardado
    guardado = Residente.objects.get(pk=residente.pk)
    assert guardado.primer_nombre == "Ana"
    assert guardado.primer_apellido == "Ruiz"
    # NULL en la base, no "" ni "   "
    assert guardado.segundo_nombre is None
    assert guardado.segundo_apellido is None


def test_un_primer_nombre_solo_con_espacios_es_un_error_de_validacion():
    # Scenario: Nombre solo con espacios (revisión de HB-06, sugerencia 3)
    antes = Entidad.objects.count()
    # ValidationError y no IntegrityError: el servicio lo detecta antes que la base
    with pytest.raises(ValidationError) as error:
        registrar_residente(nuevo(primer_nombre="   "))
    # El error es del campo, no un error general de la restricción
    assert "primer_nombre" in error.value.message_dict
    assert Entidad.objects.count() == antes


def test_la_restriccion_de_nombres_tiene_un_mensaje_claro():
    # Scenario: Mensaje claro de nombres vacíos (revisión de HB-06, sugerencia 3)
    # Sin pasar por el servicio: el mensaje es el de ck_residente_nombres
    residente = nuevo(primer_apellido="   ")
    with pytest.raises(ValidationError) as error:
        residente.validate_constraints()
    assert MENSAJE_NOMBRES in error.value.messages


def test_con_datos_invalidos_el_residente_recibido_queda_como_estaba():
    # Scenario: Datos inválidos no alteran el Residente recibido (revisión de HB-06,
    # sugerencia 2)
    residente = nuevo(
        primer_nombre=" Ana ",
        primer_apellido="Ruiz ",
        segundo_apellido="   ",
        estado="EGRESADO",
        fecha_baja=date(2026, 2, 1),
        fecha_ingreso=date(1930, 1, 1),
    )
    # Control: falla por las fechas, la validación que se quiere provocar
    with pytest.raises(ValidationError, match="ingreso no puede ser anterior"):
        registrar_residente(residente)
    assert residente.estado == "EGRESADO"
    assert residente.fecha_baja == date(2026, 2, 1)
    # Los nombres originales, sin quitarles los espacios
    assert residente.primer_nombre == " Ana "
    assert residente.primer_apellido == "Ruiz "
    assert residente.segundo_apellido == "   "
    # Sigue sin Entidad
    assert residente.pk is None


def test_un_fallo_al_guardar_permite_reintentar(monkeypatch):
    # Scenario: Un fallo al guardar permite reintentar (revisión de HB-06, sugerencia 2)
    # Única falla inyectada (decisión 5 del diseño): Residente.save lanza IntegrityError la
    # primera vez y después guarda de verdad en PostgreSQL.
    guardar_original = Residente.save
    entidad_creada_al_fallar = []

    def guardar_que_falla_una_vez(self, *args, **kwargs):
        if not entidad_creada_al_fallar:
            entidad_creada_al_fallar.append(Entidad.objects.filter(pk=self.pk).exists())
            raise IntegrityError("falla simulada al guardar el Residente")
        return guardar_original(self, *args, **kwargs)

    monkeypatch.setattr(Residente, "save", guardar_que_falla_una_vez)
    entidades = Entidad.objects.count()
    residente = nuevo()
    with pytest.raises(IntegrityError, match="falla simulada"):
        registrar_residente(residente)
    # Control: la falla ocurrió en Residente.save, con la Entidad ya creada
    assert entidad_creada_al_fallar == [True]
    # La transacción revirtió la Entidad, y el objeto recibido sigue sin ella
    assert Entidad.objects.count() == entidades
    assert residente.pk is None
    # Segundo intento, ya sin la falla, con el mismo objeto
    registrado = registrar_residente(residente)
    guardado = Residente.objects.get(pk=registrado.pk)
    assert guardado.estado == Residente.Estado.ACTIVO
    assert guardado.primer_nombre == "Ana"
    assert Entidad.objects.count() == entidades + 1
