# Design

## Context

HB-03 dejó la base con `app_owner` como dueño, los privilegios por defecto de `app_user` (`accounts.0002_privilegios`) y el arnés de pytest con `ejecutar_sql`. Todavía no hay extensiones ni tablas de dominio. La motivación está en `proposal.md`, y el comportamiento, en `specs/`.

El código de la guía se ensayó en una copia desechable de `app/`:

- **Tests:** los 18 de `test_modelos.py` pasan, incluido el `lento`. La suite completa da 35 passed y 1 skipped, con 95 % de cobertura.
- **Migraciones:** en una base desechable, la migración aplica, siembra las 8 presentaciones, se revierte con `catalogo zero` (quita tablas, función y extensiones) y se vuelve a aplicar.
- **Búsqueda:** el ORM, como `app_user`, encuentra «Losartán» al buscar «losartan».
- **Calidad:** `manage.py check` no da advertencias y `ruff check` pasa. Hay que aplicar `ruff format` a 2 archivos.

## Goals / Non-Goals

**Goals:**

- Que la base, y no solo el formulario, impida duplicados sin mayúsculas ni acentos y textos vacíos.
- Que la expresión de búsqueda del ORM sea exactamente la de los índices, comprobado con el plan de ejecución.

**Non-Goals:**

- El registro del catálogo en `/admin/` (HB-09).
- La regla «no se da de baja un Medicamento con saldo» (TK-02).

## Decisions

### 1. `f_unaccent` como envoltura `IMMUTABLE`

`unaccent()` es `STABLE` y PostgreSQL no la acepta en índices. `f_unaccent(text)` la envuelve con el diccionario calificado (`public.unaccent`) y se declara `IMMUTABLE PARALLEL SAFE STRICT` (sección 3.1, [ADR-0017](../../../docs/adr/0017-busqueda-sin-acentos-con-trigram.md)). Va en `catalogo.0001_extensiones`, antes que cualquier tabla.

### 2. `sin_acentos()` es la única forma de escribir la expresión

`apps/expresiones.py` devuelve `Func(Lower(campo), function="f_unaccent")`, que genera `f_unaccent(LOWER(campo))`. La usan las restricciones, los índices y las búsquedas. `Unaccent(Lower(...))` de `django.contrib.postgres` generaría `UNACCENT(LOWER(...))`, y el plan no usaría el índice. El test `lento` lo vigila.

### 3. Únicos por expresión como `UniqueConstraint`, no como `RunSQL`

Así `full_clean()`, y por tanto el panel de HB-09, valida la restricción y muestra `violation_error_message` en lugar de un error `500` (sección 3.1).

### 4. Diferencias de forma con el DDL del readme, con el mismo efecto

| Readme | Lo que genera Django | Por qué se acepta |
|---|---|---|
| `CHECK (btrim(x) <> '')` | `CHECK (LENGTH(TRIM(x)) > 0)` | Son equivalentes. `no_vacio()` es una expresión de Django, así que `full_clean()` también la valida. El nombre de la restricción es el del readme |
| `DEFAULT now()` | `DEFAULT STATEMENT_TIMESTAMP()` | `Now()` de Django en PostgreSQL. Solo cambia el instante dentro de una transacción larga, y no importa para una fecha de alta |
| `presentacion.nombre UNIQUE` | Además, el índice `presentacion_nombre_..._like` (`varchar_pattern_ops`) | Django lo crea siempre para un `CharField` único. No es una FK de la tabla puente, y la tabla tiene 8 filas |

Los nombres de las restricciones y los índices son exactamente los de las secciones 3.1 y 3.3.

### 5. Rojo inicial por importación

El paso 1 de la guía deja `ModuleNotFoundError: apps.catalogo.models` como rojo inicial. Después de los modelos (paso 4), los tests que dependen de las presentaciones semilla siguen en rojo hasta el paso 5. `implementer` lo reporta.

## Risks / Trade-offs

- [`./scripts/migrate.sh catalogo zero` en el cierre borra las tablas del catálogo de la base local] → Hoy están vacías. Se vuelven a crear en el mismo paso, y el paso 5 de la verificación crea y borra su propio Medicamento.
- [Los tests de HB-03 (`test_privilegios.py`) ahora revisan también las tablas del catálogo] → Es lo esperado: comprueban que nacen con dueño `app_owner` y con los 4 permisos de `app_user`.
