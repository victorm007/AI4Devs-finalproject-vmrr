# Tasks

## 1. Tests en rojo

- [x] 1.1 `test-writer` en `app/apps/inventario/tests/test_esquema.py`: el test de migraciones revierte a `0004_fk_sin_indice`, comprueba el cuerpo de `0003` y después baja a `0002_triggers`; al volver a migrar exige 2 `FOR SHARE`; "Rojo comprobado" en los bloques anteriores del *docstring*. Verificar con `python scripts/verificar.py --corregir`.
- [x] 1.2 `test-writer` en `app/apps/conteos/tests/test_esquema.py`: borrar un renglón mientras se cierra el conteo; la conexión se cierra si falla su preparación; "Rojo comprobado" en el *docstring*. Verificar con `python scripts/verificar.py --corregir`.
- [x] 1.3 `test-writer` en `tests/test_makefile.py`: `docker` falso con `make test` para el `.env` con espacios y CRLF, el `.env` con la clave 2 veces y el entorno sin `.env`; "Rojo comprobado" en el *docstring*. Verificar con `ruff check --config ruff.toml tests`.
- [x] 1.4 Rojo, archivo por archivo: `dtest apps/inventario/tests/test_esquema.py`, `dtest apps/conteos/tests/test_esquema.py` y `python -m pytest tests/test_makefile.py`. Deben fallar los casos de la clave duplicada, del entorno y de los argumentos con la contraseña. El de CRLF, el de migraciones y el de borrar en paralelo son de regresión. Congelar por su huella.

## 2. Implementación

- [x] 2.1 `Makefile`: `CLAVE_OWNER` y la contraseña por el entorno de `docker compose exec`, en `test`, `test-ci` y `e2e`. Verificar con `python -m pytest tests/test_makefile.py` y con `make test T=apps/conteos` (0 líneas con la contraseña).
- [x] 2.2 Verde con la huella intacta: `sha256sum -c`, `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80` y `python -m pytest tests -q`.

## 3. Documentación y cierre

- [x] 3.1 readme 3.3: `FOR SHARE` en el DDL de `fn_detalle_conteo_cerrado`, y la regla de ADR-0018 pendiente para `pauta` en la nota de la tabla "FK sin índice…". Anexo de `03`. Verificar con `grep -c "FOR SHARE" readme.md 03-modelo-datos.md`.
- [x] 3.2 Guía de TK-01:
  - El bloque del `Makefile` del paso 1, idéntico al `Makefile`.
  - Sin `DB_PASSWORD=***`.
  - Nota de la tercera revisión: el *nit* 5 como límite aceptado, la ubicación de los tests de concurrencia y `tests/test_makefile.py`, que hace depender de `make` al *job* `herramientas`.

  En `pendientes.md` y en la guía de HB-10:
  - Qué falta de los tests del `Makefile`: los 18 comandos, `HOGAR_NOMBRE` y `migrate.sh` con valores con espacios.
  - En TK-06, los 2 riesgos de bloqueo (captura y cierre en la misma transacción, y el orden de bloqueo conteo → `existencia`).

  Verificar con `grep -rn "solo se comprueban a mano" docs/tickets` (solo la mención histórica marcada como sustituida) y que la guía de TK-01 ya no muestre la contraseña tapada con asteriscos como estado actual.
- [x] 3.3 `python scripts/verificar.py`, `dj makemigrations --check --dry-run`, `python .claude/hooks/bloquear_secretos.py --escanear-repo` y `openspec validate tk-01-ajustes-revision-3 --strict`.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`). Después del push, una revisión adversarial acotada al diff de esta ronda.
- `/openspec-verify-change tk-01-ajustes-revision-3` y `/openspec-archive-change tk-01-ajustes-revision-3`, sincronizando las specs.
