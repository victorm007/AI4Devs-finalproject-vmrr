"""bloquear_secretos.py: qué bloquea y qué cuenta como ejemplo (CLAUDE.md, "Datos que no salen del proyecto").

Las líneas con datos que parecen reales llevan el comentario secreto-ok, que el propio hook
reconoce: así este archivo puede commitearse sin que el hook lo bloquee.
"""

import subprocess
import sys

import bloquear_secretos
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
    # Las frases de paso de GPG, LUKS y la CA (HB-10)
    ("GPG_PASSPHRASE=Xk82hd9Qw7zP", "secreto_asignado"),  # secreto-ok
    # En Markdown, la comilla invertida cierra el valor, pero no lo vuelve de ejemplo
    ("`DB_PASSWORD: Xk82hd9Qw7zP`", "secreto_asignado"),  # secreto-ok
    # Un valor que solo contiene "app-ci" o un dominio que solo empieza igual no son de ejemplo
    ("DB_PASSWORD=hogar-app-cifrado1", "secreto_asignado"),  # secreto-ok
    ("contacto = 'x@app-cielo.mx'", "correo"),  # secreto-ok
    ("contacto = 'digit@github.com'", "correo"),  # secreto-ok
    # La frase de paso como opción de gpg, separada por un espacio o en una lista de subprocess
    ("gpg --batch --passphrase 'Xk82hd9Qw7zP' --decrypt respaldo.gpg", "secreto_asignado"),  # secreto-ok
    ('    "--passphrase", "Xk82hd9Qw7zP",', "secreto_asignado"),  # secreto-ok
    # La clave entre comillas invertidas y el valor también
    ("`DB_PASSWORD`: `Xk82hd9Qw7zP`", "secreto_asignado"),  # secreto-ok
    # Entre comillas, el valor se evalúa completo: con espacios y aunque sea solo de minúsculas
    ('gpg --batch --passphrase "mi frase de paso larga" --decrypt respaldo.gpg', "secreto_asignado"),  # secreto-ok
    ("PASSPHRASE='frase con espacios larga'", "secreto_asignado"),  # secreto-ok
    ('DB_PASSWORD = "hogarapp2026"', "secreto_asignado"),  # secreto-ok
    ("gpg --batch --passphrase 'correcthorsebattery' --decrypt respaldo.gpg", "secreto_asignado"),  # secreto-ok
    # Las mismas claves que en una asignación, también como opción
    ("curl --token Xk82hd9Qw7zPq1 https://api.example.com", "secreto_asignado"),  # secreto-ok
    ("herramienta --api-key Xk82hd9Qw7zP", "secreto_asignado"),  # secreto-ok
    ("herramienta --client-secret Xk82hd9Qw7zP", "secreto_asignado"),  # secreto-ok
    # Un secreto en base64 con relleno no es un argumento con nombre (nombre=valor)
    ("API_KEY=Xk82hd9Qw7zPq1Ab2c3d4e5f6g7h8i9j0k1lmnop=", "secreto_asignado"),  # secreto-ok
    ("API_KEY=Xk82hd9Qw7zPq1Ab2c3d4e5f6g7h8i9j0k1lmno==", "secreto_asignado"),  # secreto-ok
    ('SECRET_KEY = "Xk82hd9Qw7zPq1Ab2c3d4e5f6g7h8i9j0k1lmnop="', "secreto_asignado"),  # secreto-ok
    ('SECRET_KEY = "clave=Xk82hd9Qw7zP"', "secreto_asignado"),  # secreto-ok
]

PERMITE = [
    "contacto = 'ana.lopez@example.com'",
    "Co-Authored-By: Claude <noreply@anthropic.com>",
    "SECRET_KEY=cambia-esto-por-una-clave-larga",
    "DB_PASSWORD=${DB_APP_PASSWORD}",
    "SECRET_KEY: solo-para-ci-no-es-secreto",
    "nota = 'texto sin datos personales'",
    # Las contraseñas de prueba del CI (.github/workflows/ci.yml), también entre comillas invertidas
    "  DB_OWNER_PASSWORD: owner-ci",
    "el `env:` define `DB_OWNER_PASSWORD: owner-ci`, y Compose lo prefiere al `.env`",
    # El usuario SSH de GitHub en la URL de clonación (guía de HB-10, paso 8)
    "git clone git@github.com:org/repo.git /opt/hogar",
    # Las opciones de gpg sin frase, con la frase en una variable o leída de un descriptor (HB-10)
    "gpg --batch --passphrase '' --quick-gen-key \"Ensayo <ensayo@respaldos.test>\"",
    '            "--passphrase",',
    'gpg --batch --passphrase "$FRASE" --decrypt respaldo.gpg',
    "gpg --batch --passphrase-fd 0 --decrypt respaldo.gpg",
    # Una palabra en minúsculas, con acentos o ñ, es texto y no un secreto
    "`DB_PASSWORD`: contraseña de app_user",
    # También con mayúscula inicial, si la sigue más texto
    "`DB_PASSWORD`: Contraseña de app_user",
    # En Markdown, la comilla invertida marca código: un identificador sigue siendo de ejemplo
    "| `DB_OWNER_PASSWORD`: `app_owner` |",
    # La definición de una opción, otra opción a continuación o una ruta no son el valor de la clave
    'parser.add_argument("--password", required=True)',
    'parser.add_argument("--token", type=str, default=None)',
    "gpg --passphrase --decrypt respaldo.gpg",
    "herramienta --private-key ./nginx/certs/local-key.pem",
    "docker login --password-stdin",
]


@pytest.mark.parametrize(("linea", "categoria"), BLOQUEA)
def test_bloquea_datos_reales(linea, categoria):
    assert categoria in revisar_linea("app/config/settings/base.py", linea)


@pytest.mark.parametrize("linea", PERMITE)
def test_permite_ejemplos(linea):
    assert revisar_linea("app/config/settings/base.py", linea) == []


# Un caso por fila de la tabla "Límites aceptados" de docs/herramientas/hook-secretos.md, en su orden
LIMITES_ACEPTADOS = [
    # 1. Sin comillas y solo de minúsculas: no se distingue de un nombre de variable
    "gpg --batch --passphrase correcthorsebattery --decrypt respaldo.gpg",
    # 2. El valor en la línea siguiente (una lista de subprocess con un elemento por línea)
    '            "--passphrase",',
    '            "Xk82hd9Qw7zP",',
    # 3. Sin comillas, una comilla en medio corta el valor y quedan menos de 8 caracteres
    "DB_PASSWORD=ab`cdefghij",
    # 4. Una palabra con mayúscula inicial seguida de más texto cuenta como prosa
    "`DB_PASSWORD`: Hogarseguro y algo más",
    # 5. Sin comillas, lo que empieza como otra opción, una ruta o un argumento con nombre
    "DB_PASSWORD=-Xk82hd9Qw7zP",
    "DB_PASSWORD=/Xk82hd9Qw7zP",
    "API_KEY=clave=Xk82hd9Qw7zP",
    # 6. Paréntesis, corchetes o llaves en el valor, también en una frase entre comillas
    'gpg --passphrase "mi frase (2026) larga"',
    # 7. Comillas escapadas dentro del valor
    'DB_PASSWORD = "ab\\"cdefghijkl"',
    # 8. Claves con otro nombre o en español, y otras formas de pasar el valor
    "CONTRASENA=Xk82hd9Qw7zP",
    "mysql -u app_user -p Xk82hd9Qw7zP",
    "openssl pkcs12 -passin pass:Xk82hd9Qw7zP",
    "Authorization: Bearer Xk82hd9Qw7zPq1Ab2c3d4",
]

# Se bloquean aunque no sean secretos: la tabla "Falsos positivos aceptados" del mismo documento.
# Mientras tanto, la línea se marca con secreto-ok.
FALSOS_POSITIVOS_ACEPTADOS = [
    # Un identificador entre comillas cuenta como valor literal
    'PASSWORD_FIELD = "password"',  # secreto-ok
    # Un mensaje de error de un formulario de Django cuyo código lleva el nombre de la clave
    '"password_mismatch": "Las contraseñas no coinciden.",',  # secreto-ok
]


@pytest.mark.parametrize("linea", LIMITES_ACEPTADOS)
def test_limites_aceptados_del_hook(linea):
    """Estos casos pasan a propósito: son los límites de docs/herramientas/hook-secretos.md.

    Si un cambio del hook cierra alguno, este test falla: se quita de esta lista y del documento.
    """
    assert revisar_linea("app/config/settings/base.py", linea) == []


def test_limite_lista_de_permitidos_por_subcadena(monkeypatch):
    # Fila 9 de la tabla: fuera de los correos, una entrada vale como subcadena del valor
    monkeypatch.setattr(bloquear_secretos, "PERMITIDOS", ["valor-publico-largo"])
    assert revisar_linea("x.py", "DB_PASSWORD=Xk82valor-publico-largo") == []  # secreto-ok


@pytest.mark.parametrize("linea", FALSOS_POSITIVOS_ACEPTADOS)
def test_falsos_positivos_aceptados_del_hook(linea):
    """Si un cambio del hook deja de bloquear alguno, se quita de esta lista y del documento."""
    assert "secreto_asignado" in revisar_linea("app/apps/accounts/forms.py", linea)


def test_escanear_repo_incluye_los_archivos_sin_rastrear(tmp_path, monkeypatch, capsys):
    # El cierre de implementar-ticket lo corre antes de cualquier git add: debe ver lo nuevo
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("ignorado.txt\n", encoding="utf-8")
    (tmp_path / "ignorado.txt").write_text("DB_PASSWORD=Xk82hd9Qw7zP\n", encoding="utf-8")  # secreto-ok
    monkeypatch.setattr(bloquear_secretos, "RAIZ", tmp_path)
    monkeypatch.setattr(sys, "argv", ["bloquear_secretos.py", "--escanear-repo"])
    assert bloquear_secretos.main() == 0
    assert "0 hallazgo(s)" in capsys.readouterr().out

    (tmp_path / "nuevo.py").write_text("DB_PASSWORD = 'Xk82hd9Qw7zP'\n", encoding="utf-8")  # secreto-ok
    assert bloquear_secretos.main() == 1
    salida = capsys.readouterr().out
    assert "nuevo.py:1 secreto_asignado" in salida
    assert "ignorado.txt" not in salida


def test_secreto_ok_exceptua_la_linea():
    assert revisar_linea("x.py", "correo = 'ana.lopez@empresa.mx'  # secreto-ok") == []  # secreto-ok


def test_los_correos_permitidos_se_comparan_completos(monkeypatch):
    # Un correo de la lista solo vale completo: como subcadena dejaría pasar otros correos
    monkeypatch.setattr(bloquear_secretos, "PERMITIDOS", ["contacto@curso.mx"])  # secreto-ok
    assert revisar_linea("x.md", "Contacto: contacto@curso.mx") == []  # secreto-ok
    assert revisar_linea("x.md", "Contacto: Contacto@Curso.MX") == []  # secreto-ok
    assert "correo" in revisar_linea("x.md", "Contacto: otro.contacto@curso.mx")  # secreto-ok
    assert "correo" in revisar_linea("x.md", "Contacto: contacto@curso.mx.empresa.com")  # secreto-ok


def test_los_datos_personales_del_mock_son_ejemplo():
    assert revisar_linea("app/fixtures/mock/demo.json", '"curp": "GOMA800101HDFRRN09"') == []  # secreto-ok


@pytest.mark.parametrize(
    ("ruta", "bloquea"),
    [(".env", True), ("app/.env.local", True), (".env.example", False), ("docs/env.md", False)],
)
def test_detecta_archivos_env(ruta, bloquea):
    assert (bool(RE_ENV.search(ruta)) and not RE_ENV_EJEMPLO.search(ruta)) is bloquea
