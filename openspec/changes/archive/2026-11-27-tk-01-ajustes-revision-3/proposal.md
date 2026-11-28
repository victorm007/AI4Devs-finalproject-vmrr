# Terceros ajustes de la revisión adversarial de TK-01 (PR #3)

**Historia:** HU-01, HU-02, HU-03 · **Ticket:** TK-01 · **Épica:** EP-02

## Why

La revisión de `4523afd` no encontró bloqueantes. Encontró 2 mayores: el DDL del readme no refleja `FOR SHARE`, y la reversa de `conteos/0005` no tiene test. También encontró 7 menores y 5 *nits*. Esta ronda atiende los mayores y los menores baratos, y anota los demás como pendientes. El PR #3 sigue abierto para los tickets siguientes.

## What Changes

- **Mayor 1:** el DDL de `fn_detalle_conteo_cerrado` en la sección 3.3 del readme (y el anexo de `03`) lleva `FOR SHARE` en las 2 lecturas del estado.
- **Mayor 2 y menor 1:** el test de migraciones revierte primero a `conteos/0004_fk_sin_indice` y comprueba el cuerpo de `0003` (los 2 conteos, sin `FOR SHARE` ni `v_conteo`). Al volver a migrar, exige 2 `FOR SHARE`. Un test nuevo de concurrencia cubre la rama de `OLD`: borrar un renglón mientras se cierra el conteo.
- **Menores 3 y 4, y *nit* 1:** el `Makefile` toma `DB_OWNER_PASSWORD` del entorno si está definida, y si no, de la primera línea que la define en `.env`. Se la pasa a `docker compose exec` como variable de entorno (`-e DB_PASSWORD` sin valor), así que tampoco aparece en los argumentos del proceso. Un test con un `docker` falso en el `PATH` lo comprueba con `make test` real.
- **Menores 2, 5, 6 y 7:**
  - Riesgos de bloqueo del servicio de conteos en el pendiente de TK-06.
  - Documentación desfasada en la guía de TK-01, en `pendientes.md` y en la guía de HB-10.
  - En la nota de la sección 3.3, la regla de ADR-0018 queda pendiente para `pauta`.
  - Se quita de la spec de `inventario` un MUST que es propiedad del test.
- ***Nits* 2 y 4:** "Rojo comprobado" en los *docstrings* de los tests ya comprobados, y la conexión del test de concurrencia se cierra aunque falle su preparación.

**Fuera de alcance**, anotado como pendiente:
- Índices de `pauta` (historia de Pautas, menor 6).
- Que falle cada FK del historial por separado. Haría falta borrar Movimientos, que son inmutables (*nit* 5, límite aceptado en la guía de TK-01).
- Ubicación de los tests de concurrencia (*nit* 3, anotado en la guía de TK-01).
- `tablas_referidas` duplicada, igual que los demás helpers de cada `test_esquema.py` (*nit* 4, aceptado).

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `conteos`: la reversa de cada migración de la función queda probada, y también el borrado de un renglón en paralelo con el cierre.
- `inventario`: el requisito de migraciones reversibles deja de exigir una propiedad del test.
- `infraestructura`: el `Makefile` toma la contraseña del entorno o de la primera línea de `.env`, y no la pone en los argumentos de `docker compose`.

## Impact

- **Archivos:**
  - Código: `Makefile`.
  - Tests: los 2 `test_esquema.py` y `tests/test_makefile.py`.
  - Documentación: `readme.md` (3.3), anexo de `03`, guías de TK-01 y HB-10, `docs/tickets/pendientes.md` y el transcript de `06`.
- **Puntos de integración:** ninguno cambia.
- **ADR aplicables:** ADR-0018, ADR-0005, ADR-0006 y ADR-0023.
