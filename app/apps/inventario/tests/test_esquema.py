"""Esquema de Existencias y Movimientos: la base rechaza lo que las reglas prohíben (TK-01).

Capa de servicio y base de datos, contra PostgreSQL real y como app_owner (el dueño de las
tablas): así se comprueba que los triggers rechazan incluso al dueño. Los privilegios de
app_user sobre movimiento están en apps/accounts/tests/test_privilegios.py, y los conteos
físicos en apps/conteos/tests/test_esquema.py.

Además de los casos inválidos de la guía (sección 3.1), los nombres de las restricciones, los
triggers, los índices, los tipos y el fillfactor se leen del catálogo de PostgreSQL (design,
decisión 9). Los índices se comparan por su primera columna (pg_index.indkey[0]), porque Django
pone un hash en el nombre de los que crea él. Los eventos de un trigger se comparan como
conjunto: pg_get_triggerdef los escribe en su propio orden ("DELETE OR UPDATE").

Casos agregados a la guía (no estaban en su tabla, sí en el DDL de las secciones 3.1 y 3.3):
entregado_por con solo espacios, origen_entrada desconocido, un movimiento que se corrige a sí
mismo, una Existencia duplicada, una entrada de un Medicamento dado de baja y la corrección
que sí entra a un Residente egresado. También van aquí las migraciones (revertir hasta zero y
volver a aplicar, design, decisión 10; makemigrations --check) y los fixtures compartidos
(datos_demo, demo, como_app_user y saldo).

Rojo comprobado: apps.inventario.models no existe, así que falla la importación del módulo
(ModuleNotFoundError) y ninguno de estos tests llega a correr. Después de crear los modelos,
cada test falla hasta que existe la restricción, el trigger o el índice que comprueba.

Ajustes de la revisión de TK-01 (PR #3): Transferencia a un Residente egresado y Entrada a uno
fallecido (hallazgo 9), las claves foráneas que impiden borrar un Medicamento con historial, con
el ORM y saltándose Django (hallazgo 3, ADR-0027), ejecutar_sql con rol= dentro de
como_app_user (hallazgo 11; design, decisión 3) y el try/finally que deja la base migrada si
falla una aserción de test_revertir_y_volver_a_aplicar_las_migraciones. Rojo comprobado: solo
test_ejecutar_sql_con_otro_rol_no_deshace_como_app_user (hoy ejecutar_sql termina con RESET
ROLE y current_user queda en app_owner). Los demás son de regresión (design, decisión 5): TK-01
ya rechaza esos destinos con tg_movimiento_validar_destino, y las FK de Django ya son PROTECT
en el ORM y NO ACTION DEFERRABLE en la base.

Ajustes de la segunda revisión de TK-01 (PR #3):
- test_las_fk_de_motivo_y_usuario_de_movimiento_sin_indice (bloqueante 1, ADR-0018). Rojo
  esperado: Django crea movimiento_motivo_baja_id_<hash> y movimiento_usuario_id_<hash>, así
  que el conjunto no está vacío.
- test_django_impide_borrar_lo_que_tiene_historial y
  test_la_base_rechaza_borrar_lo_que_tiene_historial (mayor 2; design, decisión 3), para
  Eutirox, el Hogar, operador.demo y CONSUMO. En la base, el test quita antes las referencias
  que no son historial (principios activos, Pautas y grupo del usuario) y exige que el mensaje
  nombre una tabla del historial. Regresión: las FK ya son PROTECT y NO ACTION DEFERRABLE; el
  cambio es que ahora prueban la causa.
- test_revertir_y_volver_a_aplicar_las_migraciones (menor 1; design, decisión 7): el try
  protege también migrate conteos zero, y el cuerpo de fn_detalle_conteo_cerrado se compara en
  0002_triggers y al volver a migrar. Rojo esperado: la última aserción, FOR SHARE, porque
  conteos/0005_detalle_conteo_bloqueo no existe todavía.
- test_ejecutar_sql_con_otro_rol_vuelve_al_usuario_de_la_sesion (nit 3): compara con
  session_user en lugar de suponer que no es app_user. Regresión.
"""

import re
from decimal import Decimal

import pytest
from django.contrib import admin
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import DatabaseError, connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.models import ProtectedError

from apps.catalogo.models import Medicamento
from apps.inventario.models import Existencia, Movimiento
from pruebas import ejecutar_sql, saldo

pytestmark = pytest.mark.django_db

USUARIO = "(SELECT id FROM usuario WHERE username = 'operador.demo')"
CORRECCION = "(SELECT id FROM motivo_baja WHERE clave = 'CORRECCION')"
HOGAR = "(SELECT id FROM entidad WHERE tipo = 'HOGAR')"
INMUTABLES = "Los movimientos son inmutables: registre un movimiento de corrección"


def insertar_movimiento(**campos) -> tuple[str, list]:
    """INSERT válido (entrada de 10 Metformina a María) con los campos que cambie el test."""
    valores = {
        "tipo": "ENTRADA",
        "medicamento_id": 1,
        "cantidad": Decimal("10"),
        "entidad_origen_id": None,
        "entidad_destino_id": 101,
        "motivo_baja_id": None,
        "origen_entrada": "FAMILIAR",
        "entregado_por": "Rosa Torres",
    } | campos
    columnas = ", ".join(valores)
    marcadores = ", ".join(["%s"] * len(valores))
    sql = f"INSERT INTO movimiento ({columnas}, usuario_id) SELECT {marcadores}, {USUARIO}"
    return sql, list(valores.values())


SIN_ENTRADA = {"origen_entrada": None, "entregado_por": None}

CASOS = [
    pytest.param(
        "UPDATE movimiento SET cantidad = 1 WHERE id = 1", None, INMUTABLES, id="update-movimiento"
    ),
    pytest.param("DELETE FROM movimiento WHERE id = 1", None, INMUTABLES, id="delete-movimiento"),
    pytest.param(
        *insertar_movimiento(entidad_destino_id=None),
        "ck_movimiento_por_tipo",
        id="entrada-sin-destino",
    ),
    pytest.param(
        *insertar_movimiento(
            tipo="BAJA", entidad_origen_id=101, entidad_destino_id=None, **SIN_ENTRADA
        ),
        "ck_movimiento_por_tipo",
        id="baja-sin-motivo",
    ),
    pytest.param(
        *insertar_movimiento(
            tipo="TRANSFERENCIA", entidad_origen_id=1, entidad_destino_id=1, **SIN_ENTRADA
        ),
        "ck_movimiento_por_tipo",
        id="transferencia-misma-entidad",
    ),
    pytest.param(
        *insertar_movimiento(cantidad=Decimal("0")), "ck_movimiento_cantidad", id="cantidad-cero"
    ),
    # La corrección del mock: el movimiento 23 (baja CORRECCION) corrige la entrada errónea 22
    pytest.param(
        f"""INSERT INTO movimiento (tipo, medicamento_id, cantidad, entidad_origen_id,
                                    motivo_baja_id, corrige_a_id, usuario_id)
            SELECT 'BAJA', medicamento_id, 1, 101, {CORRECCION}, corrige_a_id, {USUARIO}
            FROM movimiento WHERE corrige_a_id IS NOT NULL LIMIT 1""",
        None,
        "uq_movimiento_corrige",
        id="segunda-correccion",
    ),
    pytest.param(
        "UPDATE existencia SET saldo = -1 WHERE id = (SELECT min(id) FROM existencia)",
        None,
        "ck_existencia_saldo",
        id="saldo-negativo",
    ),
    # Agregados a la guía (DDL de las secciones 3.1 y 3.3)
    pytest.param(
        *insertar_movimiento(entregado_por="   "),
        "ck_movimiento_entregado",
        id="entregado-solo-espacios",
    ),
    pytest.param(
        *insertar_movimiento(origen_entrada="VECINO"),
        "ck_movimiento_origen_entrada",
        id="origen-entrada-desconocido",
    ),
    pytest.param(
        *insertar_movimiento(id=1000, corrige_a_id=1000),
        "ck_movimiento_no_autocorrige",
        id="se-corrige-a-si-mismo",
    ),
    pytest.param(
        "INSERT INTO existencia (entidad_id, medicamento_id, saldo) "
        "SELECT entidad_id, medicamento_id, 0 FROM existencia "
        "WHERE id = (SELECT min(id) FROM existencia)",
        None,
        "uq_existencia",
        id="existencia-duplicada",
    ),
]


@pytest.mark.parametrize(("sql", "params", "mensaje"), CASOS)
def test_la_base_rechaza(datos_demo, sql, params, mensaje):
    # Scenario: Modificar un Movimiento, Borrar un Movimiento, Entrada sin destino, Baja sin
    # motivo, Transferencia a la misma Entidad, Cantidad cero, Segunda corrección del mismo
    # Movimiento y Saldo negativo (TK-01, criterio 8)
    with pytest.raises(DatabaseError, match=mensaje):
        ejecutar_sql(sql, params)
    # El rechazo no tocó el historial ni los saldos del mock
    assert ejecutar_sql("SELECT count(*) FROM movimiento") == [(28,)]
    assert ejecutar_sql("SELECT count(*) FROM v_conciliacion_existencia") == [(0,)]


def test_el_movimiento_valido_de_los_casos_si_se_guarda(datos_demo):
    # Control de test_la_base_rechaza: el INSERT base de insertar_movimiento es válido, así que
    # cada rechazo de arriba se debe solo al campo que cambia el caso
    ejecutar_sql(*insertar_movimiento())
    assert ejecutar_sql("SELECT count(*) FROM movimiento") == [(29,)]


def test_no_entra_medicamento_a_residente_egresado(datos_demo):
    # Scenario: Entrada a un Residente egresado (TK-01, criterio 8)
    # Control: mientras Carmen está activa, la misma entrada sí se guarda
    ejecutar_sql(*insertar_movimiento(entidad_destino_id=103))
    ejecutar_sql(
        "UPDATE residente SET estado = 'EGRESADO', fecha_baja = '2026-10-16' WHERE entidad_id = 103"
    )
    with pytest.raises(DatabaseError, match="La entidad destino 103 no está activa"):
        ejecutar_sql(*insertar_movimiento(entidad_destino_id=103))
    assert ejecutar_sql(
        "SELECT count(*) FROM movimiento WHERE entidad_destino_id = 103 AND id > 28"
    ) == [(1,)]


@pytest.mark.parametrize(
    ("residente", "estado", "movimiento"),
    [
        # Paracetamol (6) del Hogar (1) a Carmen
        (
            103,
            "EGRESADO",
            insertar_movimiento(
                tipo="TRANSFERENCIA",
                medicamento_id=6,
                cantidad=Decimal("1"),
                entidad_origen_id=1,
                entidad_destino_id=103,
                **SIN_ENTRADA,
            ),
        ),
        # Cozaar (3) para José Luis
        (102, "FALLECIDO", insertar_movimiento(medicamento_id=3, entidad_destino_id=102)),
    ],
    ids=["transferencia-a-egresado", "entrada-a-fallecido"],
)
def test_no_entra_medicamento_a_residente_inactivo(datos_demo, residente, estado, movimiento):
    # Scenario: Transferencia a un Residente egresado y Entrada a un Residente fallecido
    # (revisión de TK-01, hallazgo 9). Regresión: TK-01 ya los rechaza (design, decisión 5)
    # Control: mientras el Residente está activo, el mismo Movimiento sí se guarda
    ejecutar_sql(*movimiento)
    ejecutar_sql(
        "UPDATE residente SET estado = %s, fecha_baja = '2026-10-16' WHERE entidad_id = %s",
        [estado, residente],
    )
    assert ejecutar_sql("SELECT estado FROM residente WHERE entidad_id = %s", [residente]) == [
        (estado,)
    ]
    with pytest.raises(DatabaseError, match=f"La entidad destino {residente} no está activa"):
        ejecutar_sql(*movimiento)
    assert ejecutar_sql(
        "SELECT count(*) FROM movimiento WHERE entidad_destino_id = %s AND id > 28", [residente]
    ) == [(1,)]


@pytest.mark.parametrize(
    ("dueno", "modelos_del_historial"),
    [
        # Eutirox (8): las entradas 9 y 27 y la baja 19 de Carmen, y su Existencia de 33 dosis
        pytest.param(lambda demo: demo.med["Eutirox"], {Movimiento, Existencia}, id="medicamento"),
        pytest.param(lambda demo: demo.hogar, {Movimiento}, id="entidad"),
        # operador.demo registró los 28 movimientos del mock
        pytest.param(lambda demo: demo.operador, {Movimiento}, id="usuario"),
        # Las bajas 15 a 21 son por CONSUMO
        pytest.param(lambda demo: demo.motivo["CONSUMO"], {Movimiento}, id="motivo-de-baja"),
    ],
)
def test_django_impide_borrar_lo_que_tiene_historial(demo, dueno, modelos_del_historial):
    # Scenario: Django impide borrar un Medicamento con historial (revisión de TK-01,
    # hallazgo 3) y Django impide borrar la Entidad, el usuario o el motivo de baja con
    # historial (segunda revisión de TK-01, mayor 2; ADR-0027). Regresión: las FK ya son
    # PROTECT (design, decisión 5); ahora el test exige que la causa sea el historial
    registro = dueno(demo)
    with pytest.raises(ProtectedError) as excinfo:
        registro.delete()
    # Los objetos protegidos son del historial, no solo los principios activos o las Pautas
    protegidos = {type(objeto) for objeto in excinfo.value.protected_objects}
    assert modelos_del_historial <= protegidos, protegidos
    assert type(registro).objects.filter(pk=registro.pk).exists()


EUTIROX = "(SELECT id FROM medicamento WHERE nombre_comercial = 'Eutirox')"
TABLA_DEL_HISTORIAL = (
    r'violates foreign key constraint "\w+" on table '
    r'"(movimiento|existencia|conteo_fisico|detalle_conteo)"'
)

# (tabla, filtro de la fila, referencias que no son historial con las filas que borra cada una)
BORRADOS_CON_HISTORIAL = [
    # Eutirox tiene 1 principio activo (Levotiroxina) y ninguna Pauta en el mock
    pytest.param(
        "medicamento",
        "nombre_comercial = 'Eutirox'",
        [
            (f"DELETE FROM medicamento_principio_activo WHERE medicamento_id = {EUTIROX}", 1),
            (f"DELETE FROM pauta WHERE medicamento_id = {EUTIROX}", 0),
        ],
        id="medicamento",
    ),
    # El Hogar no es Residente: no tiene Pautas ni fila en residente
    pytest.param("entidad", "tipo = 'HOGAR'", [], id="entidad"),
    # operador.demo está en el grupo "Lectura y escritura" y registró las 3 Pautas del mock
    pytest.param(
        "usuario",
        "username = 'operador.demo'",
        [
            (f"DELETE FROM usuario_groups WHERE usuario_id = {USUARIO}", 1),
            (f"DELETE FROM pauta WHERE registrado_por_id = {USUARIO}", 3),
        ],
        id="usuario",
    ),
    # Solo movimiento apunta a motivo_baja
    pytest.param("motivo_baja", "clave = 'CONSUMO'", [], id="motivo-de-baja"),
]


@pytest.mark.parametrize(("tabla", "filtro", "referencias_ajenas"), BORRADOS_CON_HISTORIAL)
def test_la_base_rechaza_borrar_lo_que_tiene_historial(
    datos_demo, tabla, filtro, referencias_ajenas
):
    # Scenario: La base rechaza el borrado aunque se salte Django (revisión de TK-01,
    # hallazgo 3; segunda revisión, mayor 2; ADR-0027). Regresión: las FK de Django ya existen
    # (design, decisión 5); ahora el test exige que la causa sea el historial.
    # Sin Residentes: fk_residente_entidad es inmediata y saltaría antes que el historial.
    # Las FK son DEFERRABLE INITIALLY DEFERRED: sin SET CONSTRAINTS ALL IMMEDIATE en el mismo
    # savepoint, el DELETE pasaría y solo fallaría al confirmar, cosa que el test nunca hace.
    # Si el SET CONSTRAINTS sobrevive al savepoint, solo afecta al resto de este test
    with pytest.raises(DatabaseError, match=TABLA_DEL_HISTORIAL):
        with transaction.atomic(), connection.cursor() as cursor:
            # Como app_owner, se quitan las referencias que no son historial: así el rechazo
            # solo puede venir de movimiento, existencia, conteo_fisico o detalle_conteo
            for sql, filas in referencias_ajenas:
                cursor.execute(sql)
                # Control: la referencia ajena estaba en el mock y se quitó de verdad
                assert cursor.rowcount == filas, sql
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cursor.execute(f"DELETE FROM {tabla} WHERE {filtro}")
    # El savepoint se revirtió: el registro sigue en la base
    assert ejecutar_sql(f"SELECT count(*) FROM {tabla} WHERE {filtro}") == [(1,)]


def test_la_correccion_si_entra_a_un_residente_egresado(datos_demo):
    # Requirement: Destino activo en las Entradas y Transferencias, "salvo que sea una
    # corrección". La baja por consumo de Eutirox de Carmen (movimiento 19, 27 dosis) se
    # corrige con la entrada inversa aunque Carmen ya esté egresada
    ejecutar_sql(
        "UPDATE residente SET estado = 'EGRESADO', fecha_baja = '2026-10-16' WHERE entidad_id = 103"
    )
    ejecutar_sql(
        f"""INSERT INTO movimiento (tipo, medicamento_id, cantidad, entidad_destino_id,
                                    corrige_a_id, usuario_id)
            SELECT 'ENTRADA', 8, 27, 103, 19, {USUARIO}"""
    )
    assert ejecutar_sql("SELECT entidad_destino_id FROM movimiento WHERE corrige_a_id = 19") == [
        (103,)
    ]


def test_no_entra_un_medicamento_dado_de_baja(datos_demo):
    # Requirement: Destino activo en las Entradas y Transferencias (Medicamento dado de baja).
    # Tempra (7) tiene saldo 0 en el Hogar, así que sí se puede dar de baja
    entrada_de_tempra = insertar_movimiento(medicamento_id=7, entidad_destino_id=1)
    # Control: activo, la entrada sí se guarda
    ejecutar_sql(*entrada_de_tempra)
    ejecutar_sql("UPDATE medicamento SET activo = false WHERE id = 7")
    with pytest.raises(DatabaseError, match="El medicamento 7 está dado de baja"):
        ejecutar_sql(*entrada_de_tempra)


def test_el_mock_cuadra(datos_demo):
    # Scenario: El mock cuadra (TK-01, criterio 7)
    # Control: el mock se cargó completo (28 movimientos y 13 existencias de la sección 3.4)
    assert ejecutar_sql("SELECT count(*) FROM movimiento") == [(28,)]
    assert ejecutar_sql("SELECT count(*) FROM existencia") == [(13,)]
    assert ejecutar_sql("SELECT count(*) FROM v_conciliacion_existencia") == [(0,)]


def test_la_conciliacion_detecta_un_saldo_que_no_cuadra(datos_demo):
    # Scenario: Un saldo que no cuadra aparece en la conciliación (TK-01, descripción técnica 4)
    ejecutar_sql(
        "UPDATE existencia SET saldo = saldo + 1 WHERE id = (SELECT min(id) FROM existencia)"
    )
    assert ejecutar_sql("SELECT count(*) FROM v_conciliacion_existencia") == [(1,)]
    # Es esa Existencia, con su saldo y la suma de sus movimientos
    filas = ejecutar_sql(
        "SELECT v.saldo - v.suma_movimientos FROM v_conciliacion_existencia v "
        "JOIN existencia e USING (entidad_id, medicamento_id) "
        "WHERE e.id = (SELECT min(id) FROM existencia)"
    )
    assert filas == [(Decimal("1"),)]


@pytest.mark.parametrize("modelo", [Movimiento, Existencia], ids=["movimiento", "existencia"])
def test_el_modelo_no_esta_en_el_admin(modelo):
    # Scenario: Movimiento y Existencia no están en el panel (TK-01, descripción técnica 8)
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


def triggers(tabla: str) -> dict[str, str]:
    """Los triggers propios de la tabla (sin los internos de las FK), con su definición."""
    filas = ejecutar_sql(
        "SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger "
        "WHERE tgrelid = %s::regclass AND NOT tgisinternal",
        [tabla],
    )
    return dict(filas)


DEFINICION_TRIGGER = re.compile(
    r"^CREATE TRIGGER \S+ (BEFORE|AFTER|INSTEAD OF) (.+?) ON \S+ .*?(FOR EACH (?:ROW|STATEMENT))"
)


def momento(definicion: str) -> tuple[str, frozenset[str], str]:
    """(momento, eventos, nivel) de un trigger: ("BEFORE", {"DELETE", "UPDATE"}, "FOR EACH ROW")."""
    partes = DEFINICION_TRIGGER.match(definicion)
    assert partes, definicion
    return partes.group(1), frozenset(partes.group(2).split(" OR ")), partes.group(3)


def indices(tabla: str) -> dict[str, str]:
    filas = ejecutar_sql(
        "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = %s",
        [tabla],
    )
    return dict(filas)


PARTES_INDICE = re.compile(r" USING (\w+) \((.+?)\)(?: INCLUDE \((.+?)\))?(?: WHERE (.+))?$")


def partes_del_indice(definicion: str) -> tuple[str, str, str | None, str | None]:
    """(método, columnas, INCLUDE, predicado sin paréntesis) de un CREATE INDEX."""
    partes = PARTES_INDICE.search(definicion)
    assert partes, definicion
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


def columna(tabla: str, nombre: str) -> tuple[str, str | None]:
    """(tipo, expresión del DEFAULT) de una columna."""
    filas = ejecutar_sql(
        """SELECT format_type(a.atttypid, a.atttypmod), pg_get_expr(d.adbin, d.adrelid)
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
        (
            "movimiento",
            {
                "ck_movimiento_por_tipo",
                "ck_movimiento_cantidad",
                "ck_movimiento_origen_entrada",
                "ck_movimiento_entregado",
                "ck_movimiento_no_autocorrige",
                "uq_movimiento_corrige",
            },
        ),
        ("existencia", {"uq_existencia", "ck_existencia_saldo"}),
    ],
    ids=["movimiento", "existencia"],
)
def test_las_restricciones_tienen_sus_nombres_exactos(tabla, esperadas):
    # Scenario: Restricciones, índices y triggers con sus nombres exactos (TK-01, criterio 5)
    # Exactamente estas: ni un CHECK con nombre generado por Django ni uno de más
    assert restricciones(tabla) == esperadas


@pytest.mark.parametrize(
    ("tabla", "esperados"),
    [
        (
            "movimiento",
            {
                "tg_movimiento_inmutable": ("BEFORE", {"UPDATE", "DELETE"}),
                "tg_movimiento_validar_destino": ("BEFORE", {"INSERT"}),
            },
        ),
    ],
    ids=["movimiento"],
)
def test_los_triggers_de_movimiento(tabla, esperados):
    # Scenario: Restricciones, índices y triggers con sus nombres exactos (TK-01, criterio 5)
    definiciones = triggers(tabla)
    assert set(definiciones) == set(esperados)
    for nombre, (cuando, eventos) in esperados.items():
        assert momento(definiciones[nombre]) == (cuando, frozenset(eventos), "FOR EACH ROW"), (
            definiciones[nombre]
        )


def test_medicamento_tiene_el_trigger_de_baja():
    # Scenario: Restricciones, índices y triggers con sus nombres exactos (TK-01, criterio 5):
    # medicamento tiene tg_medicamento_baja, BEFORE UPDATE OF activo (sección 3.3)
    definiciones = triggers("medicamento")
    assert "tg_medicamento_baja" in definiciones
    assert momento(definiciones["tg_medicamento_baja"]) == (
        "BEFORE",
        frozenset({"UPDATE OF activo"}),
        "FOR EACH ROW",
    )


@pytest.mark.parametrize(
    ("tabla", "nombre", "metodo", "columnas", "predicado"),
    [
        (
            "movimiento",
            "ix_movimiento_origen_med_fecha",
            "btree",
            "entidad_origen_id, medicamento_id, fecha_hora",
            "entidad_origen_id IS NOT NULL",
        ),
        (
            "movimiento",
            "ix_movimiento_dest_med_fecha",
            "btree",
            "entidad_destino_id, medicamento_id, fecha_hora",
            "entidad_destino_id IS NOT NULL",
        ),
        ("movimiento", "ix_movimiento_med_fecha", "btree", "medicamento_id, fecha_hora", None),
        ("movimiento", "brin_movimiento_fecha", "brin", "fecha_hora", None),
        ("existencia", "ix_existencia_med_entidad", "btree", "medicamento_id, entidad_id", None),
        ("existencia", "uq_existencia", "btree", "entidad_id, medicamento_id", None),
    ],
    ids=[
        "ix-movimiento-origen-med-fecha",
        "ix-movimiento-dest-med-fecha",
        "ix-movimiento-med-fecha",
        "brin-movimiento-fecha",
        "ix-existencia-med-entidad",
        "uq-existencia",
    ],
)
def test_los_indices_tienen_su_definicion(tabla, nombre, metodo, columnas, predicado):
    # Scenario: Restricciones, índices y triggers con sus nombres exactos (TK-01, criterio 5)
    definiciones = indices(tabla)
    assert nombre in definiciones, sorted(definiciones)
    assert partes_del_indice(definiciones[nombre]) == (metodo, columnas, None, predicado), (
        definiciones[nombre]
    )


def test_los_tipos_de_las_cantidades_y_de_las_fechas():
    # Scenario: Tipos de las cantidades y de las fechas (TK-01, descripción técnica 1)
    assert columna("existencia", "saldo")[0] == "numeric(10,2)"
    assert columna("movimiento", "cantidad")[0] == "numeric(10,2)"
    for tabla, nombre in (("existencia", "actualizado_en"), ("movimiento", "fecha_hora")):
        tipo, por_omision = columna(tabla, nombre)
        assert tipo == "timestamp with time zone", (tabla, nombre)
        # now() en el DDL; Now() de Django genera statement_timestamp()
        assert por_omision in ("now()", "statement_timestamp()", "CURRENT_TIMESTAMP"), (
            tabla,
            nombre,
            por_omision,
        )
    # El 0 por omisión del saldo, como lo escriba PostgreSQL: 0, 0.0, '0'::numeric...
    por_omision = columna("existencia", "saldo")[1]
    assert por_omision is not None
    assert re.fullmatch(r"\(?'?0(\.0*)?'?\)?(::numeric)?", por_omision), por_omision


def test_los_valores_por_omision_los_pone_la_base(datos_demo):
    # Scenario: Tipos de las cantidades y de las fechas (TK-01, descripción técnica 1), con un
    # INSERT directo que no pasa por Django: el Hogar no tiene Existencia de Metformina (1)
    filas = ejecutar_sql(
        f"INSERT INTO existencia (entidad_id, medicamento_id) VALUES ({HOGAR}, 1) "
        "RETURNING saldo, actualizado_en >= now() AND actualizado_en <= clock_timestamp()"
    )
    assert filas == [(Decimal("0"), True)]
    sql, params = insertar_movimiento()
    filas = ejecutar_sql(
        sql + " RETURNING fecha_hora >= now() AND fecha_hora <= clock_timestamp()", params
    )
    assert filas == [(True,)]


def test_existencia_deja_espacio_en_la_pagina():
    # Scenario: Espacio para actualizar el saldo en la misma página (TK-01, descripción técnica 4)
    filas = ejecutar_sql("SELECT reloptions FROM pg_class WHERE oid = 'existencia'::regclass")
    assert filas, "no existe la tabla existencia"
    assert "fillfactor=90" in (filas[0][0] or [])


@pytest.mark.parametrize(
    ("tabla", "columna_fk", "esperados"),
    [
        ("existencia", "entidad_id", {"uq_existencia"}),
        ("existencia", "medicamento_id", {"ix_existencia_med_entidad"}),
        ("movimiento", "entidad_origen_id", {"ix_movimiento_origen_med_fecha"}),
        ("movimiento", "entidad_destino_id", {"ix_movimiento_dest_med_fecha"}),
        ("movimiento", "medicamento_id", {"ix_movimiento_med_fecha"}),
        ("movimiento", "corrige_a_id", {"uq_movimiento_corrige"}),
    ],
    ids=[
        "existencia-entidad",
        "existencia-medicamento",
        "movimiento-origen",
        "movimiento-destino",
        "movimiento-medicamento",
        "movimiento-corrige-a",
    ],
)
def test_cada_fk_cubierta_solo_por_su_indice_compuesto(tabla, columna_fk, esperados):
    # Scenario: Cada FK cubierta solo por su índice compuesto (TK-01, criterio 6)
    # Un índice de más con nombre de Django (movimiento_medicamento_id_1a2b3c4d) rompe la igualdad
    assert indices_por_primera_columna(tabla, columna_fk) == esperados


def tablas_referidas(tabla: str, columna_fk: str) -> list[str]:
    """Las tablas a las que apunta la FK cuya primera columna es columna_fk."""
    filas = ejecutar_sql(
        """SELECT c.confrelid::regclass::text
           FROM pg_constraint c
           JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
           WHERE c.conrelid = %s::regclass AND c.contype = 'f' AND a.attname = %s""",
        [tabla, columna_fk],
    )
    return [fila[0] for fila in filas]


@pytest.mark.parametrize(
    ("columna_fk", "referida"),
    [("motivo_baja_id", "motivo_baja"), ("usuario_id", "usuario")],
    ids=["motivo-baja", "usuario"],
)
def test_las_fk_de_motivo_y_usuario_de_movimiento_sin_indice(columna_fk, referida):
    # Scenario: Las FK de motivo y usuario de movimiento sin índice (segunda revisión de TK-01,
    # bloqueante 1; ADR-0018)
    # Control: la columna existe y su FK sigue protegiendo el historial (ADR-0027); con un
    # nombre mal escrito, el conjunto vacío de abajo pasaría por casualidad
    assert tablas_referidas("movimiento", columna_fk) == [referida]
    assert indices_por_primera_columna("movimiento", columna_fk) == set()


MOTIVOS = {
    "CONSUMO",
    "CADUCIDAD",
    "MERMA",
    "ROTURA",
    "DEVOLUCION_FAMILIA",
    "DEFUNCION",
    "EGRESO",
    "CORRECCION",
}


def test_los_8_motivos_tras_migrar():
    # Scenario: Los 8 motivos tras migrar (TK-01, descripción técnica 6), sin el mock
    assert dict(ejecutar_sql("SELECT clave, activo FROM motivo_baja")) == dict.fromkeys(
        MOTIVOS, True
    )


VER = {"view_existencia", "view_movimiento", "view_motivobaja"}


@pytest.mark.parametrize(
    ("grupo", "esperados"),
    [("Solo lectura", VER), ("Lectura y escritura", VER | {"add_movimiento"})],
    ids=["solo-lectura", "lectura-y-escritura"],
)
def test_permisos_de_cada_grupo(grupo, esperados):
    # Scenario: Permisos de cada grupo (TK-01, descripción técnica 7)
    # Exactamente estos: sin change_movimiento ni delete_movimiento
    codenames = set(
        Group.objects.get(name=grupo)
        .permissions.filter(content_type__app_label="inventario")
        .values_list("codename", flat=True)
    )
    assert codenames == esperados


# ---------------------------------------------------------------------------------------------
# Migraciones reversibles (design, decisión 10)
# ---------------------------------------------------------------------------------------------

TABLAS_DE_INVENTARIO = ("motivo_baja", "existencia", "movimiento", "v_conciliacion_existencia")
TABLAS_DE_CONTEOS = ("conteo_fisico", "detalle_conteo")
FUNCIONES = (
    "fn_movimiento_inmutable",
    "fn_movimiento_validar_destino",
    "fn_medicamento_baja_sin_existencias",
    "fn_conteo_cerrado",
    "fn_detalle_conteo_cerrado",
)


def existentes(nombres) -> set[str]:
    """Las tablas o vistas de la lista que existen en public."""
    return {
        nombre
        for nombre in nombres
        if ejecutar_sql("SELECT to_regclass(%s) IS NOT NULL", [f"public.{nombre}"]) == [(True,)]
    }


def funciones_existentes() -> set[str]:
    filas = ejecutar_sql(
        "SELECT proname FROM pg_proc "
        "WHERE pronamespace = 'public'::regnamespace AND proname = ANY(%s)",
        [list(FUNCIONES)],
    )
    return {fila[0] for fila in filas}


def hay_trigger_de_baja() -> bool:
    return ejecutar_sql("SELECT count(*) FROM pg_trigger WHERE tgname = 'tg_medicamento_baja'") == [
        (1,)
    ]


def cuerpo_de_fn_detalle_conteo_cerrado() -> str:
    """pg_get_functiondef de la función, en mayúsculas y con los espacios normalizados."""
    ((definicion,),) = ejecutar_sql(
        "SELECT pg_get_functiondef('fn_detalle_conteo_cerrado'::regproc)"
    )
    return " ".join(definicion.split()).upper()


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_revertir_y_volver_a_aplicar_las_migraciones():
    # Scenario: Revertir y volver a aplicar (TK-01, criterio 1), de inventario y de conteos, y
    # La función del conteo cerrado vuelve a su versión anterior (segunda revisión de TK-01,
    # menor 1)
    todas = set(TABLAS_DE_INVENTARIO) | set(TABLAS_DE_CONTEOS)
    # Control: la base migrada tiene todo, y la función ya mira por separado el conteo de OLD y
    # el de NEW (desde 0003), sin la variable v_conteo de 0002
    assert existentes(todas) == todas
    assert funciones_existentes() == set(FUNCIONES)
    assert hay_trigger_de_baja()
    assert "V_CONTEO" not in cuerpo_de_fn_detalle_conteo_cerrado()

    # Si una aserción o una migración falla a medias, el finally deja la base migrada para los
    # tests siguientes (migrate sin argumentos no hace nada si ya está al día)
    try:
        # Con 0002_triggers, la función mira un solo conteo (v_conteo: OLD en DELETE, NEW en lo
        # demás) y no bloquea
        call_command("migrate", "conteos", "0002_triggers", verbosity=0)
        cuerpo = cuerpo_de_fn_detalle_conteo_cerrado()
        assert "V_CONTEO" in cuerpo, cuerpo
        assert "FOR SHARE" not in cuerpo, cuerpo

        call_command("migrate", "conteos", "zero", verbosity=0)
        assert existentes(todas) == set(TABLAS_DE_INVENTARIO)

        call_command("migrate", "inventario", "zero", verbosity=0)
        assert existentes(todas) == set()
        assert funciones_existentes() == set()
        assert not hay_trigger_de_baja()
        # El catálogo no se toca
        assert existentes(["medicamento"]) == {"medicamento"}

        call_command("migrate", verbosity=0)
        assert existentes(todas) == todas
        assert funciones_existentes() == set(FUNCIONES)
        assert hay_trigger_de_baja()
        # La migración vuelve a quitar los permisos de app_user sobre movimiento
        filas = ejecutar_sql(
            "SELECT p, has_table_privilege('app_user', 'movimiento', p) "
            "FROM unnest(ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE']) AS p"
        )
        assert dict(filas) == {
            "SELECT": True,
            "INSERT": True,
            "UPDATE": False,
            "DELETE": False,
            "TRUNCATE": False,
        }
        assert dict(ejecutar_sql("SELECT clave, activo FROM motivo_baja")) == dict.fromkeys(
            MOTIVOS, True
        )
        filas = ejecutar_sql("SELECT reloptions FROM pg_class WHERE oid = 'existencia'::regclass")
        assert "fillfactor=90" in (filas[0][0] or [])
        # Al volver a migrar, la función mira el conteo de OLD y el de NEW con FOR SHARE (0005)
        cuerpo = cuerpo_de_fn_detalle_conteo_cerrado()
        assert "V_CONTEO" not in cuerpo, cuerpo
        assert "OLD.CONTEO_ID" in cuerpo, cuerpo
        assert "NEW.CONTEO_ID" in cuerpo, cuerpo
        assert "FOR SHARE" in cuerpo, cuerpo
    finally:
        call_command("migrate", verbosity=0)


def test_sin_migraciones_pendientes():
    # Scenario: Sin migraciones pendientes (TK-01, criterio 2)
    # Control: inventario y conteos tienen migraciones; sin ellas, el --check no probaría nada
    grafo = MigrationLoader(connection).graph
    assert grafo.leaf_nodes("inventario")
    assert grafo.leaf_nodes("conteos")
    # Con cambios pendientes, makemigrations --check termina con SystemExit
    call_command("makemigrations", check=True, dry_run=True, verbosity=0)


# ---------------------------------------------------------------------------------------------
# Fixtures de prueba con el dataset mock (TK-01, descripción técnica 9)
# ---------------------------------------------------------------------------------------------


def test_el_mock_se_carga_en_el_test(demo):
    # Scenario: El mock se carga en el test (TK-01, descripción técnica 9)
    assert demo.hogar.tipo == "HOGAR"
    assert (demo.maria.pk, demo.jose.pk, demo.carmen.pk) == (101, 102, 103)
    assert demo.operador.username == "operador.demo"
    assert "Eutirox" in demo.med
    assert "CORRECCION" in demo.motivo
    assert saldo(demo.carmen, demo.med["Eutirox"]) == Decimal("33")


def test_como_app_user_corre_como_app_user(como_app_user):
    # Scenario: El test corre como app_user (TK-01, descripción técnica 9)
    assert ejecutar_sql("SELECT current_user") == [("app_user",)]
    # Y con sus permisos: como app_owner, este UPDATE lo rechazaría el trigger, no el permiso
    with pytest.raises(DatabaseError, match="permission denied for table movimiento"):
        ejecutar_sql("UPDATE movimiento SET nota = 'x' WHERE id = 1")


def usuario_actual() -> str:
    """current_user leído con el cursor de Django, sin pasar por ejecutar_sql."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        return cursor.fetchone()[0]


def test_ejecutar_sql_con_otro_rol_no_deshace_como_app_user(como_app_user):
    # Scenario: ejecutar_sql con otro rol no deshace como_app_user (revisión de TK-01,
    # hallazgo 11; design, decisión 3)
    assert usuario_actual() == "app_user"
    # Control: rol= sí cambia el rol durante la sentencia
    assert ejecutar_sql("SELECT current_user", rol="app_user") == [("app_user",)]
    ejecutar_sql("SELECT 1", rol="app_user")
    assert usuario_actual() == "app_user"


def test_ejecutar_sql_con_otro_rol_vuelve_al_usuario_de_la_sesion(db):
    # Control de test_ejecutar_sql_con_otro_rol_no_deshace_como_app_user: sin como_app_user,
    # ejecutar_sql deja el rol con el que empezó, el usuario de la sesión (nit 3 de la segunda
    # revisión de TK-01: se lee session_user en lugar de suponer que no es app_user)
    ((sesion,),) = ejecutar_sql("SELECT session_user")
    assert usuario_actual() == sesion
    assert ejecutar_sql("SELECT current_user", rol="app_user") == [("app_user",)]
    ejecutar_sql("SELECT 1", rol="app_user")
    assert usuario_actual() == sesion


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_sin_transaccion_envolvente_como_app_user_falla(request):
    # Scenario: Sin transacción envolvente, como_app_user falla (TK-01, descripción técnica 9)
    with pytest.raises(pytest.fail.Exception, match="como_app_user necesita la transacción"):
        request.getfixturevalue("como_app_user")


# ---------------------------------------------------------------------------------------------
# Plan de ejecución (consulta 2c de la sección 3.3)
# ---------------------------------------------------------------------------------------------


@pytest.mark.lento
@pytest.mark.parametrize(
    ("columna_entidad", "entidad", "medicamento", "indice"),
    [
        # Salidas del Hogar de Paracetamol en septiembre: la transferencia 12 a Carmen
        ("entidad_origen_id", "HOGAR", 6, "ix_movimiento_origen_med_fecha"),
        # Entradas de Metformina de María en septiembre: la entrada 5
        ("entidad_destino_id", 101, 1, "ix_movimiento_dest_med_fecha"),
    ],
    ids=["salidas-del-hogar", "entradas-de-maria"],
)
def test_los_movimientos_de_un_periodo_usan_indice(
    datos_demo, columna_entidad, entidad, medicamento, indice
):
    # Scenario: Salidas y entradas de un período usan su índice (TK-01, criterio 11)
    # El id del Hogar va como constante, igual que lo recibiría la consulta de la aplicación
    if entidad == "HOGAR":
        entidad = ejecutar_sql(f"SELECT {HOGAR}")[0][0]
    # Control: la consulta sí encuentra el movimiento del mock
    consulta = f"""
        SELECT tipo, cantidad, fecha_hora FROM movimiento
        WHERE {columna_entidad} = {entidad} AND medicamento_id = {medicamento}
          AND fecha_hora >= '2026-09-01' AND fecha_hora < '2026-10-01'"""
    assert len(ejecutar_sql(consulta)) == 1
    # Sin estadísticas, los índices empatan en coste y gana el último creado: con ANALYZE, el
    # test no depende del orden de Meta.indexes
    ejecutar_sql("ANALYZE movimiento")
    # Con pocos datos PostgreSQL prefiere leer la tabla completa; esto comprueba que el índice
    # SÍ sirve. El SET LOCAL dura hasta el fin de la transacción del test (el savepoint de
    # ejecutar_sql se libera, no se revierte)
    ejecutar_sql("SET LOCAL enable_seqscan = off")
    plan = "\n".join(fila[0] for fila in ejecutar_sql("EXPLAIN " + consulta))
    assert indice in plan, plan
