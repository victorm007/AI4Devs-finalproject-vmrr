"""Configuración común a todos los entornos (readme, secciones 2.3 y 2.5).

Los valores sensibles o que cambian por entorno vienen de variables de entorno
(metodología 12-factor). Nunca escribas aquí una contraseña ni la SECRET_KEY.
"""

import os
from pathlib import Path

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
    # Apps del proyecto (readme, sección 2.3)
    "apps.accounts",
    "apps.catalogo",
]

AUTH_USER_MODEL = "accounts.Usuario"

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
