# HB-01 · Guía paso a paso: servicio de PostgreSQL y usuarios de base de datos

> **Ticket:** [readme, sección 6, HB-01](../../readme.md#tickets-de-habilitación-hb-01-a-hb-10) · **Tipo:** infraestructura · **Estimación:** 2 puntos · **Rama:** `feature/HB-01-postgresql`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket y en las secciones 2.4 y 2.5 del readme. Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.

**Resultado al terminar:** `docker compose up -d db` levanta PostgreSQL 17 con su volumen persistente y su *healthcheck*. Al crear el volumen, el contenedor crea solo los 2 usuarios de la aplicación: `app_owner` (dueño de la base) y `app_user` (el que usará Django). PostgreSQL no publica ningún puerto al host.

**Alcance:** **solo** el servicio `db` y sus volúmenes. No hay todavía proyecto Django, Dockerfile ni Nginx (HB-02 y HB-04).

---

## 0. Antes de empezar

### 0.1 Lee primero (20 min)

| Qué | Dónde | Para qué |
|---|---|---|
| Contenedores, redes y volúmenes | readme, sección 2.4.1 | El servicio `db`, su red `backend` y el volumen `pgdata` |
| Aislamiento de red y privilegios mínimos | readme, sección 2.5 | Por qué no se publica el puerto y por qué hay 2 usuarios |
| Los 2 usuarios de base de datos | readme, sección 6, TK-01, punto 5 | Qué puede y qué no puede hacer cada uno |
| Imagen oficial de PostgreSQL | <https://hub.docker.com/_/postgres> ("Initialization scripts") | Cómo se ejecutan los scripts de `/docker-entrypoint-initdb.d/` |

### 0.2 Requisitos previos

- Docker con Docker Compose v2: `docker compose version` debe responder `v2.x`.
- Git Bash (en Windows) o una terminal de Linux/macOS.

### 0.3 Crea la rama

```bash
git switch main && git pull
git switch -c feature/HB-01-postgresql
```

---

## 1. Archivos que vas a crear

```
AI4Devs-finalproject-vmrr/
├── .gitattributes          # NUEVO: los .sh siempre con fin de línea LF
├── .env.example            # NUEVO: variables de ejemplo (el .env real no se versiona)
├── docker-compose.yml      # NUEVO: solo el servicio db, el volumen pgdata y la red backend
└── db/
    └── init/
        └── 01_roles.sh     # NUEVO: crea app_owner y app_user al crear el volumen
```

> `.env` ya está en `.gitignore`: nunca lo agregues al repositorio.

---

## 2. Tareas paso a paso

Haz un commit al terminar cada paso (mensajes en español: `feat(infra): agrega servicio de PostgreSQL`).

### Antes del paso 1: verificación primero (≈ 5 min)

> **Excepción al TDD de `CLAUDE.md`:** este ticket es configuración declarativa y todavía no existe pytest (llega en HB-03). La fase en rojo son los comandos con resultado esperado de la sección 3.

Lee la tabla de la sección 3 y confirma el punto de partida:

```bash
docker compose ps db     # falla: todavía no existe docker-compose.yml
```

Al terminar el paso 4, las 8 pruebas de la tabla deben dar su resultado esperado.

### Paso 1. Variables de entorno (≈ 15 min)

**1.1 Crea `.env.example`** en la raíz:

```dotenv
# ---------------------------------------------------------------------------
# Variables de entorno (readme, secciones 1.4 y 2.4). Copia este archivo a .env
# y cambia las contraseñas. Sin $, # ni comillas en los valores: make (TK-01)
# lee .env y los interpreta distinto que el shell.
# ---------------------------------------------------------------------------

# PostgreSQL: superusuario, solo para la inicialización del contenedor db
POSTGRES_DB=hogar
POSTGRES_USER=postgres
POSTGRES_PASSWORD=cambia-esto

# Dueño de las tablas: solo para migraciones, la carga del mock y los tests
DB_OWNER_PASSWORD=cambia-esto-owner
# true en desarrollo y CI (pytest crea la base de tests); false en producción
DB_OWNER_CREATEDB=true

# Usuario de la aplicación en tiempo de ejecución
DB_APP_PASSWORD=cambia-esto-app
```

**1.2 Crea tu `.env`** a partir del ejemplo y cambia las 3 contraseñas:

```bash
cp .env.example .env
# Genera contraseñas sin $, # ni comillas (solo letras y números):
python -c "import secrets; print(secrets.token_urlsafe(24).replace('-', 'a').replace('_', 'b'))"
```

> En el servidor del hogar y en la demo local, `DB_OWNER_CREATEDB=false`: en producción nadie crea bases nuevas.

### Paso 2. Script de inicio: los 2 usuarios (≈ 30 min)

**2.1 Crea `db/init/01_roles.sh`:**

```sh
#!/bin/sh
# Crea los usuarios de la aplicación (readme, sección 6, HB-01).
# PostgreSQL ejecuta este script solo al crear el volumen pgdata por primera vez.
# El CI lo ejecuta antes de los tests, igual que en desarrollo.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v owner_pw="$DB_OWNER_PASSWORD" -v app_pw="$DB_APP_PASSWORD" \
     -v createdb="${DB_OWNER_CREATEDB:-false}" <<'SQL'
-- Idempotente: solo crea los usuarios si no existen
SELECT format('CREATE ROLE app_owner LOGIN PASSWORD %L', :'owner_pw')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_owner') \gexec
SELECT format('CREATE ROLE app_user LOGIN PASSWORD %L', :'app_pw')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') \gexec
SELECT 'ALTER ROLE app_owner CREATEDB' WHERE :'createdb' = 'true' \gexec

-- Los tests pueden actuar como app_user (SET ROLE); app_user no gana nada del dueño
GRANT app_user TO app_owner;

-- app_owner es dueño de la base y del esquema; app_user solo se conecta y lo usa
SELECT format('ALTER DATABASE %I OWNER TO app_owner', current_database()) \gexec
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database()) \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO app_user', current_database()) \gexec
ALTER SCHEMA public OWNER TO app_owner;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO app_user;
SQL
```

Qué hace cada parte:

| Línea | Para qué |
|---|---|
| `\gexec` con `WHERE NOT EXISTS` | Ejecuta el `CREATE ROLE` solo si el usuario no existe: el script se puede correr 2 veces sin error |
| `format(... %L ...)` | Pone la contraseña entre comillas de forma segura, aunque tenga caracteres especiales |
| `ALTER ROLE app_owner CREATEDB` | Solo en desarrollo y CI: `pytest` necesita crear la base de tests |
| `GRANT app_user TO app_owner` | Permite `SET ROLE app_user` en los tests; no le da a `app_user` nada del dueño |
| `ALTER DATABASE ... OWNER TO app_owner` | El dueño de la base podrá crear las extensiones de confianza (`pg_trgm`, `unaccent`, `btree_gist`) en HB-05 |
| `REVOKE CREATE ON SCHEMA public FROM PUBLIC` | `app_user` nunca puede crear tablas |

**2.2 En Windows, evita los 2 errores más comunes con scripts `.sh`:**

```bash
printf '*.sh text eol=lf\n' > .gitattributes          # sin CRLF: sh falla con "\r: not found"
git add .gitattributes db/init/01_roles.sh
git update-index --chmod=+x db/init/01_roles.sh       # permiso de ejecución dentro de Git
```

> Si ya habías guardado el script con CRLF, conviértelo: `sed -i 's/\r$//' db/init/01_roles.sh`.

### Paso 3. `docker-compose.yml` con el servicio `db` (≈ 30 min)

Crea `docker-compose.yml` en la raíz:

```yaml
# Servicios del sistema (readme, sección 2.4.1).
# HB-01 crea db; HB-02 agrega web y HB-04 agrega nginx.
name: hogar

services:
  db:
    image: postgres:17-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:?Falta POSTGRES_DB en .env}
      POSTGRES_USER: ${POSTGRES_USER:?Falta POSTGRES_USER en .env}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Falta POSTGRES_PASSWORD en .env}
      # Las lee db/init/01_roles.sh para crear los 2 usuarios de la aplicación
      DB_OWNER_PASSWORD: ${DB_OWNER_PASSWORD:?Falta DB_OWNER_PASSWORD en .env}
      DB_APP_PASSWORD: ${DB_APP_PASSWORD:?Falta DB_APP_PASSWORD en .env}
      DB_OWNER_CREATEDB: ${DB_OWNER_CREATEDB:-false}
    volumes:
      - pgdata:/var/lib/postgresql/data          # datos persistentes
      - ./db/init:/docker-entrypoint-initdb.d:ro # scripts de inicio, solo lectura
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \"$$POSTGRES_USER\" -d \"$$POSTGRES_DB\""]
      interval: 5s
      timeout: 5s
      retries: 10
    networks: [backend]
    # Sin "ports": PostgreSQL no se publica al host (readme, sección 2.5, aislamiento de red)

volumes:
  pgdata:

networks:
  backend:
```

Puntos clave:
- **`${VAR:?mensaje}`**: si falta la variable en `.env`, Compose se detiene con ese mensaje en lugar de arrancar con una contraseña vacía.
- **`$$POSTGRES_USER`**: el doble `$` hace que la variable la lea el *shell* del contenedor y no Compose.
- **`name: hogar`**: fija el nombre del proyecto. El volumen se llama `hogar_pgdata` en cualquier carpeta.
- **Sin `ports:`**: solo los contenedores de la red `backend` (en HB-02, `web`) llegan a la base.

### Paso 4. Levanta y comprueba (≈ 30 min)

```bash
docker compose config --quiet && echo "compose válido"
docker compose up -d db
docker compose ps                        # db debe quedar "healthy" en menos de 30 s
docker compose logs db | grep -E "01_roles|ready to accept"
```

Ejecuta los comandos de verificación de la sección 5 y compara con el resultado esperado.

### Paso 5. *Pull request* (≈ 15 min)

Ejecuta **todos** los comandos de la sección 5, marca la lista de la sección 6 y abre el PR hacia `main` con la plantilla.

---

## 3. Tests requeridos

Este ticket no tiene código Python, así que no hay tests de `pytest` (el *job* `tests` del CI se activa en HB-03). Los tests son **comandos con resultado esperado**, y van copiados en la descripción del PR:

| # | Prueba | Comando | Resultado esperado |
|---|---|---|---|
| 1 | El servicio arranca sano | `docker compose ps db` | `healthy` |
| 2 | Existen los 2 usuarios | `\du` (sección 5, paso 2) | `app_owner` con `Create DB` y `app_user` sin atributos |
| 3 | `app_owner` es dueño de la base y del esquema | `\l hogar` y `\dn+ public` | Dueño: `app_owner` |
| 4 | `app_user` no puede crear tablas | `CREATE TABLE prueba (id int)` como `app_user` | `ERROR: permission denied for schema public` |
| 5 | Las contraseñas de `.env` funcionan | Conexión TCP con `app_user` y su contraseña | `current_user = app_user` |
| 6 | El script es idempotente | Ejecutarlo a mano una segunda vez | Sin errores |
| 7 | El puerto no se publica | `docker compose port db 5432` | Sin salida (o error "no port") |
| 8 | Los datos sobreviven a un reinicio | `restart` y consultar la tabla de prueba | La tabla sigue ahí |

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| Ni contraseñas ni `.env` en el repositorio; `.env.example` solo con valores de ejemplo (`cambia-esto…`) | `git status` antes de cada commit |
| `01_roles.sh` con fin de línea LF y permiso de ejecución | `git ls-files --eol db/init/01_roles.sh` muestra `i/lf`; `git ls-files -s` muestra `100755` |
| El script es idempotente | Prueba 6 |
| PostgreSQL no publica puertos | Prueba 7 |
| Imagen con versión mayor fija (`postgres:17-alpine`), nunca `latest` | Revisión del PR |
| Comentarios en español | Revisión del PR |

---

## 5. Verificación: comandos y resultado esperado

Ejecútalos en orden desde la raíz. Copia la salida de los pasos 2 a 5 en la descripción del PR.

```bash
set -a && . ./.env && set +a            # carga las variables de .env en tu terminal

# 1. Arranque desde cero
docker compose down -v                  # ⚠️ borra el volumen local (solo desarrollo)
docker compose up -d db
docker compose ps db                    # STATUS: ... (healthy)

# 2. Usuarios
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\du'
#  app_owner | Create DB
#  app_user  |
#  postgres  | Superuser, Create role, Create DB, Replication, Bypass RLS

# 3. Dueños de la base y del esquema
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\l hogar' -c '\dn+ public'
#  hogar  | app_owner | UTF8 ...       y   public | app_owner | ...

# 4. app_user no puede crear tablas
docker compose exec db psql -U app_user -d "$POSTGRES_DB" -c 'CREATE TABLE prueba (id int)'
# ERROR:  permission denied for schema public

# 5. Contraseña real por TCP, por la IP del contenedor (scram-sha-256).
#    Por localhost no sirve: la imagen oficial usa trust ahí y acepta cualquier contraseña.
docker compose exec -e PGPASSWORD="$DB_APP_PASSWORD" db sh -c \
    'psql -h "$(hostname -i)" -U app_user -d "$POSTGRES_DB" -tAc "SELECT current_user"'
# app_user

# 6. Idempotencia: el script se puede volver a ejecutar sin errores
docker compose exec db sh /docker-entrypoint-initdb.d/01_roles.sh && echo "idempotente"

# 7. Puerto no publicado
docker compose port db 5432 || echo "no publicado"

# 8. Persistencia
docker compose exec db psql -U app_owner -d "$POSTGRES_DB" -c 'CREATE TABLE prueba (id int)'
docker compose restart db && sleep 5
docker compose exec db psql -U app_owner -d "$POSTGRES_DB" -c '\dt prueba'   # sigue ahí, dueño app_owner
docker compose exec db psql -U app_owner -d "$POSTGRES_DB" -c 'DROP TABLE prueba'
```

> En el paso 2, `psql` dentro del contenedor no pide contraseña porque usa el *socket* local (confianza local de la imagen oficial). El paso 5 sí la valida, por TCP.

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] La descripción del PR incluye la salida de `\du`, la del `CREATE TABLE` rechazado y la de `docker compose ps`.
- [ ] `git status` no muestra `.env`.

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `sh: 01_roles.sh: not found` o `\r: not found` | El script tiene fines de línea CRLF | Paso 2.2 y `docker compose down -v && docker compose up -d db` |
| `\du` no muestra `app_owner` ni `app_user` | El volumen `pgdata` ya existía: los scripts de inicio solo corren con el volumen vacío | `docker compose down -v` (desarrollo) o ejecútalo a mano (verificación, paso 6) |
| `Falta POSTGRES_PASSWORD en .env` | No copiaste `.env.example` a `.env` | Paso 1.2 |
| `permission denied` al ejecutar el script | Falta el permiso de ejecución | Paso 2.2 (`git update-index --chmod=+x`) |
| `db` queda en `starting` o `unhealthy` | El *healthcheck* usa un usuario o base que no existe | Revisa `POSTGRES_USER` y `POSTGRES_DB` en `.env` y `docker compose logs db` |
| El paso 5 falla con `password authentication failed` | Cambiaste la contraseña en `.env` después de crear el volumen | `docker compose down -v && docker compose up -d db`, o `ALTER ROLE app_user PASSWORD '...'` como `postgres` |
