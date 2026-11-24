# Ajustes de la sexta revisión adversarial de HB-09 (documentación)

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-09 · **Épica:** EP-01

## Why

La sexta revisión adversarial (commit `5f031f4`, PR #2) no encontró bloqueantes ni mayores. Dejó 3 menores de redacción, y el usuario pidió atenderlos.

## What Changes

- **Menor 1, la nota de la V2** (readme, sección 4, y su anexo en `04-api.md`): "el esquema del campo aplica la misma regla que el formulario" pasa a "exige lo mismo que el formulario del panel (al menos uno) y comparte su mensaje".
- **Menor 2, la spec:** la descripción del requisito "Principios activos en la pantalla del medicamento" separa las 2 ideas:
  - la regla se reutiliza fuera del panel, por ejemplo desde código que guarda sin pasar por un formulario;
  - aparte, el esquema de la V2 exige lo mismo por su cuenta.
- **Menor 3, la guía de HB-09:**
  - el paso 1 ejecuta `test_formularios.py` aparte, con su error de recolección esperado;
  - en la tabla del rojo, el paso 3 incluye ese archivo;
  - una sección 3.4 nueva trae su versión base;
  - la sección 5 lleva la tabla de estos ajustes.
- **Transcripto:** la entrada 29 de `06-tickets-trabajo.md`.

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `catalogo`: la descripción del requisito "Principios activos en la pantalla del medicamento", sin cambiar el comportamiento ni los escenarios.

## Impact

- **Código:** ninguno.
- **Documentación:**
  - `readme.md` y `04-api.md`;
  - `docs/tickets/HB-09-admin-catalogo-residentes.md`;
  - `06-tickets-trabajo.md`.
- **ADR aplicables:**
  - [ADR-0019](../../../docs/adr/0019-api-rest-solo-lectura-openapi-design-first.md): el contrato es la fuente de verdad; la nota no cambia lo que dice `openapi.yaml`.
