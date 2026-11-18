"""Tests de las herramientas del repositorio (hooks de Claude Code y scripts), no de la aplicación.

Corren con el Python del equipo o del CI, fuera del contenedor web: python -m pytest tests
Los tests de la aplicación viven en app/ y tienen su propia configuración (app/pyproject.toml).
"""

import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no dejar __pycache__ en .claude/hooks/ ni en scripts/

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / ".claude" / "hooks"))
sys.path.insert(0, str(RAIZ / "scripts"))
