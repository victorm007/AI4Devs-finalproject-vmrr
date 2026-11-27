# Tasks

## 1. Tests en rojo

- [x] 1.1 Crear `app/apps/catalogo/tests/test_formularios.py` (la regla y el conjunto de renglones, sin HTTP) y actualizar en `app/apps/catalogo/tests/test_admin.py` el test del alta sin principio activo (el mensaje literal) y agregar el del cambio sin principio activo, un test por Scenario de `specs/catalogo/spec.md`.
- [x] 1.2 Rojo: `dtest apps/catalogo/tests/test_formularios.py -q` (falla la importación de `apps.catalogo.validadores` y `apps.catalogo.forms`) y `dtest apps/catalogo/tests/test_admin.py -q` (falta el mensaje). El resto sigue en verde (línea base: 211 pasan y 1 omitido con `lento`).

## 2. Implementación

- [x] 2.1 `app/apps/catalogo/validadores.py` y `app/apps/catalogo/forms.py` (decisiones 1 y 2); verificar con `dtest apps/catalogo/tests/test_formularios.py -q`.
- [x] 2.2 `PrincipioActivoEnLinea` con `formset = PrincipiosActivosFormSet`, sin `validate_min` ni `get_formset()` (decisión 2); verificar con `dtest apps/catalogo/tests/test_admin.py -q`.
- [x] 2.3 Verde completo: `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`, `dj check` y `dj makemigrations --check --dry-run`, con la huella intacta (`sha256sum -c <tmp>/HB-09-ajustes-2/congelados.sha256`).

## 3. Documentación viva

- [x] 3.1 readme 3.2 (D2), 4 (nota de la V2) y 6 (criterio 2 de HB-09); `openapi.yaml` (decisión 3); anexos de `03-modelo-datos.md`, `04-api.md` y `06-tickets-trabajo.md` (decisión 4); verificar con `npx @redocly/cli lint docs/api/openapi.yaml` (0 errores y las 2 advertencias intencionales) y con `grep -n "al menos un principio activo" readme.md 03-modelo-datos.md 04-api.md 06-tickets-trabajo.md`.
- [x] 3.2 La guía de HB-09 (paso 3 y el hallazgo 4 atendido) y `Prompt 24`/`Respuesta 24`; verificar con `git diff --stat`.

## 4. Cierre

- [x] 4.1 `python scripts/verificar.py` y una pasada en el navegador (Chrome *headless* por CDP): el alta sin principio activo muestra el mensaje y la consola no tiene violaciones de CSP.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida.
- `/openspec-verify-change hb-09-ajustes-revision-2` y `/openspec-archive-change hb-09-ajustes-revision-2`, sincronizando las specs.
