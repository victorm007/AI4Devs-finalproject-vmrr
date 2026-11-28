# Design

## Context

Ver `proposal.md`. TK-01 sigue en el PR #3 (`c67f733`), sin integrar a `main`. Las bases de desarrollo ya aplicaron `conteos/0003_detalle_conteo_cerrado`.

## Decisions

1. **`db_index=False` en las 3 FK, con migraciones nuevas** (`inventario/0005_fk_sin_indice`, `conteos/0004_fk_sin_indice`), generadas con `makemigrations` (`AlterField`). No se editan las `0001_initial`: las bases que ya las aplicaron se ponen al día con `migrate.sh`, y la reversa recrea el índice. Sin índice, el chequeo de la FK al borrar un usuario o un motivo de baja recorrería `movimiento`, pero ninguno se borra: `PROTECT` lo impide (ADR-0027) y los catálogos usan bajas lógicas (ADR-0009). La alternativa de dejarlos con un ADR de excepción se descartó, por decisión del usuario.
2. **El shell lee la contraseña, no `make`:** `OWNER := -e DB_USER=app_owner -e DB_PASSWORD="$$(sed -n 's/^DB_OWNER_PASSWORD=//p' .env | tr -d '\r')"`. Con `:=`, `$$` queda como `$` y `make` no vuelve a expandir el valor, así que `make -n`, `--trace` y el eco normal muestran la expresión `sed`, nunca el valor. Las recetas `test`, `test-ci` y `e2e` vuelven a mostrarse sin `@` ni `echo`. Las comillas protegen un valor con espacios, y `tr -d '\r'` quita el fin de línea CRLF. Se descartó `undefine` (no existe en GNU Make 3.81 de Windows) y quitar `-include .env` (HB-10 lo usa en el candado).
3. **Tests de borrado aislando la causa.**
   - En el ORM se comprueba `ProtectedError.protected_objects`.
   - En la base, el test borra primero (como `app_owner`) las referencias que no son historial: `medicamento_principio_activo`, `pauta` y `usuario_groups`. Después exige que el mensaje nombre una tabla del historial: `on table "(movimiento|existencia|conteo_fisico|detalle_conteo)"`.
   - Se parametriza para Eutirox, el Hogar, `operador.demo` y `CONSUMO`.
   - No se usa un Residente: `fk_residente_entidad` es `ON DELETE RESTRICT` inmediata y saltaría antes que el historial.
4. **`FOR SHARE` en `fn_detalle_conteo_cerrado`** (migración `conteos/0005_detalle_conteo_bloqueo`, `CREATE OR REPLACE`, con la reversa al cuerpo de `0003`). Las 2 lecturas de `estado` (`OLD.conteo_id` y `NEW.conteo_id`) pasan a `SELECT estado … FOR SHARE`.
   - Si la captura llega primero, el `UPDATE` que cierra el conteo espera su `FOR NO KEY UPDATE`.
   - Si el cierre llega primero, la captura espera. En READ COMMITTED vuelve a leer la fila confirmada, ve `CERRADO` y rechaza.
   - `FOR SHARE` exige `UPDATE` sobre `conteo_fisico`, que `app_user` tiene, porque cierra conteos. No toca `movimiento` (CLAUDE.md).
   - La alternativa, `select_for_update()` en el servicio de TK-06, deja la base sin barrera (ADR-0005).
5. **Tests de concurrencia sin hilos**, con 2 conexiones de psycopg abiertas en el test (`transaction=True, serialized_rollback=True`). Cada conexión hace `SET ROLE app_user` y la que debe esperar usa `SET lock_timeout`. El rojo de hoy es que no espera: el cierre o la captura pasan al instante. Es determinista, sin `sleep`.
6. **Test del `Makefile` en `tests/test_makefile.py`**, con el Python y el GNU Make del equipo. Corre `make -n -C <tmp> -f <repo>/Makefile <target>` con un `.env` temporal y una contraseña de ejemplo con `demo` en el valor, para que el hook de secretos no la bloquee. Si no hay `make`, se omite con `pytest.skip`. El *job* `herramientas` del CI (Ubuntu) sí tiene `make`.
7. **Test de migraciones:** el `try` empieza antes de `migrate conteos zero`. Antes de bajar a `zero` se revierte a `0002_triggers` y se compara el cuerpo de la función (`pg_get_functiondef`), y al volver a migrar se exige el de `0005`.

## Risks / Trade-offs

- [`make -p` imprime la base de variables, incluidos los valores de `.env`] → límite aceptado y anotado en la guía de TK-01. Es una opción de depuración, no de uso diario.
- [`FOR SHARE` hace esperar al cierre mientras una captura del mismo conteo está abierta] → las transacciones de captura son cortas (una sentencia por renglón en TK-06).
- [Sin `.env`, `sed` falla y la contraseña llega vacía] → es el mismo resultado que antes con `-include`: `pytest` falla al conectar con un mensaje claro.

## Migration Plan

`./scripts/migrate.sh` aplica `inventario/0005`, `conteos/0004` y `conteos/0005`. Vuelta atrás: `./scripts/migrate.sh conteos 0003` y `./scripts/migrate.sh inventario 0004` recrean los índices y la función de `0003`.
