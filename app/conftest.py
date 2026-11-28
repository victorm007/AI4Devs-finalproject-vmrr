"""Fixtures compartidos de pytest (readme, secciones 2.6 y 6).

- datos_demo: carga el dataset mock de la sección 3.4 (app/fixtures/mock/) con cargar_mock.sql.
- demo: accesos cómodos a esos datos (demo.hogar, demo.carmen, demo.med["Eutirox"]...).
- como_app_user: el resto del test corre como app_user, igual que la aplicación.

Son un punto de integración (TK-01): TK-02 y TK-03 los usan tal cual. Este archivo existe
desde HB-03: su presencia activa el job "tests" del CI (.github/workflows/ci.yml).
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.db import connection

RUTA_MOCK = Path(settings.BASE_DIR) / "fixtures" / "mock"


def _sql_del_mock() -> str:
    """Adapta cargar_mock.sql (escrito para psql) para ejecutarlo desde Django.

    - Quita los metacomandos de psql (líneas que empiezan con "\\").
    - Quita BEGIN/COMMIT: cada test ya corre dentro de una transacción.
    - Escapa los "%" y convierte :'mock_json' en un parámetro.
    """
    lineas = (RUTA_MOCK / "cargar_mock.sql").read_text(encoding="utf-8").splitlines()
    lineas = [
        linea
        for linea in lineas
        if not linea.startswith("\\") and linea.strip() not in ("BEGIN;", "COMMIT;")
    ]
    sql = "\n".join(lineas).replace("%", "%%")
    return sql.replace(":'mock_json'", "%(mock_json)s")


@pytest.fixture
def datos_demo(db):
    """Carga el dataset mock de la sección 3.4 con sus validaciones."""
    json_texto = (RUTA_MOCK / "demo.json").read_text(encoding="utf-8")
    json.loads(json_texto)  # falla rápido si el JSON está roto
    with connection.cursor() as cursor:
        cursor.execute(_sql_del_mock(), {"mock_json": json_texto})


@pytest.fixture
def demo(datos_demo):
    """Accesos cómodos a los datos del mock: demo.carmen, demo.med["Eutirox"]...

    Lo usan los tests de TK-02 y TK-03: por eso vive aquí y no en esos tickets.
    Los modelos se importan aquí dentro para que este archivo cargue aunque una app
    todavía no tenga los suyos.
    """
    from apps.accounts.models import Usuario
    from apps.catalogo.models import Medicamento
    from apps.entidades.models import Entidad
    from apps.inventario.models import MotivoBaja

    return SimpleNamespace(
        hogar=Entidad.objects.get(tipo="HOGAR"),
        maria=Entidad.objects.get(pk=101),
        jose=Entidad.objects.get(pk=102),
        carmen=Entidad.objects.get(pk=103),
        operador=Usuario.objects.get(username="operador.demo"),
        med={m.nombre_comercial: m for m in Medicamento.objects.all()},
        motivo={m.clave: m for m in MotivoBaja.objects.all()},
    )


@pytest.fixture
def como_app_user(demo):
    """El resto del test corre como app_user, igual que la aplicación en producción.

    SET LOCAL solo dura hasta el fin de la transacción del test. En un test con
    transaction=True no hay transacción envolvente y PostgreSQL ignoraría el SET LOCAL
    con un simple aviso: el test correría como app_owner sin que nadie lo notara.
    Por eso falla aquí; en esos tests, cada hilo hace SET ROLE app_user (guía de TK-02).
    """
    if not connection.in_atomic_block:
        pytest.fail(
            "como_app_user necesita la transacción del test: no lo uses con "
            "transaction=True; ahí cada hilo hace SET ROLE app_user (guía de TK-02)."
        )
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL ROLE app_user")
        cursor.execute("SELECT current_user")
        assert cursor.fetchone()[0] == "app_user"
    return demo
