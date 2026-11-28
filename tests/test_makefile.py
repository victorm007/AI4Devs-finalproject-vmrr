"""Makefile: la contraseña de app_owner no se ve y llega completa a docker compose (TK-01).

Corre el GNU Make del equipo sobre el Makefile de la raíz, desde un directorio temporal con un
.env de ejemplo (design, decisión 6 de la segunda revisión). Sin make en el equipo, se omite; el
job "herramientas" del CI (Ubuntu) sí lo tiene.

Segunda revisión de TK-01 (PR #3, mayor 1): test_make_n_no_muestra_la_contrasena. Rojo
comprobado: el Makefile expandía la contraseña al leer .env, así que make -n imprimía el valor
de DB_OWNER_PASSWORD en cada receta que corre pytest como app_owner.

Ajustes de la tercera revisión de TK-01 (PR #3):
- test_docker_compose_recibe_la_contrasena_completa (menores 3 y 4, y nit 1; design,
  decisiones 1 y 2): make test de verdad, sin -n, con un docker falso al principio del PATH
  que anota sus argumentos y el DB_PASSWORD de su entorno. 3 casos: .env con espacios y CRLF,
  .env con la clave 2 veces y sin .env con la clave en el entorno. Se omite si make no
  encuentra el docker falso (make sin /bin/bash, por ejemplo lanzado desde PowerShell en
  Windows). Rojo esperado: hoy la contraseña va en los argumentos (DB_PASSWORD=<valor>), así
  que falta la línea DB_PASSWORD sin "=" en args.txt en los 3 casos, y clave.txt queda vacío,
  porque docker no recibe DB_PASSWORD en su entorno.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]

# Valor de ejemplo: lleva "demo" para que el hook de secretos lo tome como ejemplo
CLAVE_DE_EJEMPLO = "demo-clave-make-7f3a"

# Variables que no deben llegar a make: una contraseña exportada en la terminal (los atajos de
# CLAUDE.md exportan .env) o los MAKEFLAGS de un make que llame a pytest
SIN_HEREDAR = ("DB_OWNER_PASSWORD", "DB_PASSWORD", "MAKEFLAGS", "MFLAGS", "MAKELEVEL")


def hay_make():
    if shutil.which("make") is None:
        pytest.skip("GNU Make no está instalado en este equipo")


def entorno_sin_heredar() -> dict[str, str]:
    return {clave: valor for clave, valor in os.environ.items() if clave not in SIN_HEREDAR}


@pytest.fixture
def directorio_con_env(tmp_path):
    hay_make()
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
        env=entorno_sin_heredar(),
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


# docker falso: anota el DB_PASSWORD de su entorno (sin salto de línea) y un argumento por línea
DOCKER_FALSO = """#!/bin/sh
printf '%s' "$DB_PASSWORD" > "$(dirname "$0")/clave.txt"
printf '%s\\n' "$@" > "$(dirname "$0")/args.txt"
"""

# (contenido del .env o None si no hay, DB_OWNER_PASSWORD del entorno de make o None, esperado,
# valores que no deben aparecer en los argumentos ni en la salida)
CASOS_DE_CLAVE = [
    pytest.param(
        "DB_OWNER_PASSWORD=demo clave con espacios\r\nPOSTGRES_DB=hogar_demo\r\n",
        None,
        "demo clave con espacios",
        ("demo clave con espacios",),
        id="espacios-crlf",
    ),
    pytest.param(
        "DB_OWNER_PASSWORD=demo-primera\nDB_OWNER_PASSWORD=demo-segunda\n",
        None,
        "demo-primera",
        ("demo-primera", "demo-segunda"),
        id="clave-duplicada",
    ),
    pytest.param(
        None,
        "demo-del-entorno",
        "demo-del-entorno",
        ("demo-del-entorno",),
        id="entorno-sin-env",
    ),
]


@pytest.mark.parametrize(("env", "del_entorno", "esperado", "ocultos"), CASOS_DE_CLAVE)
def test_docker_compose_recibe_la_contrasena_completa(tmp_path, env, del_entorno, esperado, ocultos):
    # Scenario: docker compose recibe la contraseña completa (tercera revisión de TK-01,
    # menores 3 y 4)
    hay_make()
    binarios = tmp_path / "bin"
    binarios.mkdir()
    docker = binarios / "docker"
    docker.write_text(DOCKER_FALSO, encoding="utf-8", newline="\n")
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if env is not None:
        # newline="" respeta los \r\n del caso: sin él, Python escribiría los \n tal cual
        (tmp_path / ".env").write_text(env, encoding="utf-8", newline="")

    entorno = entorno_sin_heredar()
    if del_entorno is not None:
        entorno["DB_OWNER_PASSWORD"] = del_entorno
    entorno["PATH"] = str(binarios) + os.pathsep + entorno.get("PATH", "")

    resultado = subprocess.run(
        ["make", "-C", str(tmp_path), "-f", str(RAIZ / "Makefile"), "test"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=entorno,
        check=False,
        timeout=120,
    )
    salida = resultado.stdout + resultado.stderr
    clave = binarios / "clave.txt"
    # Antes del código de salida: si make no encontró el docker falso, la receta falla con
    # "docker: not found" (o corre el docker real), y eso no es un fallo del Makefile
    if not clave.exists():
        pytest.skip(
            "make no encontró el docker falso (¿make sin /bin/bash, p. ej. lanzado desde PowerShell en Windows?)"
        )
    assert resultado.returncode == 0, salida
    argumentos = (binarios / "args.txt").read_text(encoding="utf-8")
    lineas = argumentos.splitlines()

    # El valor completo: con sus espacios, sin el \r del CRLF y de la fuente que manda
    assert clave.read_text(encoding="utf-8") == esperado
    # Ni en los argumentos de docker ni en lo que imprime make
    for valor in ocultos:
        assert valor not in argumentos, argumentos
        assert valor not in resultado.stdout, resultado.stdout
        assert valor not in resultado.stderr, resultado.stderr
    # Control: docker sí recibió el exec como app_owner, y DB_PASSWORD como nombre sin valor
    # (-e DB_PASSWORD copia el valor del entorno del proceso)
    for esperada in ("compose", "exec", "-e", "DB_USER=app_owner", "DB_PASSWORD"):
        assert esperada in lineas, lineas
    assert not [linea for linea in lineas if linea.startswith("DB_PASSWORD=")], lineas
