# Tasks

## 1. Preparación: Makefile y lectura de .env (guía, paso 1)

- [x] 1.1 Rojo de configuración: sin `Makefile`, `make help` falla; con `HOGAR_NOMBRE=Hogar Gerontológico Demo` en `.env`, `./scripts/migrate.sh` termina con "command not found" (código 127). Verificar ejecutando ambos comandos antes de cambiar nada.
- [x] 1.2 Cambiar `scripts/migrate.sh` a la lectura línea por línea y crear el `Makefile` con sus 18 *targets* (incluido `actualizar`, y `reset` con `collectstatic`); verificar con `./scripts/migrate.sh`, `make help` (18 comandos), `make -n migrate`, `make -n test T=apps/inventario`, `make -n mock` y `docker compose config | grep HOGAR_NOMBRE`.
- [x] 1.3 Descomentar `HOGAR_NOMBRE` en `.env.example` y actualizar el atajo de `.env` en `readme.md` (1.4 y 2.4), `CLAUDE.md`, las guías y la skill `implementar-ticket`, la nota de HB-06 (paso 2) y el criterio 3 del readme (18 comandos); verificar con `grep -rn '\. \./\.env' --include=*.md .` sin resultados del atajo antiguo.

## 2. Tests en rojo (mock-first)

- [x] 2.1 Crear los paquetes `apps/inventario` y `apps/conteos` (`__init__.py`, `migrations/__init__.py`, `tests/__init__.py`) y agregarlos a `INSTALLED_APPS`, debajo de `apps.pautas`; verificar con `dj check`.
- [x] 2.2 Agregar a `app/conftest.py` los *fixtures* `datos_demo`, `demo` y `como_app_user`, y a `app/pruebas.py` el helper `saldo` (guía, paso 3).
- [x] 2.3 Escribir con `test-writer` `apps/inventario/tests/test_esquema.py`, `apps/conteos/tests/test_esquema.py` y los tests nuevos de `apps/accounts/tests/test_privilegios.py` y `apps/catalogo/tests/test_admin.py`, un test por Scenario de `specs/`; verificar con `python scripts/verificar.py --corregir`.
- [x] 2.4 Rojo: `dtest apps/inventario -q`, `dtest apps/conteos -q`, `dtest apps/accounts/tests/test_privilegios.py -q` y `dtest apps/catalogo/tests/test_admin.py -q`, archivo por archivo, fallan por el motivo esperado (importación de `apps.inventario.models`/`apps.conteos.models`, tabla `movimiento` inexistente o falta del mensaje), y los tests de HB-03 a HB-09 siguen en verde. Congelar los tests por su huella.

## 3. Modelos y migraciones de inventario (guía, pasos 5 a 7b)

- [x] 3.1 Crear `apps/inventario/models.py` (`MotivoBaja`, `Existencia`, `Movimiento`) y generar `0001_initial.py` con la dependencia de `accounts/0002_privilegios`; revisar con `dj sqlmigrate inventario 0001` que no haya índices sueltos sobre las FK cubiertas.
- [x] 3.2 Crear `0002_motivos_baja.py` y `0003_permisos_grupos.py`; verificar con `./scripts/migrate.sh` y `dtest apps/inventario -k "motivo or permiso" -q`.

## 4. Modelos y migraciones de conteos (guía, paso 8)

- [x] 4.1 Crear `apps/conteos/models.py`, `0001_initial.py` (con la dependencia de `accounts/0002_privilegios`) y `0002_triggers.py`; verificar con `./scripts/migrate.sh` y `dtest apps/conteos -q` (el mock ya carga).

## 5. SQL de inventario y panel (guía, pasos 9 y 9b)

- [x] 5.1 Crear `inventario/0004_sql.py` (*triggers*, `fillfactor`, vista y `REVOKE`); verificar con `dtest apps/inventario apps/conteos apps/accounts/tests/test_privilegios.py -q` en verde.
- [x] 5.2 Agregar `MedicamentoAdminForm` a `apps/catalogo/admin.py`; verificar con `dtest apps/catalogo/tests/test_admin.py -q` en verde.
- [x] 5.3 Verde completo con la huella intacta: `sha256sum -c <tmp>/TK-01/congelados.sha256`, `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80` y `dtest -m lento apps/inventario -q`.

## 6. Cierre (guía, sección 5)

- [x] 6.1 Ejecutar la sección 5 de la guía: calidad, tests, `\d movimiento` y `\d detalle_conteo`, reversión con `migrate.sh conteos zero` / `inventario zero`, instalación desde cero con el mock y la conciliación, `web` como `app_user` y el plan con 175,000 Movimientos sintéticos; verificar el resultado esperado de cada paso.
- [x] 6.2 Actualizar `readme.md` (DDL de 3.1 con `TRUNCATE`, criterio 3 con 18 comandos, estado del repositorio en `CLAUDE.md`) y anotar en la guía las diferencias con lo implementado; verificar con `git diff --stat`.
- [x] 6.3 Definición de hecho: `python scripts/verificar.py` sin errores, `dj makemigrations --check --dry-run` sin cambios, cobertura ≥ 80 % en `apps/` y `python .claude/hooks/bloquear_secretos.py --escanear-repo` con 0 hallazgos.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`). En el PR van la salida de `\d movimiento` y el conteo de la conciliación.
- Ejecutar `/openspec-verify-change tk-01-esquema-inventario` y `/openspec-archive-change tk-01-esquema-inventario`, sincronizando las specs.
