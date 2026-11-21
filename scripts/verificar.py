"""Verificador de calidad estática: ruff (Python) y djLint (plantillas de Django).

Es el mismo en los 3 lugares donde se usa (readme, secciones 2.4 y 7.3):
- El job `lint` del CI:             python scripts/verificar.py --modo local
- El hook PreToolUse de Claude Code, antes de cada `git commit`
  (.claude/hooks/verificar_antes_commit.py).
- A mano, desde la raíz:            python scripts/verificar.py [--corregir]

Corre desde app/ y con la configuración de app/pyproject.toml:
  1. ruff check .
  2. ruff format --check .
  3. djlint . --check   (solo si hay plantillas .html)
  4. djlint . --lint

Con --corregir, primero formatea (ruff format, ruff check --fix, djlint --reformat)
y después verifica. Con rutas de archivos (dentro de app/), revisa solo esos
archivos: así lo usa el hook PostToolUse (.claude/hooks/formatear_codigo.py).

Dónde busca ruff y djLint (--modo):
  auto    (por defecto) el contenedor `web` si está corriendo, que tiene las
          versiones fijadas en requirements-dev.txt; si no, las del equipo.
  docker  solo el contenedor `web`.
  local   solo las del equipo (el CI las instala desde requirements-dev.txt).

Con --herramientas revisa, en lugar de app/, las herramientas del repositorio
(scripts/, .claude/hooks/ y tests/) con ruff y la configuración de ruff.toml de la
raíz. Usa siempre el ruff del equipo, porque el contenedor `web` solo ve app/. Lo
corre el job `herramientas` del CI, junto con `pytest tests`.

Códigos de salida:
  0  sin errores, o nada que verificar (todavía no existe app/manage.py)
  1  hay errores de lint o de formato
  3  no hay ruff/djLint disponibles (ni el contenedor ni en el equipo)

Solo usa la biblioteca estándar de Python 3.10 o posterior.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "app"
# Lo mismo que extend_exclude de [tool.djlint] en app/pyproject.toml (HB-02)
EXCLUIDOS = ("staticfiles", "static/vendor", "htmlcov", "test-results", ".venv", "venv", "node_modules")

SIN_HERRAMIENTAS = 3
# Herramientas del repositorio (fuera de app/), con la configuración de ruff.toml
RUTAS_HERRAMIENTAS = ("scripts", ".claude/hooks", "tests")


def _excluido(relativa: str) -> bool:
    return any(f"/{e}/" in f"/{relativa}/" for e in EXCLUIDOS)


def hay_plantillas() -> bool:
    return any(not _excluido(p.relative_to(APP).as_posix()) for p in APP.rglob("*.html"))


def _web_corriendo() -> bool:
    if not shutil.which("docker") or not (RAIZ / "docker-compose.yml").exists():
        return False
    try:
        r = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "--services"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0 and "web" in r.stdout.split()


def elegir_ejecutor(modo: str) -> tuple[list[str], Path, str] | None:
    """Prefijo del comando, carpeta desde la que se corre y descripción."""
    if modo in ("auto", "docker") and _web_corriendo():
        # Dentro del contenedor el directorio de trabajo es /app (= ./app)
        return ["docker", "compose", "exec", "-T", "web"], RAIZ, "contenedor web"
    if modo in ("auto", "local") and shutil.which("ruff") and shutil.which("djlint"):
        return [], APP, "herramientas del equipo"
    return None


def correr(prefijo: list[str], cwd: Path, args: list[str]) -> tuple[int, str]:
    r = subprocess.run([*prefijo, *args], cwd=cwd, capture_output=True, timeout=300)
    salida = (r.stdout + r.stderr).decode("utf-8", errors="replace").strip()
    return r.returncode, salida


def _relativas(archivos: list[str]) -> tuple[list[str], list[str]]:
    """Separa en .py y .html las rutas que están dentro de app/ (relativas a app/)."""
    py: list[str] = []
    html: list[str] = []
    for a in archivos:
        p = Path(a)
        p = (p if p.is_absolute() else Path.cwd() / p).resolve()
        try:
            rel = p.relative_to(APP).as_posix()
        except ValueError:
            continue  # fuera de app/: ni ruff ni djLint tienen su configuración ahí
        if _excluido(rel):
            continue
        if p.suffix == ".py":
            py.append(rel)
        elif p.suffix == ".html":
            html.append(rel)
    return py, html


def verificar_herramientas(corregir: bool) -> int:
    """ruff sobre scripts/, .claude/hooks/ y tests/, con el ruff del equipo y ruff.toml."""
    if not shutil.which("ruff"):
        print(
            "No encuentro ruff en el equipo para revisar las herramientas del repositorio "
            "(el contenedor web solo ve app/). Lo revisa el job herramientas del CI.",
            file=sys.stderr,
        )
        return SIN_HERRAMIENTAS
    rutas = [r for r in RUTAS_HERRAMIENTAS if (RAIZ / r).exists()]
    if corregir:
        correr([], RAIZ, ["ruff", "format", *rutas])
        correr([], RAIZ, ["ruff", "check", "--fix", *rutas])
    fallidos = []
    for nombre, comando in (
        ("ruff check", ["ruff", "check", *rutas]),
        ("ruff format --check", ["ruff", "format", "--check", *rutas]),
    ):
        codigo, salida = correr([], RAIZ, comando)
        print(f"- {nombre} ({', '.join(rutas)}): {'bien' if codigo == 0 else 'FALLA'}")
        if codigo != 0:
            fallidos.append(nombre)
            print(salida)
    if fallidos:
        print(
            "\nLas herramientas tienen errores. El formato se corrige con: python scripts/verificar.py --herramientas --corregir"
        )
        return 1
    print("\nHerramientas del repositorio sin errores de lint ni de formato.")
    return 0


def main() -> int:
    for flujo in (sys.stdout, sys.stderr):  # djLint imprime emojis; la consola de Windows no es UTF-8
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="ruff y djLint, igual que el job lint del CI.")
    parser.add_argument("archivos", nargs="*", help="solo estos archivos (dentro de app/)")
    parser.add_argument("--corregir", action="store_true", help="formatea antes de verificar")
    parser.add_argument("--modo", choices=("auto", "docker", "local"), default="auto")
    parser.add_argument(
        "--herramientas", action="store_true", help="revisa scripts/, .claude/hooks/ y tests/ en lugar de app/"
    )
    opciones = parser.parse_args()

    if opciones.herramientas:
        return verificar_herramientas(opciones.corregir)

    if not (APP / "manage.py").exists():
        print("Todavía no existe app/manage.py (HB-02): nada que verificar.")
        return 0

    if opciones.archivos:
        py, html = _relativas(opciones.archivos)
        if not py and not html:
            print("Ningún archivo .py o .html de app/ que verificar.")
            return 0
    else:
        py, html = ["."], (["."] if hay_plantillas() else [])

    ejecutor = elegir_ejecutor(opciones.modo)
    if ejecutor is None:
        print(
            "No encuentro ruff ni djLint: levanta los contenedores (docker compose up -d) "
            "o instálalos con pip install -r app/requirements-dev.txt.",
            file=sys.stderr,
        )
        return SIN_HERRAMIENTAS
    prefijo, cwd, donde = ejecutor
    print(f"Verificando con las {donde}.")

    if opciones.corregir:
        if py:
            correr(prefijo, cwd, ["ruff", "format", "--force-exclude", *py])
            correr(prefijo, cwd, ["ruff", "check", "--fix", "--force-exclude", *py])
        if html:
            # --reformat termina con 1 cuando cambia algún archivo: no es un error
            correr(prefijo, cwd, ["djlint", *html, "--reformat", "--quiet"])

    pasos: list[tuple[str, list[str]]] = []
    if py:
        pasos += [
            ("ruff check", ["ruff", "check", "--force-exclude", *py]),
            ("ruff format --check", ["ruff", "format", "--check", "--force-exclude", *py]),
        ]
    if html:
        pasos += [
            ("djlint --check", ["djlint", *html, "--check"]),
            ("djlint --lint", ["djlint", *html, "--lint"]),
        ]
    else:
        print("- djLint: no hay plantillas .html todavía, se omite.")

    fallidos = []
    for nombre, comando in pasos:
        codigo, salida = correr(prefijo, cwd, comando)
        print(f"- {nombre}: {'bien' if codigo == 0 else 'FALLA'}")
        if codigo != 0:
            fallidos.append(nombre)
            print(salida)

    if fallidos:
        print(
            f"\n{len(fallidos)} paso(s) con errores: {', '.join(fallidos)}. "
            "El formato se corrige con: python scripts/verificar.py --corregir"
        )
        return 1
    print("\nSin errores de lint ni de formato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
