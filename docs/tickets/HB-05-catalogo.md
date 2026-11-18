# HB-05 · Guía paso a paso: catálogo de medicamentos (D2)

> **Ticket:** [readme, sección 6, HB-05](../../readme.md#tickets-de-habilitación-hb-01-a-hb-09) · **Tipo:** base de datos · **Estimación:** 3 puntos · **Rama:** `feature/HB-05-catalogo`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket y en las secciones 3.1, 3.2 (D2) y 3.3 del readme. Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.
>
> **Integración** (readme, sección 6, "Puntos de integración"): este ticket **provee** el punto 6 (búsqueda sin acentos: `f_unaccent` e índices trigram), que consume TK-03.

**Resultado al terminar:** existen las extensiones `pg_trgm`, `unaccent` y `btree_gist`, la función `f_unaccent` y las tablas `presentacion`, `principio_activo`, `medicamento` y `medicamento_principio_activo`, con sus restricciones e índices con los nombres exactos del readme. Las 8 presentaciones semilla están cargadas. No se puede registrar dos veces "Losartán 50 mg tableta", aunque se escriba "LOSARTAN 50 MG".

---

## 0. Antes de empezar

### 0.1 Lee primero (30 min)

| Qué | Dónde | Para qué |
|---|---|---|
| D2 — Medicamentos | readme, sección 3.2 | Columnas, tipos y reglas de las 4 tablas |
| DDL de D2 y extensiones | readme, sección 3.1 | Nombres exactos de las restricciones |
| Consulta 1, índices y "Índices de FK que Django no debe crear" | readme, sección 3.3 | Qué índice atiende cada consulta y qué FK no llevan índice propio |
| Restricciones de integridad adicionales | readme, sección 3.3 | `ck_medicamento_textos`, `ck_principio_activo_nombre`, `ck_presentacion_nombre` |
| Implementación en Django | readme, sección 3.3 | `GinIndex(OpClass(...))` y la expresión `f_unaccent(lower(...))` |

### 0.2 Requisitos previos

- HB-03 integrado en `main` (los atajos `dj`, `dtest` y `dpsql` de su guía, paso 0.3).
- `dj showmigrations accounts` muestra `[X] 0002_privilegios`.

### 0.3 Crea la rama

```bash
git switch main && git pull
git switch -c feature/HB-05-catalogo
```

---

## 1. Archivos que vas a crear o modificar

```
app/
├── config/settings/base.py                  # MODIFICAR: "apps.catalogo" en INSTALLED_APPS
└── apps/
    ├── expresiones.py                       # NUEVO: sin_acentos() y no_vacio(), compartidas
    └── catalogo/
        ├── __init__.py                      # NUEVO (vacío)
        ├── apps.py                          # NUEVO
        ├── models.py                        # NUEVO: Presentacion, PrincipioActivo, Medicamento, MedicamentoPrincipioActivo
        ├── migrations/
        │   ├── __init__.py                  # NUEVO (vacío)
        │   ├── 0001_extensiones.py          # NUEVO: extensiones y f_unaccent
        │   ├── 0002_modelos.py              # GENERADO con makemigrations
        │   └── 0003_presentaciones.py       # NUEVO: datos semilla
        └── tests/
            ├── __init__.py                  # NUEVO (vacío)
            └── test_modelos.py              # NUEVO
```

---

## 2. Tareas paso a paso

El orden sigue TDD (`CLAUDE.md`): primero los tests en rojo, después la implementación.

### Paso 1. Tests en rojo (≈ 45 min)

Crea solo lo necesario para que pytest encuentre los tests:

```bash
mkdir -p app/apps/catalogo/tests
touch app/apps/catalogo/__init__.py app/apps/catalogo/tests/__init__.py
```

Escribe los tests de la sección 3 y ejecútalos **antes** de implementar:

```bash
dtest apps/catalogo -q
# ModuleNotFoundError: No module named 'apps.catalogo.models'
```

> El error de importación es el rojo inicial: indica que el módulo aún no existe. El rojo útil llega después, cuando el módulo ya existe y fallan las reglas.

Así avanza `dtest apps/catalogo -q` con cada paso:

| Al terminar | Resultado esperado |
|---|---|
| Paso 4 (modelos) | Pasan extensiones, `f_unaccent`, principios activos e índices. Siguen en rojo los que necesitan las presentaciones semilla |
| Paso 5 (semilla) | Todos pasan |

### Paso 2. La app y la migración de extensiones (≈ 30 min)

```bash
mkdir -p app/apps/catalogo/migrations app/apps/catalogo/tests
touch app/apps/catalogo/__init__.py app/apps/catalogo/models.py \
      app/apps/catalogo/migrations/__init__.py app/apps/catalogo/tests/__init__.py
```

`app/apps/catalogo/apps.py`:

```python
from django.apps import AppConfig


class CatalogoConfig(AppConfig):
    name = "apps.catalogo"
    label = "catalogo"
    verbose_name = "Catálogo de medicamentos"
```

Agrega `"apps.catalogo"` a `INSTALLED_APPS` (debajo de `"apps.accounts"`) y crea la primera migración, vacía:

```bash
dj makemigrations catalogo --empty --name extensiones
```

Reemplaza el contenido de `0001_extensiones.py`:

```python
"""Extensiones y función f_unaccent (readme, sección 3.1).

Van antes que las tablas: los índices y restricciones del catálogo, de residentes y de
pautas las usan. app_owner puede crearlas porque es dueño de la base y las 3 son
extensiones "de confianza" (trusted) de PostgreSQL.
"""

from django.contrib.postgres.operations import (
    BtreeGistExtension,
    TrigramExtension,
    UnaccentExtension,
)
from django.db import migrations

# Envoltura IMMUTABLE de unaccent: PostgreSQL solo acepta funciones IMMUTABLE en índices
F_UNACCENT = """
CREATE FUNCTION f_unaccent(text) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    RETURN public.unaccent('public.unaccent'::regdictionary, $1);
"""


class Migration(migrations.Migration):
    initial = True
    # Las tablas que vienen después deben nacer con los permisos de app_user
    dependencies = [("accounts", "0002_privilegios")]
    operations = [
        BtreeGistExtension(),  # restricción de exclusión de pautas (HB-07)
        TrigramExtension(),    # pg_trgm: búsqueda parcial por nombre (sección 3.3)
        UnaccentExtension(),   # "Losartán" = "losartan"
        migrations.RunSQL(F_UNACCENT, "DROP FUNCTION f_unaccent(text);"),
    ]
```

### Paso 3. Expresiones compartidas (≈ 15 min)

`app/apps/expresiones.py`. Las usan los modelos de este ticket, los de HB-06 y HB-07, y el panel de HB-09:

```python
"""Expresiones SQL compartidas por los modelos (readme, sección 3.3)."""

from django.db import models
from django.db.models import Func
from django.db.models.functions import Length, Lower, Trim
from django.db.models.lookups import GreaterThan


def sin_acentos(campo) -> Func:
    """f_unaccent(lower(campo)): la misma expresión de los índices trigram (sección 3.3).

    Si la consulta no usa exactamente esta expresión, PostgreSQL no usa el índice.
    Ejemplo: Medicamento.objects.annotate(n=sin_acentos("nombre_comercial"))
                                .filter(n__contains="losartan")
    """
    return Func(Lower(campo), function="f_unaccent", output_field=models.CharField())


def no_vacio(campo: str) -> GreaterThan:
    """Equivale a btrim(campo) <> '': el texto no puede ser solo espacios (sección 3.3)."""
    return GreaterThan(Length(Trim(campo)), 0)
```

### Paso 4. Modelos (≈ 1 h)

`app/apps/catalogo/models.py`. Lee los comentarios: explican cada decisión.

```python
"""Catálogo de medicamentos (readme, sección 3.2, D2).

Los modelos no tienen lógica: las reglas viven en Meta.constraints (que Django valida en
los formularios del panel) y en la base de datos, que es la última barrera.
"""

from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now

from apps.expresiones import no_vacio, sin_acentos


class Presentacion(models.Model):
    """Forma farmacéutica: tableta, cápsula, jarabe..."""

    id = models.SmallAutoField(primary_key=True)
    nombre = models.CharField(max_length=60, unique=True)
    # default para los formularios y db_default para la base (INSERT directo, mock)
    activo = models.BooleanField(default=True, db_default=True)

    class Meta:
        db_table = "presentacion"
        verbose_name = "presentación"
        verbose_name_plural = "presentaciones"
        constraints = [
            models.CheckConstraint(condition=no_vacio("nombre"), name="ck_presentacion_nombre"),
        ]

    def __str__(self) -> str:
        return self.nombre


class PrincipioActivo(models.Model):
    """Sustancia activa: paracetamol, losartán..."""

    nombre = models.CharField(max_length=150)
    creado_en = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "principio_activo"
        verbose_name = "principio activo"
        verbose_name_plural = "principios activos"
        constraints = [
            # Índice único por expresión: "Paracetamol" = "paracetamol" = "PARACETAMOL"
            models.UniqueConstraint(
                sin_acentos("nombre"),
                name="uq_principio_activo_nombre",
                violation_error_message="Ya existe ese principio activo "
                "(sin distinguir mayúsculas ni acentos).",
            ),
            models.CheckConstraint(
                condition=no_vacio("nombre"), name="ck_principio_activo_nombre"
            ),
        ]
        indexes = [
            GinIndex(
                OpClass(sin_acentos("nombre"), name="gin_trgm_ops"),
                name="ix_principio_activo_trgm",
            ),
        ]

    def __str__(self) -> str:
        return self.nombre


class Medicamento(models.Model):
    """Producto del catálogo. La baja es lógica (activo = False)."""

    class Tipo(models.TextChoices):
        GENERICO = "GENERICO", "Genérico"
        ORIGINAL = "ORIGINAL", "Original"

    nombre_comercial = models.CharField(max_length=150)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    presentacion = models.ForeignKey(
        Presentacion, on_delete=models.PROTECT, related_name="medicamentos"
    )
    concentracion = models.CharField(max_length=60, help_text="Ejemplo: 500 mg, 50 mg / 12.5 mg")
    activo = models.BooleanField(default=True, db_default=True)
    creado_en = models.DateTimeField(db_default=Now(), editable=False)
    actualizado_en = models.DateTimeField(auto_now=True, db_default=Now())
    principios_activos = models.ManyToManyField(
        PrincipioActivo, through="MedicamentoPrincipioActivo", related_name="medicamentos"
    )

    class Meta:
        db_table = "medicamento"
        constraints = [
            # Sin duplicados de nombre + presentación + concentración, sin distinguir
            # mayúsculas ni acentos. Aplica también a los inactivos: se reactivan.
            models.UniqueConstraint(
                sin_acentos("nombre_comercial"),
                "presentacion",
                sin_acentos("concentracion"),
                name="uq_medicamento_nombre_pres_conc",
                violation_error_message="Ya existe un medicamento con ese nombre, presentación "
                "y concentración. Si está dado de baja, reactívalo.",
            ),
            models.CheckConstraint(
                condition=Q(tipo__in=["GENERICO", "ORIGINAL"]), name="ck_medicamento_tipo"
            ),
            models.CheckConstraint(
                condition=no_vacio("nombre_comercial") & no_vacio("concentracion"),
                name="ck_medicamento_textos",
            ),
        ]
        indexes = [
            # Búsqueda parcial por nombre, solo en el catálogo vigente (consulta 1)
            GinIndex(
                OpClass(sin_acentos("nombre_comercial"), name="gin_trgm_ops"),
                name="ix_medicamento_nombre_trgm",
                condition=Q(activo=True),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nombre_comercial} {self.concentracion}"


class MedicamentoPrincipioActivo(models.Model):
    """Tabla puente: un medicamento tiene uno o más principios activos."""

    # db_index=False: ya los cubren el UNIQUE y ix_mpa_principio_medicamento (sección 3.3)
    medicamento = models.ForeignKey(Medicamento, on_delete=models.PROTECT, db_index=False)
    principio_activo = models.ForeignKey(
        PrincipioActivo, on_delete=models.PROTECT, db_index=False
    )

    class Meta:
        db_table = "medicamento_principio_activo"
        verbose_name = "principio activo del medicamento"
        verbose_name_plural = "principios activos del medicamento"
        constraints = [
            models.UniqueConstraint(
                fields=["medicamento", "principio_activo"], name="uq_mpa_medicamento_principio"
            ),
        ]
        indexes = [
            models.Index(
                fields=["principio_activo", "medicamento"], name="ix_mpa_principio_medicamento"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.medicamento} · {self.principio_activo}"
```

Genera la migración y revisa el SQL contra el readme:

```bash
dj makemigrations catalogo --name modelos     # crea 0002_modelos.py
dj sqlmigrate catalogo 0002 | grep -E "CONSTRAINT|INDEX"
```

Debes ver `uq_principio_activo_nombre`, `uq_medicamento_nombre_pres_conc` (como `CREATE UNIQUE INDEX` con `f_unaccent(LOWER(...))`), `ck_*`, los 2 índices `gin_trgm_ops` y `ix_mpa_principio_medicamento`, y **ningún** índice suelto sobre `medicamento_principio_activo.medicamento_id` ni `principio_activo_id`.

### Paso 5. Presentaciones semilla (≈ 15 min)

```bash
dj makemigrations catalogo --empty --name presentaciones
```

`0003_presentaciones.py`:

```python
"""Presentaciones más comunes (readme, sección 3.1, "Datos semilla"). Idempotente."""

from django.db import migrations

PRESENTACIONES = [
    "tableta", "cápsula", "jarabe", "gotas", "ampolleta", "parche", "crema", "inhalador",
]


def crear(apps, schema_editor):
    presentacion = apps.get_model("catalogo", "Presentacion")
    for nombre in PRESENTACIONES:
        presentacion.objects.get_or_create(nombre=nombre)


def quitar(apps, schema_editor):
    apps.get_model("catalogo", "Presentacion").objects.filter(nombre__in=PRESENTACIONES).delete()


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0002_modelos")]
    operations = [migrations.RunPython(crear, quitar)]
```

```bash
./scripts/migrate.sh
dpsql -c '\d medicamento'
```

### Paso 6. Tests en verde (≈ 15 min)

Ejecuta los de la sección 3 con `dtest apps/catalogo -q`: todos deben pasar. El de plan de ejecución está marcado `lento`: córrelo aparte con `dtest -m lento apps/catalogo -q`.

### Paso 7. Verificación final y *pull request* (≈ 30 min)

Ejecuta la sección 5 completa, marca la lista de la sección 6 y abre el PR.

---

## 3. Tests requeridos

`apps/catalogo/tests/test_modelos.py`:

```python
"""Catálogo de medicamentos: unicidad sin acentos, textos obligatorios e índices (D2)."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from apps.catalogo.models import Medicamento, Presentacion, PrincipioActivo
from apps.expresiones import sin_acentos
from pruebas import ejecutar_sql

pytestmark = pytest.mark.django_db


@pytest.fixture
def tableta():
    return Presentacion.objects.get(nombre="tableta")


def nuevo_medicamento(presentacion, nombre="Losartán", concentracion="50 mg"):
    return Medicamento(
        nombre_comercial=nombre, tipo="GENERICO", presentacion=presentacion,
        concentracion=concentracion,
    )


def test_las_extensiones_estan_instaladas():
    instaladas = {nombre for (nombre,) in ejecutar_sql("SELECT extname FROM pg_extension")}
    assert {"pg_trgm", "unaccent", "btree_gist"} <= instaladas


def test_f_unaccent_quita_acentos():
    assert ejecutar_sql("SELECT f_unaccent(lower('Losartán ÁCIDO Ñandú'))") == [
        ("losartan acido nandu",)
    ]


def test_las_8_presentaciones_semilla():
    assert set(Presentacion.objects.values_list("nombre", flat=True)) == {
        "tableta", "cápsula", "jarabe", "gotas", "ampolleta", "parche", "crema", "inhalador",
    }


def test_medicamento_duplicado_sin_mayusculas_ni_acentos(tableta):
    nuevo_medicamento(tableta).save()
    with pytest.raises(IntegrityError, match="uq_medicamento_nombre_pres_conc"):
        with transaction.atomic():
            nuevo_medicamento(tableta, nombre="LOSARTAN", concentracion="50 MG").save()


def test_el_formulario_avisa_el_duplicado_antes_de_llegar_a_la_base(tableta):
    nuevo_medicamento(tableta).save()
    with pytest.raises(ValidationError, match="Ya existe un medicamento"):
        nuevo_medicamento(tableta, nombre="losartan").full_clean()


def test_otra_concentracion_no_es_duplicado(tableta):
    nuevo_medicamento(tableta).save()
    nuevo_medicamento(tableta, concentracion="100 mg").save()
    assert Medicamento.objects.count() == 2


def test_principio_activo_unico_sin_acentos():
    PrincipioActivo.objects.create(nombre="Ácido acetilsalicílico")
    with pytest.raises(IntegrityError, match="uq_principio_activo_nombre"):
        with transaction.atomic():
            PrincipioActivo.objects.create(nombre="acido acetilsalicilico")


@pytest.mark.parametrize(("sql", "restriccion"), [
    ("INSERT INTO medicamento (nombre_comercial, tipo, presentacion_id, concentracion) "
     "SELECT '   ', 'GENERICO', id, '50 mg' FROM presentacion LIMIT 1", "ck_medicamento_textos"),
    ("INSERT INTO medicamento (nombre_comercial, tipo, presentacion_id, concentracion) "
     "SELECT 'Prueba', 'OTRO', id, '50 mg' FROM presentacion LIMIT 1", "ck_medicamento_tipo"),
    ("INSERT INTO principio_activo (nombre) VALUES ('  ')", "ck_principio_activo_nombre"),
    ("INSERT INTO presentacion (nombre) VALUES ('')", "ck_presentacion_nombre"),
])
def test_la_base_rechaza(sql, restriccion):
    with pytest.raises(IntegrityError, match=restriccion):
        ejecutar_sql(sql)


@pytest.mark.parametrize(("indice", "fragmentos"), [
    ("ix_medicamento_nombre_trgm", ["USING gin", "f_unaccent(lower(", "gin_trgm_ops", "WHERE activo"]),
    ("ix_principio_activo_trgm", ["USING gin", "f_unaccent(lower(", "gin_trgm_ops"]),
    ("ix_mpa_principio_medicamento", ["(principio_activo_id, medicamento_id)"]),
    ("uq_medicamento_nombre_pres_conc", ["UNIQUE", "presentacion_id"]),
])
def test_indices_con_su_definicion(indice, fragmentos):
    [(definicion,)] = ejecutar_sql(
        "SELECT indexdef FROM pg_indexes WHERE indexname = %s", [indice]
    )
    for fragmento in fragmentos:
        assert fragmento in definicion


def test_las_fk_de_la_tabla_puente_no_tienen_indice_propio():
    sueltos = ejecutar_sql(
        "SELECT indexname FROM pg_indexes WHERE tablename = 'medicamento_principio_activo' "
        "AND indexname NOT IN ('medicamento_principio_activo_pkey', "
        "'uq_mpa_medicamento_principio', 'ix_mpa_principio_medicamento')"
    )
    assert sueltos == []


def test_app_user_puede_registrar_en_el_catalogo():
    ejecutar_sql("INSERT INTO principio_activo (nombre) VALUES ('Prueba activa')", rol="app_user")
    assert PrincipioActivo.objects.filter(nombre="Prueba activa").exists()


@pytest.mark.lento
def test_la_busqueda_por_nombre_usa_el_indice_trigram(tableta):
    consulta = (
        Medicamento.objects.filter(activo=True)
        .annotate(n=sin_acentos("nombre_comercial"))
        .filter(n__contains="losar")
    )
    sql, parametros = consulta.query.sql_with_params()
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_seqscan = off")  # la tabla es pequeña: se fuerza el índice
        cursor.execute(f"EXPLAIN {sql}", parametros)
        plan = "\n".join(fila for (fila,) in cursor.fetchall())
    assert "ix_medicamento_nombre_trgm" in plan
```

> El test de plan valida que la expresión del ORM sea **idéntica** a la del índice. Si alguien cambia `sin_acentos()` por `Unaccent(Lower(...))` de `django.contrib.postgres`, el plan deja de usar el índice y el test falla (es el error 1 de la revisión de TK-03, sección 7).

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| Nombres de tablas, restricciones e índices **idénticos** a las secciones 3.1 y 3.3 | `dpsql -c '\d medicamento'` comparado con el readme |
| Ningún nombre de índice pasa de 30 caracteres | `dj check` sin `models.E034` |
| Sin índices duplicados sobre las FK de la tabla puente | `test_las_fk_de_la_tabla_puente_no_tienen_indice_propio` |
| Todas las FK con `on_delete=PROTECT` | Revisión del PR |
| Todas las migraciones se revierten | Sección 5, paso 4 |
| Modelos sin lógica (sin `save()` ni señales) | Revisión del PR |
| Las restricciones con nombre nuevo (`ck_medicamento_tipo`, `uq_mpa_medicamento_principio`) están en el DDL de la sección 3.1 | Revisión del PR |

---

## 5. Verificación: comandos y resultado esperado

```bash
# 1. Calidad del código
docker compose exec web ruff check . && docker compose exec web ruff format --check .
dj check && dj makemigrations --check --dry-run

# 2. Tests (incluido el de plan de ejecución)
dtest apps/catalogo -q
dtest -m lento apps/catalogo -q
dtest -q --cov=apps --cov-fail-under=80

# 3. Esquema aplicado: compara contra las secciones 3.1 y 3.3
dpsql -c '\dx'                      # btree_gist, pg_trgm, unaccent (y plpgsql)
dpsql -c '\d medicamento'
dpsql -c '\d medicamento_principio_activo'
dpsql -c "SELECT nombre FROM presentacion ORDER BY id"     # 8 filas

# 4. Las migraciones se revierten y se vuelven a aplicar
./scripts/migrate.sh catalogo zero
dpsql -c '\dx'                      # ya no están pg_trgm, unaccent ni btree_gist
./scripts/migrate.sh

# 5. Búsqueda sin acentos desde el ORM (como app_user)
dj shell -c "
from apps.catalogo.models import Medicamento, Presentacion
from apps.expresiones import sin_acentos
t = Presentacion.objects.get(nombre='tableta')
Medicamento.objects.create(nombre_comercial='Losartán', tipo='GENERICO', presentacion=t, concentracion='50 mg')
print(Medicamento.objects.annotate(n=sin_acentos('nombre_comercial')).filter(n__contains='losartan').count())
Medicamento.objects.all().delete()   # solo en desarrollo: deja la base vacía
"
# 1
```

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] La descripción del PR incluye la salida de `\d medicamento` y de `dtest -m lento`.
- [ ] Si algún nombre o tipo cambió respecto de la sección 3, el readme está actualizado.

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `permission denied to create extension "pg_trgm"` | La base no es de `app_owner`, o migraste con `dj migrate` | HB-01 (dueño de la base) y `./scripts/migrate.sh` |
| `function f_unaccent(text) does not exist` al migrar `0002` | `0002_modelos` no depende de `0001_extensiones` | Genera `0002` **después** de `0001` (paso 2) |
| `functions in index expression must be marked IMMUTABLE` | Usaste `unaccent()` directamente en el índice | Usa `sin_acentos()`, que llama a `f_unaccent` |
| `models.E034: The index name ... cannot be longer than 30 characters` | Nombre de índice largo | Usa los nombres de la sección 3.3 |
| `TypeError: ... unexpected keyword argument 'condition'` en `CheckConstraint` | Django menor a 5.1 | Verifica `requirements.txt`: Django 5.2 LTS |
| El test de plan muestra `Seq Scan` | La expresión del ORM no es igual a la del índice, o faltó `enable_seqscan = off` | Usa `sin_acentos()` y el test tal cual |
| `permission denied for table medicamento` desde `dj shell` | La migración no dependía de `0002_privilegios` | Paso 2 (`dependencies`) y recrea la base |
