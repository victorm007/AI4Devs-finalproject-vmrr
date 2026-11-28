# Design

## Context

Ver `proposal.md`. TK-01 está en el PR #3 (`172eb01`), sin integrar a `main`. Las bases de desarrollo ya aplicaron `conteos/0002_triggers`.

## Decisions

1. **Migración nueva `conteos/0003_detalle_conteo_cerrado`**, en lugar de editar `0002`: las bases que ya la aplicaron se ponen al día con `migrate.sh`, sin `migrate conteos zero`. Es un `CREATE OR REPLACE FUNCTION fn_detalle_conteo_cerrado()` que rechaza en `UPDATE` y `DELETE` si el conteo de `OLD` está cerrado, y en `INSERT` y `UPDATE` si lo está el de `NEW`, con el mismo mensaje "El conteo % está cerrado". La reversa restaura el cuerpo de `0002`. El *trigger* no cambia: sigue siendo `BEFORE INSERT OR UPDATE OR DELETE`.
2. **ADR-0027 en lugar de `RunSQL` con `ON DELETE RESTRICT`.** Las FK de Django son `NO ACTION DEFERRABLE INITIALLY DEFERRED`: rechazan el borrado al confirmar la transacción, no en la sentencia. Rehacer todas las FK (también las de HB-05 a HB-07) con `RunSQL` alejaría el esquema de lo que Django gestiona y rompería `makemigrations --check`. Con `PROTECT` el ORM ya lanza `ProtectedError` antes de llegar a la base. ADR-0027 supersede en parte a ADR-0009 (solo el punto "Todas las claves foráneas son `ON DELETE RESTRICT`"). La FK manual `fk_residente_entidad` (HB-06) sigue siendo `ON DELETE RESTRICT`.
3. **`ejecutar_sql` guarda `current_user` antes de cambiar de rol** y al terminar hace `SET LOCAL ROLE <rol previo>`, en lugar de `RESET ROLE`. `SET ROLE` se autoriza contra el usuario de la sesión (`app_owner`, miembro de `app_user`), así que volver a `app_owner` desde `app_user` es válido. Si la sentencia falla, el *savepoint* revierte el `SET LOCAL`.
4. **`Makefile`:** las recetas `test`, `test-ci` y `e2e` llevan `@` y antes imprimen el comando con la contraseña oculta (`DB_PASSWORD=***`). Así se sigue viendo qué se ejecuta.
5. **Tests de regresión.** Algunos tests nuevos pasan desde el inicio, porque protegen lo que TK-01 ya hace: borrar o cambiar un renglón cerrado, borrar el encabezado cerrado, meter un renglón en un conteo cerrado, Transferencia a un Residente egresado, Entrada a uno fallecido y las FK. Nacen en rojo solo "sacar un renglón de un conteo cerrado", `ejecutar_sql` con `como_app_user` y `make test` sin contraseña.
6. **Corrección que no es el inverso del original (hallazgo 9):** el *trigger* exime cualquier Movimiento con `corrige_a`. Validar que sea el inverso exacto (mismo medicamento, cantidad y entidades intercambiadas) es regla del servicio `corregir` (TK-02). Se anota en su guía, sin cambiar el *trigger*.

## Risks / Trade-offs

- [Una base de desarrollo con `0002` pero sin `0003` conserva el hueco] → `make actualizar` o `./scripts/migrate.sh` la pone al día.
- [`@` oculta también los errores de expansión de la receta] → el `echo` previo muestra el comando con la contraseña oculta.

## Migration Plan

`./scripts/migrate.sh` aplica `conteos/0003`. Vuelta atrás: `./scripts/migrate.sh conteos 0002` restaura la función anterior.
