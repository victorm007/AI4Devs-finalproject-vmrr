# HB-07 · Guía paso a paso: esquema de pautas (D6)

> **Ticket:** [readme, sección 6, HB-07](../../readme.md#tickets-de-habilitación-hb-01-a-hb-09) · **Tipo:** base de datos · **Estimación:** 2 puntos · **Rama:** `feature/HB-07-pautas`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket y en las secciones 3.1, 3.2 (D6) y 3.3 del readme. Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.

**Resultado al terminar:** existe la tabla `pauta` con sus restricciones (`ck_pauta_*` y la de exclusión `ex_pauta_sin_traslape`), sus 2 índices y el *trigger* `tg_pauta_validar`. Ninguna pauta se traslapa con otra del mismo residente y medicamento, y solo se registran pautas de residentes activos con medicamentos activos.

**Por qué ahora, si las pautas son *Could*:** las pantallas de pautas quedan para después (sección 5), pero el dataset mock (sección 3.4) inserta 3 pautas y TK-01 lo carga en sus tests. Sin esta tabla, el mock falla. Este ticket hace **solo el esquema**: sin pantallas y sin registro en `/admin/`.

---

## 0. Antes de empezar

### 0.1 Lee primero (20 min)

| Qué | Dónde | Para qué |
|---|---|---|
| D6 — Pautas | readme, sección 3.2 | Columnas, tipos y reglas |
| DDL de D6 | readme, sección 3.1 | `ck_pauta_dosis`, `ck_pauta_frecuencia`, `ck_pauta_fechas`, `ex_pauta_sin_traslape` |
| Consulta 3 y "Índices de FK que Django no debe crear" | readme, sección 3.3 | `ix_pauta_vigente`, `ix_pauta_residente_inicio`; `pauta.residente_id` sin índice propio |
| *Trigger* de pautas | readme, sección 3.3 | `fn_pauta_validar` / `tg_pauta_validar` |
| `ExclusionConstraint` | <https://docs.djangoproject.com/en/5.2/ref/contrib/postgres/constraints/> | Ejemplo con `daterange` |

### 0.2 Requisitos previos

- HB-05 y HB-06 integrados en `main` (`btree_gist`, `Medicamento` y `Residente`).

### 0.3 Crea la rama

```bash
git switch main && git pull
git switch -c feature/HB-07-pautas
```

---

## 1. Archivos que vas a crear o modificar

```
app/
├── config/settings/base.py           # MODIFICAR: "apps.pautas" en INSTALLED_APPS
└── apps/pautas/
    ├── __init__.py                   # NUEVO (vacío)
    ├── apps.py                       # NUEVO
    ├── models.py                     # NUEVO: Pauta
    ├── migrations/
    │   ├── __init__.py               # NUEVO (vacío)
    │   ├── 0001_initial.py           # GENERADO con makemigrations
    │   └── 0002_trigger.py           # NUEVO: fn_pauta_validar + tg_pauta_validar
    └── tests/
        ├── __init__.py               # NUEVO (vacío)
        └── test_esquema.py           # NUEVO
```

---

## 2. Tareas paso a paso

El orden sigue TDD (`CLAUDE.md`): primero los tests en rojo, después la implementación.

### Paso 1. Tests en rojo (≈ 35 min)

Crea solo lo necesario para que pytest encuentre los tests:

```bash
mkdir -p app/apps/pautas/tests
touch app/apps/pautas/__init__.py app/apps/pautas/tests/__init__.py
```

Escribe los tests de la sección 3 y ejecútalos **antes** de implementar:

```bash
dtest apps/pautas -q
# ModuleNotFoundError: No module named 'apps.pautas.models'
```

> El error de importación es el rojo inicial: indica que el módulo aún no existe. El rojo útil llega después, cuando el módulo ya existe y fallan las reglas.

Así avanza `dtest apps/pautas -q` con cada paso:

| Al terminar | Resultado esperado |
|---|---|
| Paso 2 (modelo) | Fallan solo `test_no_se_registra_pauta_a_un_residente_egresado` y `test_no_se_registra_pauta_de_un_medicamento_dado_de_baja`: aún no existe el *trigger* |
| Paso 3 (*trigger*) | Todos pasan |

### Paso 2. La app y el modelo (≈ 1 h)

```bash
mkdir -p app/apps/pautas/migrations app/apps/pautas/tests
touch app/apps/pautas/__init__.py app/apps/pautas/migrations/__init__.py \
      app/apps/pautas/tests/__init__.py
```

`app/apps/pautas/apps.py`:

```python
from django.apps import AppConfig


class PautasConfig(AppConfig):
    name = "apps.pautas"
    label = "pautas"
    verbose_name = "Pautas"
```

Agrega `"apps.pautas"` a `INSTALLED_APPS`, debajo de `"apps.entidades"`.

`app/apps/pautas/models.py`:

```python
"""Pauta del residente: dosis y frecuencia, con vigencia (readme, sección 3.2, D6).

Es informativa: no mueve existencias. Para cambiar una pauta se cierra la vigente
(fecha_fin) y se crea otra, así se conserva el historial.
"""

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeBoundary, RangeOperators
from django.db import models
from django.db.models import F, Func, Q
from django.db.models.functions import Now


class RangoDeFechas(Func):
    """daterange(fecha_inicio, fecha_fin, '[]'): la vigencia, con ambos extremos incluidos."""

    function = "daterange"
    output_field = DateRangeField()


class Pauta(models.Model):
    # db_index=False: lo cubre ix_pauta_residente_inicio (sección 3.3)
    residente = models.ForeignKey(
        "entidades.Residente", on_delete=models.PROTECT, related_name="pautas", db_index=False
    )
    medicamento = models.ForeignKey(
        "catalogo.Medicamento", on_delete=models.PROTECT, related_name="pautas"
    )
    dosis = models.DecimalField(max_digits=6, decimal_places=2, help_text="Dosis por toma: 0.5, 1, 2…")
    frecuencia_horas = models.SmallIntegerField(help_text="Cada cuántas horas: 8, 12, 24; semanal = 168")
    si_necesario = models.BooleanField(default=False, db_default=False)
    indicaciones = models.TextField(null=True, blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True, help_text="Vacía = vigente")
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pautas_registradas"
    )
    creado_en = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "pauta"
        constraints = [
            models.CheckConstraint(condition=Q(dosis__gt=0), name="ck_pauta_dosis"),
            models.CheckConstraint(
                condition=Q(frecuencia_horas__gte=1, frecuencia_horas__lte=168),
                name="ck_pauta_frecuencia",
            ),
            models.CheckConstraint(
                condition=Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=F("fecha_inicio")),
                name="ck_pauta_fechas",
            ),
            # Sin vigencias traslapadas para el mismo residente y medicamento (usa btree_gist)
            ExclusionConstraint(
                name="ex_pauta_sin_traslape",
                expressions=[
                    ("residente", RangeOperators.EQUAL),
                    ("medicamento", RangeOperators.EQUAL),
                    (
                        RangoDeFechas("fecha_inicio", "fecha_fin", RangeBoundary(True, True)),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                violation_error_message="Ya hay una pauta vigente de este medicamento para el "
                "residente en esas fechas. Cierra la anterior antes de registrar la nueva.",
            ),
        ]
        indexes = [
            # Consulta 3a: pautas abiertas (casi todas las vigentes)
            models.Index(
                fields=["residente", "medicamento"], condition=Q(fecha_fin__isnull=True),
                name="ix_pauta_vigente",
            ),
            # Consulta 3b: pautas de un residente, las más recientes primero
            models.Index(fields=["residente", "-fecha_inicio"], name="ix_pauta_residente_inicio"),
        ]

    def __str__(self) -> str:
        return f"{self.medicamento} · {self.dosis} cada {self.frecuencia_horas} h"
```

```bash
dj makemigrations pautas               # crea 0001_initial.py
dj sqlmigrate pautas 0001 | grep -E "EXCLUDE|INDEX|CHECK"
```

Debes ver `EXCLUDE USING GIST ("residente_id" WITH =, "medicamento_id" WITH =, daterange(... '[]') WITH &&)`, los 3 `CHECK`, los 2 índices y el de `registrado_por_id` y `medicamento_id` que crea Django, pero **ninguno** suelto sobre `residente_id`.

### Paso 3. *Trigger* de validación (≈ 30 min)

```bash
dj makemigrations pautas --empty --name trigger
```

`0002_trigger.py` (SQL copiado de la sección 3.3):

```python
"""Solo se registran pautas de residentes activos y medicamentos activos (sección 3.3)."""

from django.db import migrations

VALIDAR = """
CREATE FUNCTION fn_pauta_validar() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM residente
                   WHERE entidad_id = NEW.residente_id AND estado = 'ACTIVO') THEN
        RAISE EXCEPTION 'El residente % no está activo', NEW.residente_id;
    END IF;
    IF NOT (SELECT activo FROM medicamento WHERE id = NEW.medicamento_id) THEN
        RAISE EXCEPTION 'El medicamento % está dado de baja', NEW.medicamento_id;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_pauta_validar BEFORE INSERT ON pauta
    FOR EACH ROW EXECUTE FUNCTION fn_pauta_validar();
"""


class Migration(migrations.Migration):
    dependencies = [("pautas", "0001_initial")]
    operations = [
        migrations.RunSQL(
            VALIDAR,
            "DROP TRIGGER tg_pauta_validar ON pauta; DROP FUNCTION fn_pauta_validar();",
        ),
    ]
```

```bash
./scripts/migrate.sh
dpsql -c '\d pauta'
```

### Paso 4. Tests en verde (≈ 10 min)

Ejecuta los de la sección 3 con `dtest apps/pautas -q`: todos deben pasar.

### Paso 5. Verificación final y *pull request* (≈ 20 min)

Ejecuta la sección 5 completa, marca la lista de la sección 6 y abre el PR.

---

## 3. Tests requeridos

`apps/pautas/tests/test_esquema.py`:

```python
"""Pautas: dosis, frecuencia, vigencias sin traslape y solo residentes/medicamentos activos."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction

from apps.catalogo.models import Medicamento, Presentacion
from apps.entidades.models import Residente
from apps.entidades.services import registrar_residente
from apps.pautas.models import Pauta

pytestmark = pytest.mark.django_db


@pytest.fixture
def datos():
    """Un residente activo, un medicamento activo y quien registra."""
    residente = registrar_residente(Residente(
        primer_nombre="Prueba", primer_apellido="Pauta",
        fecha_nacimiento=date(1940, 1, 1), fecha_ingreso=date(2026, 1, 5),
    ))
    medicamento = Medicamento.objects.create(
        nombre_comercial="Prueba", tipo="GENERICO", concentracion="50 mg",
        presentacion=Presentacion.objects.get(nombre="tableta"),
    )
    usuario = get_user_model().objects.create_user("prueba.pautas")
    return residente, medicamento, usuario


def pauta(datos, **cambios):
    residente, medicamento, usuario = datos
    valores = dict(residente=residente, medicamento=medicamento, dosis=Decimal("1"),
                   frecuencia_horas=24, fecha_inicio=date(2026, 2, 1), registrado_por=usuario)
    return Pauta(**(valores | cambios))


@pytest.mark.parametrize(("cambios", "restriccion"), [
    ({"dosis": Decimal("0")}, "ck_pauta_dosis"),
    ({"frecuencia_horas": 0}, "ck_pauta_frecuencia"),
    ({"frecuencia_horas": 169}, "ck_pauta_frecuencia"),
    ({"fecha_fin": date(2026, 1, 31)}, "ck_pauta_fechas"),
])
def test_la_base_rechaza_pautas_invalidas(datos, cambios, restriccion):
    with pytest.raises(IntegrityError, match=restriccion):
        with transaction.atomic():
            pauta(datos, **cambios).save()


def test_dos_pautas_traslapadas_se_rechazan(datos):
    pauta(datos).save()  # vigente desde el 1 de febrero, sin fin
    with pytest.raises(IntegrityError, match="ex_pauta_sin_traslape"):
        with transaction.atomic():
            pauta(datos, fecha_inicio=date(2026, 3, 1)).save()


def test_cerrar_la_vigente_permite_registrar_la_nueva(datos):
    anterior = pauta(datos)
    anterior.save()
    anterior.fecha_fin = date(2026, 2, 28)
    anterior.save()
    pauta(datos, fecha_inicio=date(2026, 3, 1), dosis=Decimal("0.5")).save()
    assert Pauta.objects.count() == 2


def test_el_mismo_dia_de_fin_e_inicio_se_traslapa(datos):
    # El rango es '[]': ambos extremos cuentan
    pauta(datos, fecha_fin=date(2026, 2, 28)).save()
    with pytest.raises(IntegrityError, match="ex_pauta_sin_traslape"):
        with transaction.atomic():
            pauta(datos, fecha_inicio=date(2026, 2, 28)).save()


def test_la_validacion_del_modelo_avisa_el_traslape(datos):
    pauta(datos).save()
    with pytest.raises(ValidationError, match="Ya hay una pauta vigente"):
        pauta(datos, fecha_inicio=date(2026, 3, 1)).full_clean()


def test_no_se_registra_pauta_a_un_residente_egresado(datos):
    residente, _, _ = datos
    residente.estado, residente.fecha_baja = "EGRESADO", date(2026, 1, 20)
    residente.save()
    with pytest.raises(DatabaseError, match="no está activo"):
        with transaction.atomic():
            pauta(datos).save()


def test_no_se_registra_pauta_de_un_medicamento_dado_de_baja(datos):
    _, medicamento, _ = datos
    medicamento.activo = False
    medicamento.save()
    with pytest.raises(DatabaseError, match="está dado de baja"):
        with transaction.atomic():
            pauta(datos).save()
```

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| Nombres idénticos a las secciones 3.1 y 3.3 | `dpsql -c '\d pauta'` comparado con el readme |
| `dosis` es `numeric(6,2)`, nunca `float` | `\d pauta` |
| Sin índice propio sobre `pauta.residente_id` | `\d pauta` |
| La migración del *trigger* se revierte | Sección 5, paso 3 |
| Sin pantallas ni registro en `/admin/` (fuera de alcance) | Revisión del PR |

---

## 5. Verificación: comandos y resultado esperado

```bash
# 1. Calidad del código
docker compose exec web ruff check . && docker compose exec web ruff format --check .
dj check && dj makemigrations --check --dry-run

# 2. Tests
dtest apps/pautas -q
dtest -q --cov=apps --cov-fail-under=80

# 3. Esquema aplicado y reversible
dpsql -c '\d pauta'
# ck_pauta_dosis, ck_pauta_fechas, ck_pauta_frecuencia, ex_pauta_sin_traslape,
# ix_pauta_residente_inicio, ix_pauta_vigente (WHERE fecha_fin IS NULL), tg_pauta_validar
./scripts/migrate.sh pautas zero
./scripts/migrate.sh
```

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] La descripción del PR incluye la salida de `\d pauta`.

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `data type bigint has no default operator class for access method "gist"` | Falta `btree_gist` | HB-05 debe estar aplicado (`dpsql -c '\dx'`) |
| `ImportError: cannot import name 'RangeBoundary'` | Import desde un módulo equivocado | `from django.contrib.postgres.fields import RangeBoundary` |
| El traslape no se detecta con fechas iguales | El rango no es `'[]'` | `RangeBoundary(True, True)` |
| `IntegrityError` en lugar de `ValidationError` en el panel (cuando haya pantallas) | La vista no llama a `full_clean()` | Las restricciones con `violation_error_message` se validan con `full_clean()` |
