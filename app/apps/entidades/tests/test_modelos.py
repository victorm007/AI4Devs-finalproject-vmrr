"""Entidades: un solo Hogar, subtipo coherente, fechas y nombres (D3, HB-06).

Corren como app_owner. El Hogar lo crea una migración: existe en la base de tests sin cargar
el mock, y como la base de tests es nueva, con id = 1. Antes de TK-01 no hay mock: el Residente
de prueba es Carmen Torres Vega, con los datos mínimos de la guía.
ejecutar_sql sin params no interpola, así que el SQL literal de abajo no lleva "%"; el UPDATE
parametrizado de los Residentes sí pasa params.

Los errores se buscan con el nombre de la restricción entre comillas, como lo escribe
PostgreSQL ('... violates check constraint "ck_entidad_nombre"'), para que "ck_entidad_nombre"
no se confunda con "ck_entidad_nombre_no_vacio".

"migrate entidades zero revierte todo" no es un test de pytest: se comprueba con
./scripts/migrate.sh entidades zero y ./scripts/migrate.sh en el cierre del ticket.
"""

from datetime import date

import pytest
from django.conf import settings
from django.db import IntegrityError, transaction

from apps.entidades.models import Entidad, Residente
from apps.entidades.services import registrar_residente
from pruebas import ejecutar_sql

pytestmark = pytest.mark.django_db


@pytest.fixture
def carmen():
    return registrar_residente(
        Residente(
            primer_nombre="Carmen",
            primer_apellido="Torres",
            segundo_apellido="Vega",
            fecha_nacimiento=date(1935, 7, 22),
            fecha_ingreso=date(2025, 1, 10),
        )
    )


def test_la_migracion_crea_un_solo_hogar_con_su_nombre():
    # Scenario: La migración crea un solo Hogar (HB-06, criterio 1)
    assert Entidad.objects.filter(tipo=Entidad.Tipo.HOGAR).count() == 1
    hogar = Entidad.objects.get(tipo=Entidad.Tipo.HOGAR)
    assert hogar.pk == 1  # la base de tests es nueva
    assert hogar.nombre == settings.HOGAR_NOMBRE
    # Scenario: Nombre para mostrar (HB-06, criterio 4): el del Hogar
    assert str(hogar) == settings.HOGAR_NOMBRE
    # Scenario: Activa según el estado (HB-06, criterio 4): el Hogar siempre está activo
    assert hogar.activa is True


def test_no_puede_haber_un_segundo_hogar():
    # Scenario: Un segundo Hogar viola la restricción (HB-06, criterio 1)
    with pytest.raises(IntegrityError, match='"uq_entidad_un_hogar"'):
        with transaction.atomic():
            Entidad.objects.create(tipo=Entidad.Tipo.HOGAR, nombre="Otro hogar")


def test_un_residente_no_puede_colgar_del_hogar():
    # Scenario: Un Residente no puede colgar del Hogar (HB-06, criterio 2)
    # El tipo del Residente toma su valor por defecto, RESIDENTE: el par (id del Hogar,
    # RESIDENTE) no existe en entidad
    with pytest.raises(IntegrityError, match='"fk_residente_entidad"'):
        ejecutar_sql(
            "INSERT INTO residente (entidad_id, primer_nombre, primer_apellido, "
            "fecha_nacimiento, fecha_ingreso) "
            "SELECT id, 'Prueba', 'Prueba', '1940-01-01', '2026-01-05' FROM entidad "
            "WHERE tipo = 'HOGAR'"
        )


def test_la_fk_compuesta_no_borra_en_cascada():
    # Scenario: La FK compuesta no borra en cascada (HB-06, descripción técnica)
    # Desempacar exige exactamente 1 fila: la restricción existe y con ese nombre
    [(tabla, definicion)] = ejecutar_sql(
        "SELECT conrelid::regclass::text, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'fk_residente_entidad'"
    )
    assert tabla == "residente"
    assert definicion == (
        "FOREIGN KEY (entidad_id, tipo) REFERENCES entidad(id, tipo) ON DELETE RESTRICT"
    )
    # El destino de la FK compuesta: la unicidad de (id, tipo) en entidad
    [(tabla, definicion)] = ejecutar_sql(
        "SELECT conrelid::regclass::text, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'uq_entidad_id_tipo'"
    )
    assert tabla == "entidad"
    assert definicion == "UNIQUE (id, tipo)"


@pytest.mark.parametrize(
    ("sql", "restriccion"),
    [
        # Scenario: Entidades inválidas (HB-06, criterio 3)
        # El CHECK se evalúa antes que el índice único: falla por el nombre, no por el 2.º Hogar
        ("INSERT INTO entidad (tipo) VALUES ('HOGAR')", "ck_entidad_nombre"),
        (
            "INSERT INTO entidad (tipo, nombre) VALUES ('RESIDENTE', 'Con nombre')",
            "ck_entidad_nombre",
        ),
        # Scenario: Tipo de Entidad desconocido (HB-06, criterio 3)
        ("INSERT INTO entidad (tipo) VALUES ('OTRO')", "ck_entidad_tipo"),
    ],
    ids=["hogar-sin-nombre", "residente-con-nombre", "tipo-otro"],
)
def test_la_base_rechaza_entidades_invalidas(sql, restriccion):
    # Exigir el nombre de la restricción descarta que falle por otra causa (un NOT NULL)
    with pytest.raises(IntegrityError, match=f'"{restriccion}"'):
        ejecutar_sql(sql)


def test_el_nombre_del_hogar_no_puede_ser_solo_espacios():
    # Scenario: Nombre del Hogar solo con espacios (HB-06, criterio 3)
    with pytest.raises(IntegrityError, match='"ck_entidad_nombre_no_vacio"'):
        ejecutar_sql("UPDATE entidad SET nombre = '   ' WHERE tipo = 'HOGAR'")


@pytest.mark.parametrize(
    ("cambio", "restriccion"),
    [
        # Scenario: Estado y fecha de baja incoherentes (HB-06, criterio 3)
        ("estado = 'EGRESADO'", "ck_residente_baja"),
        ("fecha_baja = '2026-01-01'", "ck_residente_baja"),
        # Scenario: Baja anterior al ingreso (HB-06, criterio 3)
        ("estado = 'EGRESADO', fecha_baja = '2000-01-01'", "ck_residente_fechas"),
        # Scenario: Estado desconocido (HB-06, criterio 3)
        # El valor debe caber en varchar(10) para que falle el CHECK y no el largo
        ("estado = 'PERDIDO', fecha_baja = fecha_ingreso", "ck_residente_estado"),
        # Scenario: Fechas de nacimiento e ingreso inválidas (HB-06, criterio 3)
        ("fecha_nacimiento = '1899-12-31'", "ck_residente_nacimiento"),
        ("fecha_ingreso = '1930-01-01'", "ck_residente_nacimiento"),
        # Scenario: Nombre o apellido solo con espacios (HB-06, criterio 3)
        ("primer_nombre = '   '", "ck_residente_nombres"),
        ("primer_apellido = ''", "ck_residente_nombres"),
        # Scenario: Tipo distinto de RESIDENTE (HB-06, criterio 3)
        # El CHECK se evalúa antes que la FK compuesta, que también fallaría
        ("tipo = 'HOGAR'", "ck_residente_tipo"),
    ],
    ids=[
        "egresado-sin-fecha-de-baja",
        "activo-con-fecha-de-baja",
        "baja-anterior-al-ingreso",
        "estado-perdido",
        "nacimiento-antes-de-1900",
        "ingreso-antes-del-nacimiento",
        "primer-nombre-solo-espacios",
        "primer-apellido-vacio",
        "tipo-hogar",
    ],
)
def test_la_base_rechaza_residentes_invalidos(carmen, cambio, restriccion):
    # Exigir el nombre de la restricción descarta que falle por otra causa
    with pytest.raises(IntegrityError, match=f'"{restriccion}"'):
        ejecutar_sql(f"UPDATE residente SET {cambio} WHERE entidad_id = %s", [carmen.pk])


def test_nombre_completo_sin_los_nombres_vacios(carmen):
    # Scenario: Nombre para mostrar (HB-06, criterio 4): el del Residente, sin segundo nombre
    assert str(carmen.entidad) == "Carmen Torres Vega"
    # Leída de la base: la Entidad llega a su Residente por el related_name "residente"
    assert str(Entidad.objects.get(pk=carmen.pk)) == "Carmen Torres Vega"


@pytest.mark.parametrize(
    ("estado", "activa"),
    [("ACTIVO", True), ("EGRESADO", False), ("FALLECIDO", False)],
    ids=["activo", "egresado", "fallecido"],
)
def test_un_residente_esta_activo_solo_si_su_estado_es_activo(carmen, estado, activa):
    # Scenario: Activa según el estado (HB-06, criterio 4)
    carmen.estado = estado
    carmen.fecha_baja = None if estado == "ACTIVO" else date(2026, 2, 1)
    carmen.save()
    assert Entidad.objects.get(pk=carmen.pk).activa is activa


def test_indice_de_nombre_sin_acentos():
    # Scenario: Definición del índice (HB-06, descripción técnica)
    # Desempacar exige exactamente 1 fila: el índice existe y con ese nombre
    [(definicion,)] = ejecutar_sql(
        "SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_residente_nombre'"
    )
    assert "residente USING btree" in definicion
    apellido = definicion.find("f_unaccent(lower((primer_apellido)")
    nombre = definicion.find("f_unaccent(lower((primer_nombre)")
    assert apellido != -1
    assert nombre != -1
    # Primero el apellido y después el nombre: el índice sirve para ordenar así
    assert apellido < nombre
