# HB-02 · Guía paso a paso: proyecto Django, imagen y servicio `web`

> **Ticket:** [readme, sección 6, HB-02](../../readme.md#tickets-de-habilitación-hb-01-a-hb-09) · **Tipo:** infraestructura · **Estimación:** 3 puntos · **Rama:** `feature/HB-02-imagen-web`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket y en las secciones 2.3 y 2.4 del readme. Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.

**Resultado al terminar:** existe el proyecto Django en `app/` con la configuración separada por entorno. Hay un `Dockerfile` que construye una imagen con Python 3.12, Django 5.2 y Gunicorn, y que corre sin `root`. `docker compose up -d` levanta `db` y `web`; `web` espera a que `db` esté sana, está en las redes `frontend` y `backend` y no publica puertos.

**Alcance:** Django todavía **no** se conecta a PostgreSQL. La conexión, el modelo de usuario y las migraciones son de HB-03. Aquí Django arranca sin base de datos (backend `dummy`), lo suficiente para comprobar que la imagen y el contenedor funcionan.

---

## 0. Antes de empezar

### 0.1 Lee primero (30 min)

| Qué | Dónde | Para qué |
|---|---|---|
| Estructura de ficheros | readme, sección 2.3 | Dónde va cada archivo de `app/` y `config/settings/` |
| Contenedor `web` | readme, sección 2.4.1 | Imagen, puerto 8000 interno, redes y volumen `static` |
| Secretos y configuración | readme, sección 2.5 | `SECRET_KEY`, `DEBUG` y `ALLOWED_HOSTS` desde el entorno |
| CI | `.github/workflows/ci.yml` (comentario inicial) | Qué *jobs* se activan con este ticket |

### 0.2 Requisitos previos

- HB-01 integrado en `main`: `docker compose up -d db` deja `db` en `healthy`.
- No necesitas Python instalado en tu equipo: todo corre dentro de contenedores.

### 0.3 Crea la rama

```bash
git switch main && git pull
git switch -c feature/HB-02-imagen-web
```

---

## 1. Archivos que vas a crear o modificar

```
AI4Devs-finalproject-vmrr/
├── .env.example                    # MODIFICAR: SECRET_KEY, DEBUG, ALLOWED_HOSTS, ajustes de web
├── .gitignore                      # MODIFICAR: archivos generados por Python y pytest
├── docker-compose.yml              # MODIFICAR: servicio web, red frontend, volumen static
└── app/
    ├── Dockerfile                  # NUEVO
    ├── .dockerignore               # NUEVO
    ├── requirements.txt            # NUEVO: Django y Gunicorn (versiones fijas)
    ├── requirements-dev.txt        # NUEVO: pytest, pytest-django, pytest-cov, ruff, djlint
    ├── pyproject.toml              # NUEVO: configuración de ruff y djLint
    ├── manage.py                   # NUEVO
    ├── static/.gitkeep             # NUEVO: carpeta de estáticos propios (vacía por ahora)
    ├── templates/.gitkeep          # NUEVO: plantillas comunes (base.html llega en HB-08)
    └── config/
        ├── __init__.py             # NUEVO (vacío)
        ├── urls.py                 # NUEVO
        ├── wsgi.py                 # NUEVO
        ├── asgi.py                 # NUEVO
        └── settings/
            ├── __init__.py         # NUEVO (vacío)
            ├── base.py             # NUEVO: configuración común, valores sensibles del entorno
            ├── local.py            # NUEVO: desarrollo y CI
            └── prod.py             # NUEVO: servidor del hogar y VPS
```

---

## 2. Tareas paso a paso

Haz un commit al terminar cada paso.

### Paso 1. Dependencias con versión fija (≈ 20 min)

El proyecto fija **todas** sus dependencias (readme, sección 2.5). Consulta la última versión estable de cada una con un contenedor desechable:

```bash
for p in django gunicorn pytest pytest-django pytest-cov ruff; do
  docker run --rm python:3.12-slim pip index versions "$p" 2>/dev/null | head -1
done
```

**`app/requirements.txt`** (usa la última 5.2.x de Django: es la LTS):

```text
# Dependencias de producción (readme, sección 2.5: versiones fijas, revisión con pip-audit).
# Una por línea, en orden alfabético.
Django==5.2.4
gunicorn==23.0.0
```

**`app/requirements-dev.txt`** (solo desarrollo y CI; nunca en la imagen de producción):

```text
# Dependencias de desarrollo y CI. Una por línea, en orden alfabético.
djlint==1.50.4
pytest==8.4.1
pytest-cov==6.2.1
pytest-django==4.11.1
ruff==0.12.4
```

> Los números son un ejemplo de julio de 2025: pon los que te dio `pip index versions`, **salvo `djlint`, que se queda en 1.50.4**: es la versión acordada, y las plantillas de las guías (HB-08, TK-03) están comprobadas con ella. Subirla cambia el formato esperado, así que se hace en un PR propio que reformatee todas las plantillas. Anota las versiones en el PR. El CI instala `ruff` y `djlint` con la versión exacta de este archivo.

### Paso 2. Proyecto Django y configuración por entorno (≈ 1 h)

**2.1 `app/manage.py`:**

```python
#!/usr/bin/env python
"""Utilidad de línea de comandos de Django."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

**2.2 `app/config/settings/base.py`:**

```python
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

# DATABASES: lo agrega HB-03 (conexión como app_user con variables DB_*).
# Mientras tanto Django usa el backend "dummy" y no toca ninguna base.

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True  # fechas con hora en timestamptz (readme, sección 3)

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstatic escribe aquí; nginx (HB-04) lo sirve
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

**2.3 `app/config/settings/local.py`** (desarrollo y CI):

```python
"""Desarrollo y CI. DEBUG se controla desde .env: en CI es False."""

from .base import *  # noqa: F403
```

**2.4 `app/config/settings/prod.py`** (servidor del hogar y VPS):

```python
"""Producción: servidor del hogar y VPS (readme, sección 2.4).

HB-04 agrega aquí los ajustes de HTTPS detrás de nginx.
"""

from .base import *  # noqa: F403

DEBUG = False  # nunca True en producción, aunque .env diga otra cosa
```

**2.5 `app/config/urls.py`:**

```python
"""Rutas del proyecto. Cada app agrega las suyas en su ticket."""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
```

**2.6 `app/config/wsgi.py` y `app/config/asgi.py`:**

```python
"""Punto de entrada WSGI: lo usa Gunicorn (config.wsgi:application)."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_wsgi_application()
```

```python
"""Punto de entrada ASGI (no se usa en el MVP; se deja por convención de Django)."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_asgi_application()
```

> `wsgi.py` usa `prod` por defecto, y `manage.py` usa `local`. En los contenedores manda la variable `DJANGO_SETTINGS_MODULE` de `.env`, así que el valor por defecto solo cuenta si falta.

**2.7 Carpetas vacías:** `touch app/static/.gitkeep app/templates/.gitkeep app/config/__init__.py app/config/settings/__init__.py`.

### Paso 3. Configuración de ruff y djLint (≈ 15 min)

El proyecto tiene un formateador por tipo de archivo: **ruff** para Python y **djLint** para las plantillas de Django (`.html`). No hay formateador de CSS ni de JS: todo el CSS y el JS es de terceros y ya viene minificado (Bootstrap en HB-08, HTMX en TK-03), y se excluye de la revisión.

`app/pyproject.toml`:

```toml
# Herramientas del proyecto. HB-03 agrega la sección de pytest.
[tool.ruff]
line-length = 100
target-version = "py312"
# Las migraciones generadas por Django no se reformatean (se revisan con sqlmigrate)
extend-exclude = ["**/migrations/*.py"]

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "B", "UP"]

[tool.ruff.lint.isort]
known-first-party = ["apps", "config"]

[tool.djlint]
# Formato y lint de las plantillas de Django (readme, sección 6: definición de hecho común)
profile = "django"
indent = 2
max_line_length = 120
# H030 y H031 piden <meta> de descripción y palabras clave: no aplican a una app interna con login
ignore = "H030,H031"
# Archivos generados (collectstatic, cobertura, trazas de Playwright) y de terceros
extend_exclude = "staticfiles,static/vendor,htmlcov,test-results"
```

> djLint solo revisa `.html`. Su lint también protege la CSP: la regla `H021` rechaza los estilos en línea (`style="..."`), que nginx bloquea (HB-04). Mientras no haya plantillas (hasta HB-08), `djlint .` responde `No files to check!` con código de salida 2: es lo esperado, y por eso el CI se salta ese paso si no existe ningún `.html`.

### Paso 4. `Dockerfile` e imagen (≈ 45 min)

**4.1 `app/Dockerfile`:**

```dockerfile
# Imagen de la aplicación (readme, sección 2.4.1): Python 3.12 + Django 5.2 + Gunicorn.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Primero las dependencias, para aprovechar la caché de Docker
COPY requirements.txt requirements-dev.txt ./
# INSTALAR_DEV=true en desarrollo (pytest, ruff y djLint dentro del contenedor); false en producción
ARG INSTALAR_DEV=false
RUN pip install -r requirements.txt \
 && if [ "$INSTALAR_DEV" = "true" ]; then pip install -r requirements-dev.txt; fi

# Usuario sin privilegios: el proceso nunca corre como root
ARG APP_UID=1000
RUN useradd --create-home --uid "$APP_UID" django \
 && mkdir -p /app/staticfiles && chown django /app/staticfiles

COPY --chown=django . .
USER django

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
```

**4.2 `app/.dockerignore`** (lo que no entra en la imagen):

```text
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.coverage
coverage.xml
staticfiles/
test-results/
```

**4.3 `.gitignore`** de la raíz: agrega al final

```text
# Python y pruebas
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.coverage
coverage.xml
app/staticfiles/
app/test-results/
```

### Paso 5. Servicio `web` en `docker-compose.yml` (≈ 30 min)

**5.1 Agrega a `.env.example`** (y copia los valores a tu `.env`):

```dotenv
# Django (readme, sección 2.5)
# Genera la tuya con: docker compose run --rm --no-deps web python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
SECRET_KEY=cambia-esto-por-una-clave-larga-y-aleatoria
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
# config.settings.local en desarrollo; config.settings.prod en el servidor del hogar y el VPS
DJANGO_SETTINGS_MODULE=config.settings.local

# Imagen de web: true instala pytest, ruff y djLint (desarrollo); false en producción
INSTALAR_DEV=true
# Opcional en desarrollo: --reload reinicia Gunicorn al guardar un .py
GUNICORN_CMD_ARGS=--reload
```

> La `SECRET_KEY` generada puede traer `$` o `#`. Si los trae, genera otra: `.env` no debe tenerlos (lo lee `make`, TK-01).

**5.2 En `docker-compose.yml`**, agrega el servicio `web`, el volumen `static` y la red `frontend`:

```yaml
services:
  db:
    # ... sin cambios (HB-01)

  web:
    build:
      context: ./app
      args:
        INSTALAR_DEV: ${INSTALAR_DEV:-false}
        APP_UID: ${APP_UID:-1000}
    restart: unless-stopped
    environment:
      DJANGO_SETTINGS_MODULE: ${DJANGO_SETTINGS_MODULE:-config.settings.prod}
      SECRET_KEY: ${SECRET_KEY:?Falta SECRET_KEY en .env}
      DEBUG: ${DEBUG:-False}
      ALLOWED_HOSTS: ${ALLOWED_HOSTS:-localhost}
      GUNICORN_CMD_ARGS: ${GUNICORN_CMD_ARGS:-}
    volumes:
      - ./app:/app                 # el código del repositorio (makemigrations escribe aquí)
      - static:/app/staticfiles    # collectstatic escribe; nginx (HB-04) lo lee
    depends_on:
      db:
        condition: service_healthy # nunca arranca antes de que la base responda
    networks: [frontend, backend]
    # Sin "ports": el 8000 solo es visible para nginx dentro de la red frontend

volumes:
  pgdata:
  static:

networks:
  backend:
  frontend:
```

Puntos clave:
- **Variables una por una, sin `env_file`:** `web` recibe solo lo que necesita. Nunca ve `POSTGRES_PASSWORD` ni `DB_OWNER_PASSWORD`.
- **`./app:/app`:** los archivos que genera Django (migraciones) aparecen en tu repositorio. En el servidor también funciona, porque el despliegue es `git pull` (sección 2.4).

### Paso 6. Construye, levanta y comprueba (≈ 30 min)

```bash
docker compose build web
docker compose up -d
docker compose ps                  # db healthy, web running
docker compose logs web | tail -5  # "Booting worker with pid ..." 3 veces
```

Ejecuta la sección 5 completa.

### Paso 7. *Pull request* (≈ 15 min)

En el PR, el CI corre por primera vez `lint` (con `scripts/verificar.py`) y `build de la imagen`. `tests` y `e2e` aparecen como saltados (*skipped*): se activan en HB-03 y TK-03, y un *job* saltado cuenta como aprobado (sección 7.3).

---

## 3. Tests requeridos

Este ticket todavía no tiene código de negocio ni base de datos, así que **no agrega tests de `pytest`**: el *job* `tests` del CI se activa en HB-03, cuando existe `app/conftest.py`. Se prueba con estos comandos, cuya salida va en el PR:

| # | Prueba | Comando | Resultado esperado |
|---|---|---|---|
| 1 | La configuración de Django es válida | `docker compose exec web python manage.py check` | `System check identified no issues (0 silenced).` |
| 2 | Gunicorn sirve peticiones | Script de la sección 5, paso 3 | `404` (Django responde; aún no hay páginas) |
| 3 | Corre sin `root` | `docker compose exec web whoami` | `django` |
| 4 | `web` no publica puertos | `docker compose port web 8000` | Sin salida |
| 5 | `web` llega a `db` por la red `backend` | Sección 5, paso 5 | `db:5432 alcanzable` |
| 6 | Sin `SECRET_KEY`, no arranca | `SECRET_KEY= docker compose config --quiet` | Error: `Falta SECRET_KEY en .env` (la variable del *shell* manda sobre `.env`) |
| 7 | La imagen de producción no trae herramientas de desarrollo | Sección 5, paso 6 | `WARNING: Package(s) not found: pytest` |
| 8 | Lint y formato de Python | `ruff check .` y `ruff format --check .` | Sin errores |
| 9 | djLint instalado y configurado | `djlint . --check` | `No files to check!` (aún no hay plantillas; el código de salida 2 es lo esperado) |

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| Ningún secreto en el código ni en la imagen: `SECRET_KEY` solo desde el entorno | `git grep -n SECRET_KEY app/` solo muestra `os.environ["SECRET_KEY"]` |
| El contenedor corre con un usuario sin privilegios | Prueba 3 |
| `web` recibe solo sus variables (sin contraseñas de PostgreSQL) | `docker compose exec web env \| grep -i password` sin salida |
| Versiones de dependencias fijas (`==`) | Revisión de `requirements*.txt` |
| La imagen de producción no instala `requirements-dev.txt` | Prueba 7 |
| Capas de Docker ordenadas: dependencias antes que el código | Un cambio en un `.py` no reinstala dependencias al reconstruir |
| Código y comentarios en español; ruff sin errores | Prueba 8 |
| djLint lee su configuración de `pyproject.toml` | Prueba 9 |

---

## 5. Verificación: comandos y resultado esperado

```bash
set -a && . ./.env && set +a

# 1. Lint y configuración
docker compose exec web ruff check . && docker compose exec web ruff format --check .
docker compose exec web python manage.py check
# System check identified no issues (0 silenced).
docker compose exec web djlint . --check
# No files to check! 😢   (código 2: las plantillas llegan en HB-08)
# Lo mismo que el job lint del CI (necesita Python en tu equipo; usa el contenedor web):
python scripts/verificar.py
# - djLint: no hay plantillas .html todavía, se omite.  ...  Sin errores de lint ni de formato.

# 2. Usuario del proceso y puertos
docker compose exec web whoami                       # django
docker compose port web 8000 || echo "no publicado"  # no publicado

# 3. Gunicorn responde (Django aún no tiene páginas: 404 es lo correcto)
docker compose exec -T web python - <<'EOF'
import urllib.error
import urllib.request

try:
    urllib.request.urlopen("http://localhost:8000/")
except urllib.error.HTTPError as error:
    print(error.code)
EOF
# 404

# 4. web solo recibe sus variables
docker compose exec web env | grep -iE "password|postgres" || echo "sin contraseñas de la base"

# 5. Red backend: web alcanza a db (aunque todavía no se conecta a la base)
docker compose exec -T web python - <<'EOF'
import socket

socket.create_connection(("db", 5432), timeout=3).close()
print("db:5432 alcanzable")
EOF

# 6. Imagen de producción (la misma que construye el CI): sin herramientas de desarrollo
docker build -t hogar-web:prueba app
docker run --rm hogar-web:prueba pip show pytest 2>&1 | tail -1
# WARNING: Package(s) not found: pytest

# 7. Sin SECRET_KEY, Compose se niega a arrancar
SECRET_KEY= docker compose config --quiet
# error ... Falta SECRET_KEY en .env

# 8. Reconstrucción rápida: cambiar código no reinstala dependencias
touch app/config/urls.py && docker compose build web 2>&1 | grep "RUN pip install"
# La línea debe empezar con CACHED
```

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] La descripción del PR incluye las versiones fijadas y la salida de los pasos 1 a 3.
- [ ] En el CI, `lint` y `build de la imagen` están en verde, y `tests` y `e2e` aparecen saltados.

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `KeyError: 'SECRET_KEY'` al arrancar `web` | Falta `SECRET_KEY` en `.env` | Paso 5.1 |
| `web` se reinicia en bucle | Error de Python al importar la configuración | `docker compose logs web` muestra la línea; `docker compose run --rm --no-deps web python manage.py check` |
| `ModuleNotFoundError: No module named 'config'` | `WORKDIR` o `context` distintos de `app/` | Revisa `build.context: ./app` y `WORKDIR /app` |
| `Permission denied` al escribir en `/app` (Linux) | Tu usuario del equipo no tiene el UID 1000 | Agrega `APP_UID=<salida de id -u>` a `.env` y `docker compose build web` |
| `ruff format --check` falla | Formato distinto al de ruff | `docker compose exec web ruff format .` y vuelve a commitear |
| `djlint` revisa archivos de `staticfiles/` o de `vendor/` | Falta `extend_exclude` o `djlint` no corre desde `app/` | Revisa `[tool.djlint]` (paso 3); `docker compose exec web` ya corre en `/app` |
| `pip index versions` dice "unknown command" | pip antiguo en la imagen | Usa `docker run --rm python:3.12-slim pip install <paquete>==` y lee las versiones del error |
| En Git Bash, rutas como `/app` se convierten a `C:/Program Files/Git/app` | Conversión automática de rutas de MSYS | Antepón `MSYS_NO_PATHCONV=1` al comando `docker` |
