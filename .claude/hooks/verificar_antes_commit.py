"""Hook PreToolUse (Bash|PowerShell): corre el verificador antes de cada `git commit`.

Si el commit incluye código de la aplicación (.py o .html dentro de app/, o
app/pyproject.toml), ejecuta scripts/verificar.py, el mismo que corre el job
`lint` del CI, y niega el commit (permissionDecision=deny) si:
  - hay errores de lint o de formato, o
  - no se pudo verificar (no hay ruff ni djLint, error o tiempo agotado):
    falla cerrada, igual que el hook de secretos.
Los commits que no tocan código (documentación, CI, hooks) pasan sin verificar.

Revisa el árbol de trabajo completo, como el CI revisa el árbol del commit.
Si dejas cambios sin preparar, el resultado puede no coincidir con lo commiteado.

Corre junto con bloquear_secretos.py; ninguno sustituye al otro.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no dejar __pycache__ en .claude/hooks/
from comandos_git import comandos_git  # noqa: E402  (mismo directorio: solo comandos git reales)

RE_CODIGO = re.compile(r"^app/(?:.+\.(?:py|html)|pyproject\.toml)$")

RAIZ = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
SIN_HERRAMIENTAS = 3


def _git(cwd: str, *args: str) -> str:
    r = subprocess.run(["git", "-C", cwd, "-c", "core.quotepath=off", *args], capture_output=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"git {args[0]} falló ({r.returncode})")
    return r.stdout.decode("utf-8", errors="replace")


def archivos_del_commit(cwd: str, agrega: bool, todo: bool) -> list[str]:
    archivos = _git(cwd, "diff", "--cached", "--name-only").splitlines()
    if agrega or todo:
        archivos += _git(cwd, "diff", "--name-only").splitlines()
    if agrega:
        archivos += _git(cwd, "ls-files", "--others", "--exclude-standard").splitlines()
    return [a.strip() for a in archivos if a.strip()]


def negar(motivo: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": motivo,
                }
            }
        )  # ensure_ascii por defecto: la consola de Windows no es UTF-8
    )


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
    except ValueError:
        return 0
    comando = (entrada.get("tool_input") or {}).get("command") or ""
    try:
        git = comandos_git(comando, entrada.get("cwd") or str(RAIZ))
    except Exception as e:  # noqa: BLE001
        if re.search(r"\bgit\b[^;&|\n]*?\bcommit\b", comando):
            negar(f"No se pudo analizar el comando git ({type(e).__name__}). Bloqueado por precaución.")
        return 0
    # Solo un `git commit` que se va a ejecutar; `git -C <ruta>` y `cd <ruta> &&` fijan el repositorio.
    commits = [c for c in git if c.subcomando == "commit"]
    if not commits:
        return 0
    commit = commits[0]
    agrega = any(c.subcomando == "add" for c in git)

    try:
        raiz = Path(_git(commit.cwd, "rev-parse", "--show-toplevel").strip())
        archivos = archivos_del_commit(commit.cwd, agrega, commit.tiene_opcion_corta("a", "--all"))
        codigo = [a for a in archivos if RE_CODIGO.match(a)]
        if not codigo:
            return 0
        verificador = raiz / "scripts" / "verificar.py"
        if not verificador.exists():
            verificador = RAIZ / "scripts" / "verificar.py"
        r = subprocess.run([sys.executable, str(verificador)], cwd=raiz, capture_output=True, timeout=240)
    except Exception as e:  # falla cerrada: sin verificación no hay commit
        negar(f"No se pudo verificar el código antes del commit ({type(e).__name__}: {e}). Bloqueado por precaución.")
        return 0

    if r.returncode == 0:
        return 0
    salida = (r.stdout + r.stderr).decode("utf-8", errors="replace").strip()
    detalle = "\n".join(salida.splitlines()[-40:])
    if r.returncode == SIN_HERRAMIENTAS:
        negar(
            "Bloqueado git commit: no se pudo verificar el código porque no hay ruff ni djLint "
            f"(lo mismo que exige el job lint del CI).\n{detalle}"
        )
    else:
        negar(
            f"Bloqueado git commit: el verificador (scripts/verificar.py, el mismo del job lint) "
            f"encontró errores en el código ({len(codigo)} archivo(s) de app/ en el commit).\n{detalle}\n"
            "Corrige el formato con `python scripts/verificar.py --corregir`, arregla lo demás, "
            "vuelve a preparar los archivos y reintenta el commit."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
