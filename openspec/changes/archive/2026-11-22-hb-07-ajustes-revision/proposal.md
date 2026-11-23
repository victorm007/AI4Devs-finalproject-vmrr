# Ajustes de HB-07 tras la revisión adversarial

**Historia:** — (habilitador de EP-05) · **Ticket:** HB-07 · **Épica:** EP-05

## Why

La revisión adversarial del PR #2 no encontró bloqueantes en HB-07, pero sí un hallazgo importante, que se comprobó: validar con `full_clean()` una Pauta cuya fecha de fin es anterior a la de inicio lanza `DataError` ("range lower bound must be less than or equal to range upper bound") en lugar de `ValidationError`. Cuando existan el formulario o `/admin/` de Pautas, ese caso daría un `500` por una regla de negocio. Contradice el ADR-0005 y `CLAUDE.md`. Se arregla ahora, junto con 3 hallazgos menores de poco esfuerzo, antes de que TK-01 y las pantallas dependan del modelo.

## What Changes

- **Fin anterior al inicio sin `DataError`** (hallazgo 1): la validación del modelo rechaza esa Pauta con un `ValidationError` sobre `fecha_fin`, con el mensaje "La fecha de fin no puede ser anterior a la de inicio.", antes de evaluar `ex_pauta_sin_traslape`. El esquema de la base no cambia.
- **Mensajes de las restricciones** (hallazgo 2): `ck_pauta_dosis`, `ck_pauta_frecuencia` y `ck_pauta_fechas` llevan `violation_error_message` en español. Llegan en una migración `0003` con `AlterConstraint`, que no cambia la base (como `entidades.0004_mensaje_nombres`).
- **Aviso en `RangoDeFechas`** (hallazgo 4): un comentario indica que la migración `0001` la importa y que no se renombra ni se mueve.
- **Tests** (hallazgo 7):
  - la exclusión no rechaza Pautas de Medicamentos distintos del mismo Residente, ni del mismo Medicamento para Residentes distintos;
  - `app_user` puede cerrar una Pauta (`UPDATE` de `fecha_fin`);
  - el test de `app_user` que registra una Pauta cuenta las Pautas antes y después, en lugar de exigir que no haya ninguna.

**Fuera de alcance** (hallazgos que no contradicen al readme y quedan para la historia de Pautas o una decisión del readme):

- los índices que Django crea sobre `medicamento_id` y `registrado_por_id` (hallazgo 3);
- `tg_pauta_validar` solo en `INSERT`, como define la sección 3.3 (hallazgo 5);
- `Pauta.__str__` (hallazgo 6) y la sección 3 de la guía (hallazgo 8).

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `pautas`: la validación del modelo avisa con mensajes en español la dosis, la frecuencia y las fechas inválidas, sin un error de base de datos; la exclusión no rechaza Pautas de otro Medicamento ni de otro Residente, y `app_user` puede cerrar una Pauta.

## Impact

- **Archivos modificados:** `app/apps/pautas/models.py` y `app/apps/pautas/tests/test_esquema.py`. **Nuevo:** `app/apps/pautas/migrations/0003_mensajes.py`. Documentación: la nota de la guía de HB-07.
- **Esquema:** sin cambios en la base. `0003` solo cambia el estado de las migraciones.
- **Puntos de integración:** TK-01 carga Pautas válidas del mock y no lo afecta. Los futuros formularios de Pautas reciben `ValidationError` en vez de un `500`.
- **ADR aplicables:**
  - [ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md): la base es la última barrera, no el mensaje al usuario;
  - [ADR-0006](../../../docs/adr/0006-dos-usuarios-de-base-de-datos.md): `app_user` cierra Pautas;
  - [ADR-0016](../../../docs/adr/0016-pautas-informativas-con-vigencia.md): la exclusión conserva `daterange(fecha_inicio, fecha_fin, '[]')`;
  - [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md): pruebas contra PostgreSQL real.
