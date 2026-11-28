# Spec Delta

## MODIFIED Requirements

### Requirement: Variables de entorno de la aplicación

`.env.example` DEBE (MUST) documentar las variables del servicio `web`, y el `.env` local DEBE (MUST) poder cargarse en el shell.

#### Scenario: Archivos de entorno del servicio web (HB-02, descripción técnica)

- **GIVEN** los archivos `.env.example` y `.env`
- **WHEN** se revisan sus variables
- **THEN** `.env.example` define `SECRET_KEY` con un valor de ejemplo, `DEBUG`, `ALLOWED_HOSTS`, `DJANGO_SETTINGS_MODULE`, `INSTALAR_DEV` y `GUNICORN_CMD_ARGS`
- **AND** `.env` se carga sin errores con la lectura línea por línea de `scripts/migrate.sh` y de los atajos (TK-01), también con valores con espacios

## ADDED Requirements

### Requirement: Makefile de desarrollo local

El `Makefile` de la raíz DEBE (MUST) listar con `make help` sus 18 comandos con su descripción, y cada *target* DEBE (MUST) ejecutar los mismos comandos directos de la guía: `make migrate` es `./scripts/migrate.sh`, `make test` corre `pytest` en `web` como `app_owner` y `make mock` carga el mock con `cargar_mock.sql` como `app_owner`.

#### Scenario: make help lista los comandos (TK-01, criterio 3)

- **GIVEN** el repositorio con su `Makefile` y un `.env`
- **WHEN** se ejecuta `make help`
- **THEN** lista 18 comandos con su descripción, incluidos `e2e` y `actualizar`

#### Scenario: Los atajos hacen lo mismo que sus comandos directos (TK-01, criterio 3)

- **GIVEN** el repositorio con su `Makefile`
- **WHEN** se ejecutan `make -n migrate`, `make -n test T=apps/inventario` y `make -n mock`
- **THEN** muestran `./scripts/migrate.sh`, `docker compose exec -e DB_USER=app_owner … web pytest -q apps/inventario` y la copia del mock seguida de `psql -U app_owner … -v ON_ERROR_STOP=1 -f /tmp/mock/cargar_mock.sql`

#### Scenario: Poner al día imagen, migraciones y estáticos (TK-01, guía, paso 1)

- **GIVEN** los contenedores levantados
- **WHEN** se ejecuta `make actualizar`
- **THEN** termina sin errores y `https://localhost/static/css/vendor/bootstrap.min.css` responde `200`

### Requirement: Valores con espacios en .env

Un valor con espacios y sin comillas en `.env`, como `HOGAR_NOMBRE=Hogar Gerontológico Demo`, DEBE (MUST) leerse completo con `make`, con `scripts/migrate.sh` y los atajos de la documentación, y con `docker compose`. `.env.example` DEBE (MUST) traer esa línea sin comentar.

#### Scenario: migrate.sh con un valor con espacios (TK-01, criterio 4)

- **GIVEN** un `.env` con `HOGAR_NOMBRE=Hogar Gerontológico Demo` sin comentar
- **WHEN** se ejecutan `./scripts/migrate.sh`, `make help` y `docker compose config`
- **THEN** ninguno falla con "command not found", y `docker compose config` muestra `HOGAR_NOMBRE: Hogar Gerontológico Demo`

#### Scenario: El Hogar de una base nueva lleva el nombre de .env (TK-01, criterio 4)

- **GIVEN** ese `.env` y una base nueva (`docker compose down -v`, `up` y `./scripts/migrate.sh`)
- **WHEN** se consulta el nombre de la Entidad `HOGAR`
- **THEN** es "Hogar Gerontológico Demo", el de `.env`

#### Scenario: .env.example sin comentar (TK-01, criterio 4)

- **GIVEN** el repositorio
- **WHEN** se busca `HOGAR_NOMBRE` en `.env.example`
- **THEN** la línea `HOGAR_NOMBRE=Hogar Gerontológico Demo` está sin comentar

### Requirement: Instalación nueva lista para la aplicación

En una instalación nueva, los 2 usuarios de base de datos DEBEN (MUST) crearse solos y `scripts/migrate.sh` DEBE (MUST) dejar la base lista para que `web` arranque como `app_user`, sin poder borrar Movimientos.

#### Scenario: Instalación desde cero con el mock (TK-01, criterios 7 y 10)

- **GIVEN** `docker compose down -v` y `docker compose up -d`
- **WHEN** se ejecutan `./scripts/migrate.sh` y la carga del mock con `cargar_mock.sql`
- **THEN** el resumen dice 2 usuarios, 13 principios activos, 15 medicamentos, 3 residentes, 3 pautas, 28 movimientos, 13 existencias, 2 conteos y 5 detalles de conteo
- **AND** `web` se conecta como `app_user`, y `DELETE FROM movimiento WHERE id = 1` como `app_user` responde `permission denied for table movimiento`
