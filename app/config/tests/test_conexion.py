"""La aplicación usa PostgreSQL 17 con los 2 usuarios de HB-01 (readme, sección 2.5).

Va en config/tests/ y no en apps/accounts/tests/: prueba la configuración de la conexión
y los roles de BD, no el comportamiento de accounts. Se corre sola con -m infra.
"""

import pytest
from django.db import connection

from pruebas import ejecutar_sql

pytestmark = [pytest.mark.django_db, pytest.mark.infra]


def test_la_base_es_postgresql_17():
    # Scenario: La base es PostgreSQL 17
    assert connection.vendor == "postgresql"
    assert connection.pg_version >= 170000


def test_los_tests_corren_como_app_owner():
    # Scenario: Los tests corren como app_owner
    # pytest crea la base de tests, así que se conecta con el dueño (atajo dtest y CI)
    assert ejecutar_sql("SELECT current_user") == [("app_owner",)]


def test_set_role_cambia_a_app_user():
    # Scenario: Los tests pueden actuar como app_user
    assert ejecutar_sql("SELECT current_user", rol="app_user") == [("app_user",)]
    # Control: sin rol, la sesión vuelve a ser app_owner. Si la conexión ya fuera
    # app_user, la aserción anterior pasaría sin que SET LOCAL ROLE cambiara nada.
    assert ejecutar_sql("SELECT current_user") == [("app_owner",)]


def test_app_user_no_tiene_atributos_especiales():
    # Scenario: app_user sin atributos especiales
    # Exigir exactamente 1 fila también comprueba que el rol existe
    assert ejecutar_sql(
        "SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = 'app_user'"
    ) == [(False, False, False)]
