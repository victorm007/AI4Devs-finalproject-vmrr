# Proyecto Django, imagen y servicio `web`

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-02 · **Épica:** EP-01

## Why

El proyecto ya tiene base de datos, pero todavía no tiene aplicación que la use. HB-03 y los tickets siguientes necesitan un proyecto Django que se construya en una imagen y corra en su contenedor (readme.md, sección 6, HB-02).

## What Changes

- Se crea el proyecto Django 5.2 en `app/`, con la configuración separada en `config/settings/{base,local,prod}.py`. `SECRET_KEY` (obligatoria), `DEBUG` y `ALLOWED_HOSTS` vienen del entorno, con `es-mx`, `America/Mexico_City` y `USE_TZ = True`.
- `DATABASES` todavía no se define: Django arranca con el backend `dummy` hasta HB-03.
- Se agregan `requirements.txt` (Django y Gunicorn) y `requirements-dev.txt` (djLint 1.50.4, pytest, pytest-django, pytest-cov y ruff), con versiones fijas.
- Se agrega `pyproject.toml` con la configuración de ruff y de djLint (perfil `django`, sin revisar `staticfiles/` ni `static/vendor/`).
- Se agrega un `Dockerfile` sobre `python:3.12-slim`: instala primero las dependencias, solo instala las de desarrollo con `INSTALAR_DEV=true`, corre como el usuario sin privilegios `django` y arranca Gunicorn en el puerto 8000.
- Se agrega a Compose el servicio `web`: monta `./app` y el volumen `static`, está en las redes `frontend` y `backend`, espera a `db` sana, recibe solo sus variables y no publica puertos.

**Fuera de alcance:** la conexión de Django a PostgreSQL, el modelo de usuario, las migraciones y la configuración de pytest (HB-03), y `nginx` (HB-04).

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `infraestructura`: agrega los requisitos del servicio `web`, su imagen, la configuración de Django por entorno y la calidad estática. Los requisitos del servicio `db` no cambian.

## Impact

- **Archivos nuevos:** `app/Dockerfile`, `app/.dockerignore`, `app/requirements.txt`, `app/requirements-dev.txt`, `app/pyproject.toml`, `app/manage.py`, `app/config/` y las carpetas `app/static/` y `app/templates/`.
- **Archivos modificados:** `docker-compose.yml`, `.env.example` y `.gitignore`. El `.env` local recibe las variables nuevas y no se versiona.
- **Puntos de integración:** ninguno de la tabla de readme.md, sección 6, cambia. `config/settings/base.py`, `requirements*.txt` y `docker-compose.yml` son archivos compartidos que los tickets siguientes completan.
- **CI:** al existir `app/manage.py`, se activan los *jobs* `lint` y `build de la imagen`. `tests` y `e2e` siguen saltados.
- **ADR aplicables:** [ADR-0001](../../../docs/adr/0001-monolito-modular-mvt-django.md) (Django 5.2 LTS), [ADR-0003](../../../docs/adr/0003-despliegue-docker-compose-tres-contenedores.md) (contenedores y redes), [ADR-0004](../../../docs/adr/0004-configuracion-por-entorno-variables-db.md) (configuración por entorno y secretos) y [ADR-0024](../../../docs/adr/0024-calidad-estatica-con-verificador-unico.md) (ruff, djLint y verificador único).
