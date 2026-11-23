# Tasks

## 1. Tests en rojo

- [x] 1.1 Actualizar y agregar en `test_login.py`, `test_grupos.py` y `test_admin_usuarios.py` los tests de los Scenarios de `specs/accounts/spec.md` marcados "2.ª revisión" y el control positivo de `_save` (`design.md`, decisiones 1 a 3); verificar con `dtest <archivo> -q`, uno por uno, que solo falla el del mensaje de bloqueo y que los demás pasan.

## 2. Implementación

- [x] 2.1 El texto nuevo de `registration/bloqueado.html` (decisión 3); verificar con `dtest apps/accounts -q`, `python scripts/verificar.py` y la suite completa con cobertura, sin cambios en los tests congelados (`sha256sum -c <tmp>/HB-08-ajustes-2/congelados.sha256`).

## 3. Documentación

- [x] 3.1 ADR-0022 y ADR-0021, el readme (D1 y el nivel `ADMINISTRADOR`) con sus anexos, la nota de la guía de HB-08, el *Purpose* de la spec de `accounts` y la entrada 20 de `06-tickets-trabajo.md`; verificar con `git diff --stat` y los anexos sincronizados.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`).
- Ejecutar `/openspec-verify-change hb-08-ajustes-revision-2` y `/openspec-archive-change hb-08-ajustes-revision-2`, sincronizando las specs.
