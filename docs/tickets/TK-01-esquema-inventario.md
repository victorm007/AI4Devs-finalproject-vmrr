# TK-01 · Guía paso a paso: esquema de existencias, movimientos y conteos

> **Ticket:** [readme, sección 6, TK-01](../../readme.md#6-tickets-de-trabajo) · **Tipo:** base de datos · **Estimación:** 5 puntos · **Rama:** `feature/TK-01-esquema-inventario`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket y en la sección 3 del readme. Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.
>
> **Integración** (readme, sección 6, "Puntos de integración"): este ticket **provee** los puntos 1, 3, 4, 5, 7 y 8 y **consume** el punto 11 (`Entidad.activa`, de HB-06). No cambies un punto que provees sin avisar en el PR. La prueba conjunta de los 3 tickets está en [`integracion.md`](integracion.md).

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

### 0.2 Requisitos previos (tickets de habilitación HB-01 a HB-08)

Comprueba cada uno. Si alguno falla, **no empieces**: avisa al Tech Lead.

```bash
# Desde la raíz del repositorio
docker compose up -d
docker compose ps                     # db "healthy", web y nginx "running"

docker compose exec web python manage.py showmigrations accounts catalogo entidades pautas
# Todas las migraciones con [X], incluidas accounts 0002_privilegios y 0003_grupos

docker compose exec web python manage.py shell -c "
from django.db import connection
from apps.entidades.models import Entidad
c = connection.cursor(); c.execute('SELECT current_user'); print(c.fetchone())   # ('app_user',)
print(Entidad.objects.get(tipo='HOGAR').activa)                                 # True
"
docker compose exec db sh -c 'psql -U app_owner -d "$POSTGRES_DB" -c "\du"'   # app_owner y app_user
```

También deben existir: las extensiones `pg_trgm`, `unaccent` y `btree_gist` y la función `f_unaccent` (HB-05), la tabla `pauta` (HB-07), los grupos `Solo lectura` y `Lectura y escritura` (HB-08), `scripts/migrate.sh`, `app/conftest.py` y `app/pruebas.py` con `ejecutar_sql` (HB-03).

### 0.3 Crea la rama

```bash
git switch main && git pull
git switch -c feature/TK-01-esquema-inventario
```

### 0.4 Atajos de terminal para esta guía

Pégalos en tu terminal (Git Bash o Linux) cada vez que la abras:

```bash
while IFS= read -r linea || [ -n "$linea" ]; do case $linea in ''|'#'*) ;; *) export "$linea" ;; esac; done < .env  # carga las variables de .env
dj()    { docker compose exec web python manage.py "$@"; }                       # manage.py como app_user
dtest() { docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" web pytest "$@"; }
dpsql() { docker compose exec db psql -U app_owner -d "$POSTGRES_DB" "$@"; }    # psql como app_owner
```

> Los tests corren como `app_owner` porque `pytest` necesita crear la base de tests. Los tests que deben comportarse como la aplicación cambian a `app_user` con `SET LOCAL ROLE` (paso 3).

---

## 1. Archivos que vas a crear o modificar

```
AI4Devs-finalproject-vmrr/
├── Makefile                               # NUEVO: atajos de desarrollo local (make help)
├── .env.example                           # MODIFICAR (de HB-06): descomenta HOGAR_NOMBRE
├── scripts/migrate.sh                     # MODIFICAR (de HB-03): lee .env sin ". ./.env"
└── app/
    ├── conftest.py                        # MODIFICAR (de HB-03): fixtures datos_demo, demo y como_app_user
    ├── pruebas.py                         # MODIFICAR (de HB-03): agrega el helper saldo
    ├── config/settings/base.py            # MODIFICAR: "apps.inventario" y "apps.conteos"
    └── apps/
        ├── catalogo/admin.py                           # MODIFICAR (de HB-09): baja con existencias
        ├── inventario/
        │   ├── models.py                               # NUEVO: MotivoBaja, Existencia, Movimiento
        │   ├── migrations/0001_initial.py              # GENERADO con makemigrations
        │   ├── migrations/0002_motivos_baja.py         # NUEVO: datos semilla
        │   ├── migrations/0003_permisos_grupos.py      # NUEVO: permisos de los grupos
        │   ├── migrations/0004_sql.py                  # NUEVO: triggers, vista, fillfactor, REVOKE
        │   ├── migrations/0005_fk_sin_indice.py        # GENERADO (segunda revisión): FK sin índice
        │   └── tests/test_esquema.py                   # NUEVO
        └── conteos/
            ├── models.py                               # NUEVO: ConteoFisico, DetalleConteo
            ├── migrations/0001_initial.py              # GENERADO
            ├── migrations/0002_triggers.py             # NUEVO
            ├── migrations/0003_detalle_conteo_cerrado.py  # NUEVO (revisión): mira OLD y NEW
            ├── migrations/0004_fk_sin_indice.py        # GENERADO (segunda revisión): FK sin índice
            ├── migrations/0005_detalle_conteo_bloqueo.py  # NUEVO (segunda revisión): FOR SHARE
            └── tests/test_esquema.py                   # NUEVO
        └── accounts/tests/test_privilegios.py          # MODIFICAR (de HB-03): tests de movimiento
```

> Los 2 usuarios de base de datos, `migrate.sh`, `DATABASES` y la migración `accounts/0002_privilegios` ya existen: los crearon HB-01 y HB-03.

---

## 2. Tareas paso a paso

Haz un commit al terminar cada paso (mensajes en español, en imperativo: `agrega modelos de inventario`). El orden sigue TDD (`CLAUDE.md`): primero los *fixtures* y los tests en rojo, después la implementación.

### Paso 1. Comprueba la base de habilitación y crea el `Makefile` (≈ 45 min)

Los 2 usuarios de base de datos (`db/init/01_roles.sh`), la conexión como `app_user`, `scripts/migrate.sh` y los privilegios por defecto de `app_user` (`accounts/0002_privilegios`) **ya existen**: los crearon HB-01 y HB-03. Antes de crear tablas, confirma que tu base local está al día:

```bash
./scripts/migrate.sh                                  # aplica lo que falte de HB-03 a HB-08
dpsql -c '\du'                                        # app_owner (Create DB) y app_user
dj shell -c "from django.db import connection; c = connection.cursor(); c.execute('SELECT current_user'); print(c.fetchone())"
# ('app_user',)
```

**Crea el `Makefile` de la raíz.** Son atajos legibles para el desarrollo local (`make test`, `make migrate`…). Cada *target* ejecuta los mismos comandos que esta guía, así que los comandos directos siguen siendo válidos. El CI no lo usa: allí no hay `docker compose exec`.

```make
# Atajos de desarrollo local (readme, sección 1.4). El CI usa los comandos directos.
# Las recetas van indentadas con tabulador. .env se lee con -include: sus valores no
# deben llevar $, # ni comillas, porque make los interpreta distinto que el shell.
SHELL := /bin/bash
.DEFAULT_GOAL := help
-include .env
# Sin "export": las recetas usan los valores con $(...) y docker compose lee .env por su
# cuenta. Exportarlos haría que compose prefiriera la copia de make, que en Windows (GNU Make
# de GnuWin32) cambia la codificación de los acentos: "Gerontológico" llegaba a web como
# "GerontolÃ³gico". También evita pasar las contraseñas a cada proceso hijo.

DC    := docker compose
# La contraseña de app_owner la lee el shell al ejecutar la receta, no make: así ni el eco de
# la receta, ni make -n, ni --trace la muestran (solo la expresión). Manda DB_OWNER_PASSWORD del
# entorno si está definida, como en HB-10; si no, la primera línea de .env que la define (head),
# sin el \r de un .env con fin de línea CRLF (tr). Con :=, $$ queda como $ y make no la expande.
# La receta la pone en el entorno de docker compose, entre comillas para un valor con espacios,
# y -e DB_PASSWORD sin valor la copia de ahí: no va en sus argumentos ni aparece en ps. make -p
# sí imprime los valores de .env, porque se incluye arriba para el candado de HB-10: límite
# aceptado (pendiente de HB-10).
CLAVE_OWNER := $${DB_OWNER_PASSWORD-$$(sed -n 's/^DB_OWNER_PASSWORD=//p' .env | head -n 1 | tr -d '\r')}
OWNER := -e DB_USER=app_owner -e DB_PASSWORD
T ?=

.PHONY: help up down reset actualizar migrate superuser static mock test test-ci e2e lint format check-migrations shell psql openapi

help: ## Lista los comandos disponibles
	@grep -hE '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-17s %s\n", $$1, $$2}'

up: ## Levanta los contenedores
	$(DC) up -d --build
down: ## Detiene los contenedores
	$(DC) down
# Después de down -v, nginx no tiene estáticos: sin collectstatic, el login sale sin estilos
reset: ## Borra la base LOCAL y la recrea con las migraciones (solo desarrollo)
	$(DC) down -v && $(DC) up -d --build && ./scripts/migrate.sh && $(DC) exec web python manage.py collectstatic --noinput
actualizar: ## Pone al día imagen, migraciones y estáticos tras traer cambios
	$(DC) up -d --build && ./scripts/migrate.sh && $(DC) exec web python manage.py collectstatic --noinput
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
	DB_PASSWORD="$(CLAVE_OWNER)" $(DC) exec $(OWNER) web pytest -q $(T)
test-ci: ## Corre lo mismo que el CI en cada PR, con cobertura
	DB_PASSWORD="$(CLAVE_OWNER)" $(DC) exec $(OWNER) web pytest -m "not e2e and not lento" --cov=apps --cov-fail-under=80
e2e: ## Corre las pruebas de extremo a extremo con Playwright
	DB_PASSWORD="$(CLAVE_OWNER)" $(DC) exec $(OWNER) -e DJANGO_ALLOW_ASYNC_UNSAFE=true web pytest -m e2e e2e/ -q
lint: ## Revisa Python (ruff) y plantillas (djLint) sin modificar archivos
	$(DC) exec web ruff check . && $(DC) exec web ruff format --check .
	$(DC) exec web djlint . --check && $(DC) exec web djlint . --lint
# djlint --reformat termina con 1 cuando cambia algún archivo: aquí no es un error
format: ## Formatea Python (ruff) y plantillas (djLint)
	$(DC) exec web ruff format . && $(DC) exec web ruff check --fix .
	$(DC) exec web djlint . --reformat --quiet || true
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
- **`.env` se lee con `-include .env`.** Funciona con valores simples (`CLAVE=valor`), también con espacios (`HOGAR_NOMBRE=Hogar Gerontológico Demo`). Los valores no deben llevar `$`, `#` ni comillas, porque `make` los interpreta distinto que el shell.
- **En Windows, Git Bash no trae `make`.** Instálalo, por ejemplo con `winget install ezwinports.make` o `choco install make`, o trabaja desde WSL.

```bash
make help        # lista los 18 comandos con su descripción (17 + actualizar)
make openapi     # 0 errores y 2 advertencias intencionales
```

**Valores con espacios en `.env` (pendiente de HB-06).** HB-06 dejó `HOGAR_NOMBRE` comentada en `.env.example` porque el valor lleva espacios. `make` y `docker compose` lo leen bien sin comillas, pero `. ./.env` (en `scripts/migrate.sh` y en los atajos `dtest`, `dj` y `dpsql`) lo lee como `HOGAR_NOMBRE=Hogar` seguido del comando `Gerontológico`. `migrate.sh`, que usa `set -e`, termina con el código 127. Este ticket lo resuelve, porque es el que fija cómo se lee `.env`:

1. Cambia `set -a; . ./.env; set +a` en `scripts/migrate.sh` por una lectura línea por línea, que exporta cada `CLAVE=valor` tal cual y salta las líneas vacías y los comentarios:

   ```sh
   while IFS= read -r linea || [ -n "$linea" ]; do
       case $linea in ''|'#'*) ;; *) export "$linea" ;; esac
   done < .env
   ```

   Se probó con `bash --posix` y con el `sh` de BusyBox (Alpine): exporta `HOGAR_NOMBRE` completo. Si `.env` tiene fines de línea CRLF, el valor arrastra un `\r`; el `.env` debe estar en LF, como `db/init/01_roles.sh` (HB-01).
2. Usa la misma lectura en el atajo `set -a && . ./.env && set +a` de la sección 0.4 de esta guía, de `CLAUDE.md` ("Comandos"), del readme (sección 1.4) y de las guías que lo repiten (`grep -rn '\. \./\.env' --include=*.md .`).
3. Descomenta en `.env.example` la línea `HOGAR_NOMBRE=Hogar Gerontológico Demo`. De su comentario, quita solo la explicación de por qué iba comentada y **conserva** el resto: la usa `0003_hogar` una sola vez, es obligatoria en producción (`config.settings.prod` no arranca sin ella ni con más de 150 caracteres) y en desarrollo basta el valor por defecto de `settings`. Actualiza la nota "Por qué comentada" de la guía de HB-06, paso 2, para decir que TK-01 lo resolvió.

Comprueba con un `.env` que tenga la línea sin comentar:

```bash
./scripts/migrate.sh                                  # sin "command not found"
make help >/dev/null && echo ok                       # make lee el .env sin errores
docker compose config | grep HOGAR_NOMBRE             # HOGAR_NOMBRE: Hogar Gerontológico Demo
```

El nombre del Hogar en una base nueva se comprueba en la sección 5, paso 5.

**Poner al día los contenedores al traer la rama (pendiente de HB-08).** Las versiones fijas de las dependencias viven en `app/requirements.txt`: desde HB-08, por ejemplo, `django-axes==9.1.0`. Bootstrap 5.3.9 vive en `app/static/*/vendor/`. El `Dockerfile` y `docker-compose.yml` no repiten esas versiones, así que no se tocan cuando cambian. Lo que sí hace falta, en cada equipo y en el servidor del hogar, son 3 pasos después de traer cambios, porque `docker compose` no los hace solo:

| Paso | Por qué |
|---|---|
| `docker compose up -d --build web` | Reinstala `requirements.txt` en la imagen. Sin `--build`, el contenedor sigue con las versiones anteriores |
| `./scripts/migrate.sh` | Aplica las migraciones nuevas, también las de las dependencias (por ejemplo, las tablas de `axes`) |
| `collectstatic --noinput` | Copia los estáticos al volumen `static`, que es el que sirve nginx. El volumen persiste entre reinicios, y `down -v` también lo borra |

El código no necesita reconstrucción, porque `web` monta `./app`. El CI tampoco necesita nada: instala desde `requirements*.txt` y construye la imagen solo. Al crear el `Makefile`:

1. Agrega un *target* que encadene los 3 pasos, por ejemplo:

   ```make
   actualizar: ## Pone al día imagen, migraciones y estáticos tras traer cambios
   	$(DC) up -d --build && ./scripts/migrate.sh && $(DC) exec web python manage.py collectstatic --noinput
   ```

   Súmalo a `.PHONY` y al conteo de `make help`.
2. Haz que `reset` termine también con `collectstatic`: después de `down -v`, nginx no tiene estáticos y el login se ve sin estilos.
3. Revisa que la primera instalación del readme (sección 2.4) y el despliegue en el servidor del hogar (HB-10, semana 6) incluyan los 3 pasos, o `make actualizar`.

Compruébalo con `make actualizar`: termina sin errores, y `curl -sk -o /dev/null -w "%{http_code}" https://localhost/static/css/vendor/bootstrap.min.css` devuelve `200`.

### Paso 2. Privilegios de `app_user` (ya hechos en HB-03)

La migración `accounts/0002_privilegios.py` existe desde HB-03: da a `app_user` los 4 permisos sobre todas las tablas que cree `app_owner`, también las de este ticket. Lo único propio de TK-01 es retirar `UPDATE`, `DELETE` y `TRUNCATE` sobre `movimiento` (paso 9), y para eso las tablas nuevas deben depender de `0002_privilegios` (paso 6).

### Paso 3. Fixtures de pytest para el mock y para SQL directo (≈ 45 min)

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
    """El resto del test corre como app_user, igual que la aplicación en producción.

    SET LOCAL solo dura hasta el fin de la transacción del test. En un test con
    transaction=True no hay transacción envolvente y PostgreSQL ignoraría el SET LOCAL
    con un simple aviso: el test correría como app_owner sin que nadie lo notara.
    Por eso falla aquí; en esos tests, cada hilo hace SET ROLE app_user (guía de TK-02).
    """
    if not connection.in_atomic_block:
        pytest.fail(
            "como_app_user necesita la transacción del test: no lo uses con "
            "transaction=True; ahí cada hilo hace SET ROLE app_user (guía de TK-02)."
        )
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL ROLE app_user")
        cursor.execute("SELECT current_user")
        assert cursor.fetchone()[0] == "app_user"
    return demo
```

`app/pruebas.py` ya existe desde HB-03 con `ejecutar_sql`. Agrégale `saldo`; el archivo completo queda así (va en un módulo propio porque importar desde `conftest.py` es mala práctica en pytest):

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

`pyproject.toml` ya tiene desde HB-03 la configuración de pytest (marcadores `lento`, `http`, `integracion`, `infra` y `e2e` con `--strict-markers`, y `app/` en la ruta de importación) y la de cobertura (sin migraciones ni tests, con ramas). Compruébalo:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
addopts = "--strict-markers"
markers = [
    "lento: tests de plan de ejecución (EXPLAIN), corren en el CI nocturno",
    "http: tests de URL + vista + plantilla con el cliente de Django (test_views_*, test_admin*); corren en el CI de cada PR",
    "integracion: flujo completo Vista → Servicio → BD → v_conciliacion_existencia (test_integracion.py); corre en el CI de cada PR",
    "infra: configuración e infraestructura (test_proxy.py, test_conexion.py); corre en el CI de cada PR",
    "e2e: pruebas de extremo a extremo con Playwright (TK-03)",
]
```

### Paso 4. Tests en rojo (≈ 1 h 45 min)

Crea los paquetes de las 2 apps:

```bash
mkdir -p app/apps/inventario/migrations app/apps/inventario/tests \
         app/apps/conteos/migrations app/apps/conteos/tests
touch app/apps/inventario/__init__.py app/apps/inventario/migrations/__init__.py \
      app/apps/inventario/tests/__init__.py app/apps/conteos/__init__.py \
      app/apps/conteos/migrations/__init__.py app/apps/conteos/tests/__init__.py
```

Agrega `"apps.inventario"` y `"apps.conteos"` a `INSTALLED_APPS`, debajo de `"apps.pautas"`, en `app/config/settings/base.py`.

Escribe los tests de la sección 3 y ejecútalos **antes** de implementar:

```bash
dtest apps/inventario apps/conteos -q
# ModuleNotFoundError: No module named 'apps.conteos.models'

dtest apps/accounts/tests/test_privilegios.py apps/catalogo/tests/test_admin.py -q
# Fallan los 8 casos nuevos; los de HB-03 y HB-09 siguen pasando
```

El commit de este paso queda en rojo a propósito: el PR se abre cuando todo está en verde.

Así avanza el rojo con cada paso:

| Al terminar | Comando | Resultado esperado |
|---|---|---|
| Paso 8 (conteos) | `dtest apps/inventario apps/conteos apps/accounts/tests/test_privilegios.py -q` | El mock ya carga. Siguen en rojo los *triggers* de `movimiento`, `v_conciliacion_existencia` y el `REVOKE` |
| Paso 9 (SQL) | El mismo comando | Todos pasan |
| Paso 9 (SQL) | `dtest apps/catalogo/tests/test_admin.py -k medicamento_con_existencias -q` | `1 failed`: falta el mensaje del formulario |
| Paso 9b (panel) | El mismo comando | `1 passed` |

### Paso 5. Modelos de `inventario` (≈ 1.5 h)

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

### Paso 6. Genera y revisa la migración inicial (≈ 30 min)

```bash
dj makemigrations inventario          # crea 0001_initial.py
```

Abre `0001_initial.py` y agrega a mano esta dependencia, para que las tablas nazcan **después** de los permisos por defecto de `app_user` (HB-03):

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

### Paso 7. Migración de datos: motivos de baja (≈ 20 min)

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

### Paso 7b. Permisos de los grupos sobre los modelos nuevos (≈ 30 min)

Los grupos `Solo lectura` y `Lectura y escritura` se crearon en HB-08 (`accounts/0003_grupos`), antes de que existieran estos modelos, así que todavía no tienen sus permisos. Sin este paso, la pantalla de TK-03 responde `403` a todos.

```bash
dj makemigrations inventario --empty --name permisos_grupos
```

Contenido de `0003_permisos_grupos.py` (el paso 9 crea `0004_sql.py`):

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
    dependencies = [("inventario", "0002_motivos_baja"), ("accounts", "0003_grupos")]
    operations = [migrations.RunPython(asignar_permisos, retirar_permisos)]
```

> Repite el mismo patrón en `conteos` cuando se haga TK-06 (`view_conteofisico`, `add_conteofisico`...), también con la dependencia de `accounts/0003_grupos`.

### Paso 8. Modelos y migraciones de `conteos` (≈ 1 h)

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

`0002_triggers.py`: copia de la sección 3.3 las funciones `fn_conteo_cerrado` y `fn_detalle_conteo_cerrado` con sus *triggers*. Cada `RunSQL` lleva su reversa:

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

### Paso 9. Migración SQL de `inventario`: *triggers*, vista, `fillfactor` y `REVOKE` (≈ 1 h)

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

# Es del catálogo (HB-05), pero consulta existencia: nace con esta tabla (sección 3.3)
MEDICAMENTO_BAJA = """
CREATE FUNCTION fn_medicamento_baja_sin_existencias() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.activo AND NOT NEW.activo AND EXISTS (
        SELECT 1 FROM existencia WHERE medicamento_id = NEW.id AND saldo > 0) THEN
        RAISE EXCEPTION 'No se puede dar de baja el medicamento %: tiene existencias', NEW.id;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_medicamento_baja BEFORE UPDATE OF activo ON medicamento
    FOR EACH ROW EXECUTE FUNCTION fn_medicamento_baja_sin_existencias();
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
            MEDICAMENTO_BAJA,
            "DROP TRIGGER tg_medicamento_baja ON medicamento;"
            "DROP FUNCTION fn_medicamento_baja_sin_existencias();",
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

### Paso 9b. Baja de un medicamento con existencias en el panel (≈ 20 min)

El *trigger* `tg_medicamento_baja` es la última barrera. Antes, el formulario de `MedicamentoAdmin` (HB-09) debe dar un mensaje, como pide la sección 5 ("Controles"). En `app/apps/catalogo/admin.py`:

```python
from django import forms

from apps.inventario.models import Existencia


class MedicamentoAdminForm(forms.ModelForm):
    class Meta:
        model = Medicamento
        fields = "__all__"

    def clean_activo(self):
        activo = self.cleaned_data["activo"]
        dando_de_baja = self.instance.pk and self.instance.activo and not activo
        if dando_de_baja and Existencia.objects.filter(
            medicamento=self.instance, saldo__gt=0
        ).exists():
            raise forms.ValidationError(
                "No se puede dar de baja: hay existencias de este medicamento."
            )
        return activo
```

y en `MedicamentoAdmin`: `form = MedicamentoAdminForm`. Su test va en `apps/catalogo/tests/test_admin.py` (sección 3.4 de esta guía).

### Paso 10. Aplica todo y carga el mock (≈ 20 min)

```bash
./scripts/migrate.sh
docker compose cp app/fixtures/mock/. db:/tmp/mock/
dpsql -v ON_ERROR_STOP=1 -f /tmp/mock/cargar_mock.sql
```

La última consulta del script muestra el resumen. Debe decir: 2 usuarios, 13 principios activos, 15 medicamentos, 3 residentes, 3 pautas, 28 movimientos, 13 existencias, 2 conteos y 5 detalles de conteo.

### Paso 11. Tests en verde (≈ 15 min)

```bash
dtest apps/inventario apps/conteos apps/accounts apps/catalogo -q     # todos deben pasar
```

### Paso 12. Verificación final y *pull request* (≈ 1 h)

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

El archivo existe desde HB-03, con los tests de dueño de las tablas, de los 4 permisos (que ya excluye `movimiento`) y de que `app_user` no crea tablas. Agrega estos 3, que son propios de `movimiento`:

```python
def test_app_user_solo_lee_e_inserta_movimientos(db):
    filas = ejecutar_sql(
        "SELECT p, has_table_privilege('app_user', 'movimiento', p) "
        "FROM unnest(ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE']) AS p"
    )
    assert dict(filas) == {
        "SELECT": True, "INSERT": True, "UPDATE": False, "DELETE": False, "TRUNCATE": False,
    }


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

### 3.4 `apps/catalogo/tests/test_admin.py`: baja de un medicamento con existencias (agrega)

El archivo existe desde HB-09. Agrega estos 2 tests y los imports `from django.db import DatabaseError` y `from pruebas import ejecutar_sql`:

```python
def test_no_se_da_de_baja_un_medicamento_con_existencias(admin_client, demo):
    eutirox = demo.med["Eutirox"]                       # Carmen tiene 33 dosis
    url = f"/admin/catalogo/medicamento/{eutirox.pk}/change/"
    datos = {
        "nombre_comercial": eutirox.nombre_comercial, "tipo": eutirox.tipo,
        "presentacion": eutirox.presentacion_id, "concentracion": eutirox.concentracion,
        # "activo" no se envía: la casilla desmarcada
        "medicamentoprincipioactivo_set-TOTAL_FORMS": "0",
        "medicamentoprincipioactivo_set-INITIAL_FORMS": "0",
        "medicamentoprincipioactivo_set-MIN_NUM_FORMS": "1",
        "medicamentoprincipioactivo_set-MAX_NUM_FORMS": "1000",
    }
    respuesta = admin_client.post(url, datos)
    assert respuesta.status_code == 200                 # mensaje en el formulario, no un 500
    assert "hay existencias de este medicamento" in respuesta.content.decode()
    eutirox.refresh_from_db()
    assert eutirox.activo


def test_el_trigger_rechaza_la_baja_aunque_se_salte_el_formulario(datos_demo):
    with pytest.raises(DatabaseError, match="tiene existencias"):
        ejecutar_sql("UPDATE medicamento SET activo = false WHERE nombre_comercial = 'Eutirox'")
```

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
dpsql -c "SELECT id, nombre FROM entidad WHERE tipo = 'HOGAR'"     # 1 | el HOGAR_NOMBRE de .env

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

> **Diferencias de forma con el DDL de las secciones 3.1 y 3.3, con el mismo efecto** (cambio de OpenSpec `tk-01-esquema-inventario`). Los nombres son idénticos; cambia cómo los escribe Django:
>
> | Readme | `\d movimiento` / `\d detalle_conteo` | Por qué está bien |
> |---|---|---|
> | `DEFAULT now()` | `DEFAULT statement_timestamp()` | Es lo que genera `Now()`, como en HB-06 y HB-07 |
> | `btrim(entregado_por) <> ''` | `length(TRIM(BOTH FROM entregado_por)) > 0` | `no_vacio()` de `apps/expresiones.py`, el helper de HB-05 a HB-07, en lugar de la expresión regular del paso 5 |
> | `diferencia <> 0` | `NOT diferencia = 0::numeric` | Equivalentes |
> | `(estado = 'CERRADO') = (cerrado_en IS NOT NULL)` | `Q(estado="CERRADO", cerrado_en__isnull=False) \| (~Q(estado="CERRADO") & Q(cerrado_en__isnull=True))` | La forma del DDL. La del paso 8 (`EN_PROCESO` con `cerrado_en` nulo) también rechazaba un estado desconocido, y PostgreSQL evalúa los `CHECK` en orden alfabético: el error salía con el nombre `ck_conteo_cierre` en lugar de `ck_conteo_estado` |
> | FK con `ON DELETE RESTRICT` | FK `DEFERRABLE INITIALLY DEFERRED`, sin `ON DELETE` | `PROTECT` lo impide en Django, como en HB-05 a HB-07 |
>
> Las FK `motivo_baja_id` y `usuario_id` de `movimiento`, y `usuario_id` de `conteo_fisico`, llevan `db_index=False` desde la segunda revisión: ninguna consulta de la sección 3.3 filtra por ellas (ADR-0018; tabla "FK sin índice porque ninguna consulta las usa"). Sus índices los quitan `inventario/0005_fk_sin_indice` y `conteos/0004_fk_sin_indice`. `corrige_a` lleva `db_index=False`: la cubre `uq_movimiento_corrige`.

> **Diferencias con el código de esta guía.**
>
> - **`Makefile` sin `export`.** Las recetas usan los valores con `$(...)` y `docker compose` lee `.env` por su cuenta. Con `export`, compose prefería la copia de `make`, y en Windows (GNU Make 3.81 de GnuWin32) los acentos llegaban mal a `web`: "Gerontológico" como "GerontolÃ³gico". La base no se veía afectada, porque `migrate.sh` vuelve a leer `.env`. Así tampoco se pasan las contraseñas a cada proceso hijo. GNU Make 3.81 de GnuWin32 no usa `SHELL := /bin/bash`, sino el `sh` de Git, y las recetas funcionan igual. Si un ticket futuro (HB-10) necesita una variable en el entorno de un script, la exporta por su nombre.
> - **`ix_movimiento_med_fecha` va primero en `Meta.indexes`.** Sin estadísticas, los índices de `movimiento` empatan en coste y gana el último creado; el test `lento` hace además `ANALYZE movimiento` antes del `EXPLAIN`.
> - **Sin `# noqa: DJ001`:** `ruff` no tiene activas las reglas DJ.
> - **Mensaje del panel** en la constante `CON_EXISTENCIAS` de `apps/catalogo/admin.py`, con punto final.
> - **`make help` lista 18 comandos** (los 17 del paso 1 y `actualizar`).
>
> **Tests añadidos a los de la sección 3:** nombres exactos de las restricciones y de los *triggers*, definición de los índices, tipos y valores por omisión, `fillfactor`, ningún índice extra por columna inicial en las FK cubiertas, los 8 motivos, los permisos de los grupos, migraciones reversibles con `call_command` (`transaction=True, serialized_rollback=True`), los *fixtures* (`como_app_user` falla sin transacción), la lectura de la conciliación como `app_user` y, en el panel, el control de que Tempra (saldo 0) sí se da de baja. El test del panel envía el renglón real del principio activo, para que el aviso no se confunda con el de "al menos un principio activo". Los 3 tests de HB-08 que fijaban los permisos de los grupos (`test_grupos.py` y `test_admin_usuarios.py`) suman ahora los de inventario: 8 en *Solo lectura* y 19 en *Lectura y escritura*. La rama fue `final-project-vmrr`, no `feature/TK-01-esquema-inventario` (`CLAUDE.md`, sección Git).
>
> **Consulta 2c con un año de datos:** las salidas solas usan *Index Scan using `ix_movimiento_origen_med_fecha`*. La consulta completa, con `OR` entre origen y destino, usa un *Bitmap Index Scan* sobre `ix_movimiento_med_fecha` y filtra por entidad, como prevé la sección 3.3. En ningún caso hay *Seq Scan*.

> **Ajustes de la revisión adversarial del PR #3** (cambio de OpenSpec `tk-01-ajustes-revision`). El código del paso 8 (`0002_triggers`) es el original. En el repositorio cambia esto:
>
> - **`conteos/0003_detalle_conteo_cerrado`:** en un `UPDATE`, `fn_detalle_conteo_cerrado` solo miraba `NEW.conteo_id`, así que `UPDATE detalle_conteo SET conteo_id = 2 WHERE conteo_id = 1 ...` sacaba un renglón de un conteo cerrado. Ahora revisa también `OLD.conteo_id` (readme, sección 3.3). Es una migración nueva, para que las bases que ya aplicaron `0002` se pongan al día con `migrate.sh`.
> - **ADR-0027** supersede en parte a ADR-0009: las FK son `PROTECT` en Django y `NO ACTION` diferidas en PostgreSQL, no `ON DELETE RESTRICT`. Un test lo comprueba con `SET CONSTRAINTS ALL IMMEDIATE`.
> - **`ejecutar_sql(..., rol=...)`** restaura el rol que había, en lugar de `RESET ROLE`, que deshacía `como_app_user`.
> - **`make test`, `test-ci` y `e2e`** ya no muestran la contraseña de `app_owner`: imprimían el comando con la contraseña tapada por asteriscos (sustituido en la segunda y la tercera revisión: ver sus notas abajo). El bloque del paso 1 es el `Makefile` del repositorio.
> - **Tests de regresión nuevos:** borrar y cambiar renglones de un conteo cerrado, borrar su encabezado, meter un renglón en él, Transferencia a un Residente egresado, Entrada a uno fallecido y el borrado de un Medicamento con historial.
> - `ck_movimiento_origen_entrada` y `ck_conteo_estado` están ahora en el DDL de la sección 3.1.
>
> **Pendientes** de la misma revisión. No contradicen al readme, y se siguen en [`pendientes.md`](pendientes.md), con el ticket que retoma cada uno:
>
> | Pendiente | Hallazgo | Qué hacer |
> |---|---|---|
> | Los Scenarios del `Makefile` y de `.env` (18 comandos, `HOGAR_NOMBRE` sin comentar, valores con espacios) solo se comprueban a mano (sustituido en la segunda y la tercera revisión: `tests/test_makefile.py` cubre ya `make -n` y la contraseña) | 5 | Un test en `tests/` con un `.env` temporal (con HB-10, que agrega `tests/test_candado.py`) para lo que falta: los 18 comandos, `HOGAR_NOMBRE` y `migrate.sh` con valores con espacios |
> | Django crea índices sobre `movimiento.motivo_baja_id`, `movimiento.usuario_id` y `conteo_fisico.usuario_id`, sin consulta de la sección 3.3 que los use (ADR-0018) | 6 | Decidir en el readme si se quedan o se declaran con `db_index=False`, con la historia de reportes |
> | EXPLAIN solo de la consulta 2c; faltan `ix_existencia_med_entidad` (consulta 1, con TK-03) e `ix_detalle_con_diferencia` (2b, con TK-06). El criterio 11 dice "1c", que no existe | 8 | Medirlas en esos tickets y corregir "1c" en el readme |
> | `migrate.sh` no quita el `\r` de un `.env` en CRLF; `make format` con `\|\| true` oculta fallos reales de djLint; "Rojo esperado" queda como texto en los *docstrings* de los tests | *nits* | Al tocar esos archivos |

> **Ajustes de la segunda revisión adversarial** (cambio de OpenSpec `tk-01-ajustes-revision-2`). Atiende los pendientes 6 y 8 ("1c") de la tabla anterior. En el repositorio cambia esto:
>
> - **B1 (ADR-0018):** `db_index=False` en `movimiento.motivo_baja_id`, `movimiento.usuario_id` y `conteo_fisico.usuario_id`. Las migraciones `inventario/0005_fk_sin_indice` y `conteos/0004_fk_sin_indice` (generadas con `makemigrations` como `app_owner`) quitan los índices, y su reversa los recrea. La sección 3.3 del readme suma la tabla "FK sin índice porque ninguna consulta las usa".
> - **M1:** el `Makefile` ya no expande la contraseña de `app_owner`: `OWNER` la lee el shell de `.env` al ejecutar la receta (`$$(sed -n 's/^DB_OWNER_PASSWORD=//p' .env | tr -d '\r')`). Ni el eco de la receta, ni `make -n`, ni `--trace` la muestran. `test`, `test-ci` y `e2e` vuelven a ser una sola línea, sin `@` ni `echo` (también el *nit* 1). Lo comprueba `tests/test_makefile.py` con un `.env` temporal. El bloque del paso 1 es el `Makefile` del repositorio. La tercera revisión cambia de dónde sale la contraseña y cómo llega a `docker compose` (ver su nota).
> - **M2:** el borrado con historial se prueba para Eutirox, el Hogar, `operador.demo` y `CONSUMO`: en el ORM, con `protected_objects`; en la base, sin las referencias que no son historial (principios activos, Pautas y grupo del usuario) y con la tabla del historial en el mensaje.
> - **m1:** el `try` del test de migraciones empieza antes de `migrate conteos zero`, y el cuerpo de `fn_detalle_conteo_cerrado` se compara en `0002_triggers` y al volver a migrar.
> - **m2, m3, m4 y m6 (documentación):** la ficha de TK-01 y el árbol de archivos con las migraciones y restricciones nuevas; `PROTECT` (ADR-0027) en "Sin índices redundantes"; `conteos/migrations/0006_permisos_grupos.py` en el ejemplo de PR de TK-06 (la revisión proponía `0004`, pero `0004` y `0005` ya los toma este cambio), y el criterio 11 con "las consultas 1 y 2c", marcado como parcial.
> - **m5:** `conteos/0005_detalle_conteo_bloqueo`: `fn_detalle_conteo_cerrado` lee el estado del conteo de `OLD` y el de `NEW` con `FOR SHARE`. Si la captura de un renglón llega primero, el cierre del conteo la espera; si llega el cierre, la captura espera y la base la rechaza. `app_user` puede hacer `FOR SHARE` sobre `conteo_fisico` porque tiene `UPDATE`; nunca sobre `movimiento`. Lo prueban 2 tests con 2 conexiones como `app_user` y `lock_timeout`.
> - **n2 y n3:** referencias de `pendientes.md` precisadas; el *docstring* de `ejecutar_sql` dice que el rol distingue mayúsculas, y su test compara con `session_user`.
>
> **Límite aceptado:** `make -p` imprime la base de variables de `make`, incluidos los valores de `.env` (contraseñas), porque el `Makefile` hace `-include .env` para el candado de HB-10. Es una opción de depuración, no de uso diario, y se decide al completar el `Makefile` en HB-10 ([`pendientes.md`](pendientes.md)).

> **Ajustes de la tercera revisión adversarial** (cambio de OpenSpec `tk-01-ajustes-revision-3`). Atiende los mayores 1 y 2, los menores 1 a 5 y 7 y los *nits* 1, 2 y 4. En el repositorio cambia esto:
>
> - **Mayor 1:** el DDL de `fn_detalle_conteo_cerrado` de la sección 3.3 del readme (y del anexo de `03`) lleva `FOR SHARE` en las 2 lecturas del estado, como `conteos/0005_detalle_conteo_bloqueo`.
> - **Mayor 2 y menor 1:** el test de migraciones revierte primero a `conteos/0004_fk_sin_indice` y comprueba que la función es la de `0003` (los conteos de `OLD` y `NEW`, sin `FOR SHARE` ni `v_conteo`); después baja a `0002_triggers`. Al volver a migrar exige 2 `FOR SHARE`. Un tercer test de concurrencia borra un renglón mientras se cierra el conteo (la rama de `OLD`).
> - **Menores 3 y 4, y *nit* 1:** `CLAVE_OWNER` toma `DB_OWNER_PASSWORD` del entorno si está definida (como en HB-10) y, si no, de la primera línea de `.env` que la define, sin el `\r` de un CRLF. Las recetas `test`, `test-ci` y `e2e` la ponen en el entorno de `docker compose` (`DB_PASSWORD="$(CLAVE_OWNER)" $(DC) exec ... -e DB_PASSWORD ...`), así que no va en sus argumentos ni aparece en `ps`. `tests/test_makefile.py` corre `make test` de verdad con un `docker` falso en el `PATH`: `.env` con espacios y CRLF, con la clave 2 veces y sin `.env` con la clave en el entorno. El bloque del paso 1 es el `Makefile` del repositorio.
> - **Menores 2, 5 y 7:** los 2 riesgos de bloqueo del servicio de conteos en el pendiente de TK-06; esta guía, [`pendientes.md`](pendientes.md) y la guía de HB-10 al día; y la spec de `inventario` sin el MUST que era una propiedad del test.
> - ***Nits* 2 y 4:** "Rojo comprobado" en los *docstrings* de los tests ya comprobados, y la conexión del test de concurrencia se cierra aunque falle el `SET ROLE`.
>
> **Límites aceptados y decisiones:**
> - ***Nit* 5:** el test del borrado con historial exige que falle alguna FK del historial, no cada una por separado. Aislar cada FK exigiría borrar Movimientos, que son inmutables (ADR-0005).
> - ***Nit* 4:** `tablas_referidas` queda duplicado en los 2 `test_esquema.py`, como los demás *helpers* de cada archivo.
> - ***Nit* 3:** los tests de concurrencia del conteo siguen en `conteos/tests/test_esquema.py`, porque prueban un *trigger* y no un servicio. Usan 2 conexiones en lugar de hilos, porque así son deterministas sin `sleep`. `test_concurrencia.py` queda para los servicios, desde TK-02.
> - `tests/test_makefile.py` hace depender de GNU Make al *job* `herramientas` del CI: Ubuntu lo trae. Sin `make` en el equipo, sus tests se omiten.
> - **Menor 6:** `pauta.medicamento_id` y `pauta.registrado_por_id` conservan su índice sin consulta. La nota de la tabla "FK sin índice…" de la sección 3.3 lo deja pendiente para la historia de Pautas.

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
| `como_app_user necesita la transacción del test` | El test usa `transaction=True` (sin transacción envolvente, `SET LOCAL` no tendría efecto) | Quita `como_app_user` de ese test: en los tests con hilos, cada hilo hace `SET ROLE app_user` (guía de TK-02) |
| `sh: 01_roles.sh: not found` o `\r: not found` al levantar `db` | El script tiene fines de línea CRLF (Windows) | Guía de HB-01, paso 2.2, y `docker compose down -v` |
| El script de roles no se ejecutó | El volumen `pgdata` ya existía | `docker compose down -v` (desarrollo) o ejecútalo a mano: `docker compose exec db sh /docker-entrypoint-initdb.d/01_roles.sh` |
| `permission denied to create database` al correr `pytest` | `app_owner` sin `CREATEDB` | `DB_OWNER_CREATEDB=true` en `.env` y recrea el volumen |
| `permission denied for table ...` en la aplicación | Una tabla se creó antes de la migración de privilegios | Revisa la dependencia agregada en el paso 6 y vuelve a ejecutar `./scripts/migrate.sh` |
| `models.E034: The index name ... cannot be longer than 30 characters` | Nombre de índice largo | Usa los nombres de la sección 3.3 |
| `TypeError: ... unexpected keyword argument 'condition'` | Django menor a 5.1 | Verifica `requirements.txt`: Django 5.2 LTS |
| `function f_unaccent does not exist` al cargar el mock | Falta la migración de HB-05 que crea la función | Requisitos previos, paso 0.2 |
| El mock falla con "La base ya tiene datos de negocio" | Ya lo cargaste antes | `docker compose down -v`, `up -d`, `./scripts/migrate.sh` y vuelve a cargarlo |
