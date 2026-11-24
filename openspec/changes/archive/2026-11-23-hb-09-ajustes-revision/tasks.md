# Tasks

## 1. Tests en rojo

- [x] 1.1 Agregar a `app/apps/catalogo/tests/test_modelos.py`, `app/apps/catalogo/tests/test_admin.py` y `app/apps/entidades/tests/test_admin.py` un test por cada Scenario nuevo o modificado de `specs/catalogo/spec.md` y `specs/entidades/spec.md` que se prueba con pytest, y ampliar el patrón de CSP (`design.md`, decisión 5), con datos mínimos (sin mock antes de TK-01).
- [x] 1.2 Rojo: `dtest apps/catalogo/tests/test_modelos.py -q`, `dtest apps/catalogo/tests/test_admin.py -q` y `dtest apps/entidades/tests/test_admin.py -q`, uno por uno. Los tests nuevos fallan por el motivo esperado (el duplicado se guarda, la búsqueda de varias palabras no encuentra, el alta ofrece la presentación inactiva, no existe `panel.E001`). Los que pasan desde el inicio (`app_user`, CSP ampliada y *Solo lectura*) son de regresión y se declaran. El resto de la suite sigue en verde (línea base: 187 pasan y 1 omitido).

## 2. Presentación sin duplicados

- [x] 2.1 `uq_presentacion_nombre` en `Presentacion` sin `unique=True` y la migración `catalogo/0004_presentacion_unica` generada con `makemigrations` (decisión 1), aplicada con `./scripts/migrate.sh`; verificar con `dtest apps/catalogo/tests/test_modelos.py -q`, con `dpsql -c '\d presentacion'` y con la reversión `./scripts/migrate.sh catalogo 0003` seguida de `./scripts/migrate.sh`.

## 3. Panel

- [x] 3.1 Búsqueda por palabras y `panel.E001` en `app/apps/panel.py` (decisiones 2 y 4); verificar con `dtest apps/catalogo/tests/test_admin.py apps/entidades/tests/test_admin.py -k "busqueda or E001 or configuracion" -q` y con `dj check`.
- [x] 3.2 Presentaciones activas en `MedicamentoAdmin.get_form()` (decisión 3); verificar con `dtest apps/catalogo/tests/test_admin.py -q`.
- [x] 3.3 Verde completo: `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80` y `dj makemigrations --check --dry-run`, sin cambios en los tests congelados (`sha256sum -c <tmp>/HB-09-ajustes/congelados.sha256`).

## 4. Documentación viva

- [x] 4.1 `readme.md` (3.1: Mermaid, DDL y párrafo; 3.2: D2; 6: ficha de HB-09), el anexo de `03-modelo-datos.md` a mano y el de `06-tickets-trabajo.md` regenerado (decisión 6); verificar con `grep -n uq_presentacion_nombre readme.md 03-modelo-datos.md 06-tickets-trabajo.md`.
- [x] 4.2 ADR-0017, las guías de HB-05 y HB-09 (con los hallazgos 4, 5 y 10 como pendientes), `CLAUDE.md` y las entradas `Prompt 22`/`Respuesta 22` y `Prompt 23`/`Respuesta 23` en `06-tickets-trabajo.md`; verificar con `git diff --stat`.

## 5. Cierre

- [x] 5.1 `python scripts/verificar.py`, `dj check`, `dj makemigrations --check --dry-run`, `dtest -q --cov=apps --cov-fail-under=80` y una pasada en el navegador (Chrome *headless* por CDP): duplicado de "Tableta" con mensaje, búsqueda "losartan " y consola sin violaciones de CSP.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`). El usuario regenera el PNG del modelo de datos en `diagramas/`.
- Ejecutar `/openspec-verify-change hb-09-ajustes-revision` y `/openspec-archive-change hb-09-ajustes-revision`, sincronizando las specs.
