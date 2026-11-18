"""comandos_git.py: los hooks solo reaccionan a los git commit / git push que se van a ejecutar."""

import pytest
from comandos_git import comandos_git

BASE = "F:/repo"


def _resumen(comando: str) -> list[tuple[str, str, bool]]:
    """(subcomando, carpeta, ¿lleva -a/--all?) de cada comando git real."""
    return [
        (c.subcomando, c.cwd.replace("\\", "/"), c.tiene_opcion_corta("a", "--all"))
        for c in comandos_git(comando, BASE)
    ]


REALES = [
    ("git commit -m 'x'", [("commit", BASE, False)]),
    (
        "git commit -F - <<'EOF'\ndocs: x\n\ngit commit y git push dentro del mensaje\nEOF",
        [("commit", BASE, False)],
    ),
    ("cd /otro && git add -A && git commit -am 'x'", [("add", "/otro", False), ("commit", "/otro", True)]),
    ("git -C F:/otro commit -m x", [("commit", "F:/otro", False)]),
    ('git -C "C:\\Users\\x y\\repo" push origin main', [("push", "C:/Users/x y/repo", False)]),
    ("git status; git log --oneline -1", [("status", BASE, False), ("log", BASE, False)]),
    ("git commit -m 'arregla -a' --no-edit", [("commit", BASE, False)]),
    ('git commit -m "usa git -C ruta commit"', [("commit", BASE, False)]),
    ("git commit --all -m x", [("commit", BASE, True)]),
    ("GIT_EDITOR=true git -c user.name=x commit -m x", [("commit", BASE, False)]),
    ("git commit -m @'\nlinea con git push\n'@", [("commit", BASE, False)]),
    ("& git commit -m x; if ($?) { git log -1 }", [("commit", BASE, False), ("log", BASE, False)]),
    ("Set-Location F:/otro; git push", [("push", "F:/otro", False)]),
    ("git commit -m x 2>&1 | tail -3", [("commit", BASE, False)]),
    ("git commit -m 'linea1\nlinea2 && git push'", [("commit", BASE, False)]),
    ("git \\\n  commit -m x", [("commit", BASE, False)]),
    ("echo x | git hash-object --stdin", [("hash-object", BASE, False)]),
]

SOLO_TEXTO = [
    'echo "### Pre: git -C ruta add + commit desde otro cwd"',
    "python - <<'EOF'\nnuevo = '''antes de cada `git commit` y `git -C <ruta>`'''\nEOF",
    'C="git comm""it"; echo $C',
    "# git commit -m comentario\nls",
    "grep -n 'git commit' archivo.md",
    "bash probar.sh  # hace git commit dentro",
]


@pytest.mark.parametrize(("comando", "esperado"), REALES)
def test_reconoce_los_comandos_git_reales(comando, esperado):
    assert _resumen(comando) == esperado


@pytest.mark.parametrize("comando", SOLO_TEXTO)
def test_ignora_git_commit_cuando_solo_es_texto(comando):
    assert [c for c in comandos_git(comando, BASE) if c.subcomando in ("commit", "push")] == []
