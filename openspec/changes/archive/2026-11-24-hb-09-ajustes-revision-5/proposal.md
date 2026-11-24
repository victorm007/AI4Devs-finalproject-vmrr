# Ajustes de la cuarta revisión adversarial de HB-09 (documentación)

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-09 · **Épica:** EP-01

## Why

La cuarta revisión adversarial (commit `3309cbb`, PR #2) no encontró bloqueantes ni mayores. Dejó 7 menores de documentación y robustez. El usuario pidió atender los menores 1, 2, 3, 5 y 7, que son solo de documentación, y anotar el 4 y el 6.

## What Changes

- **Guía de HB-09:**
  - en la sección 3.1, el *import* de `SIN_PRINCIPIO_ACTIVO` va dentro de su test;
  - el test del Hogar pasa a la sección 3.2;
  - una sección 3.3 nueva trae los tests del paso 3b (`uq_presentacion_nombre`);
  - el paso 1 y el paso 3b se ajustan;
  - lleva las notas de los hallazgos 4 y 6.
- **Una sola capa para la regla en la V2:** el esquema rechaza la lista vacía con `CAMPO_VACIO` y el mensaje de la regla, y la función protege a quien guarde sin pasar por el esquema. Esto cambia:
  - la nota del readme (sección 4) y `04-api.md`;
  - `openapi.yaml`;
  - el *docstring* de `validadores.py`, solo comentarios;
  - el escenario de la spec.
- **`CLAUDE.md`:** nombra `panel.E003`.
- **Transcripto:** la entrada 27.

**Fuera de alcance:**

- **hallazgo 4:** el mapeo general de los errores de esquema; se decide al implementar la V2;
- **hallazgo 6:** la robustez de `check()` ante valores que no son texto. Los 2 quedan como notas.

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `catalogo`: la descripción del requisito "Principios activos en la pantalla del medicamento" y su escenario "La regla se puede reutilizar fuera del panel", sin cambiar el comportamiento.

## Impact

- **Código:** ninguno. Solo el *docstring* de `app/apps/catalogo/validadores.py`.
- **Documentación:**
  - `docs/tickets/HB-09-admin-catalogo-residentes.md`;
  - `readme.md`, `04-api.md` y `06-tickets-trabajo.md`;
  - `docs/api/openapi.yaml`;
  - `CLAUDE.md`.
- **ADR aplicables:**
  - [ADR-0019](../../../docs/adr/0019-api-rest-solo-lectura-openapi-design-first.md): el contrato es la fuente de verdad.
