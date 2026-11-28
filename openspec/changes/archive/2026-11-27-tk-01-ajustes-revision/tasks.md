# Tasks

## 1. Tests en rojo

- [x] 1.1 Rojo del `Makefile`: `make test T=apps/conteos` muestra hoy el valor de `DB_OWNER_PASSWORD`. Verificar contando las líneas que lo contienen (> 0), sin imprimirlo.
- [x] 1.2 `test-writer`: en `apps/conteos/tests/test_esquema.py`, borrar el encabezado cerrado, cambiar y borrar un renglón cerrado, sacar un renglón del conteo 1 y meter uno en él; en `apps/inventario/tests/test_esquema.py`, Transferencia a un Residente egresado, Entrada a uno fallecido, borrado de un Medicamento con historial (ORM y `SET CONSTRAINTS ALL IMMEDIATE`), `ejecutar_sql` con `como_app_user`, y el `try/finally` del test de migraciones. Verificar con `python scripts/verificar.py --corregir`.
- [x] 1.3 Rojo: `dtest apps/conteos -q` y `dtest apps/inventario -q`, archivo por archivo. Fallan solo "sacar un renglón de un conteo cerrado" (el `UPDATE` pasa) y el de `ejecutar_sql` (`current_user` es `app_owner`); los demás, de regresión, pasan. Congelar por su huella.

## 2. Implementación

- [x] 2.1 `ADR-0027` y ADR-0009 "supersedido en parte" (ficha e índice), antes del código; verificar con `git diff --stat docs/adr`.
- [x] 2.2 `conteos/migrations/0003_detalle_conteo_cerrado.py` (`CREATE OR REPLACE FUNCTION`, con la reversa de `0002`); verificar con `./scripts/migrate.sh` y `dtest apps/conteos -q`.
- [x] 2.3 `app/pruebas.py`: `ejecutar_sql` restaura el rol previo; verificar con `dtest apps/inventario -q`.
- [x] 2.4 `Makefile`: `@` y comando con la contraseña oculta en `test`, `test-ci` y `e2e`; verificar con `make test T=apps/conteos` (0 líneas con la contraseña) y `make -n test`.
- [x] 2.5 Verde con la huella intacta: `sha256sum -c`, `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80` y `dtest -m lento apps/inventario -q`.

## 3. Documentación y cierre

- [x] 3.1 readme: DDL de 3.1 (`ck_movimiento_origen_entrada`, `ck_conteo_estado`), `fn_detalle_conteo_cerrado` en 3.3, ADR-0027 en la ficha de TK-01 ("Todas las FK con `PROTECT`"), mensaje del panel con punto en la sección 5, sección 1.4 ("pasos previstos" y "lo crea TK-01"); anexos de `03`, `05` y `06`. Verificar con la comparación del anexo de `06` contra el readme.
- [x] 3.2 `CLAUDE.md` (tabla de comandos con `make reset` y `make actualizar`, ADR-0027 en la protección de datos históricos), guías de HB-03 (paso 251), HB-06 (tabla de problemas) y TK-01 (bloque del `Makefile` sin `export`, nota de ajustes y pendientes 5, 6 y 8), y TK-02 (validar que la corrección sea el inverso). Verificar con `grep -rn "Hasta TK-01" docs CLAUDE.md readme.md`.
- [x] 3.3 `python scripts/verificar.py`, `dj makemigrations --check --dry-run`, `python .claude/hooks/bloquear_secretos.py --escanear-repo` y `./scripts/migrate.sh conteos 0002` seguido de `./scripts/migrate.sh` (reversa de `0003`).

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`); el push actualiza el PR #3 y lanza otra revisión adversarial.
- `/openspec-verify-change tk-01-ajustes-revision` y `/openspec-archive-change tk-01-ajustes-revision`, sincronizando las specs.
