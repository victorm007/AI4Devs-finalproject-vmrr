# Ajustes de la revisión adversarial de TK-01 (PR #3)

**Historia:** HU-01, HU-02, HU-03 · **Ticket:** TK-01 · **Épica:** EP-02

## Why

La revisión adversarial del PR #3 no encontró bloqueantes, pero sí 3 hallazgos mayores y varios menores reales: un renglón puede salir de un conteo cerrado, la spec de `accounts` contradice a sus tests, las claves foráneas no son `ON DELETE RESTRICT` como dice ADR-0009, el `Makefile` muestra la contraseña de `app_owner` y `ejecutar_sql` deshace en silencio `como_app_user`. Se corrigen antes de integrar TK-01, porque TK-02 y TK-03 dependen de este esquema y de sus *fixtures*.

## What Changes

- **Hallazgo 2:** `fn_detalle_conteo_cerrado` también rechaza un `UPDATE` que saca un renglón de un conteo cerrado (`OLD.conteo_id`). Migración nueva `conteos/0003`, reversible. Se agregan tests de borrar y cambiar renglones y de borrar el encabezado cerrado, y se corrige el DDL de la sección 3.3 del readme.
- **Hallazgo 1:** delta de `accounts` con los permisos que los grupos tienen desde TK-01 (8 y 19).
- **Hallazgo 3:** ADR-0027, que supersede en parte a ADR-0009: `PROTECT` en Django más la FK de PostgreSQL `NO ACTION DEFERRABLE INITIALLY DEFERRED` es la protección aceptada. Se agrega un test de borrado con `SET CONSTRAINTS ALL IMMEDIATE`.
- **Hallazgo 4:** las recetas `test`, `test-ci` y `e2e` del `Makefile` no muestran la contraseña.
- **Hallazgo 7:** `ck_movimiento_origen_entrada` y `ck_conteo_estado` entran en el DDL de la sección 3.1.
- **Hallazgo 9 (tests):** Transferencia a un Residente egresado y Entrada a uno fallecido. La validación de que una corrección sea el inverso del original queda anotada para TK-02.
- **Hallazgo 10:** el test de migraciones reversibles restaura la base aunque falle a la mitad.
- **Hallazgo 11:** `ejecutar_sql(..., rol=...)` restaura el rol que había, en lugar de `RESET ROLE`.
- **Hallazgo 12:** documentación sincronizada (HB-06, HB-03, `CLAUDE.md`, readme 1.4 y 5, guía de TK-01).

**Fuera de alcance:** se anotan como pendientes en la guía de TK-01 los hallazgos 5 (tests automáticos del `Makefile` y de `.env`), 6 (índices de Django sobre `usuario_id` y `motivo_baja_id`) y 8 (EXPLAIN de las consultas 1 y 2b), y los *nits*.

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `accounts`: los permisos exactos de los 2 grupos incluyen los de inventario.
- `conteos`: un conteo cerrado tampoco pierde renglones por un cambio de `conteo_id`.
- `inventario`: claves foráneas que impiden borrar el historial (ADR-0027), destino activo también en Transferencias y para Residentes fallecidos, y `ejecutar_sql` que no deshace `como_app_user`.
- `infraestructura`: `make test` no muestra la contraseña.

## Impact

- **Archivos:** `app/apps/conteos/migrations/0003_*.py` (nuevo), `app/pruebas.py`, `Makefile`, los tests de `inventario` y `conteos`, `docs/adr/0027-*.md` (nuevo), `docs/adr/0009-*.md` y `docs/adr/README.md`, `readme.md` (3.1, 3.3, 1.4, 5 y la ficha de TK-01), los anexos de `03` y `06`, `CLAUDE.md` y las guías de HB-03, HB-06, TK-01 y TK-02.
- **Puntos de integración:** 7 (*fixtures*): `ejecutar_sql` cambia solo cómo restaura el rol. Su firma no cambia. Los puntos 1, 3, 4, 5 y 8 no cambian.
- **ADR aplicables:** ADR-0005, ADR-0009 (supersedido en parte por ADR-0027), ADR-0015, ADR-0023 y ADR-0007.
