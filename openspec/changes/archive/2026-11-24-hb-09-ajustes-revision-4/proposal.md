# Ajustes de la tercera revisión adversarial de HB-09

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-09 · **Épica:** EP-01

## Why

La tercera revisión adversarial (commit `eedb21a`, PR #2) no encontró bloqueantes. Dejó 2 mayores: la guía de HB-09 no se puede seguir completa, y `null` en la V2 se documenta de 2 formas que se contradicen. Además dejó 5 menores. El usuario pidió atender los mayores y los menores 3, 4, 6 y 7, y anotar el 5.

## What Changes

- **Guía de HB-09 ejecutable de punta a punta:**
  - la sección 1 lista todos los archivos;
  - el paso 2 trae el `panel.py` vigente;
  - el paso 3, el `admin.py` vigente, con `get_form()`;
  - un paso nuevo, "3b", cambia `Presentacion` y crea la migración `catalogo/0004_presentacion_unica`.
- **Una sola semántica de `null` en la V2:**
  - en el *docstring*, `None` es un caso defensivo;
  - el contrato, el readme y `04-api.md` dicen que la lista vacía (`minItems`) responde `CAMPO_VACIO` y un valor que no es *array* (incluido `null`) responde `TIPO_INVALIDO`.
- **La traducción a `CAMPO_VACIO`** pasa del escenario a la descripción del requisito, porque no se comprueba en el MVP.
- **`exigir_principio_activo()`** también lanza `TypeError` con `bytearray` y `memoryview`.
- **`panel.E003`:** `campos_sin_acentos` declarado como texto da un solo error, en lugar de un `panel.E002` por cada letra.
- **Test de `panel.E002`:** una relación inversa válida no da error.
- **Hallazgo 5:** el falso positivo de `"pk"` en `panel.E002` queda anotado en la guía.
- **Transcripto:** la entrada 26.

**Fuera de alcance:** el hallazgo 5 (solo nota).

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `catalogo`: configuración comprobada (`panel.E003` y la relación inversa) y la regla de principio activo (bytes y la traducción en la descripción).

## Impact

- **Código:** `app/apps/panel.py` y `app/apps/catalogo/validadores.py`. Sin migraciones.
- **Tests:** `app/apps/catalogo/tests/test_admin.py` y `app/apps/catalogo/tests/test_formularios.py`.
- **Documentación:**
  - `docs/tickets/HB-09-admin-catalogo-residentes.md`;
  - `readme.md` (nota de la V2) y `04-api.md`;
  - `docs/api/openapi.yaml`;
  - `06-tickets-trabajo.md`.
- **ADR aplicables:**
  - [ADR-0019](../../../docs/adr/0019-api-rest-solo-lectura-openapi-design-first.md): el contrato es la fuente de verdad;
  - [ADR-0020](../../../docs/adr/0020-habilitadores-en-panel-admin.md): habilitadores en el panel.
