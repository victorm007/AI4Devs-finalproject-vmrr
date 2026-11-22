# Tasks

## 1. Tests en rojo

- [x] 1.1 Crear `app/apps/entidades/__init__.py`, `tests/__init__.py`, `tests/test_modelos.py` y `tests/test_services.py` (sección 3 de la guía, con un test por cada Scenario de `specs/entidades/spec.md`, incluidos los que la guía no trae: id 1 del Hogar, `ck_entidad_nombre_no_vacio` y la definición de `fk_residente_entidad`), y verificar con `dtest apps/entidades/tests/test_modelos.py -q` y `dtest apps/entidades/tests/test_services.py -q` que el rojo inicial es `ModuleNotFoundError: No module named 'apps.entidades.models'`.
- [x] 1.2 Rojo: ningún test de entidades pasa, y `dtest config apps/accounts apps/catalogo -q` sigue en verde (36 pasan y 1 omitido en la línea base).

## 2. Nombre del Hogar desde el entorno

- [x] 2.1 Agregar `HOGAR_NOMBRE` a `app/config/settings/base.py` (por defecto "Hogar Gerontológico Demo"), al `environment` de `web` en `docker-compose.yml` y, comentada, a `.env.example` (`design.md`, decisión 6, opción A); verificar con `docker compose up -d web`, `dj shell -c "from django.conf import settings; print(settings.HOGAR_NOMBRE)"` y que `set -a && . ./.env.example && set +a` no falla.

## 3. App y modelos

- [x] 3.1 Crear `apps.py` (`EntidadesConfig`), agregar `"apps.entidades"` a `INSTALLED_APPS` debajo de `"apps.catalogo"` y crear `models.py` con `Entidad` y `Residente` (paso 3 de la guía); verificar con `dj check`.

## 4. Migraciones

- [x] 4.1 Generar `0001_initial.py` con `dj makemigrations entidades` y agregarle la dependencia `("catalogo", "0001_extensiones")`; verificar con `dj sqlmigrate entidades 0001` los nombres de las secciones 3.1 y 3.3, y con `dj makemigrations --check --dry-run` que no quedan cambios pendientes.
- [x] 4.2 Crear `0002_fk_compuesta.py` (`RunSQL` de `fk_residente_entidad ... ON DELETE RESTRICT`, con su inversa) y `0003_hogar.py` (el Hogar con `settings.HOGAR_NOMBRE`, con su inversa); aplicar con `./scripts/migrate.sh` y verificar con `dpsql -c "SELECT id, tipo, nombre FROM entidad"` la fila `1 | HOGAR | Hogar Gerontológico Demo`.
- [x] 4.3 Esqueleto de `services.py` (`registrar_residente` lanza `NotImplementedError`); verificar con `dtest apps/entidades -q` que pasan los tests de esquema y fallan con `NotImplementedError` los que dan de alta un Residente.

## 5. Servicio de alta de Residentes

- [x] 5.1 Implementar `registrar_residente()` en `services.py` (paso 5 de la guía); verificar con `dtest apps/entidades -q` que pasan todos.
- [x] 5.2 Verde completo: `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`, sin cambios en los tests congelados (`sha256sum -c <tmp>/HB-06/congelados.sha256`).

## 6. Cierre

- [x] 6.1 Ejecutar los pasos 1 a 4 de la sección 5 de la guía: calidad, tests, esquema con `\d entidad` y `\d residente`, y reversión con `./scripts/migrate.sh entidades zero` seguido de `./scripts/migrate.sh`; verificar el resultado esperado de cada uno.
- [x] 6.2 Ejecutar el paso 5 de la sección 5 (alta de "Ana Ruiz" como `app_user` con `dj shell`) dentro de una transacción que se revierte, para no dejar Residentes en la base local antes de cargar el mock; verificar la salida `Ana Ruiz True` y que `dpsql -c "SELECT count(*) FROM residente"` devuelve 0.
- [x] 6.3 Anotar en la guía las diferencias con lo que trae (`.env.example`, tests añadidos y el paso 5 revertido) y actualizar el estado del repositorio en `CLAUDE.md`; verificar con `git diff --stat`.
- [x] 6.4 Verificar la definición de hecho: `python scripts/verificar.py`, `dj check` y `dj makemigrations --check --dry-run` sin errores, y el `sqlmigrate` revisado contra las secciones 3.1 y 3.3.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`). En el PR van la salida de `\d residente` y la fila del Hogar.
- Ejecutar `/openspec-verify-change hb-06-entidades` y `/openspec-archive-change hb-06-entidades`, sincronizando las specs.
