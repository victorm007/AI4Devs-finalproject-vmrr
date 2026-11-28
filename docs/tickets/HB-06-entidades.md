# HB-06 · Guía paso a paso: entidades, el Hogar y los residentes (D3)

> **Ticket:** [readme, sección 6, HB-06](../../readme.md#tickets-de-habilitación-hb-01-a-hb-10) · **Tipo:** base de datos · **Estimación:** 3 puntos · **Rama:** `feature/HB-06-entidades`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket y en las secciones 3.1, 3.2 (D3) y 3.3 del readme. Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.
>
> **Integración** (readme, sección 6, "Puntos de integración"): este ticket **provee** el punto 11 (`Entidad.activa` y `Entidad.__str__`), que consumen TK-01, TK-02 y TK-03. No cambies su comportamiento sin avisar en el PR.

**Resultado al terminar:** existen las tablas `entidad` (supertipo) y `residente` (subtipo), con la FK compuesta que impide que un residente cuelgue del Hogar, el índice `ix_residente_nombre` y todas sus restricciones. La migración crea el Hogar, único. `registrar_residente()` da de alta la entidad y el residente en una sola transacción.

---

## 0. Antes de empezar

### 0.1 Lee primero (30 min)

| Qué | Dónde | Para qué |
|---|---|---|
| D3 — Entidades | readme, sección 3.2 | Supertipo/subtipo, columnas y reglas |
| DDL de D3 | readme, sección 3.1 | `uq_entidad_un_hogar`, `uq_entidad_id_tipo`, `fk_residente_entidad`, `ck_*` |
| Restricciones adicionales | readme, sección 3.3 | `ck_entidad_nombre_no_vacio`, `ck_residente_nombres`, `ck_residente_nacimiento` |
| Consulta 3 | readme, sección 3.3 | `ix_residente_nombre` |
| Punto de integración 11 | readme, sección 6 | Contrato de `activa` y `__str__` |

### 0.2 Requisitos previos

- HB-05 integrado en `main`: existe la función `f_unaccent` (`dpsql -c '\df f_unaccent'`) y el módulo `apps/expresiones.py`.

### 0.3 Crea la rama

```bash
git switch main && git pull
git switch -c feature/HB-06-entidades
```

---

## 1. Archivos que vas a crear o modificar

```
AI4Devs-finalproject-vmrr/
├── .env.example                       # MODIFICAR: HOGAR_NOMBRE
├── docker-compose.yml                 # MODIFICAR: HOGAR_NOMBRE en web
└── app/
    ├── config/settings/base.py        # MODIFICAR: "apps.entidades" y HOGAR_NOMBRE
    └── apps/entidades/
        ├── __init__.py                # NUEVO (vacío)
        ├── apps.py                    # NUEVO
        ├── models.py                  # NUEVO: Entidad, Residente
        ├── services.py                # NUEVO: registrar_residente
        ├── migrations/
        │   ├── __init__.py            # NUEVO (vacío)
        │   ├── 0001_initial.py        # GENERADO con makemigrations
        │   ├── 0002_fk_compuesta.py   # NUEVO: fk_residente_entidad
        │   └── 0003_hogar.py          # NUEVO: dato semilla
        └── tests/
            ├── __init__.py            # NUEVO (vacío)
            ├── test_modelos.py        # NUEVO
            └── test_services.py       # NUEVO
```

---

## 2. Tareas paso a paso

El orden sigue TDD (`CLAUDE.md`): primero los tests en rojo, después la implementación.

### Paso 1. Tests en rojo (≈ 45 min)

Crea solo lo necesario para que pytest encuentre los tests:

```bash
mkdir -p app/apps/entidades/tests
touch app/apps/entidades/__init__.py app/apps/entidades/tests/__init__.py
```

Escribe los tests de la sección 3 y ejecútalos **antes** de implementar:

```bash
dtest apps/entidades -q
# ModuleNotFoundError: No module named 'apps.entidades.models'
```

> El error de importación es el rojo inicial: indica que el módulo aún no existe. El rojo útil llega después, cuando el módulo ya existe y fallan las reglas.

Así avanza `dtest apps/entidades -q` con cada paso:

| Al terminar | Resultado esperado |
|---|---|
| Esqueleto del servicio (inicio del paso 5) | Pasan los tests de esquema. Fallan con `NotImplementedError` los que dan de alta un residente |
| Paso 5 (servicio) | Todos pasan |

### Paso 2. Nombre del Hogar desde el entorno (≈ 10 min)

El Hogar es una entidad fija que crea la migración. Su nombre cambia por instalación (el real en el servidor del hogar, "Hogar Gerontológico Demo" en desarrollo y en la demo), así que viene del entorno:

```python
# app/config/settings/base.py  (from django.core.exceptions import ImproperlyConfigured)
# Nombre del Hogar que crea la migración entidades/0003_hogar (readme, sección 3.2, D3).
# Vacía o ausente: el de la demo, que esperan los tests de TK-03 con el dataset mock.
HOGAR_NOMBRE = os.environ.get("HOGAR_NOMBRE", "").strip() or "Hogar Gerontológico Demo"
if len(HOGAR_NOMBRE) > 150:  # el largo de entidad.nombre
    raise ImproperlyConfigured(
        f"HOGAR_NOMBRE tiene {len(HOGAR_NOMBRE)} caracteres; el máximo es 150 (entidad.nombre)."
    )
```

```python
# app/config/settings/prod.py  (después de "from .base import *")
# Sin valor por defecto, como SECRET_KEY: el servidor del hogar no arranca sin haberlo elegido
HOGAR_NOMBRE = os.environ.get("HOGAR_NOMBRE", "").strip()
if not HOGAR_NOMBRE:
    raise ImproperlyConfigured(
        "Falta HOGAR_NOMBRE en .env: en producción el Hogar debe tener su nombre real "
        "(o el de la demo, si es la demo). Sin ella, el contenedor web no arranca y se reinicia."
    )
```

En el `environment` de `web`, **sin valor por defecto**, para que un servidor sin la variable no cree un Hogar "Demo" que después no se puede renombrar: `HOGAR_NOMBRE: ${HOGAR_NOMBRE:-}`.

En `.env.example`, **comentada**, con un comentario que dice que la usa `0003_hogar` una sola vez, que es obligatoria en producción y que en desarrollo basta el valor por defecto de `settings`:

```dotenv
# HOGAR_NOMBRE=Hogar Gerontológico Demo
```

> **Por qué comentada.** El valor lleva espacios. Sin comillas, `. ./.env` (lo usan `scripts/migrate.sh` y los atajos `dtest`, `dj` y `dpsql`) lo lee como `HOGAR_NOMBRE=Hogar` seguido del comando `Gerontológico`, y `migrate.sh` falla. Con comillas, `make` (TK-01) exportaría las comillas literales. Por eso la regla de `.env` es "sin comillas", y el valor por defecto de `settings` cubre el desarrollo y el CI (`design.md` de `hb-06-entidades`, decisión 6, y de `hb-06-ajustes-revision`, decisión 4). **Resuelto en [TK-01](TK-01-esquema-inventario.md)** (paso 1, "Valores con espacios en `.env`"): `migrate.sh` y los atajos leen `.env` línea por línea en lugar de `. ./.env`, y `.env.example` trae la línea sin comentar. Así el servidor del hogar puede poner su nombre real.

> "Hogar Gerontológico Demo" es el nombre que esperan los tests de TK-03 con el dataset mock.

### Paso 3. La app y los modelos (≈ 1.5 h)

```bash
mkdir -p app/apps/entidades/migrations app/apps/entidades/tests
touch app/apps/entidades/__init__.py app/apps/entidades/migrations/__init__.py \
      app/apps/entidades/tests/__init__.py
```

`app/apps/entidades/apps.py`:

```python
from django.apps import AppConfig


class EntidadesConfig(AppConfig):
    name = "apps.entidades"
    label = "entidades"
    verbose_name = "Residentes"
```

Agrega `"apps.entidades"` a `INSTALLED_APPS`, debajo de `"apps.catalogo"`.

`app/apps/entidades/models.py`:

```python
"""Entidades que poseen existencias: el Hogar y los residentes (readme, sección 3.2, D3).

entidad es el supertipo: existencia, movimiento y conteo_fisico tienen una sola FK real
hacia ella. residente es el subtipo, con la misma clave. Sin lógica en los modelos: las
reglas viven en Meta.constraints, en la base de datos y en services.py.
"""

from datetime import date

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now

from apps.expresiones import no_vacio, sin_acentos


class Entidad(models.Model):
    class Tipo(models.TextChoices):
        HOGAR = "HOGAR", "Hogar"
        RESIDENTE = "RESIDENTE", "Residente"

    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    # Solo el Hogar tiene nombre aquí; el del residente vive desglosado en residente
    nombre = models.CharField(max_length=150, null=True, blank=True)
    creado_en = models.DateTimeField(db_default=Now(), editable=False)
    actualizado_en = models.DateTimeField(auto_now=True, db_default=Now())

    class Meta:
        db_table = "entidad"
        verbose_name_plural = "entidades"
        constraints = [
            models.UniqueConstraint(
                fields=["tipo"], condition=Q(tipo="HOGAR"), name="uq_entidad_un_hogar",
                violation_error_message="Solo puede existir un Hogar.",
            ),
            # Destino de la FK compuesta de residente: (id, tipo)
            models.UniqueConstraint(fields=["id", "tipo"], name="uq_entidad_id_tipo"),
            models.CheckConstraint(
                condition=Q(tipo__in=["HOGAR", "RESIDENTE"]), name="ck_entidad_tipo"
            ),
            # (tipo = 'HOGAR') = (nombre IS NOT NULL)
            models.CheckConstraint(
                condition=Q(tipo="HOGAR", nombre__isnull=False)
                | (~Q(tipo="HOGAR") & Q(nombre__isnull=True)),
                name="ck_entidad_nombre",
            ),
            models.CheckConstraint(
                condition=Q(nombre__isnull=True) | no_vacio("nombre"),
                name="ck_entidad_nombre_no_vacio",
            ),
        ]

    # Punto de integración 11: lo usan TK-02 (destino activo) y TK-03 (pantalla)
    @property
    def activa(self) -> bool:
        """El Hogar siempre está activo; un residente, solo si su estado es ACTIVO."""
        return self.tipo == self.Tipo.HOGAR or self.residente.estado == Residente.Estado.ACTIVO

    def __str__(self) -> str:
        """Nombre del Hogar o nombre completo del residente (punto de integración 11)."""
        return self.nombre if self.tipo == self.Tipo.HOGAR else self.residente.nombre_completo


class Residente(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        EGRESADO = "EGRESADO", "Egresado"
        FALLECIDO = "FALLECIDO", "Fallecido"

    # Misma clave que su entidad. db_constraint=False: la FK real es compuesta
    # (entidad_id, tipo) -> entidad (id, tipo) y se crea en 0002_fk_compuesta.
    entidad = models.OneToOneField(
        Entidad, on_delete=models.PROTECT, primary_key=True, related_name="residente",
        db_constraint=False,
    )
    tipo = models.CharField(max_length=10, default="RESIDENTE", db_default="RESIDENTE", editable=False)
    primer_nombre = models.CharField(max_length=60)
    segundo_nombre = models.CharField(max_length=60, null=True, blank=True)
    primer_apellido = models.CharField(max_length=60)
    segundo_apellido = models.CharField(max_length=60, null=True, blank=True)
    fecha_nacimiento = models.DateField()
    fecha_ingreso = models.DateField()
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.ACTIVO, db_default=Estado.ACTIVO
    )
    fecha_baja = models.DateField(
        null=True, blank=True, help_text="Fecha de egreso o defunción; vacía si está activo."
    )

    class Meta:
        db_table = "residente"
        constraints = [
            models.CheckConstraint(condition=Q(tipo="RESIDENTE"), name="ck_residente_tipo"),
            models.CheckConstraint(
                condition=Q(estado__in=["ACTIVO", "EGRESADO", "FALLECIDO"]),
                name="ck_residente_estado",
            ),
            # (estado = 'ACTIVO') = (fecha_baja IS NULL)
            models.CheckConstraint(
                condition=Q(estado="ACTIVO", fecha_baja__isnull=True)
                | (~Q(estado="ACTIVO") & Q(fecha_baja__isnull=False)),
                name="ck_residente_baja",
                violation_error_message="La fecha de baja es obligatoria si el residente "
                "egresó o falleció, y debe quedar vacía si está activo.",
            ),
            models.CheckConstraint(
                condition=Q(fecha_baja__isnull=True) | Q(fecha_baja__gte=F("fecha_ingreso")),
                name="ck_residente_fechas",
                violation_error_message="La fecha de baja no puede ser anterior al ingreso.",
            ),
            models.CheckConstraint(
                condition=no_vacio("primer_nombre") & no_vacio("primer_apellido"),
                name="ck_residente_nombres",
            ),
            models.CheckConstraint(
                condition=Q(fecha_nacimiento__gte=date(1900, 1, 1))
                & Q(fecha_ingreso__gte=F("fecha_nacimiento")),
                name="ck_residente_nacimiento",
                violation_error_message="Revisa las fechas: el ingreso no puede ser anterior "
                "al nacimiento.",
            ),
        ]
        indexes = [
            # Buscar y ordenar por apellido y nombre, sin acentos (consulta 3)
            models.Index(
                sin_acentos("primer_apellido"), sin_acentos("primer_nombre"),
                name="ix_residente_nombre",
            ),
        ]

    @property
    def nombre_completo(self) -> str:
        """Ejemplo: "Carmen Torres Vega" (sin segundo nombre). Se compone, no se guarda."""
        partes = [self.primer_nombre, self.segundo_nombre, self.primer_apellido, self.segundo_apellido]
        return " ".join(parte for parte in partes if parte)

    def __str__(self) -> str:
        return self.nombre_completo
```

### Paso 4. Migraciones (≈ 45 min)

**4.1 Migración generada:**

```bash
dj makemigrations entidades            # crea 0001_initial.py
```

Abre `0001_initial.py` y agrega a mano la dependencia de las extensiones, porque `ix_residente_nombre` usa `f_unaccent`:

```python
dependencies = [
    ("catalogo", "0001_extensiones"),   # AGREGAR: f_unaccent y los permisos de app_user
]
```

**4.2 FK compuesta** (`dj makemigrations entidades --empty --name fk_compuesta`):

```python
"""FK compuesta residente -> entidad (readme, sección 3.1).

Garantiza que solo una entidad de tipo RESIDENTE tenga fila en residente: la fila
(entidad_id, 'RESIDENTE') debe existir en entidad. Django no declara FK compuestas,
por eso va en SQL.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("entidades", "0001_initial")]
    operations = [
        migrations.RunSQL(
            "ALTER TABLE residente ADD CONSTRAINT fk_residente_entidad "
            "FOREIGN KEY (entidad_id, tipo) REFERENCES entidad (id, tipo) ON DELETE RESTRICT;",
            "ALTER TABLE residente DROP CONSTRAINT fk_residente_entidad;",
        ),
    ]
```

**4.3 El Hogar** (`dj makemigrations entidades --empty --name hogar`):

```python
"""Dato semilla: la entidad HOGAR, única (readme, sección 3.1, "Datos semilla")."""

from django.conf import settings
from django.db import migrations


def crear_hogar(apps, schema_editor):
    entidad = apps.get_model("entidades", "Entidad")
    entidad.objects.get_or_create(tipo="HOGAR", defaults={"nombre": settings.HOGAR_NOMBRE})


def quitar_hogar(apps, schema_editor):
    apps.get_model("entidades", "Entidad").objects.filter(tipo="HOGAR").delete()


class Migration(migrations.Migration):
    dependencies = [("entidades", "0002_fk_compuesta")]
    operations = [migrations.RunPython(crear_hogar, quitar_hogar)]
```

```bash
./scripts/migrate.sh
dpsql -c '\d residente'
dpsql -c "SELECT id, tipo, nombre FROM entidad"     # 1 | HOGAR | Hogar Gerontológico Demo
```

> El Hogar queda con `id = 1` en una base nueva. El dataset mock y algunas pruebas de TK-01 lo dan por hecho.

> **Diferencias de forma con el DDL de las secciones 3.1 y 3.3, con el mismo efecto.** Los nombres son idénticos; cambia cómo los escribe Django:
>
> | Readme | `\d entidad` / `\d residente` | Por qué está bien |
> |---|---|---|
> | `CHECK ((tipo = 'HOGAR') = (nombre IS NOT NULL))` y su par en `ck_residente_baja` | `(a AND b) OR (NOT a AND NOT b)` | Equivalentes; así `full_clean()` también los valida |
> | `CHECK (btrim(x) <> '')` | `CHECK (length(TRIM(BOTH FROM x)) > 0)` | Equivalentes (`no_vacio()`, como en HB-05) |
> | `DEFAULT now()` | `DEFAULT statement_timestamp()` | Es lo que genera `Now()`. Solo difiere dentro de una transacción larga |
> | `CREATE UNIQUE INDEX uq_entidad_un_hogar ... WHERE tipo = 'HOGAR'` | `UNIQUE, btree (tipo) WHERE tipo = 'HOGAR'` | Es el mismo índice único parcial, declarado como `UniqueConstraint` con `condition` |

### Paso 5. Servicio de alta de residentes (≈ 30 min)

Primero crea el esqueleto en `app/apps/entidades/services.py`, para ver el rojo real del servicio:

```python
def registrar_residente(residente):
    raise NotImplementedError
```

```bash
dtest apps/entidades -q      # fallan con NotImplementedError los que dan de alta un residente
```

Después reemplaza `app/apps/entidades/services.py` por la implementación:

```python
"""Reglas de entidades (readme, sección 3.2, D3). Las usa el panel /admin/ (HB-09)."""

from django.db import transaction

from apps.entidades.models import Entidad, Residente


@transaction.atomic
def registrar_residente(residente: Residente) -> Residente:
    """Da de alta un residente: crea su entidad (supertipo) y el residente (subtipo) juntos.

    Recibe un Residente sin guardar; si sus datos no son válidos, lanza ValidationError y
    no se crea nada. Siempre queda ACTIVO y sin fecha de baja.

    Ejemplo:
        registrar_residente(Residente(primer_nombre="Ana", primer_apellido="Ruiz",
                                      fecha_nacimiento=date(1940, 3, 1),
                                      fecha_ingreso=date(2026, 1, 5)))
    """
    if residente.pk is not None:
        raise ValueError("El residente ya está registrado.")
    residente.estado = Residente.Estado.ACTIVO
    residente.fecha_baja = None
    residente.full_clean(exclude=["entidad"])  # mensajes claros antes de tocar la base
    residente.entidad = Entidad.objects.create(tipo=Entidad.Tipo.RESIDENTE)
    residente.save(force_insert=True)
    return residente
```

### Paso 6. Tests en verde (≈ 15 min)

Ejecuta los de la sección 3 con `dtest apps/entidades -q`: todos deben pasar.

### Paso 7. Verificación final y *pull request* (≈ 30 min)

Ejecuta la sección 5 completa, marca la lista de la sección 6 y abre el PR.

---

## 3. Tests requeridos

### 3.1 `apps/entidades/tests/test_modelos.py`

```python
"""Entidades: un solo Hogar, subtipo coherente, fechas y nombres (D3)."""

from datetime import date

import pytest
from django.conf import settings
from django.db import IntegrityError, transaction

from apps.entidades.models import Entidad, Residente
from apps.entidades.services import registrar_residente
from pruebas import ejecutar_sql

pytestmark = pytest.mark.django_db


@pytest.fixture
def carmen():
    return registrar_residente(Residente(
        primer_nombre="Carmen", primer_apellido="Torres", segundo_apellido="Vega",
        fecha_nacimiento=date(1935, 7, 22), fecha_ingreso=date(2025, 1, 10),
    ))


def test_la_migracion_crea_un_solo_hogar_con_su_nombre():
    hogar = Entidad.objects.get(tipo="HOGAR")
    assert hogar.nombre == settings.HOGAR_NOMBRE
    assert str(hogar) == settings.HOGAR_NOMBRE
    assert hogar.activa


def test_no_puede_haber_un_segundo_hogar():
    with pytest.raises(IntegrityError, match="uq_entidad_un_hogar"):
        with transaction.atomic():
            Entidad.objects.create(tipo="HOGAR", nombre="Otro hogar")


def test_un_residente_no_puede_colgar_del_hogar():
    with pytest.raises(IntegrityError, match="fk_residente_entidad"):
        ejecutar_sql(
            "INSERT INTO residente (entidad_id, primer_nombre, primer_apellido, "
            "fecha_nacimiento, fecha_ingreso) "
            "SELECT id, 'Prueba', 'Prueba', '1940-01-01', '2026-01-05' FROM entidad "
            "WHERE tipo = 'HOGAR'"
        )


@pytest.mark.parametrize(("sql", "restriccion"), [
    ("INSERT INTO entidad (tipo) VALUES ('RESIDENTE'), ('HOGAR')", "ck_entidad_nombre"),
    ("INSERT INTO entidad (tipo, nombre) VALUES ('RESIDENTE', 'Con nombre')", "ck_entidad_nombre"),
    ("INSERT INTO entidad (tipo) VALUES ('OTRO')", "ck_entidad_tipo"),
])
def test_la_base_rechaza_entidades_invalidas(sql, restriccion):
    with pytest.raises(IntegrityError, match=restriccion):
        ejecutar_sql(sql)


@pytest.mark.parametrize(("cambio", "restriccion"), [
    ("estado = 'EGRESADO'", "ck_residente_baja"),
    ("fecha_baja = '2026-01-01'", "ck_residente_baja"),
    ("estado = 'EGRESADO', fecha_baja = '2000-01-01'", "ck_residente_fechas"),
    ("estado = 'PERDIDO', fecha_baja = fecha_ingreso", "ck_residente_estado"),
    ("fecha_nacimiento = '1899-12-31'", "ck_residente_nacimiento"),
    ("fecha_ingreso = '1930-01-01'", "ck_residente_nacimiento"),
    ("primer_nombre = '   '", "ck_residente_nombres"),
    ("tipo = 'HOGAR'", "ck_residente_tipo"),
])
def test_la_base_rechaza_residentes_invalidos(carmen, cambio, restriccion):
    with pytest.raises(IntegrityError, match=restriccion):
        ejecutar_sql(f"UPDATE residente SET {cambio} WHERE entidad_id = %s", [carmen.pk])


def test_nombre_completo_sin_los_nombres_vacios(carmen):
    assert str(carmen.entidad) == "Carmen Torres Vega"


@pytest.mark.parametrize(("estado", "activa"), [
    ("ACTIVO", True), ("EGRESADO", False), ("FALLECIDO", False),
])
def test_un_residente_esta_activo_solo_si_su_estado_es_activo(carmen, estado, activa):
    carmen.estado = estado
    carmen.fecha_baja = None if estado == "ACTIVO" else date(2026, 2, 1)
    carmen.save()
    assert Entidad.objects.get(pk=carmen.pk).activa is activa


def test_indice_de_nombre_sin_acentos():
    [(definicion,)] = ejecutar_sql(
        "SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_residente_nombre'"
    )
    assert "f_unaccent(lower((primer_apellido)" in definicion
    assert "f_unaccent(lower((primer_nombre)" in definicion
```

### 3.2 `apps/entidades/tests/test_services.py`

```python
"""registrar_residente: supertipo y subtipo en una sola transacción, como app_user."""

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import connection

from apps.entidades.models import Entidad, Residente
from apps.entidades.services import registrar_residente

pytestmark = pytest.mark.django_db


def nuevo(**cambios):
    datos = dict(primer_nombre="Ana", primer_apellido="Ruiz",
                 fecha_nacimiento=date(1940, 3, 1), fecha_ingreso=date(2026, 1, 5))
    return Residente(**(datos | cambios))


def test_crea_la_entidad_y_el_residente_activo():
    residente = registrar_residente(nuevo())
    assert residente.entidad.tipo == Entidad.Tipo.RESIDENTE
    assert residente.estado == Residente.Estado.ACTIVO
    assert residente.fecha_baja is None


def test_con_datos_invalidos_no_crea_nada():
    antes = Entidad.objects.count()
    with pytest.raises(ValidationError, match="ingreso no puede ser anterior"):
        registrar_residente(nuevo(fecha_ingreso=date(1930, 1, 1)))
    assert Entidad.objects.count() == antes


def test_no_registra_dos_veces_al_mismo_residente():
    residente = registrar_residente(nuevo())
    with pytest.raises(ValueError):
        registrar_residente(residente)


def test_funciona_con_los_permisos_de_la_aplicacion():
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL ROLE app_user")
    registrar_residente(nuevo(primer_nombre="Prueba"))
    with connection.cursor() as cursor:
        cursor.execute("RESET ROLE")
    assert Residente.objects.filter(primer_nombre="Prueba").exists()
```

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| Nombres de restricciones e índices **idénticos** a las secciones 3.1 y 3.3 | `dpsql -c '\d residente'` y `\d entidad` comparados con el readme |
| `activa` y `__str__` cumplen el contrato del punto de integración 11 | Tests de la sección 3.1 |
| Toda FK con `PROTECT`; la FK compuesta con `ON DELETE RESTRICT` | Revisión del PR y `\d residente` |
| Sin `save()` sobrescrito ni señales: el alta pasa por `services.py` | Revisión del PR |
| Todas las migraciones se revierten | Sección 5, paso 4 |
| Sin datos personales reales en tests ni en commits | Revisión del PR (el hook de secretos también lo revisa) |
| `ck_entidad_tipo` y `ck_residente_estado` están en el DDL de la sección 3.1 | Revisión del PR |

---

## 5. Verificación: comandos y resultado esperado

```bash
# 1. Calidad del código
docker compose exec web ruff check . && docker compose exec web ruff format --check .
dj check && dj makemigrations --check --dry-run

# 2. Tests
dtest apps/entidades -q
dtest -q --cov=apps --cov-fail-under=80

# 3. Esquema aplicado: compara contra las secciones 3.1 y 3.3
dpsql -c '\d entidad'
dpsql -c '\d residente'
# Debe aparecer: fk_residente_entidad FOREIGN KEY (entidad_id, tipo) REFERENCES entidad(id, tipo) ON DELETE RESTRICT
dpsql -c "SELECT id, tipo, nombre FROM entidad"
#  1 | HOGAR | Hogar Gerontológico Demo

# 4. Las migraciones se revierten y se vuelven a aplicar
./scripts/migrate.sh entidades zero
./scripts/migrate.sh

# 5. Alta de un residente con los permisos de la aplicación (desarrollo)
dj shell -c "
from datetime import date
from apps.entidades.models import Residente
from apps.entidades.services import registrar_residente
r = registrar_residente(Residente(primer_nombre='Ana', primer_apellido='Ruiz',
    fecha_nacimiento=date(1940, 3, 1), fecha_ingreso=date(2026, 1, 5)))
print(r.entidad, r.entidad.activa)
"
# Ana Ruiz True
```

> Si ya hiciste el paso 5, recrea la base antes de cargar el mock de la sección 3.4 (el mock solo se carga en una base sin residentes): `docker compose down -v && docker compose up -d && ./scripts/migrate.sh`.
>
> **Alternativa sin borrar la base:** ejecuta el paso 5 dentro de una transacción que se revierte. Pon el alta dentro de `with transaction.atomic():` (importa `transaction` de `django.db`) y termina el bloque con `transaction.set_rollback(True)`. La salida es la misma (`Ana Ruiz True`, como `app_user`), y `dpsql -tAc "SELECT count(*) FROM residente"` sigue en 0.
>
> **Nota sobre los tests de la sección 3:** el caso de estado desconocido usa `'PERDIDO'`, no `'DESAPARECIDO'`. `estado` es `varchar(10)`, y un valor más largo falla con `DataError: value too long` antes de llegar a `ck_residente_estado`. El PR agrega además tests para el `id = 1` del Hogar, `ck_entidad_nombre_no_vacio`, la definición de `fk_residente_entidad` y `uq_entidad_id_tipo`, `primer_apellido` vacío y el alta que siempre queda `ACTIVO`.
>
> **Ajustes tras la revisión adversarial** (cambio de OpenSpec `hb-06-ajustes-revision`). El código de los pasos 3 a 5 de esta guía es el original (el paso 2 ya muestra el actual). El que está en el repositorio cambia en esto:
> - `Entidad.activa` y `__str__`: una Entidad `RESIDENTE` sin su fila en `residente` no está activa y se muestra como `Entidad <id>`, sin excepción. Las listas usan `select_related("residente")`, y así no hay una consulta por fila.
> - `registrar_residente()`:
>   - usa `_state.adding` y `pk` para saber si el Residente ya está registrado;
>   - quita los espacios de los extremos de los nombres, y el segundo nombre o el segundo apellido vacíos se guardan como `NULL`;
>   - si el alta falla, el objeto recibido queda como estaba.
> - `Residente.nombre_completo` no deja espacios de más.
> - `ck_residente_nombres` tiene mensaje propio (migración `0004_mensaje_nombres`, que no cambia la base).
> - `HOGAR_NOMBRE`: `docker-compose.yml` ya no le da un valor por defecto, y `config.settings.prod` no arranca sin ella. Desarrollo y CI siguen usando "Hogar Gerontológico Demo" (`app/config/tests/test_configuracion.py`).
>
> **Segunda revisión** (cambio `hb-06-ajustes-revision-2`):
> - `registrar_residente()` también rechaza un Residente que ya trae Entidad. Si el alta falla, restaura todos los campos recibidos, incluidas las fechas que `full_clean` convierte.
> - Los tests del reintento provocan fallas reales de PostgreSQL, sin `monkeypatch`: un `CHECK ... NOT VALID` hace fallar el guardado, y un `UNIQUE ... DEFERRABLE`, en un test con `transaction=True`, la confirmación.
> - `HOGAR_NOMBRE` admite como máximo 150 caracteres en todos los entornos.

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] La descripción del PR incluye la salida de `\d residente` y la fila del Hogar.

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `function f_unaccent(text) does not exist` al migrar | `0001_initial` no depende de `catalogo.0001_extensiones` | Paso 4.1 |
| `there is no unique constraint matching given keys for referenced table "entidad"` | `uq_entidad_id_tipo` no existe al crear la FK | `0002_fk_compuesta` debe depender de `0001_initial` |
| Una Entidad aparece como `Entidad <id>` y no está activa | Se creó una entidad RESIDENTE sin su residente | Da de alta solo con `registrar_residente()` |
| `insert or update on table "residente" violates foreign key constraint "fk_residente_entidad"` | El residente apunta a una entidad que no es `RESIDENTE` | Usa `registrar_residente()` |
| El Hogar no tiene el nombre esperado (desarrollo) | Se migró con otro valor de `HOGAR_NOMBRE` en el entorno de `web` | Desde TK-01, `.env` admite el valor con espacios sin comillas. Sin la variable, el Hogar se llama "Hogar Gerontológico Demo"; recrea la base (`docker compose down -v`, `up -d` y `./scripts/migrate.sh`) |
| `ImproperlyConfigured: Falta HOGAR_NOMBRE en .env` | `config.settings.prod` exige `HOGAR_NOMBRE` | En el servidor, defínela en `.env` con el nombre real (o el de la demo, si es la demo). Para `check --deploy` en desarrollo, pásala con `-e HOGAR_NOMBRE=...` |
| `ImproperlyConfigured: HOGAR_NOMBRE tiene N caracteres; el máximo es 150` | El nombre no cabe en `entidad.nombre` (`varchar(150)`) | Acórtalo en `.env` (o en el entorno de `web`) a 150 caracteres o menos |
