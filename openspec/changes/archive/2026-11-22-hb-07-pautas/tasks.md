# Tasks

## 1. Tests en rojo

- [x] 1.1 Crear `app/apps/pautas/__init__.py`, `tests/__init__.py` y `tests/test_esquema.py` (sección 3 de la guía, con un test por cada Scenario de `specs/pautas/spec.md`, incluidos los que la guía no trae: nombres y definiciones del criterio 1, sin índice propio sobre `residente_id`, tipos de columna y la Pauta insertada como `app_user`), y verificar con `dtest apps/pautas/tests/test_esquema.py -q` que el rojo inicial es `ModuleNotFoundError: No module named 'apps.pautas.models'`.
- [x] 1.2 Rojo: ningún test de pautas pasa, y `dtest -m "not e2e and not lento" -q` en el resto sigue en verde (80 pasan y 1 omitido en la línea base).

## 2. App y modelo

- [x] 2.1 Crear `apps.py` (`PautasConfig`), agregar `"apps.pautas"` a `INSTALLED_APPS` debajo de `"apps.entidades"` y crear `models.py` con `RangoDeFechas` y `Pauta` (paso 2 de la guía); verificar con `dj check`.
- [x] 2.2 Generar `0001_initial.py` con `dj makemigrations pautas`, revisar con `dj sqlmigrate pautas 0001` el `EXCLUDE USING gist (... daterange(..., '[]') WITH &&)`, los 3 `CHECK` y los 2 índices sin índice suelto sobre `residente_id`, y aplicar con `./scripts/migrate.sh`; verificar con `dtest apps/pautas -q` que fallan solo los tests del *trigger* (los 2 de Residente y Medicamento inactivos y el de su definición).

## 3. Trigger de validación

- [x] 3.1 Crear `0002_trigger.py` (`RunSQL` de `fn_pauta_validar` y `tg_pauta_validar` de la sección 3.3, con su inversa) y aplicar con `./scripts/migrate.sh`; verificar con `dtest apps/pautas -q` que pasan todos.
- [x] 3.2 Verde completo: `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`, sin cambios en los tests congelados (`sha256sum -c <tmp>/HB-07/congelados.sha256`).

## 4. Cierre

- [x] 4.1 Ejecutar la sección 5 de la guía: calidad (`ruff`, `dj check`, `dj makemigrations --check --dry-run`), tests, esquema con `dpsql -c '\d pauta'` y reversión con `./scripts/migrate.sh pautas zero` seguido de `./scripts/migrate.sh`; verificar el resultado esperado de cada uno.
- [x] 4.2 Anotar en la guía las diferencias con lo que trae (rama, tests añadidos) y actualizar el estado del repositorio en `CLAUDE.md`; verificar con `git diff --stat`.
- [x] 4.3 Verificar la definición de hecho: `python scripts/verificar.py` sin errores, cobertura ≥ 80 % en `apps/` y la salida de `\d pauta` guardada para el PR.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`). En el PR va la salida de `\d pauta`.
- Ejecutar `/openspec-verify-change hb-07-pautas` y `/openspec-archive-change hb-07-pautas`, sincronizando las specs.
