# Design

## Context

El repositorio todavía no tiene `docker-compose.yml`, `.env`, `.env.example`, `.gitattributes` ni `db/`. La motivación y el alcance están en `proposal.md`, y el comportamiento exigido, en `specs/infraestructura/spec.md`.

El diseño respeta [ADR-0003](../../../docs/adr/0003-despliegue-docker-compose-tres-contenedores.md), [ADR-0004](../../../docs/adr/0004-configuracion-por-entorno-variables-db.md) y [ADR-0006](../../../docs/adr/0006-dos-usuarios-de-base-de-datos.md).

## Goals / Non-Goals

**Goals:**

- Levantar `db` con un solo comando y con los 2 usuarios listos.
- Comprobar cada criterio con un comando que falle cuando el criterio no se cumple.

**Non-Goals:**

- Dar a `app_user` privilegios sobre tablas: los otorga HB-03.
- Crear las extensiones de PostgreSQL: las crea HB-05.

## Decisions

### 1. La contraseña se prueba por la IP del contenedor, no por `localhost`

La guía prueba la contraseña con `psql` hacia `localhost` dentro del contenedor. La imagen oficial marca `127.0.0.1/32` y `::1/128` como `trust` en `pg_hba.conf`, así que esa conexión acepta cualquier contraseña. Se comprobó en un contenedor `postgres:17-alpine`: una contraseña incorrecta entró por `localhost` y fue rechazada por la IP del contenedor.

La verificación se conecta a `$(hostname -i)`, que usa la regla `host all all all scram-sha-256`, y prueba también una contraseña incorrecta. La contraseña se pasa en `PGPASSWORD`, no en una URL, para que no aparezca en la salida.

*Alternativa descartada:* un segundo contenedor en la red `backend`. Prueba lo mismo con más piezas.

### 2. El *healthcheck* usa TCP: `pg_isready -h 127.0.0.1`

Durante la inicialización, la imagen levanta un servidor temporal con `listen_addresses=''`, que solo atiende por *socket*. Un `pg_isready` por *socket*, como el de la guía, puede reportar `healthy` antes de terminar `01_roles.sh`. Por TCP solo responde el servidor definitivo, y así se cumple que `web` no se conecte a una base que todavía no responde (readme 2.4.1).

*Alternativa descartada:* aumentar `start_period`. Reduce la probabilidad del problema, pero no lo elimina.

### 3. Las verificaciones viven en un script fuera del repositorio

HB-01 no tiene pytest. `verificacion.sh` se guarda en el directorio temporal de la sesión, imprime `PASS` o `FAIL` por prueba, nunca ejecuta `docker compose down -v` y queda congelado por su huella antes de implementar.

### 4. `CREATEDB=false` se prueba en un contenedor desechable

El script solo agrega `CREATEDB`: volver a ejecutarlo sobre la base de desarrollo no demuestra el caso `false`. La prueba levanta un contenedor temporal con `docker run --rm`, sin tocar `hogar_pgdata`, y solo si `db/init/01_roles.sh` existe, para que Docker no cree esa ruta como carpeta vacía durante el rojo.

### 5. La persistencia exige el volumen con nombre

Una tabla sobrevive a `docker compose restart` aunque no haya volumen, porque el contenedor no se recrea. Por eso la verificación exige además que los datos estén montados desde `hogar_pgdata`.

## Risks / Trade-offs

- [El volumen conserva las contraseñas iniciales] → Si cambian en `.env` después de crear el volumen, se recrea con `docker compose down -v`, solo en desarrollo.
- [Git Bash convierte rutas como `/docker-entrypoint-initdb.d/...`] → El script exporta `MSYS_NO_PATHCONV=1`.
- [El límite de 30 segundos solo es real con un volumen nuevo] → El cierre ejecuta la verificación completa después de `docker compose down -v`.
- [El permiso `100755` requiere el índice de Git] → Se comprueba en el cierre, no en `verificacion.sh`, porque `implementer` no ejecuta `git add`.
