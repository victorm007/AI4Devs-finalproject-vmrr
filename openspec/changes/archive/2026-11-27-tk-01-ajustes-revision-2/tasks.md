# Tasks

## 1. Tests en rojo

- [x] 1.1 `test-writer` en `apps/inventario/tests/test_esquema.py`: FK `motivo_baja_id` y `usuario_id` de `movimiento` sin índice; borrado con historial en el ORM (`protected_objects`) y en la base (sin referencias ajenas, mensaje con tabla del historial) para Eutirox, el Hogar, `operador.demo` y `CONSUMO`; el `try` desde `migrate conteos zero` con el cuerpo de `fn_detalle_conteo_cerrado` en `0002` y en `0005`; `session_user` en el control de `ejecutar_sql`. Verificar con `python scripts/verificar.py --corregir`.
- [x] 1.2 `test-writer` en `apps/conteos/tests/test_esquema.py`: FK `conteo_fisico.usuario_id` sin índice, y los 2 escenarios de cierre y captura en paralelo como `app_user`, con 2 conexiones y `lock_timeout`. Verificar con `python scripts/verificar.py --corregir`.
- [x] 1.3 `test-writer` en `tests/test_makefile.py` (nuevo): `make -n test`, `test-ci` y `e2e` sin la contraseña de un `.env` temporal y con `docker compose exec -e DB_USER=app_owner`. Además, el *docstring* de `app/pruebas.py`: el rol se cita y distingue mayúsculas. Verificar con `python scripts/verificar.py --herramientas`.
- [x] 1.4 Rojo, archivo por archivo: `dtest apps/inventario/tests/test_esquema.py`, `dtest apps/conteos/tests/test_esquema.py` y `python -m pytest tests/test_makefile.py`. Los rojos son los del plan; los demás tests siguen en verde. Congelar por su huella.

## 2. Implementación

- [x] 2.1 `db_index=False` en `Movimiento.motivo_baja`, `Movimiento.usuario` y `ConteoFisico.usuario`, y `makemigrations` como `app_owner` (`inventario/0005_fk_sin_indice`, `conteos/0004_fk_sin_indice`). Verificar con `./scripts/migrate.sh` y `dj makemigrations --check --dry-run`.
- [x] 2.2 `conteos/migrations/0005_detalle_conteo_bloqueo.py` con `FOR SHARE` y la reversa al cuerpo de `0003`. Verificar con `./scripts/migrate.sh` y `dtest apps/conteos -q`.
- [x] 2.3 `Makefile`: `OWNER` lee la contraseña con el shell, sin `OWNER_OCULTO`, `@` ni `echo`. Verificar con `python -m pytest tests/test_makefile.py` y con `make test T=apps/conteos` (0 líneas con la contraseña).
- [x] 2.4 Verde con la huella intacta: `sha256sum -c`, `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`, `dtest -m lento apps/inventario -q` y `python -m pytest tests -q`.

## 3. Documentación y cierre

- [x] 3.1 readme:
  - En 3.3, la tabla "FK sin índice porque ninguna consulta las usa" y `PROTECT (ADR-0027)` en "Sin índices redundantes".
  - En la ficha de TK-01: `ck_movimiento_origen_entrada`, `ck_conteo_estado`, las migraciones `conteos/0003` a `0005` e `inventario/0005`, y el criterio 11 con "consultas 1 y 2c", marcado como parcial.
  - En el ejemplo de PR de TK-06, `0006_permisos_grupos`.
  - Anexos de `03`, `06` y `07`.

  Verificar con `grep -n "protegidas por .RESTRICT\|1c y 2\|0003_permisos_grupos.py" readme.md 03-modelo-datos.md 06-tickets-trabajo.md 07-pull-requests.md`: solo debe quedar el `0003_permisos_grupos.py` de inventario.
- [x] 3.2 Guía de TK-01:
  - Árbol de archivos con las migraciones nuevas.
  - Nota de ajustes de la segunda revisión.
  - Las FK sin índice en las diferencias con el readme.
  - `make -p` como límite aceptado.

  En `docs/tickets/pendientes.md`:
  - Quitar el pendiente de EP-04 y la errata de TK-03.
  - Precisar "primera revisión adversarial de HB-09".
  - Anotar en TK-06 la numeración `0006` y que el cierre ya bloquea con `FOR SHARE`.
  - Anotar en HB-10 (y en su guía, sección 0.5) que `make -p` muestra los valores de `.env`. Los demás fuera de alcance ya están anotados: EXPLAIN 1 en TK-03, EXPLAIN 2b en TK-06, índices de `pauta` en la guía de HB-07 y el pendiente 5 en HB-10.

  Verificar con `grep -n "EP-04\|1c" docs/tickets/pendientes.md`.
- [x] 3.3 `python scripts/verificar.py`, `dj makemigrations --check --dry-run`, `python .claude/hooks/bloquear_secretos.py --escanear-repo`, y `./scripts/migrate.sh conteos 0003` y `./scripts/migrate.sh inventario 0004` seguidos de `./scripts/migrate.sh` (reversas).

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`). El push actualiza el PR #3 y lanza otra revisión adversarial.
- `/openspec-verify-change tk-01-ajustes-revision-2` y `/openspec-archive-change tk-01-ajustes-revision-2`, sincronizando las specs.
