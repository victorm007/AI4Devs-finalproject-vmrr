"""Catálogo de medicamentos: unicidad sin acentos, textos obligatorios e índices (D2, HB-05).

Corren como app_owner, salvo el de registro, que actúa como app_user con ejecutar_sql(rol=...).
Las presentaciones semilla las crea una migración: existen en la base de tests sin cargar el mock.
ejecutar_sql sin params no interpola, así que el SQL literal de abajo no lleva "%".

"migrate catalogo zero revierte todo" no es un test de pytest: se comprueba con
./scripts/migrate.sh en el cierre del ticket.

Ajustes de la revisión adversarial de HB-09 (hallazgo 2): la presentación es única sin
mayúsculas ni acentos por el índice uq_presentacion_nombre, que reemplaza al UNIQUE literal de
HB-05 (sin la restricción presentacion_nombre_key ni su índice _like). Rojo esperado: hoy la
base acepta "CAPSULA" junto a "cápsula", y el duplicado exacto lo rechaza presentacion_nombre_key.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from apps.catalogo.models import Medicamento, Presentacion, PrincipioActivo
from apps.expresiones import sin_acentos
from pruebas import ejecutar_sql

pytestmark = pytest.mark.django_db


@pytest.fixture
def tableta():
    return Presentacion.objects.get(nombre="tableta")


def nuevo_medicamento(presentacion, nombre="Losartán", concentracion="50 mg"):
    return Medicamento(
        nombre_comercial=nombre,
        tipo="GENERICO",
        presentacion=presentacion,
        concentracion=concentracion,
    )


def test_las_extensiones_estan_instaladas():
    # Scenario: Extensiones instaladas
    instaladas = {nombre for (nombre,) in ejecutar_sql("SELECT extname FROM pg_extension")}
    assert {"pg_trgm", "unaccent", "btree_gist"} <= instaladas


def test_f_unaccent_quita_acentos():
    # Scenario: f_unaccent quita los acentos
    assert ejecutar_sql("SELECT f_unaccent(lower('Losartán ÁCIDO Ñandú'))") == [
        ("losartan acido nandu",)
    ]


def test_las_8_presentaciones_semilla():
    # Scenario: Las 8 presentaciones
    assert set(Presentacion.objects.values_list("nombre", flat=True)) == {
        "tableta",
        "cápsula",
        "jarabe",
        "gotas",
        "ampolleta",
        "parche",
        "crema",
        "inhalador",
    }


def test_medicamento_duplicado_sin_mayusculas_ni_acentos(tableta):
    # Scenario: Duplicado rechazado por la base
    nuevo_medicamento(tableta).save()
    with pytest.raises(IntegrityError, match="uq_medicamento_nombre_pres_conc"):
        with transaction.atomic():
            nuevo_medicamento(tableta, nombre="LOSARTAN", concentracion="50 MG").save()


def test_el_formulario_avisa_el_duplicado_antes_de_llegar_a_la_base(tableta):
    # Scenario: El formulario avisa el duplicado
    nuevo_medicamento(tableta).save()
    # Control: un medicamento válido y distinto pasa full_clean(); así el error de abajo
    # se debe al duplicado y no a un campo que full_clean() rechaza siempre
    nuevo_medicamento(tableta, concentracion="100 mg").full_clean()
    with pytest.raises(ValidationError, match="Ya existe un medicamento") as error:
        nuevo_medicamento(tableta, nombre="losartan").full_clean()
    # El mensaje empieza con el texto del contrato (match solo busca dentro de str(error))
    assert any(m.startswith("Ya existe un medicamento") for m in error.value.messages)


def test_otra_concentracion_no_es_duplicado(tableta):
    # Scenario: Otra concentración no es duplicado
    nuevo_medicamento(tableta).save()
    nuevo_medicamento(tableta, concentracion="100 mg").save()
    assert Medicamento.objects.count() == 2


def test_principio_activo_unico_sin_acentos():
    # Scenario: Principio activo duplicado
    PrincipioActivo.objects.create(nombre="Ácido acetilsalicílico")
    with pytest.raises(IntegrityError, match="uq_principio_activo_nombre"):
        with transaction.atomic():
            PrincipioActivo.objects.create(nombre="acido acetilsalicilico")


@pytest.mark.parametrize(
    ("sql", "restriccion"),
    [
        # Scenario: Nombre comercial solo con espacios
        (
            "INSERT INTO medicamento (nombre_comercial, tipo, presentacion_id, concentracion) "
            "SELECT '   ', 'GENERICO', id, '50 mg' FROM presentacion LIMIT 1",
            "ck_medicamento_textos",
        ),
        # Scenario: Tipo fuera de GENERICO y ORIGINAL
        (
            "INSERT INTO medicamento (nombre_comercial, tipo, presentacion_id, concentracion) "
            "SELECT 'Prueba', 'OTRO', id, '50 mg' FROM presentacion LIMIT 1",
            "ck_medicamento_tipo",
        ),
        # Scenario: Principio activo y presentación vacíos
        ("INSERT INTO principio_activo (nombre) VALUES ('  ')", "ck_principio_activo_nombre"),
        ("INSERT INTO presentacion (nombre) VALUES ('')", "ck_presentacion_nombre"),
        # Scenario: La base rechaza una presentación duplicada sin acentos (revisión de HB-09,
        # hallazgo 2). La semilla "cápsula" ya existe
        ("INSERT INTO presentacion (nombre) VALUES ('CAPSULA')", "uq_presentacion_nombre"),
        # El duplicado exacto también lo rechaza uq_presentacion_nombre, y no el UNIQUE literal
        # de HB-05 (presentacion_nombre_key), que ya no debe existir
        ("INSERT INTO presentacion (nombre) VALUES ('tableta')", "uq_presentacion_nombre"),
    ],
    ids=[
        "nombre-solo-espacios",
        "tipo-otro",
        "principio-activo-vacio",
        "presentacion-vacia",
        "presentacion-duplicada",
        "presentacion-duplicada-exacta",
    ],
)
def test_la_base_rechaza(sql, restriccion):
    # Exigir el nombre de la restricción descarta que falle por otra causa (una FK o un NOT NULL)
    with pytest.raises(IntegrityError, match=restriccion):
        ejecutar_sql(sql)


@pytest.mark.parametrize(
    ("indice", "fragmentos"),
    [
        (
            "ix_medicamento_nombre_trgm",
            ["USING gin", "f_unaccent(lower(", "gin_trgm_ops", "WHERE activo"],
        ),
        ("ix_principio_activo_trgm", ["USING gin", "f_unaccent(lower(", "gin_trgm_ops"]),
        ("ix_mpa_principio_medicamento", ["(principio_activo_id, medicamento_id)"]),
        ("uq_medicamento_nombre_pres_conc", ["UNIQUE", "presentacion_id"]),
        # Scenario: Índice con su definición (revisión de HB-09, hallazgo 2)
        ("uq_presentacion_nombre", ["UNIQUE", "f_unaccent(lower((nombre)"]),
    ],
)
def test_indices_con_su_definicion(indice, fragmentos):
    # Scenario: Índices con su definición
    # Desempacar exige exactamente 1 fila: el índice existe y con ese nombre
    [(definicion,)] = ejecutar_sql("SELECT indexdef FROM pg_indexes WHERE indexname = %s", [indice])
    for fragmento in fragmentos:
        assert fragmento in definicion


def test_presentacion_sin_unique_literal():
    # Scenario: Índice con su definición (revisión de HB-09, hallazgo 2): la columna
    # presentacion.nombre ya no tiene la restricción UNIQUE literal
    restricciones = ejecutar_sql(
        "SELECT conname::text, contype::text FROM pg_constraint "
        "WHERE conrelid = 'presentacion'::regclass"
    )
    # Control: la consulta sí ve las restricciones de la tabla (su CHECK de HB-05); sin él, la
    # lista vacía de abajo no probaría nada
    assert ("ck_presentacion_nombre", "c") in restricciones
    assert [nombre for (nombre, tipo) in restricciones if tipo == "u"] == []
    indices = {
        nombre
        for (nombre,) in ejecutar_sql(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'presentacion'"
        )
    }
    # Control: el índice único por expresión está en la tabla
    assert "uq_presentacion_nombre" in indices
    # Ni el índice de la restricción literal (presentacion_nombre_key) ni su índice _like
    assert [nombre for nombre in indices if nombre.endswith("_like")] == []
    assert [nombre for nombre in indices if nombre.startswith("presentacion_nombre")] == []


def test_las_fk_de_la_tabla_puente_no_tienen_indice_propio():
    # Scenario: Sin índices duplicados en la tabla puente
    # Control: la tabla puente existe y tiene sus 3 índices; sin ella, la lista vacía
    # de abajo no probaría nada
    todos = {
        nombre
        for (nombre,) in ejecutar_sql(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'medicamento_principio_activo'"
        )
    }
    assert todos == {
        "medicamento_principio_activo_pkey",
        "uq_mpa_medicamento_principio",
        "ix_mpa_principio_medicamento",
    }
    sueltos = ejecutar_sql(
        "SELECT indexname FROM pg_indexes WHERE tablename = 'medicamento_principio_activo' "
        "AND indexname NOT IN ('medicamento_principio_activo_pkey', "
        "'uq_mpa_medicamento_principio', 'ix_mpa_principio_medicamento')"
    )
    assert sueltos == []


def test_app_user_puede_registrar_en_el_catalogo():
    # Scenario: app_user registra un principio activo
    # Control: el registro no existía antes del INSERT
    assert not PrincipioActivo.objects.filter(nombre="Prueba activa").exists()
    ejecutar_sql("INSERT INTO principio_activo (nombre) VALUES ('Prueba activa')", rol="app_user")
    assert PrincipioActivo.objects.filter(nombre="Prueba activa").exists()


@pytest.mark.lento
def test_la_busqueda_por_nombre_usa_el_indice_trigram(tableta):
    # Scenario: Búsqueda desde el ORM con el índice trigram
    # Si sin_acentos() deja de generar exactamente f_unaccent(lower(...)), por ejemplo con
    # Unaccent(Lower(...)) de django.contrib.postgres, el plan deja de usar el índice
    consulta = (
        Medicamento.objects.filter(activo=True)
        .annotate(n=sin_acentos("nombre_comercial"))
        .filter(n__contains="losar")
    )
    sql, parametros = consulta.query.sql_with_params()
    # Control: el SQL del ORM lleva la expresión del índice (diagnóstico más claro que el plan).
    # Sin distinguir mayúsculas: Lower() de Django escribe LOWER(...), y PostgreSQL lo trata igual
    assert "f_unaccent(lower(" in sql.lower()
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_seqscan = off")  # la tabla es pequeña: se fuerza el índice
        cursor.execute(f"EXPLAIN {sql}", parametros)
        plan = "\n".join(fila for (fila,) in cursor.fetchall())
    assert "ix_medicamento_nombre_trgm" in plan
