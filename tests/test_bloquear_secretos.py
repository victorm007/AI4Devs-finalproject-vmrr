"""bloquear_secretos.py: qué bloquea y qué cuenta como ejemplo (CLAUDE.md, "Datos que no salen del proyecto").

Las líneas con datos que parecen reales llevan el comentario secreto-ok, que el propio hook
reconoce: así este archivo puede commitearse sin que el hook lo bloquee.
"""

import pytest
from bloquear_secretos import RE_ENV, RE_ENV_EJEMPLO, revisar_linea

BLOQUEA = [
    ("contacto = 'ana.lopez@empresa.mx'", "correo"),  # secreto-ok
    ("CURP: GOMA800101HDFRRN09", "curp"),  # secreto-ok
    ("DB_PASSWORD=Xk82hd9Qw7zP", "secreto_asignado"),  # secreto-ok
    ("postgres://app:Xk82hd9Qw7zP@db:5432/hogar", "url_con_credenciales"),  # secreto-ok
    ("-----BEGIN OPENSSH PRIVATE KEY-----", "clave_privada"),  # secreto-ok
    # La llave privada GPG que exporta HB-10 (paso 12) termina en "PRIVATE KEY BLOCK-----"
    ("-----BEGIN PGP PRIVATE KEY BLOCK-----", "clave_privada"),  # secreto-ok
]

PERMITE = [
    "contacto = 'ana.lopez@example.com'",
    "Co-Authored-By: Claude <noreply@anthropic.com>",
    "SECRET_KEY=cambia-esto-por-una-clave-larga",
    "DB_PASSWORD=${DB_APP_PASSWORD}",
    "SECRET_KEY: solo-para-ci-no-es-secreto",
    "nota = 'texto sin datos personales'",
]


@pytest.mark.parametrize(("linea", "categoria"), BLOQUEA)
def test_bloquea_datos_reales(linea, categoria):
    assert categoria in revisar_linea("app/config/settings/base.py", linea)


@pytest.mark.parametrize("linea", PERMITE)
def test_permite_ejemplos(linea):
    assert revisar_linea("app/config/settings/base.py", linea) == []


def test_secreto_ok_exceptua_la_linea():
    assert revisar_linea("x.py", "correo = 'ana.lopez@empresa.mx'  # secreto-ok") == []  # secreto-ok


def test_los_datos_personales_del_mock_son_ejemplo():
    assert revisar_linea("app/fixtures/mock/demo.json", '"curp": "GOMA800101HDFRRN09"') == []  # secreto-ok


@pytest.mark.parametrize(
    ("ruta", "bloquea"),
    [(".env", True), ("app/.env.local", True), (".env.example", False), ("docs/env.md", False)],
)
def test_detecta_archivos_env(ruta, bloquea):
    assert (bool(RE_ENV.search(ruta)) and not RE_ENV_EJEMPLO.search(ruta)) is bloquea
