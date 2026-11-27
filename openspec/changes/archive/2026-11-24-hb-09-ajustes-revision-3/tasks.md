# Tasks

## 1. Tests en rojo

- [x] 1.1 Agregar a `app/apps/catalogo/tests/test_admin.py` y `app/apps/catalogo/tests/test_formularios.py` un test por cada Scenario nuevo o modificado de `specs/catalogo/spec.md`, y el `<option>` del HTML en los tests de presentaciones inactivas (`design.md`, decisión 4).
- [x] 1.2 Rojo: `dtest apps/catalogo/tests/test_admin.py -q` y `dtest apps/catalogo/tests/test_formularios.py -q`, uno por uno. Fallan el tope de palabras, `panel.E002`, `None` y el texto. Los de Hyzaar, los comodines y el `<option>` son de regresión: nacen en verde y se declaran. El resto sigue en verde (línea base: 220 pasan y 1 omitido, con `lento`).

## 2. Implementación

- [x] 2.1 Tope de palabras y `panel.E002` en `app/apps/panel.py` (decisiones 1 y 2); verificar con `dtest apps/catalogo/tests/test_admin.py -q` y `dj check`.
- [x] 2.2 `None` y texto en `app/apps/catalogo/validadores.py` (decisión 3); verificar con `dtest apps/catalogo/tests/test_formularios.py -q`.
- [x] 2.3 Verde completo: `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80` y `dj makemigrations --check --dry-run`, con la huella intacta (`sha256sum -c <tmp>/HB-09-ajustes-3/congelados.sha256`).

## 3. Documentación viva

- [x] 3.1 La guía de HB-09 (paso 3, sección 5 y las notas de los hallazgos 6 y 8), ADR-0005, la nota de la V2 en el readme con su anexo en `04-api.md`, `openapi.yaml`, `CLAUDE.md` y `Prompt 25`/`Respuesta 25` (decisión 5); verificar con `npx @redocly/cli lint docs/api/openapi.yaml` y `git diff --stat`.

## 4. Cierre

- [x] 4.1 `python scripts/verificar.py` y la suite completa con `lento`.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida.
- `/openspec-verify-change hb-09-ajustes-revision-3` y `/openspec-archive-change hb-09-ajustes-revision-3`, sincronizando las specs.
