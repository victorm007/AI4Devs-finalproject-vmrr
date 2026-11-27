# Design

## Context

HB-07 dejó `Pauta` con `ex_pauta_sin_traslape` sobre `daterange(fecha_inicio, fecha_fin, '[]')`, como fijan la sección 3.1 y el ADR-0016. La motivación está en `proposal.md`, y el comportamiento, en `specs/pautas/spec.md`.

Comprobado en el contenedor `web` (Django 5.2.19), en una transacción revertida: `full_clean()` de una Pauta con `fecha_fin` anterior a `fecha_inicio` lanza `DataError -> range lower bound must be less than or equal to range upper bound`. `ExclusionConstraint.validate()` arma una consulta con `daterange(<inicio>, <fin>, '[]')` sobre los valores de la instancia, y PostgreSQL la evalúa al planificarla, antes de filtrar nada. El `INSERT` no tiene el problema: ahí el `CHECK` se evalúa antes del índice.

## Goals / Non-Goals

**Goals:**

- Que la validación del modelo, y con ella el futuro `ModelForm` y `/admin/`, nunca lance un error de base de datos por fechas, dosis o frecuencia inválidas.
- Que la definición de las restricciones en la base no cambie.

**Non-Goals:**

- Los hallazgos 3, 5, 6 y 8 (ver `proposal.md`).

## Decisions

### 1. `Pauta.clean()` valida el orden de las fechas antes de las restricciones

`clean()` lanza `ValidationError({"fecha_fin": "La fecha de fin no puede ser anterior a la de inicio."})` si las 2 fechas existen y el fin es anterior. `full_clean()` agrega a `exclude` los campos con error antes de `validate_constraints()`. Así, `ex_pauta_sin_traslape` y `ck_pauta_fechas`, que usan `fecha_fin`, no se evalúan: no hay `DataError` ni mensaje duplicado. `ModelForm._post_clean()` hace lo mismo: excluye de `validate_constraints()` los campos con error.

`clean()` es la validación de modelo de Django, no lógica de escritura: no toca `save()` (`CLAUDE.md`) ni consulta la base. El mensaje se define una vez, en una constante, y lo comparten `clean()` y `ck_pauta_fechas`.

**Alternativas descartadas:**

- **Proteger la expresión del rango** (por ejemplo, `GREATEST(fecha_fin, fecha_inicio)` o un `CASE`): cambia la definición de `ex_pauta_sin_traslape` en la base, que el readme (3.1) y el ADR-0016 fijan como `daterange(fecha_inicio, fecha_fin, '[]')`.
- **Una subclase de `ExclusionConstraint` que omita la consulta con fechas inválidas:** cubre también una llamada directa a `validate_constraints()`, pero cambia la clase que serializan las migraciones y depende de cómo compara Django las restricciones para no generar una migración de borrar y crear.

**Límite conocido:** llamar a `validate_constraints()` directamente, sin `full_clean()` ni un formulario, con fin anterior al inicio, sigue lanzando `DataError`. Ninguna vía de la aplicación lo hace.

### 2. Mensajes de los `CheckConstraint` en una migración sin cambios en la base

`violation_error_message` en `ck_pauta_dosis` ("La dosis debe ser mayor que 0."), `ck_pauta_frecuencia` ("La frecuencia debe estar entre 1 y 168 horas.") y `ck_pauta_fechas` (el mismo mensaje de `clean()`). `makemigrations` genera `0003_mensajes` con `AlterConstraint`, que en Django 5.2 no emite SQL. Es el patrón de `entidades.0004_mensaje_nombres`. Se comprueba con `dj sqlmigrate pautas 0003`, que no debe tener SQL.

### 3. Tests ([ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md))

En `app/apps/pautas/tests/test_esquema.py`:

- **Rojos:** `full_clean()` con fin anterior al inicio (hoy `DataError`) y los mensajes de dosis y frecuencia (hoy el genérico de Django).
- **De regresión (nacen en verde):** Medicamentos distintos del mismo Residente, el mismo Medicamento para Residentes distintos y `app_user` cerrando una Pauta. Protegen contra una exclusión que excluya de más y contra perder el permiso de `UPDATE`.
- **Refactor:** el test de `app_user` que registra una Pauta cuenta antes y después del `INSERT`.

## Risks / Trade-offs

- [La regla del orden de fechas vive en 2 lugares: `clean()` y `ck_pauta_fechas`] → El mensaje es una sola constante, y la base sigue siendo la barrera final.
- [`validate_constraints()` directo sigue fallando con fin anterior al inicio] → Límite documentado en la decisión 1. Ningún flujo lo usa sin `full_clean()`.

## Migration Plan

`./scripts/migrate.sh` aplica `pautas.0003_mensajes`, que no cambia la base. Reversión: `./scripts/migrate.sh pautas 0002`.
