# TK-01 · Guía paso a paso: esquema de existencias, movimientos y conteos

> **Ticket:** [readme, sección 6, TK-01](../../readme.md#6-tickets-de-trabajo) · **Tipo:** base de datos · **Estimación:** 5 puntos · **Rama:** `feature/TK-01-esquema-inventario`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket y en la sección 3 del readme. Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.
>
> **Integración** (readme, sección 6, "Puntos de integración"): este ticket **provee** los puntos 1, 3, 4, 5, 7 y 8 y **consume** los puntos 11 (`Entidad.activa`, de la semana 1). No cambies un punto que provees sin avisar en el PR. La prueba conjunta de los 3 tickets está en [`integracion.md`](integracion.md).

**Resultado al terminar:** las tablas `motivo_baja`, `existencia`, `movimiento`, `conteo_fisico` y `detalle_conteo` existen con todas sus restricciones, *triggers* e índices. La aplicación se conecta como `app_user`, que no puede modificar ni borrar movimientos. El mock de la sección 3.4 carga sin errores y cuadra.

---

## 0. Antes de empezar

### 0.1 Lee primero (30 min)

| Qué | Dónde | Para qué |
|---|---|---|
| D4, D5 y Conteos físicos | readme, sección 3.2 | Columnas, tipos y reglas de cada tabla |
| DDL de restricciones | readme, sección 3.1 | Nombres exactos de cada restricción |
| Índices y *triggers* | readme, sección 3.3 | Qué índice atiende cada consulta y el SQL de los *triggers* |
| Dataset mock | readme, sección 3.4 | Datos con los que se prueba todo |
| TK-01 | readme, sección 6 | Criterios de aceptación |

### 0.2 Requisitos previos (semana 1)

Comprueba cada uno. Si alguno falla, **no empieces**: avisa al Tech Lead.

```bash
# Desde la raíz del repositorio
docker compose up -d
docker compose ps                     # db debe estar "healthy" y web "running"

docker compose exec web python manage.py showmigrations accounts catalogo entidades
# Todas las migraciones con [X]

docker compose exec web python manage.py shell -c "
from apps.entidades.models import Entidad
from apps.catalogo.models import Medicamento
print(Entidad.objects.filter(tipo='HOGAR').count())   # 1
print(Medicamento._meta.db_table)                      # medicamento
"
```

También deben existir (sección 3.1): las extensiones `pg_trgm`, `unaccent` y `btree_gist`, la función `f_unaccent`, los grupos `Solo lectura` y `Lectura y escritura`, y la propiedad `Entidad.activa`. Si `Entidad.activa` no existe, agrégala en `apps/entidades/models.py`:

```python
@property
def activa(self) -> bool:
    """El Hogar siempre está activo; un residente, solo si su estado es ACTIVO."""
    return self.tipo == self.Tipo.HOGAR or self.residente.estado == Residente.Estado.ACTIVO
```

### 0.3 Crea la rama

```bash
git switch main && git pull
git switch -c feature/TK-01-esquema-inventario
```

### 0.4 Atajos de terminal para esta guía

Pégalos en tu terminal (Git Bash o Linux) cada vez que la abras:

```bash
set -a && . ./.env && set +a      # carga las variables de .env
dj()    { docker compose exec web python manage.py "$@"; }                       # manage.py como app_user
dtest() { docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" web pytest "$@"; }
dpsql() { docker compose exec db psql -U app_owner -d "$POSTGRES_DB" "$@"; }    # psql como app_owner
```

> Los tests corren como `app_owner` porque `pytest` necesita crear la base de tests. Los tests que deben comportarse como la aplicación cambian a `app_user` con `SET LOCAL ROLE` (paso 9).

---

## 1. Archivos que vas a crear o modificar

```
AI4Devs-finalproject-vmrr/
├── .gitattributes                         # NUEVO: los .sh siempre con fin de línea LF
├── .env.example                           # MODIFICAR: contraseñas de app_owner y app_user
├── docker-compose.yml                     # MODIFICAR: monta db/init y usa app_user en web
├── db/init/01_roles.sh                    # NUEVO: crea app_owner y app_user
├── scripts/migrate.sh                     # NUEVO: migrate como app_owner
├── Makefile                               # NUEVO: atajos de desarrollo local (make help)
└── app/
    ├── conftest.py                        # MODIFICAR: fixtures datos_demo, demo y como_app_user
    ├── pruebas.py                         # NUEVO: helpers ejecutar_sql y saldo para los tests
    ├── pyproject.toml (o pytest.ini)      # MODIFICAR: marcador "lento"
    ├── config/settings/base.py            # MODIFICAR: DATABASES desde variables de entorno
    └── apps/
        ├── accounts/migrations/0002_privilegios.py     # NUEVO
        ├── inventario/
        │   ├── models.py                               # NUEVO: MotivoBaja, Existencia, Movimiento
        │   ├── migrations/0001_initial.py              # GENERADO con makemigrations
        │   ├── migrations/0002_motivos_baja.py         # NUEVO: datos semilla
        │   ├── migrations/0003_permisos_grupos.py      # NUEVO: permisos de los grupos
        │   ├── migrations/0004_sql.py                  # NUEVO: triggers, vista, fillfactor, REVOKE
        │   └── tests/test_esquema.py                   # NUEVO
        └── conteos/
            ├── models.py                               # NUEVO: ConteoFisico, DetalleConteo
            ├── migrations/0001_initial.py              # GENERADO
            ├── migrations/0002_triggers.py             # NUEVO
            └── tests/test_esquema.py                   # NUEVO
        └── accounts/tests/test_privilegios.py          # NUEVO
```

> Si la última migración de `accounts` no es `0001_initial`, la tuya será `000N_privilegios`: ajusta los números en esta guía.

---

## 2. Tareas paso a paso

Haz un commit al terminar cada paso (mensajes en español, en imperativo: `agrega modelos de inventario`).

### Paso 1. Usuarios de base de datos `app_owner` y `app_user` (≈ 1.5 h)

**1.1 Variables nuevas en `.env.example`** (y copia los valores a tu `.env`):

```dotenv
# Superusuario de PostgreSQL: solo lo usa la inicialización del contenedor db
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

**1.2 Crea `db/init/01_roles.sh`:**

```sh
#!/bin/sh
# Crea los usuarios de la aplicación (readme, sección 6, TK-01).
# PostgreSQL ejecuta este script solo al crear el volumen pgdata por primera vez.
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

**1.3 En Windows, evita los 2 errores más comunes con scripts `.sh`:**

```bash
printf '*.sh text eol=lf\n' >> .gitattributes        # sin CRLF: sh falla con "\r: not found"
git add .gitattributes db/init/01_roles.sh
git update-index --chmod=+x db/init/01_roles.sh       # permiso de ejecución dentro de Git
```

**1.4 `docker-compose.yml`:** monta el script y cambia el usuario de `web`:

```yaml
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      DB_OWNER_PASSWORD: ${DB_OWNER_PASSWORD}
      DB_APP_PASSWORD: ${DB_APP_PASSWORD}
      DB_OWNER_CREATEDB: ${DB_OWNER_CREATEDB:-false}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d:ro
  web:
    environment:
      DB_HOST: db
      DB_NAME: ${POSTGRES_DB}
      DB_USER: app_user                      # la aplicación NUNCA usa app_owner
      DB_PASSWORD: ${DB_APP_PASSWORD}
```

**1.5 `app/config/settings/base.py`:**

```python
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

**1.6 Crea `scripts/migrate.sh`** (y dale permiso de ejecución como en 1.3):

```sh
#!/bin/sh
# Ejecuta las migraciones como app_owner, el dueño de las tablas.
# La aplicación (contenedor web) se conecta como app_user.
set -eu
set -a; . ./.env; set +a
docker compose run --rm -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" \
    web python manage.py migrate "$@"
```

**1.7 Recrea la base local.** ⚠️ Borra los datos de tu base **de desarrollo**; nunca lo hagas en producción:

```bash
docker compose down -v            # -v borra el volumen pgdata
docker compose up -d
./scripts/migrate.sh              # migraciones de la semana 1, ahora como app_owner
dpsql -c '\du'                    # deben aparecer app_owner y app_user
```

**1.8 Crea el `Makefile` de la raíz.** Son atajos legibles para el desarrollo local (`make test`, `make migrate`…). Cada *target* ejecuta los mismos comandos que esta guía, así que los comandos directos siguen siendo válidos. El CI no lo usa: allí no hay `docker compose exec`.

```make
# Atajos de desarrollo local (readme, sección 1.4). El CI usa los comandos directos.
SHELL := /bin/bash
.DEFAULT_GOAL := help
-include .env
export

DC    := docker compose
OWNER := -e DB_USER=app_owner -e DB_PASSWORD=$(DB_OWNER_PASSWORD)
T ?=

.PHONY: help up down reset migrate superuser static mock test test-ci e2e lint format check-migrations shell psql openapi

help: ## Lista los comandos disponibles
	@grep -hE '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-17s %s\n", $$1, $$2}'

up: ## Levanta los contenedores
	$(DC) up -d --build
down: ## Detiene los contenedores
	$(DC) down
reset: ## Borra la base LOCAL y la recrea con las migraciones (solo desarrollo)
	$(DC) down -v && $(DC) up -d --build && ./scripts/migrate.sh
migrate: ## Aplica las migraciones como app_owner
	./scripts/migrate.sh
superuser: ## Crea el usuario Administrador
	$(DC) exec web python manage.py createsuperuser
static: ## Ejecuta collectstatic
	$(DC) exec web python manage.py collectstatic --noinput
mock: ## Carga el dataset mock (solo en una base recién migrada)
	$(DC) cp app/fixtures/mock/. db:/tmp/mock/
	$(DC) exec db sh -c 'psql -U app_owner -d "$$POSTGRES_DB" -v ON_ERROR_STOP=1 -f /tmp/mock/cargar_mock.sql'
test: ## Corre los tests (uno solo: make test T=ruta::nombre_del_test)
	$(DC) exec $(OWNER) web pytest -q $(T)
test-ci: ## Corre lo mismo que el CI en cada PR, con cobertura
	$(DC) exec $(OWNER) web pytest -m "not e2e and not lento" --cov=apps --cov-fail-under=80
e2e: ## Corre las pruebas de extremo a extremo con Playwright
	$(DC) exec $(OWNER) -e DJANGO_ALLOW_ASYNC_UNSAFE=true web pytest -m e2e e2e/ -q
lint: ## Corre ruff (sin modificar archivos)
	$(DC) exec web ruff check . && $(DC) exec web ruff format --check .
format: ## Formatea y corrige con ruff
	$(DC) exec web ruff format . && $(DC) exec web ruff check --fix .
check-migrations: ## Comprueba que no falten migraciones
	$(DC) exec web python manage.py makemigrations --check --dry-run
shell: ## Abre el shell de Django (como app_user)
	$(DC) exec web python manage.py shell
psql: ## Abre psql como app_owner
	$(DC) exec db psql -U app_owner -d "$(POSTGRES_DB)"
openapi: ## Valida el contrato OpenAPI
	npx @redocly/cli lint docs/api/openapi.yaml
```

Tres reglas para que funcione:
- **Las recetas se indentan con tabulador**, no con espacios. Si no, `make` falla con `missing separator`. Configura tu editor para no convertir tabuladores en este archivo.
- **`.env` se lee con `-include .env`.** Funciona con valores simples (`CLAVE=valor`). Las contraseñas de desarrollo no deben llevar `$`, `#` ni comillas, porque `make` los interpreta distinto que el shell.
- **En Windows, Git Bash no trae `make`.** Instálalo, por ejemplo con `winget install ezwinports.make` o `choco install make`, o trabaja desde WSL.

```bash
make help        # lista los 17 comandos con su descripción
make openapi     # 0 errores y 2 advertencias intencionales
```

### Paso 2. Migración de privilegios en `accounts` (≈ 30 min)

Crea `app/apps/accounts/migrations/0002_privilegios.py`:

```python
"""Privilegios mínimos de app_user (readme, sección 6, TK-01).

Va en una migración, y no en db/init, porque los permisos por defecto son de cada
base de datos: así también se aplican en la base de tests que crea pytest.
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

### Paso 3. Modelos de `inventario` (≈ 1.5 h)

Crea `app/apps/inventario/models.py`. Lee los comentarios: explican cada decisión.

```python
"""Existencias y movimientos (readme, sección 3.2, D4 y D5).

Los modelos no tienen lógica: solo inventario/services.py escribe en Existencia y
Movimiento (TK-02). Las reglas también viven en la base de datos (última barrera).
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.indexes import BrinIndex
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now


class MotivoBaja(models.Model):
    id = models.SmallAutoField(primary_key=True)
    clave = models.CharField(max_length=30, unique=True)
    descripcion = models.CharField(max_length=100)
    activo = models.BooleanField(db_default=True)

    class Meta:
        db_table = "motivo_baja"
        verbose_name = "motivo de baja"
        verbose_name_plural = "motivos de baja"

    def __str__(self) -> str:
        return self.descripcion


class Existencia(models.Model):
    # db_index=False: las cubren uq_existencia e ix_existencia_med_entidad (sección 3.3)
    entidad = models.ForeignKey(
        "entidades.Entidad", on_delete=models.PROTECT, related_name="existencias", db_index=False
    )
    medicamento = models.ForeignKey(
        "catalogo.Medicamento", on_delete=models.PROTECT, related_name="existencias", db_index=False
    )
    saldo = models.DecimalField(max_digits=10, decimal_places=2, db_default=Decimal("0"))
    actualizado_en = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "existencia"
        constraints = [
            models.UniqueConstraint(fields=["entidad", "medicamento"], name="uq_existencia"),
            models.CheckConstraint(condition=Q(saldo__gte=0), name="ck_existencia_saldo"),
        ]
        indexes = [
            models.Index(fields=["medicamento", "entidad"], name="ix_existencia_med_entidad"),
        ]


class Movimiento(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        BAJA = "BAJA", "Baja"

    class OrigenEntrada(models.TextChoices):
        FAMILIAR = "FAMILIAR", "Familiar"
        HOGAR = "HOGAR", "Hogar"
        OTRO = "OTRO", "Otro"

    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    medicamento = models.ForeignKey(
        "catalogo.Medicamento", on_delete=models.PROTECT, related_name="movimientos", db_index=False
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    entidad_origen = models.ForeignKey(
        "entidades.Entidad", on_delete=models.PROTECT, null=True, blank=True,
        related_name="salidas", db_index=False,
    )
    entidad_destino = models.ForeignKey(
        "entidades.Entidad", on_delete=models.PROTECT, null=True, blank=True,
        related_name="llegadas", db_index=False,
    )
    motivo_baja = models.ForeignKey(
        MotivoBaja, on_delete=models.PROTECT, null=True, blank=True, related_name="movimientos"
    )
    # null=True en textos a propósito: el CHECK por tipo distingue "no aplica" (NULL)
    origen_entrada = models.CharField(  # noqa: DJ001
        max_length=10, choices=OrigenEntrada.choices, null=True, blank=True
    )
    entregado_por = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001
    # ForeignKey + UniqueConstraint (y no OneToOneField) para conservar el nombre uq_movimiento_corrige
    corrige_a = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="correcciones", db_index=False,
    )
    nota = models.TextField(null=True, blank=True)  # noqa: DJ001
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movimientos"
    )
    fecha_hora = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "movimiento"
        constraints = [
            # Mismo CHECK que el DDL de la sección 3.1: columnas obligatorias y prohibidas por tipo
            models.CheckConstraint(
                name="ck_movimiento_por_tipo",
                condition=(
                    (
                        Q(tipo="ENTRADA", entidad_origen__isnull=True,
                          entidad_destino__isnull=False, motivo_baja__isnull=True)
                        & (Q(corrige_a__isnull=False)
                           | Q(origen_entrada__isnull=False, entregado_por__isnull=False))
                    )
                    | (
                        Q(tipo="TRANSFERENCIA", entidad_origen__isnull=False,
                          entidad_destino__isnull=False, motivo_baja__isnull=True,
                          origen_entrada__isnull=True, entregado_por__isnull=True)
                        & ~Q(entidad_origen=F("entidad_destino"))
                    )
                    | Q(tipo="BAJA", entidad_origen__isnull=False, entidad_destino__isnull=True,
                        motivo_baja__isnull=False, origen_entrada__isnull=True,
                        entregado_por__isnull=True)
                ),
            ),
            models.CheckConstraint(condition=Q(cantidad__gt=0), name="ck_movimiento_cantidad"),
            models.CheckConstraint(
                condition=Q(origen_entrada__isnull=True)
                | Q(origen_entrada__in=["FAMILIAR", "HOGAR", "OTRO"]),
                name="ck_movimiento_origen_entrada",
            ),
            models.CheckConstraint(
                condition=Q(entregado_por__isnull=True) | ~Q(entregado_por__regex=r"^\s*$"),
                name="ck_movimiento_entregado",
            ),
            models.CheckConstraint(
                condition=~Q(corrige_a=F("id")), name="ck_movimiento_no_autocorrige"
            ),
            models.UniqueConstraint(fields=["corrige_a"], name="uq_movimiento_corrige"),
        ]
        indexes = [
            models.Index(
                fields=["entidad_origen", "medicamento", "fecha_hora"],
                name="ix_movimiento_origen_med_fecha",
                condition=Q(entidad_origen__isnull=False),
            ),
            models.Index(
                fields=["entidad_destino", "medicamento", "fecha_hora"],
                name="ix_movimiento_dest_med_fecha",
                condition=Q(entidad_destino__isnull=False),
            ),
            models.Index(fields=["medicamento", "fecha_hora"], name="ix_movimiento_med_fecha"),
            BrinIndex(fields=["fecha_hora"], name="brin_movimiento_fecha"),
        ]
```

> **Cuidado con 3 errores típicos:**
> - Django 5.2 usa `CheckConstraint(condition=...)`. El parámetro antiguo `check=` está obsoleto.
> - Los nombres de índice no pueden pasar de **30 caracteres** (error `models.E034`). Usa los nombres de la sección 3.3 tal cual.
> - Si `ruff` no tiene activas las reglas `DJ`, los `# noqa: DJ001` sobran: quítalos.

### Paso 4. Genera y revisa la migración inicial (≈ 30 min)

```bash
dj makemigrations inventario          # crea 0001_initial.py
```

Abre `0001_initial.py` y agrega a mano esta dependencia, para que las tablas nazcan **después** de los permisos por defecto del paso 2:

```python
dependencies = [
    ("accounts", "0002_privilegios"),   # AGREGAR
    # ... las que generó Django (catalogo, entidades, AUTH_USER_MODEL)
]
```

Revisa el SQL que generará y compáralo con el DDL de las secciones 3.1 y 3.3:

```bash
dj sqlmigrate inventario 0001 | less
```

Debes ver `CREATE TABLE "movimiento"`, los `CHECK` con sus nombres, `uq_movimiento_corrige`, los 4 índices de `movimiento` y **ningún** índice suelto sobre `entidad_origen_id`, `entidad_destino_id` ni `medicamento_id`.

### Paso 5. Migración de datos: motivos de baja (≈ 20 min)

```bash
dj makemigrations inventario --empty --name motivos_baja
```

Reemplaza el contenido de `0002_motivos_baja.py`:

```python
from django.db import migrations

MOTIVOS = [
    ("CONSUMO", "Consumo / administración"),
    ("CADUCIDAD", "Caducidad"),
    ("MERMA", "Merma"),
    ("ROTURA", "Rotura"),
    ("DEVOLUCION_FAMILIA", "Devolución a la familia"),
    ("DEFUNCION", "Defunción"),
    ("EGRESO", "Egreso"),
    ("CORRECCION", "Corrección de un movimiento"),  # reservado: solo lo usa services.corregir
]


def crear_motivos(apps, schema_editor):
    MotivoBaja = apps.get_model("inventario", "MotivoBaja")
    for clave, descripcion in MOTIVOS:
        MotivoBaja.objects.update_or_create(clave=clave, defaults={"descripcion": descripcion})


def borrar_motivos(apps, schema_editor):
    apps.get_model("inventario", "MotivoBaja").objects.filter(
        clave__in=[clave for clave, _ in MOTIVOS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("inventario", "0001_initial")]
    operations = [migrations.RunPython(crear_motivos, borrar_motivos)]
```

### Paso 5b. Permisos de los grupos sobre los modelos nuevos (≈ 30 min)

Los grupos `Solo lectura` y `Lectura y escritura` se crearon en la semana 1, antes de que existieran estos modelos, así que todavía no tienen sus permisos. Sin este paso, la pantalla de TK-03 responde `403` a todos.

```bash
dj makemigrations inventario --empty --name permisos_grupos
```

Contenido de `0003_permisos_grupos.py` (el paso 6 pasa a ser `0004_sql.py`):

```python
from django.contrib.auth.management import create_permissions
from django.db import migrations

SOLO_LECTURA = ["view_existencia", "view_movimiento", "view_motivobaja"]
LECTURA_ESCRITURA = [*SOLO_LECTURA, "add_movimiento"]   # nunca change/delete_movimiento


def asignar_permisos(apps, schema_editor):
    # Django crea los permisos al final de migrate; aquí se fuerzan para poder asignarlos
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for grupo, codigos in [("Solo lectura", SOLO_LECTURA), ("Lectura y escritura", LECTURA_ESCRITURA)]:
        permisos = Permission.objects.filter(content_type__app_label="inventario", codename__in=codigos)
        Group.objects.get(name=grupo).permissions.add(*permisos)


def retirar_permisos(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    for grupo in apps.get_model("auth", "Group").objects.filter(
        name__in=["Solo lectura", "Lectura y escritura"]
    ):
        grupo.permissions.remove(*Permission.objects.filter(content_type__app_label="inventario"))


class Migration(migrations.Migration):
    dependencies = [("inventario", "0002_motivos_baja"), ("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(asignar_permisos, retirar_permisos)]
```

> Repite el mismo patrón en `conteos` cuando se haga TK-06 (`view_conteofisico`, `add_conteofisico`...). Si la migración de la semana 1 que crea los grupos está en otra app, agrégala a `dependencies`.

### Paso 6. Migración SQL de `inventario`: *triggers*, vista, `fillfactor` y `REVOKE` (≈ 1 h)

```bash
dj makemigrations inventario --empty --name sql
```

Contenido de `0004_sql.py`. Cada `RunSQL` lleva su reversa, para que `migrate inventario zero` funcione:

```python
from django.db import migrations

INMUTABLE = """
CREATE FUNCTION fn_movimiento_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Los movimientos son inmutables: registre un movimiento de corrección';
END $$;
CREATE TRIGGER tg_movimiento_inmutable BEFORE UPDATE OR DELETE ON movimiento
    FOR EACH ROW EXECUTE FUNCTION fn_movimiento_inmutable();
"""

VALIDAR_DESTINO = """
CREATE FUNCTION fn_movimiento_validar_destino() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.entidad_destino_id IS NOT NULL AND NEW.corrige_a_id IS NULL THEN
        IF NOT (SELECT activo FROM medicamento WHERE id = NEW.medicamento_id) THEN
            RAISE EXCEPTION 'El medicamento % está dado de baja', NEW.medicamento_id;
        END IF;
        IF EXISTS (SELECT 1 FROM residente
                   WHERE entidad_id = NEW.entidad_destino_id AND estado <> 'ACTIVO') THEN
            RAISE EXCEPTION 'La entidad destino % no está activa', NEW.entidad_destino_id;
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_movimiento_validar_destino BEFORE INSERT ON movimiento
    FOR EACH ROW EXECUTE FUNCTION fn_movimiento_validar_destino();
"""

CONCILIACION = """
CREATE VIEW v_conciliacion_existencia AS
WITH suma AS (
    SELECT entidad_destino_id AS entidad_id, medicamento_id, cantidad FROM movimiento
     WHERE entidad_destino_id IS NOT NULL
    UNION ALL
    SELECT entidad_origen_id, medicamento_id, -cantidad FROM movimiento
     WHERE entidad_origen_id IS NOT NULL
)
SELECT coalesce(e.entidad_id, s.entidad_id)         AS entidad_id,
       coalesce(e.medicamento_id, s.medicamento_id) AS medicamento_id,
       coalesce(e.saldo, 0)                         AS saldo,
       coalesce(s.total, 0)                         AS suma_movimientos
FROM existencia e
FULL JOIN (SELECT entidad_id, medicamento_id, sum(cantidad) AS total
           FROM suma GROUP BY 1, 2) s
  ON s.entidad_id = e.entidad_id AND s.medicamento_id = e.medicamento_id
WHERE coalesce(e.saldo, 0) <> coalesce(s.total, 0);
"""


class Migration(migrations.Migration):
    dependencies = [("inventario", "0003_permisos_grupos")]
    operations = [
        migrations.RunSQL(
            INMUTABLE,
            "DROP TRIGGER tg_movimiento_inmutable ON movimiento;"
            "DROP FUNCTION fn_movimiento_inmutable();",
        ),
        migrations.RunSQL(
            VALIDAR_DESTINO,
            "DROP TRIGGER tg_movimiento_validar_destino ON movimiento;"
            "DROP FUNCTION fn_movimiento_validar_destino();",
        ),
        migrations.RunSQL(
            "ALTER TABLE existencia SET (fillfactor = 90);",
            "ALTER TABLE existencia RESET (fillfactor);",
        ),
        migrations.RunSQL(CONCILIACION, "DROP VIEW v_conciliacion_existencia;"),
        # Doble barrera de la inmutabilidad: además del trigger, app_user no tiene el permiso
        migrations.RunSQL(
            "REVOKE UPDATE, DELETE, TRUNCATE ON movimiento FROM app_user;",
            "GRANT UPDATE, DELETE ON movimiento TO app_user;",
        ),
    ]
```

### Paso 7. Modelos y migraciones de `conteos` (≈ 1 h)

`app/apps/conteos/models.py`:

```python
"""Conteos físicos (readme, sección 3.2, "Conteos físicos"; mecánica en HU-03)."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now


class ConteoFisico(models.Model):
    class Estado(models.TextChoices):
        EN_PROCESO = "EN_PROCESO", "En proceso"
        CERRADO = "CERRADO", "Cerrado"

    entidad = models.ForeignKey(
        "entidades.Entidad", on_delete=models.PROTECT, related_name="conteos", db_index=False
    )
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    estado = models.CharField(max_length=10, choices=Estado.choices, db_default="EN_PROCESO")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="conteos"
    )
    creado_en = models.DateTimeField(db_default=Now())
    cerrado_en = models.DateTimeField(null=True, blank=True)
    nota = models.TextField(null=True, blank=True)  # noqa: DJ001

    class Meta:
        db_table = "conteo_fisico"
        constraints = [
            models.CheckConstraint(
                condition=Q(periodo_fin__gte=F("periodo_inicio")), name="ck_conteo_periodo"
            ),
            models.CheckConstraint(
                condition=Q(estado__in=["EN_PROCESO", "CERRADO"]), name="ck_conteo_estado"
            ),
            # cerrado_en es obligatoria si y solo si el conteo está CERRADO
            models.CheckConstraint(
                condition=Q(estado="CERRADO", cerrado_en__isnull=False)
                | Q(estado="EN_PROCESO", cerrado_en__isnull=True),
                name="ck_conteo_cierre",
            ),
        ]
        indexes = [
            models.Index(fields=["entidad", "-periodo_fin"], name="ix_conteo_entidad_periodo"),
        ]


class DetalleConteo(models.Model):
    conteo = models.ForeignKey(
        ConteoFisico, on_delete=models.PROTECT, related_name="detalles", db_index=False
    )
    medicamento = models.ForeignKey(
        "catalogo.Medicamento", on_delete=models.PROTECT,
        related_name="detalles_conteo", db_index=False,
    )
    cantidad_fisica = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_sistema = models.DecimalField(max_digits=10, decimal_places=2)  # foto del saldo
    # La calcula PostgreSQL: nunca se escribe a mano
    diferencia = models.GeneratedField(
        expression=F("cantidad_fisica") - F("cantidad_sistema"),
        output_field=models.DecimalField(max_digits=10, decimal_places=2),
        db_persist=True,
    )

    class Meta:
        db_table = "detalle_conteo"
        constraints = [
            models.UniqueConstraint(fields=["conteo", "medicamento"], name="uq_detalle_conteo"),
            models.CheckConstraint(condition=Q(cantidad_fisica__gte=0), name="ck_detalle_fisica"),
            models.CheckConstraint(condition=Q(cantidad_sistema__gte=0), name="ck_detalle_sistema"),
        ]
        indexes = [
            models.Index(
                fields=["medicamento", "conteo"],
                name="ix_detalle_medicamento_conteo",
                include=["cantidad_fisica", "cantidad_sistema", "diferencia"],
            ),
            models.Index(
                fields=["medicamento"], name="ix_detalle_con_diferencia",
                condition=~Q(diferencia=0),
            ),
        ]
```

```bash
dj makemigrations conteos             # 0001_initial.py: agrega ("accounts", "0002_privilegios") a dependencies
dj makemigrations conteos --empty --name triggers
```

`0002_triggers.py`: copia de la sección 3.3 las funciones `fn_conteo_cerrado` y `fn_detalle_conteo_cerrado` con sus *triggers*, igual que en el paso 6:

```python
from django.db import migrations

CONTEO_CERRADO = """
CREATE FUNCTION fn_conteo_cerrado() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.estado = 'CERRADO' THEN
        RAISE EXCEPTION 'El conteo % está cerrado y no se puede modificar', OLD.id;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_conteo_cerrado BEFORE UPDATE OR DELETE ON conteo_fisico
    FOR EACH ROW EXECUTE FUNCTION fn_conteo_cerrado();
"""

DETALLE_CERRADO = """
CREATE FUNCTION fn_detalle_conteo_cerrado() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_conteo bigint;
BEGIN
    IF TG_OP = 'DELETE' THEN v_conteo := OLD.conteo_id; ELSE v_conteo := NEW.conteo_id; END IF;
    IF (SELECT estado FROM conteo_fisico WHERE id = v_conteo) = 'CERRADO' THEN
        RAISE EXCEPTION 'El conteo % está cerrado', v_conteo;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_detalle_conteo_cerrado BEFORE INSERT OR UPDATE OR DELETE ON detalle_conteo
    FOR EACH ROW EXECUTE FUNCTION fn_detalle_conteo_cerrado();
"""


class Migration(migrations.Migration):
    dependencies = [("conteos", "0001_initial")]
    operations = [
        migrations.RunSQL(
            CONTEO_CERRADO,
            "DROP TRIGGER tg_conteo_cerrado ON conteo_fisico; DROP FUNCTION fn_conteo_cerrado();",
        ),
        migrations.RunSQL(
            DETALLE_CERRADO,
            "DROP TRIGGER tg_detalle_conteo_cerrado ON detalle_conteo;"
            "DROP FUNCTION fn_detalle_conteo_cerrado();",
        ),
    ]
```

### Paso 8. Aplica todo y carga el mock (≈ 20 min)

```bash
./scripts/migrate.sh
docker compose cp app/fixtures/mock/. db:/tmp/mock/
dpsql -v ON_ERROR_STOP=1 -f /tmp/mock/cargar_mock.sql
```

La última consulta del script muestra el resumen. Debe decir: 2 usuarios, 13 principios activos, 15 medicamentos, 3 residentes, 3 pautas, 28 movimientos, 13 existencias, 2 conteos y 5 detalles de conteo.

### Paso 9. Fixtures de pytest para el mock y para SQL directo (≈ 45 min)

Agrega a `app/conftest.py`. Estos fixtures son un **punto de integración**: TK-02 y TK-03 los usan tal cual, así que no cambies sus nombres ni lo que devuelven sin avisar.

```python
import json
from pathlib import Path

import pytest
from django.conf import settings
from django.db import connection

RUTA_MOCK = Path(settings.BASE_DIR) / "fixtures" / "mock"


def _sql_del_mock() -> str:
    """Adapta cargar_mock.sql (escrito para psql) para ejecutarlo desde Django.

    - Quita los metacomandos de psql (líneas que empiezan con "\\").
    - Quita BEGIN/COMMIT: cada test ya corre dentro de una transacción.
    - Escapa los "%" y convierte :'mock_json' en un parámetro.
    """
    lineas = (RUTA_MOCK / "cargar_mock.sql").read_text(encoding="utf-8").splitlines()
    lineas = [
        linea for linea in lineas
        if not linea.startswith("\\") and linea.strip() not in ("BEGIN;", "COMMIT;")
    ]
    sql = "\n".join(lineas).replace("%", "%%")
    return sql.replace(":'mock_json'", "%(mock_json)s")


@pytest.fixture
def datos_demo(db):
    """Carga el dataset mock de la sección 3.4 con sus validaciones."""
    json_texto = (RUTA_MOCK / "demo.json").read_text(encoding="utf-8")
    json.loads(json_texto)  # falla rápido si el JSON está roto
    with connection.cursor() as cursor:
        cursor.execute(_sql_del_mock(), {"mock_json": json_texto})


@pytest.fixture
def demo(datos_demo):
    """Accesos cómodos a los datos del mock: demo.carmen, demo.med["Eutirox"]...

    Lo usan los tests de TK-02 y TK-03: por eso vive aquí y no en esos tickets.
    """
    from types import SimpleNamespace

    from apps.accounts.models import Usuario
    from apps.catalogo.models import Medicamento
    from apps.entidades.models import Entidad
    from apps.inventario.models import MotivoBaja

    return SimpleNamespace(
        hogar=Entidad.objects.get(tipo="HOGAR"),
        maria=Entidad.objects.get(pk=101),
        jose=Entidad.objects.get(pk=102),
        carmen=Entidad.objects.get(pk=103),
        operador=Usuario.objects.get(username="operador.demo"),
        med={m.nombre_comercial: m for m in Medicamento.objects.all()},
        motivo={m.clave: m for m in MotivoBaja.objects.all()},
    )


@pytest.fixture
def como_app_user(demo):
    """El resto del test corre como app_user, igual que la aplicación en producción."""
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL ROLE app_user")
    return demo
```

Crea `app/pruebas.py` con el helper para ejecutar SQL directo. Va en un módulo propio porque importar desde `conftest.py` es mala práctica en pytest:

```python
"""Utilidades compartidas por los tests."""

from django.db import connection, transaction


def ejecutar_sql(sql: str, params=None, *, rol: str | None = None) -> list[tuple]:
    """Ejecuta SQL dentro de un savepoint, opcionalmente como otro rol.

    Si la sentencia falla, solo se revierte el savepoint y el test puede seguir.
    """
    with transaction.atomic(), connection.cursor() as cursor:
        if rol:
            cursor.execute(f"SET LOCAL ROLE {rol}")
        cursor.execute(sql, params)
        filas = cursor.fetchall() if cursor.description else []
        if rol:
            cursor.execute("RESET ROLE")
        return filas


def saldo(entidad, medicamento):
    """Saldo actual de una entidad y un medicamento (lo usan los tests de TK-02 y TK-03)."""
    from apps.inventario.models import Existencia

    return Existencia.objects.get(entidad=entidad, medicamento=medicamento).saldo
```

En `pyproject.toml` (o `pytest.ini`) registra el marcador de los tests lentos y agrega `app/` a la ruta de importación, para que los tests puedan hacer `from pruebas import ejecutar_sql`:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
markers = ["lento: tests de plan de ejecución, corren en el CI nocturno"]
```

### Paso 10. Tests (≈ 2 h)

Ver la sección 3 de esta guía. Escríbelos y ejecútalos hasta que pasen todos.

### Paso 11. Verificación final y *pull request* (≈ 1 h)

Ejecuta **todos** los comandos de la sección 5, marca la lista del PR (sección 6) y abre el PR hacia `main`.

---

## 3. Tests requeridos

### 3.1 `apps/inventario/tests/test_esquema.py`: cada regla rechaza su caso inválido

```python
"""La base de datos rechaza lo que las reglas de negocio prohíben (TK-01)."""

import pytest
from django.contrib import admin
from django.db import DatabaseError

from apps.conteos.models import ConteoFisico, DetalleConteo
from apps.inventario.models import Existencia, Movimiento
from pruebas import ejecutar_sql

USUARIO = "(SELECT id FROM usuario WHERE username = 'operador.demo')"
CORRECCION = "(SELECT id FROM motivo_baja WHERE clave = 'CORRECCION')"


def insertar_movimiento(**campos) -> tuple[str, list]:
    """INSERT válido (entrada de 10 Metformina a María) con los campos que cambie el test."""
    valores = {
        "tipo": "ENTRADA", "medicamento_id": 1, "cantidad": 10,
        "entidad_origen_id": None, "entidad_destino_id": 101, "motivo_baja_id": None,
        "origen_entrada": "FAMILIAR", "entregado_por": "Rosa Torres",
    } | campos
    columnas = ", ".join(valores)
    marcadores = ", ".join(["%s"] * len(valores))
    sql = f"INSERT INTO movimiento ({columnas}, usuario_id) SELECT {marcadores}, {USUARIO}"
    return sql, list(valores.values())


SIN_ENTRADA = {"origen_entrada": None, "entregado_por": None}

CASOS = [
    pytest.param("UPDATE movimiento SET cantidad = 1 WHERE id = 1", None,
                 "inmutables", id="update-movimiento"),
    pytest.param("DELETE FROM movimiento WHERE id = 1", None,
                 "inmutables", id="delete-movimiento"),
    pytest.param(*insertar_movimiento(entidad_destino_id=None),
                 "ck_movimiento_por_tipo", id="entrada-sin-destino"),
    pytest.param(*insertar_movimiento(tipo="BAJA", entidad_origen_id=101,
                                      entidad_destino_id=None, **SIN_ENTRADA),
                 "ck_movimiento_por_tipo", id="baja-sin-motivo"),
    pytest.param(*insertar_movimiento(tipo="TRANSFERENCIA", entidad_origen_id=1,
                                      entidad_destino_id=1, **SIN_ENTRADA),
                 "ck_movimiento_por_tipo", id="transferencia-misma-entidad"),
    pytest.param(*insertar_movimiento(cantidad=0),
                 "ck_movimiento_cantidad", id="cantidad-cero"),
    pytest.param(
        f"""INSERT INTO movimiento (tipo, medicamento_id, cantidad, entidad_origen_id,
                                    motivo_baja_id, corrige_a_id, usuario_id)
            SELECT 'BAJA', medicamento_id, 1, 101, {CORRECCION}, corrige_a_id, {USUARIO}
            FROM movimiento WHERE corrige_a_id IS NOT NULL LIMIT 1""",
        None, "uq_movimiento_corrige", id="segunda-correccion"),
    pytest.param("UPDATE existencia SET saldo = -1 WHERE id = (SELECT min(id) FROM existencia)",
                 None, "ck_existencia_saldo", id="saldo-negativo"),
    pytest.param("INSERT INTO detalle_conteo (conteo_id, medicamento_id, cantidad_fisica, "
                 "cantidad_sistema) VALUES (1, 6, 1, 1)",
                 None, "está cerrado", id="renglon-en-conteo-cerrado"),
    pytest.param("UPDATE detalle_conteo SET diferencia = 0", None,
                 "diferencia", id="columna-generada"),
]


@pytest.mark.parametrize(("sql", "params", "mensaje"), CASOS)
def test_la_base_rechaza(datos_demo, sql, params, mensaje):
    with pytest.raises(DatabaseError, match=mensaje):
        ejecutar_sql(sql, params)


def test_no_entra_medicamento_a_residente_egresado(datos_demo):
    ejecutar_sql("UPDATE residente SET estado = 'EGRESADO', fecha_baja = '2026-10-16' "
                 "WHERE entidad_id = 103")
    with pytest.raises(DatabaseError, match="no está activa"):
        ejecutar_sql(*insertar_movimiento(entidad_destino_id=103))


def test_el_mock_cuadra(datos_demo):
    assert ejecutar_sql("SELECT count(*) FROM v_conciliacion_existencia") == [(0,)]


def test_la_conciliacion_detecta_un_saldo_que_no_cuadra(datos_demo):
    ejecutar_sql("UPDATE existencia SET saldo = saldo + 1 WHERE id = (SELECT min(id) FROM existencia)")
    assert ejecutar_sql("SELECT count(*) FROM v_conciliacion_existencia") == [(1,)]


@pytest.mark.parametrize("modelo", [Movimiento, Existencia, ConteoFisico, DetalleConteo])
def test_el_modelo_no_esta_en_el_admin(modelo):
    assert not admin.site.is_registered(modelo)


@pytest.mark.lento
def test_los_movimientos_de_un_periodo_usan_indice(datos_demo):
    # Con pocos datos PostgreSQL prefiere leer la tabla completa; esto comprueba
    # que el índice SÍ sirve para la consulta 2c de la sección 3.3.
    ejecutar_sql("SET LOCAL enable_seqscan = off")
    plan = ejecutar_sql("""
        EXPLAIN SELECT tipo, cantidad, fecha_hora FROM movimiento
        WHERE entidad_destino_id = 101 AND medicamento_id = 1
          AND fecha_hora >= '2026-09-01' AND fecha_hora < '2026-10-01'""")
    assert "ix_movimiento_dest_med_fecha" in "\n".join(fila[0] for fila in plan)
```

> **Si un caso falla con otro mensaje:** imprime el error real con `pytest -k nombre-del-caso -x --tb=long`. El texto de `match` es una expresión regular que busca dentro del mensaje de PostgreSQL.

### 3.2 `apps/accounts/tests/test_privilegios.py`: la aplicación no puede reescribir el historial

```python
"""app_user tiene privilegios mínimos (readme, sección 2.5 y TK-01)."""

import pytest
from django.db import DatabaseError

from pruebas import ejecutar_sql


def test_app_user_solo_lee_e_inserta_movimientos(db):
    filas = ejecutar_sql(
        "SELECT p, has_table_privilege('app_user', 'movimiento', p) "
        "FROM unnest(ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE']) AS p"
    )
    assert dict(filas) == {
        "SELECT": True, "INSERT": True, "UPDATE": False, "DELETE": False, "TRUNCATE": False,
    }


def test_app_owner_es_dueno_de_todas_las_tablas(db):
    ajenas = ejecutar_sql(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner <> 'app_owner'"
    )
    assert ajenas == []


def test_app_user_tiene_los_4_permisos_en_las_demas_tablas(db):
    sin_permiso = ejecutar_sql("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public' AND tablename <> 'movimiento'
          AND NOT (has_table_privilege('app_user', format('public.%%I', tablename), 'SELECT')
               AND has_table_privilege('app_user', format('public.%%I', tablename), 'INSERT')
               AND has_table_privilege('app_user', format('public.%%I', tablename), 'UPDATE')
               AND has_table_privilege('app_user', format('public.%%I', tablename), 'DELETE'))""")
    assert sin_permiso == []


@pytest.mark.parametrize(("sql", "mensaje"), [
    ("UPDATE movimiento SET nota = 'x'", "permission denied"),
    ("DELETE FROM movimiento", "permission denied"),
    ("TRUNCATE movimiento", "permission denied"),
    ("ALTER TABLE movimiento DISABLE TRIGGER ALL", "must be owner"),
])
def test_app_user_no_puede_modificar_el_historial(datos_demo, sql, mensaje):
    with pytest.raises(DatabaseError, match=mensaje):
        ejecutar_sql(sql, rol="app_user")


def test_app_user_si_puede_registrar_un_movimiento(datos_demo):
    ejecutar_sql(
        "INSERT INTO movimiento (tipo, medicamento_id, cantidad, entidad_destino_id, "
        "origen_entrada, entregado_por, usuario_id) "
        "SELECT 'ENTRADA', 8, 30, 103, 'FAMILIAR', 'Rosa Torres', id "
        "FROM usuario WHERE username = 'operador.demo'",
        rol="app_user",
    )
```

> `%%I` lleva doble `%` porque el SQL pasa por los parámetros de Django: `%%` llega a PostgreSQL como `%`.

### 3.3 `apps/conteos/tests/test_esquema.py`

Con la misma estructura que 3.1, cubre:

| Test | Resultado esperado |
|---|---|
| `INSERT` en `conteo_fisico` con `periodo_fin` < `periodo_inicio` | `ck_conteo_periodo` |
| `UPDATE conteo_fisico SET estado = 'CERRADO' WHERE id = 2` sin `cerrado_en` | `ck_conteo_cierre` |
| `UPDATE conteo_fisico SET nota = 'x' WHERE id = 1` (cerrado) | "está cerrado y no se puede modificar" |
| `INSERT` de un segundo renglón de Omeprazol (medicamento 5) en el conteo 2 | `uq_detalle_conteo` |
| `SELECT diferencia FROM detalle_conteo WHERE conteo_id = 2 AND medicamento_id = 5` | `-1.00` |
| Capturar Losartán (medicamento 2, pendiente en el conteo 2) con 18 físicas y 20 registradas | `diferencia = -2` (caso de la sección 2.6) |

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| Los nombres de tablas, restricciones, índices y *triggers* son **idénticos** a las secciones 3.1 y 3.3 | `\d movimiento` en `psql` comparado con el readme |
| Ningún nombre de índice pasa de 30 caracteres | `dj check` sin errores |
| Toda migración se puede revertir | `migrate ... zero` sin errores (sección 5) |
| Sin índices duplicados sobre las FK | Tabla "Índices de FK que Django no debe crear" de la sección 3.3 |
| `app_user` nunca es dueño de nada ni tiene `UPDATE`/`DELETE` en `movimiento` | `test_privilegios.py` |
| Las cantidades son `numeric(10,2)`, nunca `float` | Revisión del PR |
| Sin lógica de negocio en los modelos (sin `save()` ni señales) | Revisión del PR |
| Comentarios y nombres en español, como el resto del proyecto | Revisión del PR |
| Ni contraseñas ni `.env` en el repositorio; solo `.env.example` con valores de ejemplo | `git status` antes del commit |

---

## 5. Verificación: comandos y resultado esperado

Ejecútalos en orden. Copia la salida de los pasos 3, 5 y 7 en la descripción del PR.

```bash
# 1. Calidad del código
docker compose exec web ruff check . && docker compose exec web ruff format --check .
dj check                                   # System check identified no issues
dj makemigrations --check --dry-run        # No changes detected

# 2. Tests del ticket
dtest apps/inventario apps/conteos apps/accounts -q
dtest -m lento apps/inventario -q

# 3. Esquema aplicado: compara contra las secciones 3.1 y 3.3
dpsql -c '\d movimiento'
dpsql -c '\d detalle_conteo'

# 4. Las migraciones se revierten y se vuelven a aplicar (base de desarrollo)
./scripts/migrate.sh conteos zero
./scripts/migrate.sh inventario zero
./scripts/migrate.sh

# 5. Instalación desde cero + mock + conciliación
docker compose down -v && docker compose up -d && ./scripts/migrate.sh
docker compose cp app/fixtures/mock/. db:/tmp/mock/
dpsql -v ON_ERROR_STOP=1 -f /tmp/mock/cargar_mock.sql
dpsql -c 'SELECT count(*) FROM v_conciliacion_existencia'          # 0

# 6. La aplicación corre como app_user
docker compose exec web python manage.py shell -c \
  "from django.db import connection; c = connection.cursor(); c.execute('SELECT current_user'); print(c.fetchone())"
# ('app_user',)
docker compose exec db psql -U app_user -d "$POSTGRES_DB" -c 'DELETE FROM movimiento WHERE id = 1'
# ERROR:  permission denied for table movimiento

# 7. Rendimiento con un año de datos sintéticos (solo en desarrollo)
dpsql -c "
INSERT INTO movimiento (tipo, medicamento_id, cantidad, entidad_origen_id, motivo_baja_id, usuario_id, fecha_hora)
SELECT 'BAJA', 1 + (g % 15), 0.01, 1, (SELECT id FROM motivo_baja WHERE clave = 'CONSUMO'),
       (SELECT id FROM usuario WHERE username = 'operador.demo'),
       timestamptz '2025-01-01' + g * interval '3 minutes'
FROM generate_series(1, 175000) g;"
dpsql -c 'ANALYZE movimiento'
dpsql -c "EXPLAIN (ANALYZE, BUFFERS) SELECT tipo, cantidad, fecha_hora FROM movimiento
          WHERE entidad_origen_id = 1 AND medicamento_id = 6
            AND fecha_hora >= '2025-03-01' AND fecha_hora < '2025-04-01'"
# Debe decir "Index Scan using ix_movimiento_origen_med_fecha" (o Bitmap), nunca "Seq Scan on movimiento"
docker compose down -v && docker compose up -d && ./scripts/migrate.sh   # deja la base limpia
```

> El paso 7 inserta bajas sin descontar existencias: por eso después se recrea la base. Es solo para medir el plan de ejecución.

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] La descripción del PR incluye: qué cambia, cómo probarlo (sección 5), la salida de `\d movimiento` y del conteo de la conciliación.
- [ ] El readme está actualizado si algún nombre o tipo cambió respecto de la sección 3.

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `sh: 01_roles.sh: not found` o `\r: not found` al levantar `db` | El script tiene fines de línea CRLF (Windows) | Paso 1.3 y `docker compose down -v` |
| El script de roles no se ejecutó | El volumen `pgdata` ya existía | `docker compose down -v` (desarrollo) o ejecútalo a mano: `docker compose exec db sh /docker-entrypoint-initdb.d/01_roles.sh` |
| `permission denied to create database` al correr `pytest` | `app_owner` sin `CREATEDB` | `DB_OWNER_CREATEDB=true` en `.env` y recrea el volumen |
| `permission denied for table ...` en la aplicación | Una tabla se creó antes de la migración de privilegios | Revisa la dependencia agregada en el paso 4 y vuelve a ejecutar `./scripts/migrate.sh` |
| `models.E034: The index name ... cannot be longer than 30 characters` | Nombre de índice largo | Usa los nombres de la sección 3.3 |
| `TypeError: ... unexpected keyword argument 'condition'` | Django menor a 5.1 | Verifica `requirements.txt`: Django 5.2 LTS |
| `function f_unaccent does not exist` al cargar el mock | Falta la migración de la semana 1 que crea la función | Requisitos previos, paso 0.2 |
| El mock falla con "La base ya tiene datos de negocio" | Ya lo cargaste antes | `docker compose down -v`, `up -d`, `./scripts/migrate.sh` y vuelve a cargarlo |
