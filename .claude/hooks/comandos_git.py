"""Reconoce los comandos `git` reales dentro de un comando de Bash o PowerShell.

Lo usan los hooks bloquear_secretos.py y verificar_antes_commit.py para
reaccionar solo a un `git commit` o `git push` que de verdad se va a ejecutar,
y no al texto "git commit" dentro de un mensaje, un `echo`, un comentario o
el cuerpo de un heredoc.

Cómo lo hace (sin ejecutar nada):
1. Recorre el comando respetando comillas simples y dobles, los heredocs de
   Bash (`<<EOF`, `<<'EOF'`, `<<-EOF`) y los here-strings de PowerShell
   (`@'...'@`, `@"..."@`): su contenido es texto, no comandos.
2. Corta en comandos simples por `;`, `&&`, `||`, `|`, `&` y saltos de línea,
   y descarta los comentarios (`#` al inicio de una palabra).
3. Un comando simple es de git si su primera palabra, quitando asignaciones
   `VAR=valor` y el operador `&` de PowerShell, es `git` o `git.exe`. Las
   opciones globales (`-C <ruta>`, `-c clave=valor`, `--no-pager`...) se saltan
   para encontrar el subcomando.
4. `cd <ruta>` y `Set-Location <ruta>` cambian la carpeta de los comandos que
   siguen, como en el shell.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

# Opciones globales de git que llevan un valor en la palabra siguiente
_GLOBALES_CON_VALOR = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
_SEPARADORES = {";", "&&", "||", "|", "&", "\n"}
_RE_HEREDOC = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
# Palabras de control que pueden ir antes del programa: `if git ...`, `then git ...`, `{ git ... }`
_PREFIJOS = set("{ } ( ) ! if then else elif do while until time exec command nohup".split())


@dataclass
class ComandoGit:
    subcomando: str
    argumentos: list[str] = field(default_factory=list)
    cwd: str = ""

    def tiene_opcion_corta(self, letra: str, larga: str) -> bool:
        """`-a`, `--all` o una combinación como `-am` (sin contar los valores de -m/-F)."""
        saltar = False
        for arg in self.argumentos:
            if saltar:
                saltar = False
                continue
            if arg == "--":
                break
            if arg == larga:
                return True
            if arg.startswith("-") and not arg.startswith("--") and len(arg) > 1:
                letras = arg[1:]
                for i, c in enumerate(letras):
                    if c == letra:
                        return True
                    if c in "mFcCt":  # opciones con valor: el resto de la palabra (o la siguiente) es el valor
                        saltar = i == len(letras) - 1
                        break
        return False


def _palabras(comando: str) -> list[str]:
    """Tokeniza: palabras (sin comillas) y separadores. Descarta heredocs y comentarios."""
    tokens: list[str] = []
    actual: list[str] = []
    hay_palabra = False
    pendientes: list[tuple[str, bool]] = []  # heredocs cuyo cuerpo empieza en la próxima línea
    i, n = 0, len(comando)

    def cerrar() -> None:
        nonlocal actual, hay_palabra
        if hay_palabra:
            tokens.append("".join(actual))
        actual, hay_palabra = [], False

    while i < n:
        c = comando[i]
        if c == "\n":
            cerrar()
            tokens.append("\n")
            i += 1
            for delimitador, quitar_tabs in pendientes:  # salta el cuerpo de cada heredoc
                while i < n:
                    fin = comando.find("\n", i)
                    fin = n if fin == -1 else fin
                    linea = comando[i:fin]
                    i = fin + 1
                    if (linea.lstrip("\t") if quitar_tabs else linea).rstrip("\r") == delimitador:
                        break
            pendientes = []
            continue
        if c in " \t\r":
            cerrar()
            i += 1
            continue
        if c == "\\" and i + 1 < n and comando[i + 1] == "\n":  # continuación de línea
            i += 2
            continue
        if c == "#" and not hay_palabra:  # comentario hasta el fin de línea
            fin = comando.find("\n", i)
            i = n if fin == -1 else fin
            continue
        if c == "@" and not hay_palabra and comando[i + 1 : i + 2] in ("'", '"'):
            cierre = "\n" + comando[i + 1] + "@"
            fin = comando.find(cierre, i + 2)
            if comando[i + 2 : i + 3] in ("\n", "\r") and fin != -1:  # here-string de PowerShell
                actual.append(comando[i + 2 : fin])
                hay_palabra = True
                i = fin + len(cierre)
                continue
        if c == "<" and comando.startswith("<<", i) and not comando.startswith("<<<", i):
            m = _RE_HEREDOC.match(comando, i)
            if m:
                cerrar()
                pendientes.append((m.group(3), m.group(1) == "-"))
                i = m.end()
                continue
        if c == "'":
            fin = comando.find("'", i + 1)
            fin = n if fin == -1 else fin
            actual.append(comando[i + 1 : fin])
            hay_palabra = True
            i = fin + 1
            continue
        if c == '"':
            j = i + 1
            while j < n and comando[j] != '"':
                if comando[j] in "\\`" and j + 1 < n and comando[j + 1] == '"':
                    actual.append('"')
                    j += 2
                    continue
                actual.append(comando[j])
                j += 1
            hay_palabra = True
            i = j + 1
            continue
        if c in ";|&":
            doble = comando[i : i + 2]
            if doble in ("&&", "||"):
                cerrar()
                tokens.append(doble)
                i += 2
                continue
            al_inicio = not hay_palabra and (not tokens or tokens[-1] in _SEPARADORES)
            if c == "&" and al_inicio and i + 1 < n and comando[i + 1] in " \t'\"":
                i += 1  # operador de llamada de PowerShell al inicio del comando: `& git ...`
                continue
            cerrar()
            tokens.append(c)
            i += 1
            continue
        actual.append(c)
        hay_palabra = True
        i += 1
    cerrar()
    return tokens


def _resolver(base: str, destino: str) -> str:
    m = re.match(r"/([A-Za-z])(/.*)?$", destino)
    if os.name == "nt" and m:  # ruta de Git Bash: /c/Users/... -> C:/Users/...
        return f"{m.group(1).upper()}:{m.group(2) or '/'}"
    if destino.startswith(("/", "\\")) or re.match(r"[A-Za-z]:", destino):
        return destino
    return str(Path(base) / destino)


def comandos_git(comando: str, cwd: str) -> list[ComandoGit]:
    """Los comandos git reales de `comando`, en orden, con la carpeta en que corren."""
    resultado: list[ComandoGit] = []
    simple: list[str] = []
    actual_cwd = cwd

    def procesar(palabras: list[str]) -> None:
        nonlocal actual_cwd
        while palabras and re.match(r"[A-Za-z_][A-Za-z0-9_]*=", palabras[0]):
            palabras = palabras[1:]  # VAR=valor git ...
        while palabras and (palabras[0].lower() in _PREFIJOS or palabras[0].startswith("(")):
            palabras = palabras[1:]  # if ($?) { git ... }
        if not palabras:
            return
        programa = palabras[0].replace("\\", "/").rsplit("/", 1)[-1].lower()
        if programa in ("cd", "set-location", "pushd") and len(palabras) > 1:
            destino = palabras[-1] if not palabras[-1].startswith("-") else ""
            if destino:
                actual_cwd = _resolver(actual_cwd, destino)
            return
        if programa not in ("git", "git.exe"):
            return
        carpeta = actual_cwd
        i = 1
        while i < len(palabras) and palabras[i].startswith("-"):
            opcion = palabras[i]
            if opcion in _GLOBALES_CON_VALOR:
                if opcion == "-C" and i + 1 < len(palabras):
                    carpeta = _resolver(carpeta, palabras[i + 1])
                i += 2
            else:
                i += 1
        if i < len(palabras):
            resultado.append(ComandoGit(palabras[i], palabras[i + 1 :], carpeta))

    for token in _palabras(comando):
        if token in _SEPARADORES:
            procesar(simple)
            simple = []
        else:
            simple.append(token)
    procesar(simple)
    return resultado
