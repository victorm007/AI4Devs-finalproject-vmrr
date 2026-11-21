# Tasks

## 1. Verificación en rojo

- [x] 1.1 Escribir `verificacion.sh` con una prueba por escenario de `specs/infraestructura/spec.md`, salvo el resultado del CI en el pull request, y verificar que imprime `PASS` o `FAIL` por prueba con `bash <tmp>/HB-02/verificacion.sh`.
- [x] 1.2 Rojo: ejecutar `bash <tmp>/HB-02/verificacion.sh` antes de crear los archivos y verificar que las 21 pruebas imprimen `FAIL` por el motivo esperado.

## 2. Dependencias y proyecto Django

- [x] 2.1 Crear `app/requirements.txt` y `app/requirements-dev.txt` con las versiones de `design.md`, y verificar la prueba de versiones fijas con `bash <tmp>/HB-02/verificacion.sh`.
- [x] 2.2 Crear `app/manage.py`, `app/config/` y las carpetas `app/static/` y `app/templates/`, y verificar la sintaxis con `docker run --rm -v "$(pwd -W)/app:/app" -w /app python:3.12-slim python -m compileall -q manage.py config`.
- [x] 2.3 Crear `app/pyproject.toml` y verificar que se lee con `python -c "import tomllib; tomllib.load(open('app/pyproject.toml', 'rb'))"`.

## 3. Imagen

- [x] 3.1 Crear `app/Dockerfile` y `app/.dockerignore`, actualizar `.gitignore`, y verificar la imagen con `docker build -t hogar-web:prueba app`.

## 4. Servicio `web`

- [x] 4.1 Agregar a `.env.example` y al `.env` local las variables del servicio `web`, con una `SECRET_KEY` de letras y números sin mostrarla, y verificar la prueba de archivos de entorno con `bash <tmp>/HB-02/verificacion.sh`.
- [x] 4.2 Agregar a `docker-compose.yml` el servicio `web`, el volumen `static` y la red `frontend`, y verificar con `docker compose config --quiet`.
- [x] 4.3 Verde: ejecutar `docker compose up -d --build` y verificar que `bash <tmp>/HB-02/verificacion.sh` imprime solo `PASS`.

## 5. Cierre

- [x] 5.1 Comprobar la huella con `sha256sum -c <tmp>/HB-02/congelados.sha256`.
- [x] 5.2 Ejecutar los comandos de la sección 5 de la guía, con la prueba de caché de `design.md`, y verificar el resultado esperado de cada uno.
- [x] 5.3 Corregir en la guía el generador de `SECRET_KEY`, la salida de `docker compose port` y la prueba de caché, y actualizar el estado del repositorio en `CLAUDE.md`; verificar con `git diff --stat`.
- [x] 5.4 Verificar la definición de hecho del ticket: `python scripts/verificar.py` sin errores, `git status --short` sin `.env` y `readme.md` al día.

## Workflow follow-up

- En el pull request, comprobar que `lint` y `build de la imagen` están en verde y que `tests` y `e2e` aparecen saltados.
- Después de esa comprobación, ejecutar `/openspec-verify-change hb-02-imagen-web` y `/openspec-archive-change hb-02-imagen-web`, sincronizando las specs.
- Commit y push solo cuando el usuario los pida, con `/commit` y `/push`.
