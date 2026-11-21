"""app_user tiene privilegios mínimos (readme, sección 2.5). TK-01 agrega los de movimiento.

ejecutar_sql sin params no interpola: el % de format('public.%I', ...) llega literal
a PostgreSQL, así que va con un solo %.
"""

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
