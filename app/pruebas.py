"""Utilidades compartidas por los tests."""

from django.db import connection, transaction


def ejecutar_sql(sql: str, params=None, *, rol: str | None = None) -> list[tuple]:
    """Ejecuta SQL dentro de un savepoint, opcionalmente como otro rol.

    Si la sentencia falla, solo se revierte el savepoint (también su SET LOCAL ROLE) y el
    test puede seguir. Con rol=, al terminar vuelve al rol que había antes, y no hace
    RESET ROLE: eso dejaba el usuario de la sesión (app_owner) y deshacía en silencio el
    SET LOCAL ROLE de como_app_user para el resto del test.
    Ejemplo: ejecutar_sql("SELECT current_user", rol="app_user") -> [("app_user",)]
    """
    with transaction.atomic(), connection.cursor() as cursor:
        if rol:
            cursor.execute("SELECT current_user")
            (previo,) = cursor.fetchone()
            cursor.execute(f"SET LOCAL ROLE {connection.ops.quote_name(rol)}")
        cursor.execute(sql, params)
        filas = cursor.fetchall() if cursor.description else []
        if rol:
            cursor.execute(f"SET LOCAL ROLE {connection.ops.quote_name(previo)}")
        return filas


def saldo(entidad, medicamento):
    """Saldo actual de una entidad y un medicamento (lo usan los tests de TK-02 y TK-03)."""
    from apps.inventario.models import Existencia

    return Existencia.objects.get(entidad=entidad, medicamento=medicamento).saldo
