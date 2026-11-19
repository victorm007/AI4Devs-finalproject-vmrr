# Servicio de PostgreSQL y usuarios de base de datos

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-01 · **Épica:** EP-01

## Why

El proyecto todavía no tiene una base de datos que levantar. Los 2 usuarios de base de datos deben existir desde el primer día para que la aplicación nunca corra como dueña de las tablas y para que el CI, que ya los espera, funcione desde el primer ticket con código (readme.md, sección 6, decisiones de diseño de la habilitación).

## What Changes

- Se crea `docker-compose.yml` con **solo** el servicio `db`: imagen `postgres:17-alpine`, volumen `pgdata`, red `backend`, *healthcheck* con `pg_isready` y ningún puerto publicado.
- Se monta `db/init/` en `/docker-entrypoint-initdb.d/` en solo lectura. Ahí, `01_roles.sh` crea de forma idempotente a `app_owner` (dueño de la base y del esquema `public`, con `CREATEDB` solo si `DB_OWNER_CREATEDB=true`) y a `app_user` (solo `CONNECT` y `USAGE`).
- Se agrega `.env.example` con `POSTGRES_*`, `DB_OWNER_PASSWORD`, `DB_OWNER_CREATEDB` y `DB_APP_PASSWORD`.
- Se agrega `.gitattributes`, que fuerza el fin de línea LF en los `.sh`.
- Compose falla con un mensaje claro si falta una contraseña (`${VAR:?}`).

**Fuera de alcance:** el proyecto Django, el `Dockerfile` y el servicio `web` (HB-02); la conexión de Django y los privilegios de `app_user` sobre las tablas (HB-03); `nginx` (HB-04).

## Capabilities

### New Capabilities

- `infraestructura`: contenedores, imagen, red, proxy, configuración por entorno y roles de base de datos. Este cambio aporta el servicio `db` y sus 2 usuarios.

### Modified Capabilities

Ninguna.

## Impact

- **Archivos nuevos:** `docker-compose.yml`, `.env.example`, `.gitattributes` y `db/init/01_roles.sh`. El `.env` local no se versiona.
- **Puntos de integración:** ninguno de la tabla de readme.md, sección 6, cambia. Este ticket prepara el punto 4 (privilegios de `app_user`), que provee HB-03.
- **CI:** el *job* `tests` ya ejecuta `sh db/init/01_roles.sh`; se activa en HB-03.
- **ADR aplicables:** [ADR-0003](../../../docs/adr/0003-despliegue-docker-compose-tres-contenedores.md) (3 contenedores y PostgreSQL sin puertos publicados), [ADR-0004](../../../docs/adr/0004-configuracion-por-entorno-variables-db.md) (secretos en `.env` y 3 contraseñas) y [ADR-0006](../../../docs/adr/0006-dos-usuarios-de-base-de-datos.md) (2 usuarios de base de datos).
