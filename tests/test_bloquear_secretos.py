"""bloquear_secretos.py: qué bloquea y qué cuenta como ejemplo (CLAUDE.md, "Datos que no salen del proyecto").

Las líneas con datos que parecen reales llevan el comentario secreto-ok, que el propio hook
reconoce: así este archivo puede commitearse sin que el hook lo bloquee.
"""

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
]


@pytest.mark.parametrize(("linea", "categoria"), BLOQUEA)
def test_bloquea_datos_reales(linea, categoria):
    assert categoria in revisar_linea("app/config/settings/base.py", linea)


@pytest.mark.parametrize("linea", PERMITE)
def test_permite_ejemplos(linea):
    assert revisar_linea("app/config/settings/base.py", linea) == []


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
