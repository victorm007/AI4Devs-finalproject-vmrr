# HB-03 · Guía paso a paso: integración de Django con PostgreSQL

> **Ticket:** [readme, sección 6, HB-03](../../readme.md#tickets-de-habilitación-hb-01-a-hb-09) · **Tipo:** infraestructura y base de datos · **Estimación:** 3 puntos · **Rama:** `feature/HB-03-conexion-bd`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket y en las secciones 2.5, 3.2 (D1) y 6 (TK-01, punto 5) del readme. Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.

**Resultado al terminar:** Django lee la conexión de las variables `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`. El contenedor `web` se conecta como `app_user` y las migraciones corren como `app_owner` con `scripts/migrate.sh`. Existe el modelo de usuario propio (`Usuario`, tabla `usuario`), las contraseñas se guardan con Argon2 y `app_user` tiene permisos sobre todas las tablas, incluidas las que creen las migraciones futuras. Los primeros tests corren en el CI contra PostgreSQL 17.

**Por qué el modelo de usuario va aquí:** Django exige definir `AUTH_USER_MODEL` **antes de la primera migración**. Cambiarlo después obliga a borrar la base. Como este ticket ejecuta el primer `migrate`, el modelo nace aquí.

---

## 0. Antes de empezar

### 0.1 Lee primero (30 min)

| Qué | Dónde | Para qué |
|---|---|---|
| D1: `usuario` y grupos | readme, sección 3.2 | Columnas del modelo de usuario y tabla `usuario_groups` |
| Los 2 usuarios de base de datos | readme, sección 6, TK-01, punto 5 | Qué hace `app_owner` y qué hace `app_user` |
| Contraseñas y privilegios mínimos | readme, sección 2.5 | Argon2 y por qué la aplicación no usa el dueño de las tablas |
| Aislamiento de la base de tests | readme, sección 2.6 | Por qué `pytest` se conecta como `app_owner` |
| Modelo de usuario propio | <https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#using-a-custom-user-model-when-starting-a-project> | Por qué se define al inicio del proyecto |

### 0.2 Requisitos previos

- HB-01 y HB-02 integrados en `main`: `docker compose up -d` deja `db` en `healthy` y `web` en `running`.
- **Base local recién creada.** Si en tu base ya corriste algún `migrate` con el usuario de Django por defecto, bórrala: `docker compose down -v && docker compose up -d` (⚠️ solo desarrollo).

### 0.3 Crea la rama y los atajos

```bash
git switch main && git pull
git switch -c feature/HB-03-conexion-bd
```

Pega estos atajos en tu terminal (Git Bash o Linux) cada vez que la abras. Son los mismos que usan todas las guías:

```bash
set -a && . ./.env && set +a      # carga las variables de .env
dj()    { docker compose exec web python manage.py "$@"; }                       # manage.py como app_user
dtest() { docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" web pytest "$@"; }
dpsql() { docker compose exec db psql -U app_owner -d "$POSTGRES_DB" "$@"; }    # psql como app_owner
```

> Los tests corren como `app_owner` porque `pytest` necesita crear la base de tests. Los que deben comportarse como la aplicación cambian a `app_user` con `SET LOCAL ROLE` (helper `ejecutar_sql` del paso 6).

---

## 1. Archivos que vas a crear o modificar

```
AI4Devs-finalproject-vmrr/
├── docker-compose.yml                      # MODIFICAR: web con DB_* y DB_USER=app_user
├── scripts/
│   └── migrate.sh                          # NUEVO: migrate como app_owner
└── app/
    ├── requirements.txt                    # MODIFICAR: Django[argon2] y psycopg
    ├── pyproject.toml                      # MODIFICAR: sección de pytest
    ├── conftest.py                         # NUEVO: su existencia activa el job "tests" del CI
    ├── pruebas.py                          # NUEVO: helper ejecutar_sql para los tests
    ├── config/settings/base.py             # MODIFICAR: DATABASES, AUTH_USER_MODEL, contraseñas
    ├── config/tests/
    │   ├── __init__.py                     # NUEVO (vacío; HB-04 agrega test_proxy.py)
    │   └── test_conexion.py                # NUEVO: la conexión y los 2 usuarios de BD (marcador infra)
    └── apps/
        ├── __init__.py                     # NUEVO (vacío)
        └── accounts/
            ├── __init__.py                 # NUEVO (vacío)
            ├── apps.py                     # NUEVO
            ├── models.py                   # NUEVO: Usuario
            ├── migrations/
            │   ├── __init__.py             # NUEVO (vacío)
            │   ├── 0001_initial.py         # GENERADO con makemigrations
            │   └── 0002_privilegios.py     # NUEVO: permisos de app_user
            └── tests/
                ├── __init__.py             # NUEVO (vacío)
                ├── test_privilegios.py     # NUEVO (TK-01 le agrega los de movimiento)
                └── test_usuario.py         # NUEVO
```

---

## 2. Tareas paso a paso

Haz un commit al terminar cada paso.

### Paso 1. Dependencias (≈ 10 min)

```bash
docker run --rm python:3.12-slim pip index versions psycopg | head -1   # anota la última 3.x
```

En `app/requirements.txt`, Django pasa a instalarse con Argon2 y se agrega el controlador de PostgreSQL:

```text
Django[argon2]==5.2.4
gunicorn==23.0.0
psycopg[binary]==3.2.9
```

### Paso 2. Conexión desde variables `DB_*` (≈ 30 min)

**2.1 En `app/config/settings/base.py`**, reemplaza el comentario de `DATABASES` por:

```python
# Conexión a PostgreSQL (readme, secciones 2.4 y 2.5). Los valores vienen del entorno:
# - web corre como app_user (docker-compose.yml);
# - migrate.sh, los tests y el CI cambian solo DB_USER y DB_PASSWORD para usar app_owner.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "CONN_MAX_AGE": 60,
    }
}
```

> Por qué variables separadas y no una sola `DATABASE_URL`: los tests y `migrate.sh` cambian **solo** el usuario y la contraseña (`-e DB_USER=app_owner -e DB_PASSWORD=...`), y una contraseña con caracteres especiales no necesita codificarse para una URL. El CI ya define estas mismas variables.

**2.2 En `docker-compose.yml`**, agrega al `environment` de `web`:

```yaml
      # Conexión a PostgreSQL: la aplicación NUNCA usa app_owner
      DB_HOST: db
      DB_PORT: "5432"
      DB_NAME: ${POSTGRES_DB:?Falta POSTGRES_DB en .env}
      DB_USER: app_user
      DB_PASSWORD: ${DB_APP_PASSWORD:?Falta DB_APP_PASSWORD en .env}
```

### Paso 3. `scripts/migrate.sh` (≈ 15 min)

```sh
#!/bin/sh
# Ejecuta las migraciones como app_owner, el dueño de las tablas (readme, sección 2.4).
# La aplicación (contenedor web) se conecta como app_user, que no puede crear tablas.
# Uso: ./scripts/migrate.sh                 (todas)
#      ./scripts/migrate.sh accounts 0001   (hasta una migración concreta)
set -eu
set -a; . ./.env; set +a
docker compose run --rm -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" \
    web python manage.py migrate "$@"
```

```bash
git add scripts/migrate.sh
git update-index --chmod=+x scripts/migrate.sh      # permiso de ejecución (HB-01, paso 2.2)
```

> Nunca uses `dj migrate`: correría como `app_user`, que no puede crear tablas, y fallaría con `permission denied for schema public`.

### Paso 4. App `accounts` y modelo `Usuario` (≈ 45 min)

**4.1 Crea las carpetas y archivos vacíos:**

```bash
mkdir -p app/apps/accounts/migrations app/apps/accounts/tests app/config/tests
touch app/apps/__init__.py app/apps/accounts/__init__.py \
      app/apps/accounts/migrations/__init__.py app/apps/accounts/tests/__init__.py \
      app/config/tests/__init__.py
```

**4.2 `app/apps/accounts/apps.py`:**

```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    label = "accounts"  # el que usan AUTH_USER_MODEL y las dependencias de las migraciones
    verbose_name = "Usuarios"
```

**4.3 `app/apps/accounts/models.py`:**

```python
"""Usuarios del sistema (readme, sección 3.2, D1).

Se define desde el inicio del proyecto, como recomienda Django. No agrega campos:
el nivel de acceso lo da el grupo (Solo lectura o Lectura y escritura, HB-08).
"""

from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    class Meta:
        db_table = "usuario"  # su tabla puente de grupos se llama usuario_groups
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
```

**4.4 En `app/config/settings/base.py`:**

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # índices GIN/BRIN y restricciones de exclusión (HB-05 y HB-07)
    # Apps del proyecto (readme, sección 2.3)
    "apps.accounts",
]

AUTH_USER_MODEL = "accounts.Usuario"

# Contraseñas (readme, sección 2.5): Argon2 para las nuevas. PBKDF2 se conserva para
# validar los hash del dataset mock y los de usuarios creados antes del cambio.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```

**4.5 Reconstruye `web` y genera la migración:**

```bash
docker compose up -d --build web
dj makemigrations accounts         # crea 0001_initial.py
dj sqlmigrate accounts 0001 | grep -E 'CREATE TABLE "usuario'
# CREATE TABLE "usuario" ...  CREATE TABLE "usuario_groups" ...  CREATE TABLE "usuario_user_permissions" ...
```

### Paso 5. Migración de privilegios de `app_user` (≈ 30 min)

```bash
dj makemigrations accounts --empty --name privilegios
```

Reemplaza el contenido de `app/apps/accounts/migrations/0002_privilegios.py`:

```python
"""Privilegios mínimos de app_user (readme, sección 6, HB-03).

Va en una migración, y no en db/init, porque los permisos por defecto son de cada
base de datos: así también se aplican en la base de tests que crea pytest.
Todas las tablas de las migraciones siguientes deben depender de esta.
"""

from django.db import migrations

OTORGAR = """
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
-- Las tablas que creen las migraciones siguientes nacen con estos permisos
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_user;
"""

RETIRAR = """
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE USAGE, SELECT ON SEQUENCES FROM app_user;
REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM app_user;
REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM app_user;
"""


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.RunSQL(OTORGAR, RETIRAR)]
```

Aplica todo y crea tu usuario Administrador:

```bash
./scripts/migrate.sh
dj createsuperuser                 # como app_user: la aplicación ya puede escribir en usuario
```

> Los permisos por defecto (`ALTER DEFAULT PRIVILEGES`) solo cubren las tablas que cree **`app_owner`**. Por eso todas las migraciones corren con `migrate.sh`.

### Paso 6. Configuración de pytest, `conftest.py` y helper de SQL (≈ 20 min)

**6.1 Agrega a `app/pyproject.toml`:**

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.local"
pythonpath = ["."]  # para que los tests puedan hacer "from pruebas import ejecutar_sql"
testpaths = ["apps", "config", "e2e"]
# Un marcador mal escrito (@pytest.mark.lent) es un error, no un test que corre sin filtro
addopts = "--strict-markers"
markers = [
    "lento: tests de plan de ejecución (EXPLAIN), corren en el CI nocturno",
    "http: tests de URL + vista + plantilla con el cliente de Django (test_views_*, test_admin*); corren en el CI de cada PR",
    "integracion: flujo completo Vista → Servicio → BD → v_conciliacion_existencia (test_integracion.py); corre en el CI de cada PR",
    "infra: configuración e infraestructura (test_proxy.py, test_conexion.py); corre en el CI de cada PR",
    "e2e: pruebas de extremo a extremo con Playwright (llegan en TK-03)",
]

# Cobertura (readme, sección 2.6): la misma medida en local y en el CI
[tool.coverage.run]
source = ["apps"]
branch = true
omit = ["*/migrations/*", "*/tests/*"]  # el 80 % se mide sobre código de la aplicación

[tool.coverage.report]
show_missing = true
skip_covered = true
```

> Con esta configuración, `pytest --cov` mide lo mismo en tu equipo y en el CI: solo el código de `apps/`, con ramas (`branch = true`) y sin contar migraciones ni tests.

**6.2 `app/conftest.py`:**

```python
"""Fixtures compartidos de pytest (readme, secciones 2.6 y 6).

TK-01 agrega aquí datos_demo, demo y como_app_user. Este archivo existe desde HB-03:
su presencia activa el job "tests" del CI (.github/workflows/ci.yml).
"""
```

**6.3 `app/pruebas.py`** (TK-01 le agrega `saldo`):

```python
"""Utilidades compartidas por los tests."""

from django.db import connection, transaction


def ejecutar_sql(sql: str, params=None, *, rol: str | None = None) -> list[tuple]:
    """Ejecuta SQL dentro de un savepoint, opcionalmente como otro rol.

    Si la sentencia falla, solo se revierte el savepoint y el test puede seguir.
    Ejemplo: ejecutar_sql("SELECT current_user", rol="app_user") -> [("app_user",)]
    """
    with transaction.atomic(), connection.cursor() as cursor:
        if rol:
            cursor.execute(f"SET LOCAL ROLE {rol}")
        cursor.execute(sql, params)
        filas = cursor.fetchall() if cursor.description else []
        if rol:
            cursor.execute("RESET ROLE")
        return filas
```

### Paso 7. Tests (≈ 45 min)

Escribe los de la sección 3 y ejecútalos:

```bash
dtest -q
dtest -q --cov=apps --cov-fail-under=80    # lo mismo que exige el CI
```

### Paso 8. Verificación final y *pull request* (≈ 30 min)

Ejecuta la sección 5 completa. En el PR, el *job* `tests` corre por primera vez en el CI (lo activa `app/conftest.py`).

---

## 3. Tests requeridos

### 3.1 `app/config/tests/test_conexion.py`

Va en `config/tests/` y no en `apps/accounts/tests/`: prueba la configuración de la conexión y los roles de BD, no el comportamiento de `accounts`. Se corre sola con `dtest config/tests -q` o `dtest -m infra`.

```python
"""La aplicación usa PostgreSQL 17 con los 2 usuarios de HB-01 (readme, sección 2.5)."""

import pytest
from django.db import connection

from pruebas import ejecutar_sql

pytestmark = [pytest.mark.django_db, pytest.mark.infra]


def test_la_base_es_postgresql_17():
    assert connection.vendor == "postgresql"
    assert connection.pg_version >= 170000


def test_los_tests_corren_como_app_owner():
    # pytest crea la base de tests, así que se conecta con el dueño (atajo dtest y CI)
    assert ejecutar_sql("SELECT current_user") == [("app_owner",)]


def test_set_role_cambia_a_app_user():
    assert ejecutar_sql("SELECT current_user", rol="app_user") == [("app_user",)]


def test_app_user_no_tiene_atributos_especiales():
    assert ejecutar_sql(
        "SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = 'app_user'"
    ) == [(False, False, False)]
```

### 3.2 `apps/accounts/tests/test_privilegios.py`

```python
"""app_user tiene privilegios mínimos (readme, sección 2.5). TK-01 agrega los de movimiento."""

import pytest
from django.db import DatabaseError

from pruebas import ejecutar_sql

pytestmark = pytest.mark.django_db


def test_app_owner_es_dueno_de_todas_las_tablas():
    ajenas = ejecutar_sql(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner <> 'app_owner'"
    )
    assert ajenas == []


def test_app_user_tiene_los_4_permisos_en_las_tablas():
    # movimiento llega en TK-01 con permisos reducidos (sin UPDATE ni DELETE)
    sin_permiso = ejecutar_sql("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public' AND tablename <> 'movimiento'
          AND NOT (has_table_privilege('app_user', format('public.%%I', tablename), 'SELECT')
               AND has_table_privilege('app_user', format('public.%%I', tablename), 'INSERT')
               AND has_table_privilege('app_user', format('public.%%I', tablename), 'UPDATE')
               AND has_table_privilege('app_user', format('public.%%I', tablename), 'DELETE'))""")
    assert sin_permiso == []


def test_las_tablas_nuevas_heredan_los_permisos():
    # Como app_owner, igual que una migración futura
    ejecutar_sql("CREATE TABLE prueba_permisos (id int)")
    assert ejecutar_sql(
        "SELECT has_table_privilege('app_user', 'prueba_permisos', 'INSERT')"
    ) == [(True,)]


def test_app_user_no_puede_crear_tablas():
    with pytest.raises(DatabaseError, match="permission denied for schema public"):
        ejecutar_sql("CREATE TABLE intrusa (id int)", rol="app_user")
```

> `%%I` lleva doble `%` porque el SQL pasa por los parámetros de Django: `%%` llega a PostgreSQL como `%`.

### 3.3 `apps/accounts/tests/test_usuario.py`

```python
"""Modelo de usuario propio y hash de contraseñas (readme, secciones 2.5 y 3.2, D1)."""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password


def test_el_proyecto_usa_su_propio_modelo_de_usuario():
    usuario = get_user_model()
    assert settings.AUTH_USER_MODEL == "accounts.Usuario"
    assert usuario._meta.db_table == "usuario"
    assert usuario.groups.through._meta.db_table == "usuario_groups"


@pytest.mark.django_db
def test_la_contrasena_se_guarda_con_argon2():
    usuario = get_user_model().objects.create_user("prueba.argon", password="Prueba-larga-2026")
    assert usuario.password.startswith("argon2$")
    assert usuario.check_password("Prueba-larga-2026")


@pytest.mark.django_db
def test_acepta_los_hash_pbkdf2_del_dataset_mock():
    usuario = get_user_model().objects.create_user("prueba.mock")
    usuario.password = make_password("Prueba-mock-2026", hasher="pbkdf2_sha256")
    assert usuario.check_password("Prueba-mock-2026")


def test_contrasena_minima_de_10_caracteres():
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        validate_password("Corta-1")
```

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| `web` se conecta como `app_user` y nunca recibe la contraseña de `app_owner` | Sección 5, paso 3 |
| Todas las tablas son de `app_owner` | `test_app_owner_es_dueno_de_todas_las_tablas` |
| La migración de privilegios se revierte | Sección 5, paso 6 |
| `AUTH_USER_MODEL` definido antes del primer `migrate` | `0001_initial` de `accounts` es la primera migración aplicada (`showmigrations`) |
| Ninguna contraseña en el código | `git grep -n -i password app/config` solo muestra `os.environ` |
| Cobertura ≥ 80 % en `apps/` | `dtest --cov=apps --cov-fail-under=80` |
| Código y comentarios en español; ruff sin errores | `docker compose exec web ruff check .` |

---

## 5. Verificación: comandos y resultado esperado

Ejecútalos en orden. Copia la salida de los pasos 2, 3 y 4 en la descripción del PR.

```bash
# 1. Calidad del código
docker compose exec web ruff check . && docker compose exec web ruff format --check .
dj check                                   # System check identified no issues
dj makemigrations --check --dry-run        # No changes detected

# 2. Instalación desde cero
docker compose down -v && docker compose up -d --build && ./scripts/migrate.sh
dj showmigrations accounts
# accounts
#  [X] 0001_initial
#  [X] 0002_privilegios

# 3. La aplicación corre como app_user
dj shell -c "from django.db import connection; c = connection.cursor(); c.execute('SELECT current_user'); print(c.fetchone())"
# ('app_user',)
docker compose exec web env | grep DB_USER          # DB_USER=app_user

# 4. Dueños y permisos
dpsql -c '\dt'                                     # Owner: app_owner en todas
docker compose exec db psql -U app_user -d "$POSTGRES_DB" -c 'SELECT count(*) FROM usuario'
#  count: 0  (app_user lee)
docker compose exec db psql -U app_user -d "$POSTGRES_DB" -c 'CREATE TABLE x (id int)'
# ERROR:  permission denied for schema public

# 5. Tests y cobertura (lo mismo que el CI)
dtest -q --cov=apps --cov-fail-under=80

# 6. La migración de privilegios se revierte y se vuelve a aplicar
./scripts/migrate.sh accounts 0001
docker compose exec db psql -U app_user -d "$POSTGRES_DB" -c 'SELECT count(*) FROM usuario'
# ERROR:  permission denied for table usuario
./scripts/migrate.sh

# 7. Administrador
dj createsuperuser
```

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] La descripción del PR incluye la salida de `showmigrations`, de `current_user` y del `CREATE TABLE` rechazado.
- [ ] En el CI, `lint`, `tests` y `build de la imagen` están en verde.

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `KeyError: 'DB_NAME'` | Falta el `environment` del paso 2.2, o `DB_NAME` en el CI | Revisa `docker-compose.yml` |
| `permission denied for schema public` al migrar | Corriste `dj migrate` (como `app_user`) | Usa `./scripts/migrate.sh` |
| `password authentication failed for user "app_user"` | La contraseña de `.env` no es la del volumen | `docker compose down -v && docker compose up -d` (desarrollo) |
| `ValueError: Dependency on app with no migrations: accounts` | Falta `makemigrations accounts` | Paso 4.5 |
| `InconsistentMigrationHistory: admin.0001_initial is applied before its dependency accounts.0001_initial` | La base ya tenía migraciones del usuario por defecto de Django | `docker compose down -v`, `up -d` y `./scripts/migrate.sh` (requisitos previos) |
| `permission denied to create database` al correr `dtest` | `app_owner` sin `CREATEDB` | `DB_OWNER_CREATEDB=true` en `.env` y recrea el volumen |
| `permission denied for table ...` en la aplicación | Una tabla se creó sin pasar por `migrate.sh` o antes de `0002_privilegios` | Agrega la dependencia de `0002_privilegios` y vuelve a ejecutar `./scripts/migrate.sh` |
| `test_los_tests_corren_como_app_owner` falla con `app_user` | Corriste `pytest` sin el atajo `dtest` | Usa `dtest` (cambia `DB_USER` a `app_owner`) |
| `ModuleNotFoundError: No module named 'pruebas'` | Falta `pythonpath = ["."]` | Paso 6.1 |
