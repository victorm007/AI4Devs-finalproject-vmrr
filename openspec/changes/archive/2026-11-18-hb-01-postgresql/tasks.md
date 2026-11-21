# Tasks

## 1. Verificación en rojo

- [x] 1.1 Escribir `verificacion.sh` con una prueba por escenario de `specs/infraestructura/spec.md`, salvo el permiso `100755`, y verificar que imprime `PASS` o `FAIL` por prueba con `bash <tmp>/HB-01/verificacion.sh`.
- [x] 1.2 Rojo: ejecutar `bash <tmp>/HB-01/verificacion.sh` antes de crear los archivos y verificar que las 15 pruebas imprimen `FAIL` por el motivo esperado.

## 2. Variables de entorno

- [x] 2.1 Crear `.env.example` con `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DB_OWNER_PASSWORD`, `DB_OWNER_CREATEDB` y `DB_APP_PASSWORD`, y verificar la prueba de archivos de entorno con `bash <tmp>/HB-01/verificacion.sh`.
- [x] 2.2 Crear el `.env` local con contraseñas generadas, sin mostrarlas, y verificar con `git check-ignore .env` que Git lo ignora.

## 3. Usuarios de base de datos

- [x] 3.1 Crear `db/init/01_roles.sh` y `.gitattributes`, y verificar la prueba de fin de línea LF con `bash <tmp>/HB-01/verificacion.sh`.

## 4. Servicio `db`

- [x] 4.1 Crear `docker-compose.yml` con el servicio `db`, el volumen `pgdata`, la red `backend` y el *healthcheck* por TCP, y verificar con `docker compose config --quiet`.
- [x] 4.2 Verde: ejecutar `docker compose up -d db` y verificar que `bash <tmp>/HB-01/verificacion.sh` imprime solo `PASS`.

## 5. Cierre

- [x] 5.1 Comprobar la huella con `sha256sum -c <tmp>/HB-01/congelados.sha256`.
- [x] 5.2 Aplicar `git add` y `git update-index --chmod=+x` a `db/init/01_roles.sh`, y verificar `100755` e `i/lf` con `git ls-files -s` y `git ls-files --eol`.
- [x] 5.3 Desde un volumen nuevo, ejecutar `docker compose down -v` y verificar que `bash <tmp>/HB-01/verificacion.sh` imprime solo `PASS`.
- [x] 5.4 Ejecutar los comandos de la sección 5 de la guía, con la prueba de contraseña por la IP del contenedor, y verificar el resultado esperado de cada uno.
- [x] 5.5 Verificar la definición de hecho del ticket: `python scripts/verificar.py` sin errores, `git status --short` sin `.env` y `readme.md` y `CLAUDE.md` al día.

## Workflow follow-up

- Ejecutar `/openspec-verify-change hb-01-postgresql` y `/openspec-archive-change hb-01-postgresql`, sincronizando las specs.
- Commit y push solo cuando el usuario los pida, con `/commit` y `/push`.
