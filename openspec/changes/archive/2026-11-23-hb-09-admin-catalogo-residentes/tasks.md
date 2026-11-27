# Tasks

## 1. Tests en rojo

- [x] 1.1 Crear `app/apps/catalogo/tests/test_admin.py` y `app/apps/entidades/tests/test_admin.py` (sección 3 de la guía, con un test por cada Scenario de `specs/catalogo/spec.md` y `specs/entidades/spec.md` que se prueba con pytest, incluidos los que la guía no trae; `design.md`, decisión 5), con los datos mínimos de la guía (sin mock antes de TK-01).
- [x] 1.2 Rojo: `dtest apps/catalogo/tests/test_admin.py -q` y `dtest apps/entidades/tests/test_admin.py -q`, uno por uno, fallan por el motivo esperado (`404`: los modelos no están en el panel; `403` en el *autocomplete*). `test_el_hogar_no_se_edita_en_el_panel` también nace en rojo, por sus controles de `Residente` (su aserción sobre `Entidad` es de regresión); los demás siguen en verde (`dtest -m "not e2e and not lento" -q`: 150 pasan y 1 omitido en la línea base).

## 2. Reglas comunes del panel

- [x] 2.1 `app/apps/panel.py` con `SinBorrarMixin` y `BusquedaSinAcentosMixin` (paso 2 de la guía; `design.md`, decisión 1); verificar con `python scripts/verificar.py` y con los tests del grupo 3.

## 3. Catálogo en el panel

- [x] 3.1 `app/apps/catalogo/admin.py` con `PresentacionAdmin`, `PrincipioActivoAdmin`, `PrincipioActivoEnLinea` y `MedicamentoAdmin` (paso 3; decisión 2); verificar con `dtest apps/catalogo/tests/test_admin.py -q` (todos pasan).

## 4. Residentes en el panel

- [x] 4.1 `app/apps/entidades/admin.py` con `ResidenteAdmin`: alta con `registrar_residente()`, sin estado en el alta y orden sin acentos (paso 4; decisión 3); verificar con `dtest apps/entidades/tests/test_admin.py -q` (todos pasan) y `dj check`.

## 5. Títulos del panel

- [x] 5.1 `site_header`, `site_title` e `index_title` en `app/config/urls.py` (paso 5; decisión 4); verificar con `curl -sk https://localhost/admin/login/ | grep "Medicamentos del Hogar"`.
- [x] 5.2 Verde completo: `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`, sin cambios en los tests congelados (`sha256sum -c <tmp>/HB-09/congelados.sha256`).

## 6. Cierre

- [x] 6.1 Sección 5 de la guía: `ruff check`, `ruff format --check`, `dj check` y `dj makemigrations --check --dry-run` ("No changes detected"), `dtest apps/catalogo apps/entidades -q` y `dtest -q --cov=apps --cov-fail-under=80`.
- [x] 6.2 Prueba manual del paso 6 en `https://localhost/admin/` con `collectstatic`, con un usuario de cada grupo: alta de "Losartán 50 mg tableta" con el buscador y el botón **+**, mensaje de duplicado, búsqueda "losartan", egreso sin fecha de baja y sin la acción "Eliminar"; la consola sin violaciones de CSP.
- [x] 6.3 Anotar en la guía las diferencias (tests añadidos, test del Hogar en `entidades`, orden sin acentos, búsqueda del panel sin mínimo ni `UNION`, rama), la precisión del panel en ADR-0017 si se aprueba, y actualizar el estado del repositorio en `CLAUDE.md` y, si cambia algo, `readme.md` con su anexo; verificar con `git diff --stat`.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`). En el PR van las capturas del alta de un medicamento con su principio activo, del mensaje de duplicado y de la lista de residentes filtrada por "Activo".
- Ejecutar `/openspec-verify-change hb-09-admin-catalogo-residentes` y `/openspec-archive-change hb-09-admin-catalogo-residentes`, sincronizando las specs.
