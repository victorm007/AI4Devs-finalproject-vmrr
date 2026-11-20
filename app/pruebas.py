"""Utilidades compartidas por los tests."""

from django.db import connection, transaction


def ejecutar_sql(sql: str, params=None, *, rol: str | None = None) -> list[tuple]:
    """Ejecuta SQL dentro de un savepoint, opcionalmente como otro rol.

    Si la sentencia falla, solo se revierte el savepoint y el test puede seguir.
    Ejemplo: ejecutar_sql("SELECT current_user", rol="app_user") -> [("app_user",)]
    """
    with transaction.atomic(), connection.cursor() as cursor:
        if rol:
            cursor.execute(f"SET LOCAL ROLE {rol}")
        cursor.execute(sql, params)
        filas = cursor.fetchall() if cursor.description else []
        if rol:
            cursor.execute("RESET ROLE")
        return filas
