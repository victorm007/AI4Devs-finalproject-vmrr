# Tasks

## 1. Tests en rojo

- [x] 1.1 Agregar a `test_login.py`, `test_admin_usuarios.py` y `test_grupos.py` un test por cada Scenario nuevo de `specs/accounts/spec.md` (`design.md`, decisión 3); verificar con `dtest <archivo> -q`, uno por uno, que fallan solo los de grupos que no se cambian, aviso único y texto del bloqueo, y que los de regresión y los anteriores pasan.

## 2. Implementación

- [x] 2.1 `GrupoAdmin.has_change_permission = False` (decisión 1) y el aviso único en `GrupoUnicoMixin` (decisión 2); verificar con `dtest apps/accounts/tests/test_admin_usuarios.py -q`.
- [x] 2.2 El texto nuevo de `registration/bloqueado.html` (decisión 4) y el `extend_exclude` de `[tool.djlint]` (decisión 5); verificar con `dtest apps/accounts -q` y `python scripts/verificar.py`.
- [x] 2.3 Verde completo: `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`, `dj check` y `dj makemigrations --check --dry-run`, sin cambios en los tests congelados (`sha256sum -c <tmp>/HB-08-ajustes/congelados.sha256`).

## 3. Documentación

- [x] 3.1 ADR-0022 (consecuencias negativas: bloqueo malicioso y datos de `axes`), paso 2 de la guía de HB-08 (`npm pack bootstrap@5.3.9`) y nota de los ajustes; verificar con `git diff --stat`.
- [x] 3.2 Registrar HB-08 y estos ajustes en `06-tickets-trabajo.md` y comprobar que su anexo sigue sincronizado con la sección 6 del readme.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`).
- Ejecutar `/openspec-verify-change hb-08-ajustes-revision` y `/openspec-archive-change hb-08-ajustes-revision`, sincronizando las specs.
