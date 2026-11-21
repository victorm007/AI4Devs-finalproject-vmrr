# Tasks

## 1. Tests en rojo

- [x] 1.1 Crear `app/apps/catalogo/__init__.py`, `tests/__init__.py` y `tests/test_modelos.py` (sección 3 de la guía), y verificar con `dtest apps/catalogo -q` que el rojo inicial es `ModuleNotFoundError: No module named 'apps.catalogo.models'`.
- [x] 1.2 Rojo: ningún test del catálogo pasa, y `dtest config apps/accounts -q` sigue en verde (12 de HB-03 y 7 de HB-04).

## 2. App y extensiones

- [x] 2.1 Crear `apps.py`, agregar `"apps.catalogo"` a `INSTALLED_APPS`, y generar y reemplazar `0001_extensiones.py` (extensiones y `f_unaccent`, que depende de `accounts.0002_privilegios`); verificar con `dj makemigrations --check --dry-run` que no faltan migraciones de extensiones.

## 3. Expresiones compartidas

- [x] 3.1 Crear `app/apps/expresiones.py` con `sin_acentos()` y `no_vacio()`; verificar con `python scripts/verificar.py`.

## 4. Modelos

- [x] 4.1 Crear `models.py` y generar `0002_modelos` con `dj makemigrations catalogo --name modelos`; verificar con `dj sqlmigrate catalogo 0002 | grep -E "CONSTRAINT|INDEX"` los nombres de las secciones 3.1 y 3.3 y que la tabla puente no tiene índices sueltos sobre sus FK.
- [x] 4.2 Aplicar con `./scripts/migrate.sh` y verificar con `dtest apps/catalogo -q` que solo siguen en rojo los tests que necesitan las presentaciones semilla.

## 5. Presentaciones semilla

- [x] 5.1 Crear `0003_presentaciones.py`, aplicar con `./scripts/migrate.sh` y verificar con `dtest apps/catalogo -q` que pasan los 18 tests.
- [x] 5.2 Verde completo: `dtest -m lento apps/catalogo -q` y `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`.

## 6. Cierre

- [x] 6.1 Comprobar la huella con `sha256sum -c <tmp>/HB-05/congelados.sha256`.
- [x] 6.2 Ejecutar los pasos 1 a 5 de la sección 5 de la guía: calidad, tests, esquema con `\dx` y `\d medicamento`, reversión con `./scripts/migrate.sh catalogo zero` y la búsqueda desde el ORM como `app_user`; verificar el resultado esperado de cada uno.
- [x] 6.3 Anotar en la guía las diferencias de forma con el DDL del readme (`design.md`, decisión 4) y actualizar el estado del repositorio en `CLAUDE.md`; verificar con `git diff --stat`.
- [x] 6.4 Verificar la definición de hecho: `python scripts/verificar.py`, `dj check` y `dj makemigrations --check --dry-run` sin errores, y el `sqlmigrate` revisado contra las secciones 3.1 y 3.3.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`). En el PR #2 van la salida de `\d medicamento` y la del test `lento`, y se comprueba que el *job* `tests` pasa.
- Después de ver el CI, ejecutar `/openspec-verify-change hb-05-catalogo` y `/openspec-archive-change hb-05-catalogo`, sincronizando las specs.
