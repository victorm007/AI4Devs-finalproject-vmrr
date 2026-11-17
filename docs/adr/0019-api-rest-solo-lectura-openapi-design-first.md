# ADR-0019 · API REST de solo lectura en el MVP, con contrato OpenAPI 3.2 *design-first*

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `api`, `inventario`, `catalogo`, `reportes`
- **Fuentes:** `readme.md` §2.2, §2.5, §4 (introducción, §4.1 a §4.4, §4.6 y §4.7) y §6 (TK-05); `CLAUDE.md` ("Stack tecnológico estricto" y "Las pantallas son la aplicación; la API no")

## Contexto

La aplicación genera sus páginas en el servidor, así que las funcionalidades del MVP se operan desde pantallas web que llaman directamente a `services.py`. La API sirve para integraciones y para documentar el contrato, y en una versión posterior podría usarla otra aplicación, como una app móvil.

## Decisión

- **Las pantallas son la aplicación; la API no.** En el MVP, la API expone solo 3 consultas de lectura bajo `https://{host}/api/v1`: `GET /existencias`, `GET /medicamentos` y `GET /reportes/mensual`. Cualquier otro método responde `405`.
- **El contrato es `docs/api/openapi.yaml`, en OpenAPI 3.2.0, escrito a mano (*design-first*) y fuente de verdad.** Tiene 34 operaciones, y cada una declara su alcance en `x-alcance`: `MVP` (las 3 anteriores) o `V2` (las otras 31, diseñadas para después). Se valida con Redocly CLI.
- **drf-spectacular** solo genera un esquema 3.0/3.1 para la documentación interactiva (Swagger UI en `/api/v1/docs/`).
- **Autenticación en el MVP:** la misma sesión de Django que la web (`SessionAuthentication`) y el permiso `IsAuthenticated`, porque los 3 endpoints son de lectura. No hay login por API ni tokens. Sin sesión, la respuesta es `401`.
- **Convenciones:**
  - JSON UTF-8 con campos en `snake_case` y en español, iguales al modelo de datos.
  - Paginación `?pagina=&por_pagina=`, con un máximo de 100.
  - Cantidades en dosis con 2 decimales ([ADR-0010](0010-cantidades-en-dosis-y-tipos-de-fecha.md)).
- **Errores con Problem Details (RFC 9457)** (`application/problem+json`), con un `code` estable y `errores[]` por campo. Un `EXCEPTION_HANDLER` propio traduce las excepciones. En V2: `409` cuando la petición choca con el estado del recurso y `422` cuando viola una regla de negocio.
- **Tests de contrato:** cada respuesta de los 3 endpoints se valida contra los esquemas de `openapi.yaml` con `jsonschema` (JSON Schema 2020-12).

## Alternativas consideradas

- **Exponer en el MVP la autenticación, las altas, los Movimientos y los conteos por API:** quedaron diseñados en el contrato como `V2` y no se implementan en el MVP (§4).

## Consecuencias

**Positivas:**
- Las operaciones V2 se implementarán sobre la misma capa `services.py`, con vistas de la API delgadas ([ADR-0011](0011-capa-de-servicios-unica-via-de-escritura.md)).
- Las 3 consultas reusan los selectores y los índices de la §3.3.

**Negativas:**
- Si una herramienta no soporta OpenAPI 3.2, hay que bajar el contrato a 3.1 (cambiar `dataValue` por `value` y quitar `summary` de los tags, §4.7).
- La gestión de usuarios no forma parte de la API: se hace en `/admin/` ([ADR-0020](0020-habilitadores-en-panel-admin.md)).
