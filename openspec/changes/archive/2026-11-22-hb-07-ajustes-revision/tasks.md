# Tasks

## 1. Tests en rojo

- [x] 1.1 Agregar a `app/apps/pautas/tests/test_esquema.py` un test por cada Scenario nuevo de `specs/pautas/spec.md` (hallazgos 1, 2 y 7), y cambiar el control del test de `app_user` que registra una Pauta por un conteo antes y después; verificar con `dtest apps/pautas/tests/test_esquema.py -q` que fallan solo el de fin anterior al inicio (con `DataError`) y los de mensajes (con el texto genérico de Django), y que los 3 de regresión y los anteriores pasan.

## 2. Validación y mensajes

- [x] 2.1 En `app/apps/pautas/models.py`: la constante del mensaje de fechas, `Pauta.clean()` (decisión 1), `violation_error_message` en los 3 `CheckConstraint` (decisión 2) y el comentario de `RangoDeFechas` (hallazgo 4); verificar con `dj check`.
- [x] 2.2 Generar `0003_mensajes.py` con `dj makemigrations pautas --name mensajes`, comprobar con `dj sqlmigrate pautas 0003` que no tiene SQL y aplicar con `./scripts/migrate.sh`; verificar con `dtest apps/pautas -q` que pasan todos.
- [x] 2.3 Verde completo: `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`, sin cambios en los tests congelados (`sha256sum -c <tmp>/HB-07-ajustes/congelados.sha256`).

## 3. Cierre

- [x] 3.1 Calidad y migraciones: `python scripts/verificar.py`, `dj check`, `dj makemigrations --check --dry-run`, y reversión con `./scripts/migrate.sh pautas 0002` seguido de `./scripts/migrate.sh`; verificar que `\d pauta` no cambia.
- [x] 3.2 Anotar en la nota de la guía de HB-07 los ajustes de la revisión; verificar con `git diff --stat`.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`).
- Ejecutar `/openspec-verify-change hb-07-ajustes-revision` y `/openspec-archive-change hb-07-ajustes-revision`, sincronizando las specs.
