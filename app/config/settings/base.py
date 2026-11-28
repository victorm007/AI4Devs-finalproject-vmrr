"""Configuración común a todos los entornos (readme, secciones 2.3 y 2.5).

Los valores sensibles o que cambian por entorno vienen de variables de entorno
(metodología 12-factor). Nunca escribas aquí una contraseña ni la SECRET_KEY.
"""

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # la carpeta app/


def lista_del_entorno(nombre: str, por_defecto: str = "") -> list[str]:
    """Lee una variable con valores separados por comas: "a, b" -> ["a", "b"]."""
    return [v.strip() for v in os.environ.get(nombre, por_defecto).split(",") if v.strip()]


SECRET_KEY = os.environ["SECRET_KEY"]  # sin valor por defecto: si falta, Django no arranca
DEBUG = os.environ.get("DEBUG", "False") == "True"
ALLOWED_HOSTS = lista_del_entorno("ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # índices GIN/BRIN y restricciones de exclusión (HB-05 y HB-07)
    "axes",  # bloqueo por intentos fallidos (readme, sección 2.5; HB-08)
    # Apps del proyecto (readme, sección 2.3)
    "apps.accounts",
    "apps.catalogo",
    "apps.entidades",
    "apps.pautas",
    "apps.inventario",
    "apps.conteos",
]

AUTH_USER_MODEL = "accounts.Usuario"

# Nombre del Hogar que crea la migración entidades/0003_hogar (readme, sección 3.2, D3).
# En desarrollo, el CI y los tests basta el por defecto, que es el que esperan los tests de
# TK-03 con el dataset mock; una variable vacía (docker-compose.yml la pasa así si .env no la
# define) también lo toma. En producción es obligatoria: prod.py no arranca sin ella.
HOGAR_NOMBRE = os.environ.get("HOGAR_NOMBRE", "").strip() or "Hogar Gerontológico Demo"
# 150 es el largo de entidad.nombre: un nombre más largo falla aquí, con un mensaje claro, y no
# como DataError en la migración. Como local.py y prod.py importan este módulo, y prod.py lee
# la misma variable, aplica en todos los entornos.
if len(HOGAR_NOMBRE) > 150:
    raise ImproperlyConfigured(
        f"HOGAR_NOMBRE tiene {len(HOGAR_NOMBRE)} caracteres; el máximo es 150 (entidad.nombre)."
    )

# Contraseñas (readme, sección 2.5): Argon2 para las nuevas. PBKDF2 se conserva para
# validar los hash del dataset mock y los de usuarios creados antes del cambio.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # primero: cuenta los intentos fallidos
    "django.contrib.auth.backends.ModelBackend",
]

# Fuerza bruta (readme, sección 2.5): 5 intentos fallidos bloquean la cuenta 15 minutos, por
# usuario y no por IP (detrás de nginx, la IP sería la del proxy). El bloqueo responde 429.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "registration/bloqueado.html"
# axes.W006 pide agregar ip_address. El bloqueo es por usuario (ADR-0022, design.md de HB-08,
# decisión 2): detrás de nginx y sin el extra ipware, todos llegarían con la IP del proxy, y
# 5 fallos de cualquiera bloquearían a todos. prod.py repite este valor.
SILENCED_SYSTEM_CHECKS = ["axes.W006"]

# Sesiones: expiran tras 30 min sin actividad y al cerrar el navegador (sección 2.5)
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "admin:index"  # TK-03 lo cambia a la pantalla de existencias
LOGOUT_REDIRECT_URL = "login"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Conexión a PostgreSQL (readme, secciones 2.4 y 2.5). Los valores vienen del entorno:
# - web corre como app_user (docker-compose.yml);
# - migrate.sh, los tests y el CI cambian solo DB_USER y DB_PASSWORD para usar app_owner.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "CONN_MAX_AGE": 60,
    }
}

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True  # fechas con hora en timestamptz (readme, sección 3)

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstatic escribe aquí; nginx (HB-04) lo sirve
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Detrás de nginx (readme, sección 2.4.1). web no publica puertos: solo nginx puede
# poner X-Forwarded-Proto, así que es seguro confiar en esa cabecera.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = lista_del_entorno("CSRF_TRUSTED_ORIGINS", "https://localhost")
# Todos los entornos usan HTTPS (mkcert en local): las cookies solo viajan cifradas
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Política CSP: la misma cadena que add_header Content-Security-Policy de nginx/default.conf
# (un test lo comprueba). Django la envía siempre para que las pruebas que no pasan por nginx
# (live_server de Playwright, TK-03) la apliquen igual que el navegador real.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
)
MIDDLEWARE += ["config.middleware.ContentSecurityPolicyMiddleware"]

# django-axes (HB-08) va el último, como pide su documentación, y después del de CSP: así la
# respuesta 429 de una cuenta bloqueada, que la arma AxesMiddleware, también lleva la CSP.
MIDDLEWARE += ["axes.middleware.AxesMiddleware"]
