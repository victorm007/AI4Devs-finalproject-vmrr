"""app_user tiene privilegios mínimos (readme, sección 2.5). TK-01 agrega los de movimiento.

ejecutar_sql sin params no interpola: el % de format('public.%I', ...) llega literal
a PostgreSQL, así que va con un solo %.

TK-01: app_user solo lee e inserta en movimiento (sin UPDATE, DELETE ni TRUNCATE), no puede
desactivar sus triggers, registra una entrada y lee v_conciliacion_existencia. Los que
modifican el historial corren con el mock (datos_demo), para que haya filas que tocar. Rojo
esperado: la tabla movimiento no existe (has_table_privilege falla con "relation does not
exist", y datos_demo con el error de cargar_mock.sql); los mensajes de permisos solo aparecen
cuando la tabla existe con el REVOKE de inventario/0004.
"""

from decimal import Decimal

import pytest
from django.db import DatabaseError

from pruebas import ejecutar_sql

pytestmark = pytest.mark.django_db

PERMISOS = ("SELECT", "INSERT", "UPDATE", "DELETE")


def _tablas_public() -> list[str]:
    return [
        fila[0]
        for fila in ejecutar_sql("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    ]


def test_app_owner_es_dueno_de_todas_las_tablas():
    # Scenario: Dueño de todas las tablas (regresión de HB-01)
    # Control: la base está migrada; sin tablas, la lista vacía de abajo no probaría nada
    assert "usuario" in _tablas_public()
    ajenas = ejecutar_sql(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner <> 'app_owner'"
    )
    assert ajenas == []


def test_app_user_tiene_los_4_permisos_en_las_tablas():
    # Scenario: Los 4 permisos de app_user
    # movimiento llega en TK-01 con permisos reducidos (sin UPDATE ni DELETE)
    filas = ejecutar_sql("""
        SELECT tablename,
               has_table_privilege('app_user', format('public.%I', tablename), 'SELECT')
               AND has_table_privilege('app_user', format('public.%I', tablename), 'INSERT')
               AND has_table_privilege('app_user', format('public.%I', tablename), 'UPDATE')
               AND has_table_privilege('app_user', format('public.%I', tablename), 'DELETE')
        FROM pg_tables
        WHERE schemaname = 'public' AND tablename <> 'movimiento'""")
    revisadas = dict(filas)
    # Control: se revisaron las tablas de accounts, no una lista vacía
    assert "usuario" in revisadas
    assert "usuario_groups" in revisadas
    sin_permiso = [tabla for tabla, completos in filas if not completos]
    assert sin_permiso == []


def test_las_tablas_nuevas_heredan_los_permisos():
    # Scenario: Las tablas nuevas heredan los permisos
    # Como app_owner, igual que una migración futura
    ejecutar_sql("CREATE TABLE prueba_permisos (id int)")
    for permiso in PERMISOS:
        assert ejecutar_sql(
            "SELECT has_table_privilege('app_user', 'public.prueba_permisos', %s)", [permiso]
        ) == [(True,)], permiso
    # Y app_user puede usarlos de verdad sobre la tabla nueva
    ejecutar_sql("INSERT INTO prueba_permisos (id) VALUES (1)", rol="app_user")
    assert ejecutar_sql("SELECT id FROM prueba_permisos", rol="app_user") == [(1,)]


def test_app_user_no_puede_crear_tablas():
    # Scenario: app_user no crea tablas (regresión de HB-01)
    with pytest.raises(DatabaseError, match="permission denied for schema public"):
        ejecutar_sql("CREATE TABLE intrusa (id int)", rol="app_user")


def test_app_user_solo_lee_e_inserta_movimientos():
    # Scenario: app_user solo lee e inserta Movimientos (TK-01, criterio 9)
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


@pytest.mark.parametrize(
    ("sql", "mensaje"),
    [
        ("UPDATE movimiento SET nota = 'x'", "permission denied for table movimiento"),
        ("DELETE FROM movimiento", "permission denied for table movimiento"),
        ("TRUNCATE movimiento", "permission denied for table movimiento"),
        ("ALTER TABLE movimiento DISABLE TRIGGER ALL", "must be owner of table movimiento"),
    ],
    ids=["update", "delete", "truncate", "desactivar-triggers"],
)
def test_app_user_no_puede_modificar_el_historial(datos_demo, sql, mensaje):
    # Scenario: app_user no reescribe el historial y app_user no desactiva los triggers
    # (TK-01, criterio 8)
    with pytest.raises(DatabaseError, match=mensaje):
        ejecutar_sql(sql, rol="app_user")
    # Los 28 movimientos del mock siguen ahí, y app_user los lee
    assert ejecutar_sql("SELECT count(*) FROM movimiento", rol="app_user") == [(28,)]


def test_app_user_lee_la_conciliacion(datos_demo):
    # Scenario: app_user registra un Movimiento y lee la conciliación (TK-01, descripción
    # técnica 5): la consulta responde sin error de permisos, y el mock cuadra
    assert ejecutar_sql("SELECT count(*) FROM v_conciliacion_existencia", rol="app_user") == [(0,)]


def test_app_user_si_puede_registrar_un_movimiento(datos_demo):
    # Scenario: app_user registra un Movimiento y lee la conciliación (TK-01, descripción
    # técnica 5): una entrada de 30 Eutirox (8) para Carmen (103), entregada por Rosa Torres
    ejecutar_sql(
        "INSERT INTO movimiento (tipo, medicamento_id, cantidad, entidad_destino_id, "
        "origen_entrada, entregado_por, usuario_id) "
        "SELECT 'ENTRADA', 8, 30, 103, 'FAMILIAR', 'Rosa Torres', id "
        "FROM usuario WHERE username = 'operador.demo'",
        rol="app_user",
    )
    # La inserción se guardó (también lo lee app_user)
    filas = ejecutar_sql(
        "SELECT cantidad FROM movimiento "
        "WHERE medicamento_id = 8 AND entidad_destino_id = 103 AND entregado_por = 'Rosa Torres'",
        rol="app_user",
    )
    assert filas == [(Decimal("30"),)]
    # Sin el servicio de TK-02 nadie actualizó la Existencia de Carmen (33), y la conciliación,
    # que app_user también lee, lo detecta: 33 registradas contra 63 de los movimientos
    assert ejecutar_sql("SELECT count(*) FROM v_conciliacion_existencia", rol="app_user") == [(1,)]
