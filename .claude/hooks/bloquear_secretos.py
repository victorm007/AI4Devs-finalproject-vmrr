"""Hook PreToolUse: bloquea `git commit` / `git push` que lleven secretos,
correos o datos personales reales, o un archivo .env.

Lee el JSON del hook por stdin. Si el comando no es un commit ni un push, sale
sin hacer nada. Si encuentra algo, niega la llamada con
permissionDecision=deny y agrega una línea a .claude/logs/secretos-bloqueados.log.
Ni el mensaje ni el registro incluyen el valor encontrado: solo archivo, línea
y categoría.

Qué cuenta como ejemplo (y no bloquea):
- Correos de dominios reservados (example.com, *.test, *.invalid, localhost)
  y los noreply de GitHub/Anthropic.
- Datos personales y hashes en rutas de datos ficticios (fixtures/mock, *.example).
- Valores con marcadores de ejemplo (demo, ejemplo, cambia-esto, ${VAR}, <valor>...).
- Cualquier línea con el comentario `secreto-ok`.
- Los valores listados en .claude/hooks/secretos-permitidos.txt.
Los tokens con formato inconfundible (claves privadas, AWS, GitHub, etc.) solo
se exceptúan con `secreto-ok` o la lista de permitidos.

Prueba manual: python bloquear_secretos.py --escanear-repo
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no dejar __pycache__ en .claude/hooks/
from comandos_git import comandos_git  # noqa: E402  (mismo directorio: solo comandos git reales)

# ---------------------------------------------------------------- patrones

# Alta confianza: el formato basta para saber que es una credencial.
ALTA = [
    # También la llave privada PGP de GPG ("PRIVATE KEY BLOCK"), la de los respaldos (HB-10)
    ("clave_privada", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{22,}")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai_key", re.compile(r"\bsk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{20,}")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("stripe_key", re.compile(r"\b[sr]k_live_[0-9A-Za-z]{16,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
]

# Media: depende del valor; se exceptúa si el valor parece de ejemplo.
# PASSPHRASE: las frases de paso de GPG, LUKS y la CA (HB-10). La comilla invertida cierra el valor,
# como las otras comillas: en Markdown queda pegada a él (`CLAVE: valor`).
RE_ASIGNACION = re.compile(
    r"(?i)\b[A-Z0-9_-]*(?:PASSWORD|PASSWD|PASSPHRASE|PWD|SECRET|TOKEN|API_?KEY|ACCESS_?KEY|PRIVATE_?KEY)"
    r"""[A-Z0-9_]*\b["'`]?\s*[:=]\s*(["'`]?)([^\s"'`#,;]{8,})"""
)
RE_URL_CRED = re.compile(r"""\b[a-z][a-z0-9+.-]*://[^/\s:@"']+:([^@\s/"']+)@""", re.I)
RE_HASH = re.compile(
    r"\b(?:pbkdf2_sha256|pbkdf2_sha1|argon2|bcrypt_sha256)\$\S{20,}|\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}"
)

# Datos personales (formatos de México, donde opera el hogar).
RE_CORREO = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})\b")
PERSONALES = [
    (
        "curp",
        re.compile(
            r"\b[A-Z][AEIOUX][A-Z]{2}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[HM][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d\b"
        ),
    ),
    ("rfc", re.compile(r"\b[A-ZÑ&]{3,4}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[A-Z0-9]{2}[A0-9]\b")),
    (
        "telefono",
        re.compile(
            r"(?i)(?:\b(?:tel[eé]fono|tel|celular|cel|m[oó]vil|whatsapp|phone)\b\s*[:=.]?\s*[\"']?\+?(?:[\d\s().-]){10,}|\+52[\s.-]?\d(?:[\s.-]?\d){9})"
        ),
    ),
    ("nss", re.compile(r"(?i)\b(?:nss|seguro social|imss)\b\D{0,15}\d{11}\b")),
]
RE_TARJETA = re.compile(r"\b[3-6]\d{3}([ -]?)\d{4}\1\d{4}\1\d{1,7}\b")

DOMINIOS_EJEMPLO = re.compile(r"(?i)(?:^|\.)(?:example\.(?:com|org|net)|example|test|invalid|localhost|local)$")
# git@github.com: el usuario SSH de GitHub en las URLs de clonación (guía de HB-10, paso 8). Va aquí,
# anclado, y no en secretos-permitidos.txt, que compara por subcadena y dejaría pasar cualquier correo que termine igual.
CORREOS_PERMITIDOS = re.compile(
    r"(?i)^(?:noreply@anthropic\.com|noreply@github\.com|[^@]+@users\.noreply\.github\.com|git@github\.com)$"
)
MARCADORES_EJEMPLO = re.compile(
    r"(?i)ejemplo|example|ficticio|ficticia|dummy|placeholder|fake|sample|demo|cambia|changeme|"
    r"change-me|your[_-]|tu[_-]|xxx|redacted|\*\*\*|test|prueba|no-es-secreto|(?:^|[-_])ci(?:$|[-_])|"
    r"<[^>]*>|\$\{?[A-Za-z_]|\.\.\."
)
RUTAS_EJEMPLO = re.compile(r"(?i)(?:^|/)fixtures/mock/|\.(?:example|sample|template|dist)$")
RE_ENV = re.compile(r"(?:^|/)\.env(?:\.[^/]+)?$")
RE_ENV_EJEMPLO = re.compile(r"\.env\.(?:example|sample|template|dist)$")
MARCA_OK = "secreto-ok"

RAIZ = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
LOG = RAIZ / ".claude" / "logs" / "secretos-bloqueados.log"
PERMITIDOS_TXT = Path(__file__).with_name("secretos-permitidos.txt")


def _permitidos() -> list[str]:
    try:
        lineas = PERMITIDOS_TXT.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [linea.strip() for linea in lineas if linea.strip() and not linea.lstrip().startswith("#")]


PERMITIDOS = _permitidos()


def _permitido(valor: str) -> bool:
    return any(p in valor for p in PERMITIDOS)


def _luhn(numero: str) -> bool:
    digitos = [int(c) for c in numero if c.isdigit()]
    total = 0
    for i, d in enumerate(reversed(digitos)):
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return len(digitos) >= 13 and total % 10 == 0


def _valor_de_ejemplo(valor: str) -> bool:
    if MARCADORES_EJEMPLO.search(valor):
        return True
    if any(c in valor for c in "([{"):  # llamadas o índices: os.environ[...], env(...)
        return True
    if re.fullmatch(r"[a-z_][a-z0-9_.]*", valor):  # nombre de variable en código
        return True
    return valor.lower() in {"none", "null", "true", "false", "required", "optional"}


def revisar_linea(ruta: str, linea: str) -> list[str]:
    """Devuelve las categorías encontradas en una línea agregada."""
    if MARCA_OK in linea:
        return []
    ruta_ejemplo = bool(RUTAS_EJEMPLO.search(ruta))
    hallazgos: list[str] = []

    for categoria, patron in ALTA:
        for m in patron.finditer(linea):
            if not _permitido(m.group(0)) and "EXAMPLE" not in m.group(0):
                hallazgos.append(categoria)
                break

    for m in RE_ASIGNACION.finditer(linea):
        valor = m.group(2)
        if not (_valor_de_ejemplo(valor) or _permitido(valor)):
            hallazgos.append("secreto_asignado")
            break

    for m in RE_URL_CRED.finditer(linea):
        if not (_valor_de_ejemplo(m.group(1)) or _permitido(m.group(0))):
            hallazgos.append("url_con_credenciales")
            break

    if not ruta_ejemplo:
        for m in RE_HASH.finditer(linea):
            if not _permitido(m.group(0)):
                hallazgos.append("hash_contrasena")
                break

        for m in RE_CORREO.finditer(linea):
            correo, dominio = m.group(0), m.group(1)
            if DOMINIOS_EJEMPLO.search(dominio) or CORREOS_PERMITIDOS.match(correo) or _permitido(correo):
                continue
            hallazgos.append("correo")
            break

        linea_ejemplo = bool(MARCADORES_EJEMPLO.search(linea))
        if not linea_ejemplo:
            for categoria, patron in PERSONALES:
                m = patron.search(linea)
                if m and not _permitido(m.group(0)):
                    hallazgos.append(categoria)
            for m in RE_TARJETA.finditer(linea):
                if _luhn(m.group(0)) and not _permitido(m.group(0)):
                    hallazgos.append("tarjeta")
                    break

    return hallazgos


# ---------------------------------------------------------------- git


def _git(cwd: str, *args: str) -> str:
    r = subprocess.run(
        ["git", "-C", cwd, "-c", "core.quotepath=off", *args],
        capture_output=True,
        timeout=60,
    )
    if r.returncode != 0:
        raise RuntimeError(f"git {args[0]} falló ({r.returncode})")
    return r.stdout.decode("utf-8", errors="replace")


def revisar_parche(parche: str) -> list[tuple[str, str, str]]:
    """Recorre un diff unificado (-U0) y revisa solo las líneas agregadas."""
    hallazgos: list[tuple[str, str, str]] = []
    ruta, num, borrado = "", 0, False
    for linea in parche.splitlines():
        if linea.startswith("diff --git "):
            m = re.match(r'diff --git "?a/(.*?)"? "?b/(.*?)"?$', linea)
            ruta, borrado = (m.group(2) if m else ""), False
            continue
        if linea.startswith("deleted file mode"):
            borrado = True
            continue
        if linea.startswith("new file mode") or linea.startswith("rename to") or linea.startswith("+++ "):
            if not borrado and RE_ENV.search(ruta) and not RE_ENV_EJEMPLO.search(ruta):
                hallazgos.append((ruta, "-", "archivo_env"))
            continue
        if linea.startswith("@@"):
            m = re.search(r"\+(\d+)", linea)
            num = int(m.group(1)) if m else 0
            continue
        if linea.startswith("+") and not borrado:
            for cat in revisar_linea(ruta, linea[1:]):
                hallazgos.append((ruta, str(num), cat))
            num += 1
    return hallazgos


def revisar_archivo(cwd: str, ruta: str) -> list[tuple[str, str, str]]:
    hallazgos: list[tuple[str, str, str]] = []
    if RE_ENV.search(ruta) and not RE_ENV_EJEMPLO.search(ruta):
        hallazgos.append((ruta, "-", "archivo_env"))
    p = Path(cwd) / ruta
    try:
        if p.stat().st_size > 2_000_000:
            return hallazgos
        datos = p.read_bytes()
    except OSError:
        return hallazgos
    if b"\0" in datos[:8000]:
        return hallazgos
    for i, linea in enumerate(datos.decode("utf-8", errors="replace").splitlines(), 1):
        for cat in revisar_linea(ruta, linea):
            hallazgos.append((ruta, str(i), cat))
    return hallazgos


def _dedup(h: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    return list(dict.fromkeys(h))


def revisar_commit(cwd: str, agrega: bool, todo: bool) -> list[tuple[str, str, str]]:
    base = ["diff", "-U0", "--no-color", "--no-ext-diff"]
    hallazgos = revisar_parche(_git(cwd, *base, "--cached"))
    if agrega or todo:
        # `git commit -a` o `git add ... && git commit`: lo no preparado también entra.
        hallazgos += revisar_parche(_git(cwd, *base))
    if agrega:
        for ruta in _git(cwd, "ls-files", "--others", "--exclude-standard").splitlines():
            if ruta.strip():
                hallazgos += revisar_archivo(cwd, ruta.strip())
    return _dedup(hallazgos)


def revisar_push(cwd: str) -> list[tuple[str, str, str]]:
    parche = _git(
        cwd, "log", "-p", "-U0", "--no-color", "--no-ext-diff", "--format=", "--branches", "--not", "--remotes"
    )
    return _dedup(revisar_parche(parche))


# ---------------------------------------------------------------- salida


def registrar(operacion: str, hallazgos: list[tuple[str, str, str]]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ahora = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    detalle = "; ".join(f"{r}:{n} {c}" for r, n, c in hallazgos)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{ahora} | BLOQUEO | git {operacion} | {len(hallazgos)} hallazgo(s) | {detalle}\n")


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
    if "--escanear-repo" in sys.argv:
        cwd = str(RAIZ)
        h: list[tuple[str, str, str]] = []
        for ruta in _git(cwd, "ls-files").splitlines():
            h += revisar_archivo(cwd, ruta)
        for r, n, c in h:
            print(f"{r}:{n} {c}")
        print(f"{len(h)} hallazgo(s)")
        return 0

    try:
        entrada = json.load(sys.stdin)
    except ValueError:
        return 0
    comando = (entrada.get("tool_input") or {}).get("command") or ""
    # Solo los `git commit` / `git push` que se van a ejecutar, no el texto dentro de un
    # mensaje, un echo o un heredoc. `git -C <ruta>` y `cd <ruta> &&` fijan el repositorio.
    try:
        git = comandos_git(comando, entrada.get("cwd") or str(RAIZ))
    except Exception:  # noqa: BLE001  si no se puede analizar, se revisa por precaución
        git = []
        if re.search(r"\bgit\b[^;&|\n]*?\b(commit|push)\b", comando):
            negar("No se pudo analizar el comando git. Bloqueado por precaución.")
            return 0
    operaciones = [c for c in git if c.subcomando in ("commit", "push")]
    if not operaciones:
        return 0
    ops = {c.subcomando for c in operaciones}
    agrega = any(c.subcomando == "add" for c in git)

    hallazgos: list[tuple[str, str, str]] = []
    try:
        for c in operaciones:
            if c.subcomando == "commit":
                hallazgos += revisar_commit(c.cwd, agrega, c.tiene_opcion_corta("a", "--all"))
            else:
                hallazgos += revisar_push(c.cwd)
    except Exception as e:  # falla cerrada: sin revisión no hay commit ni push
        registrar("/".join(sorted(ops)), [("-", "-", f"error_revision:{type(e).__name__}")])
        negar(f"No se pudo revisar el contenido antes de git {'/'.join(sorted(ops))} ({e}). Bloqueado por precaución.")
        return 0

    hallazgos = _dedup(hallazgos)
    if not hallazgos:
        return 0

    operacion = "/".join(sorted(ops))
    registrar(operacion, hallazgos)
    lista = "\n".join(f"  - {r}:{n} -> {c}" for r, n, c in hallazgos[:30])
    extra = f"\n  ... y {len(hallazgos) - 30} más" if len(hallazgos) > 30 else ""
    negar(
        f"Bloqueado git {operacion}: posible secreto, correo, dato personal o archivo .env "
        f"({len(hallazgos)} hallazgo(s)):\n{lista}{extra}\n"
        "Quita el dato o sácalo del staging. Si es un ejemplo, márcalo con el comentario "
        "`secreto-ok` o agrégalo a .claude/hooks/secretos-permitidos.txt. "
        "Registro: .claude/logs/secretos-bloqueados.log"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
