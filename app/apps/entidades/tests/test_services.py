"""registrar_residente: supertipo y subtipo en una sola transacción, como app_user (HB-06).

Corren como app_owner, salvo el de los permisos, que actúa como app_user con SET LOCAL ROLE
dentro de la transacción del test (el fixture como_app_user llega en TK-01). Antes de TK-01 no
hay mock: el Residente de prueba es Ana Ruiz, con los datos mínimos de la guía.

Ajustes de la revisión de HB-06: el servicio quita los espacios de los nombres antes de validar,
y si el alta falla deja el Residente recibido como estaba, para poder reintentar.

Segunda revisión de HB-06: ningún test simula la base (ADR-0023), no hay monkeypatch. Las
fallas de escritura son restricciones temporales reales de PostgreSQL que Django no conoce, así
que full_clean pasa y es la base la que rechaza el alta: ck_prueba_falla (CHECK ... NOT VALID)
falla en el INSERT del Residente, y uq_prueba_apellido (UNIQUE ... DEFERRABLE INITIALLY
DEFERRED) falla en el COMMIT, después de un save correcto. Los 2 tests corren como app_owner,
el dueño de la tabla, porque necesitan ALTER TABLE. El de la falla al confirmar usa
transaction=True y serialized_rollback=True: sin transacción envolvente, el atomic del servicio
es la transacción real, y el vaciado final no borra el Hogar de la migración (CLAUDE.md).
ejecutar_sql sin params no interpola, así que el SQL literal de abajo no lleva "%".
"""

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection

from apps.entidades.models import Entidad, Residente
from apps.entidades.services import registrar_residente
from pruebas import ejecutar_sql

pytestmark = pytest.mark.django_db

MENSAJE_FECHAS = "Revisa las fechas: el ingreso no puede ser anterior al nacimiento."
MENSAJE_NOMBRES = "El primer nombre y el primer apellido no pueden quedar vacíos."
MENSAJE_YA_REGISTRADO = "El residente ya está registrado."


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


def test_un_residente_con_entidad_asignada_no_se_registra():
    # Scenario: Un Residente con Entidad asignada no se registra (segunda revisión de HB-06,
    # sugerencia 2)
    # Rojo esperado: hoy solo se mira _state.adding, y este objeto sin guardar lo tiene en True
    ana = registrar_residente(nuevo())
    otro = nuevo(primer_nombre="Prueba", entidad=ana.entidad)
    # Control: el objeto no está guardado, pero ya trae la Entidad de Ana
    assert otro._state.adding is True
    assert otro.pk == ana.pk
    antes = _conteos()
    with pytest.raises(ValueError, match=MENSAJE_YA_REGISTRADO):
        registrar_residente(otro)
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
    # Rojo esperado: full_clean convierte la fecha de ingreso de texto a date, y hoy el servicio
    # no restaura las fechas
    residente = nuevo(
        primer_nombre=" Ana ",
        primer_apellido="Ruiz ",
        segundo_apellido="   ",
        estado="EGRESADO",
        fecha_baja=date(2026, 2, 1),
        # Como texto, anterior al nacimiento (1940-03-01)
        fecha_ingreso="1930-01-01",
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
    # Las fechas como llegaron: el mismo texto, no un date
    assert residente.fecha_ingreso == "1930-01-01"
    assert residente.fecha_nacimiento == date(1940, 3, 1)
    # Sigue sin Entidad
    assert residente.pk is None


def test_un_fallo_al_guardar_permite_reintentar():
    # Scenario: Un fallo al guardar permite reintentar (revisión de HB-06, sugerencia 2)
    # Regresión: nace en verde. Cambia la forma de provocar la falla (decisión 3 del diseño):
    # una restricción real de PostgreSQL, desconocida para Django, en lugar de monkeypatch.
    # El test corre como app_owner, dueño de la tabla, y el DDL se revierte con su transacción.
    # Control: no hay ninguna Ana antes del alta, así que el rechazo es por este alta
    assert not Residente.objects.filter(primer_nombre="Ana").exists()
    ejecutar_sql(
        "ALTER TABLE residente ADD CONSTRAINT ck_prueba_falla "
        "CHECK (primer_nombre <> 'Ana') NOT VALID"
    )
    entidades = Entidad.objects.count()
    residente = nuevo()
    # full_clean pasa y se crea la Entidad; el INSERT del Residente es el que falla. Control: el
    # error es el de la restricción temporal, no otro anterior
    with pytest.raises(IntegrityError, match='"ck_prueba_falla"'):
        registrar_residente(residente)
    # La transacción revirtió la Entidad, y el objeto recibido sigue sin ella
    assert Entidad.objects.count() == entidades
    assert residente.pk is None
    assert residente._state.adding is True
    # Segundo intento, ya sin la restricción, con el mismo objeto
    ejecutar_sql("ALTER TABLE residente DROP CONSTRAINT ck_prueba_falla")
    registrado = registrar_residente(residente)
    guardado = Residente.objects.get(pk=registrado.pk)
    assert guardado.estado == Residente.Estado.ACTIVO
    assert guardado.primer_nombre == "Ana"
    assert Entidad.objects.count() == entidades + 1


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_un_fallo_al_confirmar_permite_reintentar():
    # Scenario: Un fallo al confirmar permite reintentar (segunda revisión de HB-06,
    # sugerencia 3)
    # Regresión: nace en verde, porque el servicio ya restaura _state. Es el único test que
    # sostiene esa restauración: la falla ocurre en el COMMIT, después de un save correcto, así
    # que _state.adding ya había pasado a False y el servicio debe devolverlo a True.
    # Sin transacción envolvente (transaction=True), el atomic del servicio es la transacción
    # real y su COMMIT comprueba las restricciones diferidas. Corre como app_owner, el dueño de
    # la tabla, porque necesita ALTER TABLE. El marcador del test reemplaza al del módulo.
    carmen = registrar_residente(
        nuevo(
            primer_nombre="Carmen",
            primer_apellido="Torres",
            fecha_nacimiento=date(1935, 7, 22),
            fecha_ingreso=date(2025, 1, 10),
        )
    )
    # Control: Carmen Torres quedó confirmada, así que otro "Torres" viola la restricción
    assert Residente.objects.filter(pk=carmen.pk, primer_apellido="Torres").exists()
    # El DDL queda confirmado en este test: el finally quita la restricción aunque algo falle
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE residente ADD CONSTRAINT uq_prueba_apellido "
                "UNIQUE (primer_apellido) DEFERRABLE INITIALLY DEFERRED"
            )
            # Control: la restricción es diferida, así que solo se comprueba al confirmar
            cursor.execute(
                "SELECT condeferrable, condeferred FROM pg_constraint "
                "WHERE conname = 'uq_prueba_apellido'"
            )
            assert cursor.fetchone() == (True, True)
        entidades, residentes = _conteos()
        # Ana Torres
        otro = nuevo(primer_apellido="Torres")
        with pytest.raises(IntegrityError, match='"uq_prueba_apellido"'):
            registrar_residente(otro)
        # El COMMIT falló y revirtió todo: ninguna Entidad ni Residente nuevos
        assert _conteos() == (entidades, residentes)
        # El objeto recibido vuelve a estar sin guardar y sin Entidad
        assert otro._state.adding is True
        assert otro.pk is None
        assert "entidad" not in otro._state.fields_cache
        # Segundo intento, ya sin la restricción, con el mismo objeto
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE residente DROP CONSTRAINT uq_prueba_apellido")
        registrado = registrar_residente(otro)
        guardado = Residente.objects.get(pk=registrado.pk)
        assert guardado.estado == Residente.Estado.ACTIVO
        assert guardado.primer_nombre == "Ana"
        assert guardado.primer_apellido == "Torres"
        assert Entidad.objects.count() == entidades + 1
    finally:
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE residente DROP CONSTRAINT IF EXISTS uq_prueba_apellido")
