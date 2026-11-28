"""Esquema de los conteos físicos: período, cierre, renglones y diferencia (TK-01).

Capa de servicio y base de datos, contra PostgreSQL real y como app_owner. Misma estructura
que apps/inventario/tests/test_esquema.py (guía, sección 3.3): los casos inválidos, sus
controles positivos y los nombres leídos del catálogo de PostgreSQL (design, decisión 9).
Los 2 casos de conteos que la guía pone en la tabla de inventario (renglón en el conteo 1
cerrado y la columna generada) viven aquí, una sola vez.

Datos del mock (sección 3.4): el conteo 1 es de María (101) y está CERRADO; el conteo 2 es del
Hogar, EN_PROCESO, con Paracetamol (6), Omeprazol (5, 58 contadas contra 59) y Aspirina
Protect (10), y le faltan Losartán (2) y Tempra (7).

Casos agregados a la guía (DDL de las secciones 3.1 y 3.3): ck_conteo_estado, ck_detalle_fisica
y ck_detalle_sistema.

Rojo esperado: apps.conteos.models no existe, así que falla la importación del módulo
(ModuleNotFoundError). Después de crear los modelos, cada test falla hasta que existe la
restricción, el trigger o el índice que comprueba.

Ajustes de la revisión de TK-01 (PR #3): el conteo cerrado es inmutable también al borrar su
encabezado, al cambiar o borrar sus renglones y al cambiar el conteo_id de un renglón, para
sacarlo del conteo cerrado o meterlo en él (hallazgo 2; design, decisiones 1 y 5). Rojo
esperado: solo test_sacar_un_renglon_de_un_conteo_cerrado (hoy fn_detalle_conteo_cerrado mira
solo el conteo de NEW, así que el UPDATE pasa: "DID NOT RAISE"). Los demás son de regresión:
TK-01 ya los rechaza con tg_conteo_cerrado y tg_detalle_conteo_cerrado, y los protegen de que
la migración 0003 los rompa.
"""

import re
from decimal import Decimal

import pytest
from django.contrib import admin
from django.db import DatabaseError

from apps.catalogo.models import Medicamento
from apps.conteos.models import ConteoFisico, DetalleConteo
from pruebas import ejecutar_sql

pytestmark = pytest.mark.django_db

USUARIO = "(SELECT id FROM usuario WHERE username = 'operador.demo')"
HOGAR = "(SELECT id FROM entidad WHERE tipo = 'HOGAR')"


def insertar_conteo(**campos) -> tuple[str, list]:
    """INSERT válido (conteo de octubre de José Luis, EN_PROCESO) con los campos que cambie."""
    valores = {
        "entidad_id": 102,
        "periodo_inicio": "2026-10-01",
        "periodo_fin": "2026-10-31",
        "estado": "EN_PROCESO",
        "nota": "Conteo de prueba",
    } | campos
    columnas = ", ".join(valores)
    marcadores = ", ".join(["%s"] * len(valores))
    sql = (
        f"INSERT INTO conteo_fisico ({columnas}, usuario_id, creado_en) "
        f"SELECT {marcadores}, {USUARIO}, now()"
    )
    return sql, list(valores.values())


def insertar_renglon(conteo_id, medicamento_id, fisica, sistema) -> tuple[str, list]:
    sql = (
        "INSERT INTO detalle_conteo (conteo_id, medicamento_id, cantidad_fisica, "
        "cantidad_sistema) VALUES (%s, %s, %s, %s)"
    )
    return sql, [conteo_id, medicamento_id, Decimal(fisica), Decimal(sistema)]


CASOS = [
    pytest.param(
        *insertar_conteo(periodo_inicio="2026-10-31", periodo_fin="2026-10-01"),
        "ck_conteo_periodo",
        id="periodo-al-reves",
    ),
    pytest.param(
        "UPDATE conteo_fisico SET estado = 'ABIERTO' WHERE id = 2",
        None,
        "ck_conteo_estado",
        id="estado-desconocido",
    ),
    pytest.param(
        "UPDATE conteo_fisico SET estado = 'CERRADO' WHERE id = 2",
        None,
        "ck_conteo_cierre",
        id="cerrar-sin-fecha",
    ),
    pytest.param(
        "UPDATE conteo_fisico SET nota = 'x' WHERE id = 1",
        None,
        "El conteo 1 está cerrado y no se puede modificar",
        id="cambiar-conteo-cerrado",
    ),
    # Paracetamol en el conteo 1 de María, ya cerrado
    pytest.param(
        *insertar_renglon(1, 6, "1", "1"),
        "El conteo 1 está cerrado",
        id="renglon-en-conteo-cerrado",
    ),
    # El conteo 2 ya tiene su renglón de Omeprazol
    pytest.param(*insertar_renglon(2, 5, "58", "59"), "uq_detalle_conteo", id="segundo-renglon"),
    pytest.param(*insertar_renglon(2, 2, "-1", "20"), "ck_detalle_fisica", id="fisica-negativa"),
    pytest.param(*insertar_renglon(2, 2, "18", "-1"), "ck_detalle_sistema", id="sistema-negativa"),
    # En el conteo 2 (EN_PROCESO): el rechazo se debe a la columna generada, no al cierre
    pytest.param(
        "UPDATE detalle_conteo SET diferencia = 0 WHERE conteo_id = 2",
        None,
        r'column "diferencia" can only be updated to DEFAULT',
        id="columna-generada",
    ),
]


@pytest.mark.parametrize(("sql", "params", "mensaje"), CASOS)
def test_la_base_rechaza(datos_demo, sql, params, mensaje):
    # Scenario: Período al revés, Cerrar sin fecha de cierre, Cambiar el encabezado de un
    # conteo cerrado, Agregar un renglón a un conteo cerrado, Segundo renglón del mismo
    # Medicamento y Escribir la diferencia a mano (TK-01, prueba 3.3 y criterio 8)
    with pytest.raises(DatabaseError, match=mensaje):
        ejecutar_sql(sql, params)
    # El rechazo no cambió los conteos del mock
    assert ejecutar_sql("SELECT id, estado FROM conteo_fisico ORDER BY id") == [
        (1, "CERRADO"),
        (2, "EN_PROCESO"),
    ]
    assert ejecutar_sql("SELECT count(*) FROM detalle_conteo") == [(5,)]


def test_un_conteo_valido_si_se_guarda(datos_demo):
    # Control de periodo-al-reves: el INSERT base de insertar_conteo es válido, y entra
    # EN_PROCESO sin fecha de cierre
    ejecutar_sql(*insertar_conteo())
    assert ejecutar_sql("SELECT estado, cerrado_en FROM conteo_fisico WHERE entidad_id = 102") == [
        ("EN_PROCESO", None)
    ]


def test_cerrar_con_fecha_si_se_guarda_y_ya_no_se_modifica(datos_demo):
    # Control de cerrar-sin-fecha y de cambiar-conteo-cerrado: con cerrado_en, el conteo 2 sí
    # se cierra; mientras estaba EN_PROCESO, su nota sí se podía cambiar
    ejecutar_sql("UPDATE conteo_fisico SET nota = 'Revisado' WHERE id = 2")
    ejecutar_sql("UPDATE conteo_fisico SET estado = 'CERRADO', cerrado_en = now() WHERE id = 2")
    assert ejecutar_sql("SELECT estado, nota FROM conteo_fisico WHERE id = 2") == [
        ("CERRADO", "Revisado")
    ]
    # Recién cerrado, ya no se modifica ni recibe renglones
    with pytest.raises(DatabaseError, match="El conteo 2 está cerrado y no se puede modificar"):
        ejecutar_sql("UPDATE conteo_fisico SET nota = 'x' WHERE id = 2")
    with pytest.raises(DatabaseError, match="El conteo 2 está cerrado"):
        ejecutar_sql(*insertar_renglon(2, 2, "18", "20"))


RENGLONES = "SELECT conteo_id, medicamento_id, cantidad_fisica FROM detalle_conteo ORDER BY 1, 2"

CERRADO_INMUTABLE = [
    pytest.param(
        "DELETE FROM conteo_fisico WHERE id = 1",
        "El conteo 1 está cerrado y no se puede modificar",
        id="borrar-encabezado-cerrado",
    ),
    # El renglón de Metformina (1) del conteo 1 de María
    pytest.param(
        "UPDATE detalle_conteo SET cantidad_fisica = 5 WHERE conteo_id = 1 AND medicamento_id = 1",
        "El conteo 1 está cerrado",
        id="cambiar-renglon-cerrado",
    ),
    pytest.param(
        "DELETE FROM detalle_conteo WHERE conteo_id = 1 AND medicamento_id = 1",
        "El conteo 1 está cerrado",
        id="borrar-renglon-cerrado",
    ),
    # El renglón de Omeprazol (5) del conteo 2 pasaría al conteo 1, que no tiene Omeprazol
    pytest.param(
        "UPDATE detalle_conteo SET conteo_id = 1 WHERE conteo_id = 2 AND medicamento_id = 5",
        "El conteo 1 está cerrado",
        id="meter-renglon-en-conteo-cerrado",
    ),
]


@pytest.mark.parametrize(("sql", "mensaje"), CERRADO_INMUTABLE)
def test_un_conteo_cerrado_no_se_borra_ni_cambian_sus_renglones(datos_demo, sql, mensaje):
    # Scenario: Borrar el encabezado de un conteo cerrado, Cambiar o borrar un renglón de un
    # conteo cerrado y Meter un renglón en un conteo cerrado (revisión de TK-01, hallazgo 2).
    # Regresión: TK-01 ya los rechaza (design, decisión 5)
    antes = ejecutar_sql(RENGLONES)
    # Control: el mock tiene el renglón de Metformina en el conteo 1 y el de Omeprazol en el 2
    assert (1, 1, Decimal("2")) in antes
    assert (2, 5, Decimal("58")) in antes
    with pytest.raises(DatabaseError, match=mensaje):
        ejecutar_sql(sql)
    assert ejecutar_sql("SELECT id, estado FROM conteo_fisico ORDER BY id") == [
        (1, "CERRADO"),
        (2, "EN_PROCESO"),
    ]
    assert ejecutar_sql(RENGLONES) == antes


def test_sacar_un_renglon_de_un_conteo_cerrado(datos_demo):
    # Scenario: Sacar un renglón de un conteo cerrado (revisión de TK-01, hallazgo 2). El
    # conteo 2 no tiene Metformina (1), así que el cambio no choca con uq_detalle_conteo
    with pytest.raises(DatabaseError, match="El conteo 1 está cerrado"):
        ejecutar_sql(
            "UPDATE detalle_conteo SET conteo_id = 2 WHERE conteo_id = 1 AND medicamento_id = 1"
        )
    # El renglón sigue en el conteo 1
    assert ejecutar_sql(
        "SELECT conteo_id, cantidad_fisica FROM detalle_conteo WHERE medicamento_id = 1"
    ) == [(1, Decimal("2"))]


def test_los_renglones_de_un_conteo_en_proceso_si_se_mueven_y_se_borran(datos_demo):
    # Control de CERRADO_INMUTABLE y de test_sacar_un_renglon_de_un_conteo_cerrado: entre
    # conteos EN_PROCESO, el mismo UPDATE de conteo_id y el mismo DELETE sí se aplican, así que
    # los rechazos de arriba se deben al cierre del conteo 1
    sql, params = insertar_conteo()
    ((nuevo,),) = ejecutar_sql(sql + " RETURNING id", params)
    ejecutar_sql(
        "UPDATE detalle_conteo SET conteo_id = %s WHERE conteo_id = 2 AND medicamento_id = 5",
        [nuevo],
    )
    ejecutar_sql("DELETE FROM detalle_conteo WHERE conteo_id = 2 AND medicamento_id = 6")
    assert ejecutar_sql(
        "SELECT conteo_id, medicamento_id FROM detalle_conteo WHERE conteo_id IN (2, %s) "
        "ORDER BY 1, 2",
        [nuevo],
    ) == [(2, 10), (nuevo, 5)]


def test_la_diferencia_del_mock(datos_demo):
    # Scenario: Diferencia del mock (TK-01, prueba 3.3): 58 contadas contra 59 registradas
    assert ejecutar_sql(
        "SELECT cantidad_fisica, cantidad_sistema, diferencia FROM detalle_conteo "
        "WHERE conteo_id = 2 AND medicamento_id = 5"
    ) == [(Decimal("58"), Decimal("59"), Decimal("-1.00"))]


def test_capturar_un_renglon_pendiente(datos_demo):
    # Scenario: Capturar un renglón pendiente (TK-01, prueba 3.3; readme, sección 2.6)
    sql, params = insertar_renglon(2, 2, "18", "20")
    assert ejecutar_sql(sql + " RETURNING diferencia", params) == [(Decimal("-2"),)]
    # El conteo no ajusta Existencias: el Hogar sigue con 20 dosis de Losartán
    assert ejecutar_sql(
        f"SELECT saldo FROM existencia WHERE entidad_id = {HOGAR} AND medicamento_id = 2"
    ) == [(Decimal("20"),)]


def test_la_diferencia_se_recalcula_al_corregir_la_captura(datos_demo):
    # Control de columna-generada: la base sí recalcula diferencia cuando cambia la captura
    ejecutar_sql(
        "UPDATE detalle_conteo SET cantidad_fisica = 59 WHERE conteo_id = 2 AND medicamento_id = 5"
    )
    assert ejecutar_sql(
        "SELECT diferencia FROM detalle_conteo WHERE conteo_id = 2 AND medicamento_id = 5"
    ) == [(Decimal("0"),)]


@pytest.mark.parametrize(
    "modelo", [ConteoFisico, DetalleConteo], ids=["conteo-fisico", "detalle-conteo"]
)
def test_el_modelo_no_esta_en_el_admin(modelo):
    # Scenario: Los conteos no están en el panel (TK-01, descripción técnica 8)
    # Control: el panel está cargado y registra el catálogo; la ausencia no es un panel vacío
    assert admin.site.is_registered(Medicamento)
    assert not admin.site.is_registered(modelo)


# ---------------------------------------------------------------------------------------------
# Catálogo de PostgreSQL: nombres, tipos, triggers e índices (design, decisión 9)
# ---------------------------------------------------------------------------------------------


def restricciones(tabla: str) -> set[str]:
    """Las CHECK, UNIQUE y EXCLUDE de la tabla (sin las FK ni la PK)."""
    filas = ejecutar_sql(
        "SELECT conname FROM pg_constraint "
        "WHERE conrelid = %s::regclass AND contype IN ('c', 'u', 'x')",
        [tabla],
    )
    return {fila[0] for fila in filas}


DEFINICION_TRIGGER = re.compile(
    r"^CREATE TRIGGER \S+ (BEFORE|AFTER|INSTEAD OF) (.+?) ON \S+ .*?(FOR EACH (?:ROW|STATEMENT))"
)


def triggers(tabla: str) -> dict[str, tuple[str, frozenset[str], str]]:
    """Los triggers propios de la tabla, con (momento, eventos, nivel).

    pg_get_triggerdef escribe los eventos en su propio orden ("INSERT OR DELETE OR UPDATE"),
    así que se comparan como conjunto.
    """
    filas = ejecutar_sql(
        "SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger "
        "WHERE tgrelid = %s::regclass AND NOT tgisinternal",
        [tabla],
    )
    resultado = {}
    for nombre, definicion in filas:
        partes = DEFINICION_TRIGGER.match(definicion)
        assert partes, definicion
        eventos = frozenset(partes.group(2).split(" OR "))
        resultado[nombre] = (partes.group(1), eventos, partes.group(3))
    return resultado


PARTES_INDICE = re.compile(r" USING (\w+) \((.+?)\)(?: INCLUDE \((.+?)\))?(?: WHERE (.+))?$")


def partes_del_indice(tabla: str, nombre: str) -> tuple[str, str, str | None, str | None]:
    """(método, columnas, INCLUDE, predicado sin paréntesis) del índice."""
    filas = ejecutar_sql(
        "SELECT indexdef FROM pg_indexes "
        "WHERE schemaname = 'public' AND tablename = %s AND indexname = %s",
        [tabla, nombre],
    )
    assert filas, f"no existe el índice {nombre} en {tabla}"
    partes = PARTES_INDICE.search(filas[0][0])
    assert partes, filas[0][0]
    metodo, columnas, incluye, predicado = partes.groups()
    if predicado is not None:
        predicado = re.sub(r"[()]", "", predicado).strip()
    return metodo, columnas, incluye, predicado


def indices_por_primera_columna(tabla: str, columna: str) -> set[str]:
    filas = ejecutar_sql(
        """SELECT i.relname
           FROM pg_index x
           JOIN pg_class i ON i.oid = x.indexrelid
           JOIN pg_attribute a ON a.attrelid = x.indrelid AND a.attnum = x.indkey[0]
           WHERE x.indrelid = %s::regclass AND a.attname = %s""",
        [tabla, columna],
    )
    return {fila[0] for fila in filas}


def columna(tabla: str, nombre: str) -> tuple[str, str | None, str]:
    """(tipo, expresión del DEFAULT o de la generación, attgenerated) de una columna."""
    filas = ejecutar_sql(
        """SELECT format_type(a.atttypid, a.atttypmod), pg_get_expr(d.adbin, d.adrelid),
                  a.attgenerated::text
           FROM pg_attribute a
           LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
           WHERE a.attrelid = %s::regclass AND a.attname = %s AND NOT a.attisdropped""",
        [tabla, nombre],
    )
    assert len(filas) == 1, f"{tabla}.{nombre} no existe"
    return filas[0]


@pytest.mark.parametrize(
    ("tabla", "esperadas"),
    [
        ("conteo_fisico", {"ck_conteo_periodo", "ck_conteo_estado", "ck_conteo_cierre"}),
        ("detalle_conteo", {"uq_detalle_conteo", "ck_detalle_fisica", "ck_detalle_sistema"}),
    ],
    ids=["conteo-fisico", "detalle-conteo"],
)
def test_las_restricciones_tienen_sus_nombres_exactos(tabla, esperadas):
    # Scenario: Restricciones, índices y triggers con sus nombres exactos (TK-01, criterio 5)
    assert restricciones(tabla) == esperadas


@pytest.mark.parametrize(
    ("tabla", "nombre", "eventos"),
    [
        ("conteo_fisico", "tg_conteo_cerrado", {"UPDATE", "DELETE"}),
        ("detalle_conteo", "tg_detalle_conteo_cerrado", {"INSERT", "UPDATE", "DELETE"}),
    ],
    ids=["conteo-fisico", "detalle-conteo"],
)
def test_los_triggers_de_los_conteos(tabla, nombre, eventos):
    # Scenario: Restricciones, índices y triggers con sus nombres exactos (TK-01, criterio 5)
    assert triggers(tabla) == {nombre: ("BEFORE", frozenset(eventos), "FOR EACH ROW")}


def test_los_indices_de_los_conteos():
    # Scenario: Restricciones, índices y triggers con sus nombres exactos (TK-01, criterio 5)
    assert partes_del_indice("detalle_conteo", "ix_detalle_medicamento_conteo") == (
        "btree",
        "medicamento_id, conteo_id",
        "cantidad_fisica, cantidad_sistema, diferencia",
        None,
    )
    assert partes_del_indice("conteo_fisico", "ix_conteo_entidad_periodo") == (
        "btree",
        "entidad_id, periodo_fin DESC",
        None,
        None,
    )
    assert partes_del_indice("detalle_conteo", "uq_detalle_conteo")[:2] == (
        "btree",
        "conteo_id, medicamento_id",
    )
    # Parcial, diferencia <> 0: Django puede escribirlo como NOT (diferencia = 0), y
    # PostgreSQL agrega el ::numeric del 0
    metodo, columnas, incluye, predicado = partes_del_indice(
        "detalle_conteo", "ix_detalle_con_diferencia"
    )
    assert (metodo, columnas, incluye) == ("btree", "medicamento_id", None)
    assert predicado is not None, "ix_detalle_con_diferencia no es parcial"
    normalizado = predicado.replace("::numeric", "").replace("'", "")
    assert re.fullmatch(r"(diferencia <> |NOT diferencia = )0(\.0+)?", normalizado), predicado


def test_las_cantidades_del_conteo_y_la_diferencia_generada():
    # Scenario: Restricciones, índices y triggers con sus nombres exactos (TK-01, criterio 5):
    # diferencia es numeric(10,2) generada y guardada (attgenerated = 's')
    for nombre in ("cantidad_fisica", "cantidad_sistema"):
        assert columna("detalle_conteo", nombre)[0] == "numeric(10,2)", nombre
        assert columna("detalle_conteo", nombre)[2] == "", nombre
    tipo, expresion, generada = columna("detalle_conteo", "diferencia")
    assert (tipo, generada) == ("numeric(10,2)", "s")
    assert re.sub(r"[()]", "", expresion) == "cantidad_fisica - cantidad_sistema", expresion


@pytest.mark.parametrize(
    ("tabla", "columna_fk", "esperados"),
    [
        ("detalle_conteo", "conteo_id", {"uq_detalle_conteo"}),
        (
            "detalle_conteo",
            "medicamento_id",
            {"ix_detalle_medicamento_conteo", "ix_detalle_con_diferencia"},
        ),
        ("conteo_fisico", "entidad_id", {"ix_conteo_entidad_periodo"}),
    ],
    ids=["detalle-conteo", "detalle-medicamento", "conteo-entidad"],
)
def test_sin_indices_duplicados_sobre_las_fk(tabla, columna_fk, esperados):
    # Scenario: Sin índices duplicados sobre las FK (TK-01, criterio 6)
    assert indices_por_primera_columna(tabla, columna_fk) == esperados
