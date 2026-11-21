# Integración de Django con PostgreSQL

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-03 · **Épica:** EP-01

## Why

Django arranca con el backend `dummy` desde HB-02 y todavía no usa la base de datos. Los tickets siguientes necesitan que la aplicación se conecte como `app_user`, que las migraciones corran como `app_owner` y que el modelo de usuario exista antes del primer `migrate`, porque cambiarlo después obliga a borrar la base (readme.md, sección 6, HB-03).

## What Changes

- `DATABASES` se configura desde `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`. En Compose, `web` se conecta como `app_user`.
- Se crea `scripts/migrate.sh`, que ejecuta `migrate` como `app_owner`.
- `requirements.txt` instala `Django[argon2]` y `psycopg[binary]`.
- Se crea la app `accounts` con `Usuario(AbstractUser)` (tabla `usuario`, readme.md 3.2, D1) y `AUTH_USER_MODEL = "accounts.Usuario"` antes del primer `migrate`.
- Argon2 es el *hasher* principal; PBKDF2 se conserva para el dataset mock. Las contraseñas exigen al menos 10 caracteres.
- La migración `accounts/0002_privilegios` da a `app_user` `SELECT`, `INSERT`, `UPDATE` y `DELETE` sobre todas las tablas, también las futuras (`ALTER DEFAULT PRIVILEGES`).
- Se configuran pytest (marcadores `lento`, `http`, `integracion`, `infra` y `e2e` con `--strict-markers`) y la cobertura (solo `apps/`, con ramas, sin migraciones ni tests). Se crean `conftest.py`, que activa el *job* `tests` del CI, y `pruebas.py`, con el helper `ejecutar_sql`.

**Fuera de alcance:** `nginx` y HTTPS (HB-04), los grupos y el login (HB-08), y los *fixtures* `datos_demo`, `demo` y `como_app_user` (TK-01).

## Capabilities

### New Capabilities

- `accounts`: modelo de usuario propio, *hash* de contraseñas y su validación.

### Modified Capabilities

- `infraestructura`: la conexión `default` deja de usar el backend `dummy` y pasa a PostgreSQL; se agregan la conexión por entorno, las migraciones como `app_owner`, los privilegios de `app_user` y el *job* `tests` del CI.

## Impact

- **Archivos nuevos:** `scripts/migrate.sh`, `app/conftest.py`, `app/pruebas.py`, `app/apps/accounts/` (con sus migraciones y tests) y `app/config/tests/`.
- **Archivos modificados:** `docker-compose.yml`, `app/requirements.txt`, `app/pyproject.toml` y `app/config/settings/base.py`.
- **Puntos de integración:** provee el punto 4 (privilegios de `app_user` sobre todas las tablas) y el helper `ejecutar_sql` del punto 7, que consumen TK-01, TK-02 y TK-03. No cambia ningún contrato existente.
- **CI:** al existir `app/conftest.py`, se activa el *job* `tests`.
- **ADR aplicables:** [ADR-0004](../../../docs/adr/0004-configuracion-por-entorno-variables-db.md) (variables `DB_*`), [ADR-0006](../../../docs/adr/0006-dos-usuarios-de-base-de-datos.md) (2 usuarios de base de datos), [ADR-0022](../../../docs/adr/0022-autenticacion-sesion-argon2-axes.md) (usuario propio y Argon2) y [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md) (pruebas contra PostgreSQL real).
