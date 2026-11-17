"""Hook PostToolUse (Edit|Write): formatea y revisa el archivo de código recién escrito.

Solo actúa sobre archivos .py y .html dentro de app/, que son los que tienen
configuración de ruff y djLint (app/pyproject.toml). Llama a
scripts/verificar.py --corregir <archivo>, el mismo verificador del CI:
  - Si el formateador cambió el archivo, avisa a Claude para que lo vuelva a
    leer antes de editarlo otra vez.
  - Si después de corregir quedan errores de lint, se los devuelve a Claude
    (decision=block) para que los arregle. La edición ya está hecha: no se deshace.
  - Si no hay ruff ni djLint (contenedor apagado), solo lo avisa.
Nunca falla de forma ruidosa: un error del hook no debe interrumpir el trabajo.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
VERIFICADOR = RAIZ / "scripts" / "verificar.py"
SIN_HERRAMIENTAS = 3


def _huella(p: Path) -> str:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return ""


def responder(contexto: str = "", bloqueo: str = "") -> None:
    salida: dict = {}
    if bloqueo:
        salida["decision"] = "block"
        salida["reason"] = bloqueo
    if contexto:
        salida["hookSpecificOutput"] = {"hookEventName": "PostToolUse", "additionalContext": contexto}
    if salida:
        print(json.dumps(salida))  # ensure_ascii por defecto: la consola de Windows no es UTF-8


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
    except ValueError:
        return 0
    ruta = (entrada.get("tool_input") or {}).get("file_path") or ""
    if not ruta:
        return 0
    archivo = Path(ruta)
    if not archivo.is_absolute():
        archivo = Path(entrada.get("cwd") or RAIZ) / archivo
    archivo = archivo.resolve()
    if archivo.suffix not in (".py", ".html") or not archivo.is_relative_to(RAIZ / "app"):
        return 0
    if not VERIFICADOR.exists() or not (RAIZ / "app" / "manage.py").exists():
        return 0  # sin proyecto Django todavía no hay configuración de ruff ni de djLint

    nombre = archivo.relative_to(RAIZ).as_posix()
    antes = _huella(archivo)
    try:
        r = subprocess.run(
            [sys.executable, str(VERIFICADOR), "--corregir", str(archivo)],
            cwd=RAIZ,
            capture_output=True,
            timeout=100,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        responder(
            contexto=f"No se pudo formatear {nombre} ({type(e).__name__}). Revísalo con python scripts/verificar.py."
        )
        return 0
    salida = (r.stdout + r.stderr).decode("utf-8", errors="replace").strip()
    cambiado = _huella(archivo) != antes
    aviso = f"El formateador cambió {nombre}: vuelve a leerlo antes de editarlo otra vez." if cambiado else ""

    if r.returncode == 0:
        responder(contexto=aviso)
    elif r.returncode == SIN_HERRAMIENTAS:
        responder(contexto=f"No se formateó {nombre}: {salida}")
    else:
        lineas = salida.splitlines()
        detalle = "\n".join(lineas[-40:])
        responder(
            contexto=aviso,
            bloqueo=f"{nombre} tiene errores de lint que el formateador no corrige solo:\n{detalle}",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
