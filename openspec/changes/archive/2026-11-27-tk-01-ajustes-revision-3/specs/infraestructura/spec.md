# Spec Delta

## MODIFIED Requirements

### Requirement: Makefile de desarrollo local

El `Makefile` de la raíz DEBE (MUST) listar con `make help` sus 18 comandos con su descripción, y cada *target* DEBE (MUST) ejecutar los mismos comandos directos de la guía: `make migrate` es `./scripts/migrate.sh`, `make test` corre `pytest` en `web` como `app_owner` y `make mock` carga el mock con `cargar_mock.sql` como `app_owner`. La contraseña de `app_owner` NO DEBE (MUST NOT) aparecer en lo que `make` imprime ni en los argumentos de `docker compose`. La lee el shell al ejecutar la receta: de `DB_OWNER_PASSWORD` del entorno si está definida, y si no, de la primera línea que la define en `.env`.

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

#### Scenario: make test no muestra la contraseña (revisión de TK-01, hallazgo 4)

- **GIVEN** el repositorio con su `Makefile` y un `.env`
- **WHEN** se ejecuta `make test T=apps/conteos`
- **THEN** la salida no contiene el valor de `DB_OWNER_PASSWORD`

#### Scenario: make -n no muestra la contraseña (segunda revisión de TK-01, mayor 1)

- **GIVEN** un directorio con el `Makefile` y un `.env` temporal con un `DB_OWNER_PASSWORD` de ejemplo
- **WHEN** se ejecutan `make -n test`, `make -n test-ci` y `make -n e2e`
- **THEN** ninguna salida contiene el valor de `DB_OWNER_PASSWORD`
- **AND** cada una muestra `docker compose exec -e DB_USER=app_owner` y el `pytest` de su receta

#### Scenario: docker compose recibe la contraseña completa (tercera revisión de TK-01, menores 3 y 4)

- **GIVEN** un `docker` falso en el `PATH` que anota sus argumentos y el `DB_PASSWORD` que recibe
- **WHEN** se ejecuta `make test` con un `.env` cuyo `DB_OWNER_PASSWORD` tiene espacios y fin de línea CRLF, con un `.env` que la define 2 veces, o sin `.env` y con `DB_OWNER_PASSWORD` en el entorno
- **THEN** el `DB_PASSWORD` recibido es el valor completo: el de la primera línea en el segundo caso y el del entorno en el tercero
- **AND** ni los argumentos de `docker` ni la salida de `make` contienen el valor
