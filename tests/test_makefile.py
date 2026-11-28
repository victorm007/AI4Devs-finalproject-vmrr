"""Makefile: make -n no muestra la contraseña de app_owner (segunda revisión de TK-01, mayor 1).

Corre el GNU Make del equipo sobre el Makefile de la raíz, desde un directorio temporal con un
.env de ejemplo (design, decisión 6). Sin make en el equipo, se omite; el job "herramientas"
del CI (Ubuntu) sí lo tiene.

Rojo esperado: hoy el Makefile expande la contraseña al leer .env, así que make -n imprime el
valor de DB_OWNER_PASSWORD en cada receta que corre pytest como app_owner.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]

# Valor de ejemplo: lleva "demo" para que el hook de secretos lo tome como ejemplo
CLAVE_DE_EJEMPLO = "demo-clave-make-7f3a"

# Variables que no deben llegar a make: una contraseña exportada en la terminal (los atajos de
# CLAUDE.md exportan .env) o los MAKEFLAGS de un make que llame a pytest
SIN_HEREDAR = ("DB_OWNER_PASSWORD", "DB_PASSWORD", "MAKEFLAGS", "MFLAGS", "MAKELEVEL")


@pytest.fixture
def directorio_con_env(tmp_path):
    if shutil.which("make") is None:
        pytest.skip("GNU Make no está instalado en este equipo")
    (tmp_path / ".env").write_text(
        f"DB_OWNER_PASSWORD={CLAVE_DE_EJEMPLO}\nPOSTGRES_DB=hogar_demo\n",
        encoding="utf-8",
        newline="\n",
    )
    return tmp_path


@pytest.mark.parametrize(
    ("target", "pytest_de_la_receta"),
    [
        ("test", "pytest -q"),
        ("test-ci", 'pytest -m "not e2e and not lento"'),
        ("e2e", "pytest -m e2e e2e/"),
    ],
)
def test_make_n_no_muestra_la_contrasena(directorio_con_env, target, pytest_de_la_receta):
    # Scenario: make -n no muestra la contraseña (segunda revisión de TK-01, mayor 1)
    entorno = {clave: valor for clave, valor in os.environ.items() if clave not in SIN_HEREDAR}
    resultado = subprocess.run(
        [
            "make",
            "-n",
            "-C",
            str(directorio_con_env),
            "-f",
            str(RAIZ / "Makefile"),
            target,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=entorno,
        check=False,
    )
    salida = resultado.stdout + resultado.stderr
    assert resultado.returncode == 0, salida
    assert CLAVE_DE_EJEMPLO not in salida, salida
    # Control: la receta sí corre pytest como app_owner y le pasa la contraseña; lo que no
    # aparece es su valor, no el comando
    assert "docker compose exec -e DB_USER=app_owner" in salida, salida
    assert "DB_PASSWORD=" in salida, salida
    assert pytest_de_la_receta in salida, salida
