# Tasks

## 1. Tests en rojo

- [x] 1.1 Agregar a `app/apps/catalogo/tests/test_admin.py` los tests de `panel.E003` y de la relación inversa, y a `app/apps/catalogo/tests/test_formularios.py` `bytearray` y `memoryview` (decisión 4).
- [x] 1.2 Rojo: `dtest apps/catalogo/tests/test_admin.py -q` y `dtest apps/catalogo/tests/test_formularios.py -q`, uno por uno. Fallan `panel.E003`, `bytearray` y `memoryview`. El test de la relación inversa es de regresión: nace en verde y se declara. El resto sigue en verde (línea base: 232 pasan y 1 omitido, con `lento`).

## 2. Implementación

- [x] 2.1 `panel.E003` en `app/apps/panel.py`, y `bytearray`/`memoryview` y el *docstring* de `None` en `app/apps/catalogo/validadores.py` (decisiones 2 y 3); verificar con `dtest apps/catalogo/tests/test_admin.py apps/catalogo/tests/test_formularios.py -q` y `dj check`.
- [x] 2.2 Verde completo: `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80` y `dj makemigrations --check --dry-run`, con la huella intacta (`sha256sum -c <tmp>/HB-09-ajustes-4/congelados.sha256`).

## 3. Documentación viva

- [x] 3.1 Guía de HB-09: sección 1, pasos 2, 3 y 3b con el código real (decisión 1), y la nota del hallazgo 5; verificar que los bloques coinciden con los archivos (`diff` entre lo extraído de la guía y cada archivo).
- [x] 3.2 `null` en la V2: `openapi.yaml`, la nota del readme (sección 4) y `04-api.md` (decisión 2); verificar con `npx @redocly/cli lint docs/api/openapi.yaml`. Además, `Prompt 26`/`Respuesta 26` en `06-tickets-trabajo.md`.

## 4. Cierre

- [x] 4.1 `python scripts/verificar.py` y la suite completa con `lento`.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida.
- `/openspec-verify-change hb-09-ajustes-revision-4` y `/openspec-archive-change hb-09-ajustes-revision-4`, sincronizando las specs.
