# ADR-0027 · Claves foráneas: `PROTECT` en Django y FK diferidas de PostgreSQL

- **Estado:** Aceptado
- **Fecha:** 2026-11-27
- **Supersede a:** en parte [ADR-0009](0009-bajas-logicas-y-on-delete-restrict.md): el punto "Todas las claves foráneas son `ON DELETE RESTRICT`".
- **Capabilities afectadas:** `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`
- **Fuentes:** `readme.md` §3.1, §3.3 y §6 (TK-01); revisión adversarial del PR #3 (hallazgo 3)

## Contexto

ADR-0009 dice que todas las claves foráneas son `ON DELETE RESTRICT` (`on_delete=models.PROTECT` en Django). Pero Django no traduce `PROTECT` a la base: crea cada clave foránea como `NO ACTION DEFERRABLE INITIALLY DEFERRED`, sin cláusula `ON DELETE`.

Así, la protección del historial tiene 2 capas:

- **Django:** con `on_delete=PROTECT`, el ORM busca los registros que dependen del que se borra y lanza `ProtectedError` antes de llegar a la base.
- **PostgreSQL:** si alguien se salta el ORM (un `DELETE` en SQL), la clave foránea rechaza el borrado, pero al confirmar la transacción, no en la sentencia. Con `SET CONSTRAINTS ALL IMMEDIATE`, lo rechaza en la misma sentencia.

La revisión adversarial del PR #3 (hallazgo 3) señaló que el esquema no coincide con la letra de ADR-0009.

## Decisión

- **La protección aceptada es la combinación de las 2 capas:** `on_delete=models.PROTECT` en Django y la clave foránea `NO ACTION DEFERRABLE INITIALLY DEFERRED` que Django crea en PostgreSQL. Ningún Medicamento, Entidad, usuario ni motivo de Baja con historial se puede borrar: el ORM lo impide y la base lo rechaza al confirmar.
- **No se reescriben las claves foráneas con `RunSQL`** para volverlas `ON DELETE RESTRICT`: alejaría el esquema de lo que gestiona Django y de `makemigrations --check`.
- **La clave foránea manual `fk_residente_entidad`** (HB-06), declarada con `RunSQL`, sigue siendo `ON DELETE RESTRICT`.
- **Un test de TK-01 lo comprueba:** el ORM lanza `ProtectedError` al borrar un Medicamento con historial, y la base rechaza el mismo borrado en SQL con `SET CONSTRAINTS ALL IMMEDIATE`.
- El resto de ADR-0009 (las Bajas lógicas, el panel sin borrado y los grupos sin `delete_*`) sigue vigente.

## Alternativas consideradas

- **`RunSQL` con `ON DELETE RESTRICT` en todas las claves foráneas** (también las de HB-05 a HB-07): se descarta, porque alejaría el esquema de lo que gestiona Django y de `makemigrations --check`.

## Consecuencias

**Positivas:**
- El historial queda protegido igual: el ORM no borra un registro con dependientes y la base tampoco lo acepta al confirmar.
- El esquema sigue gestionado por Django, y `makemigrations --check` sigue sirviendo.

**Negativas:**
- El error de la base llega al confirmar la transacción, no en la sentencia. Dentro de la transacción de un test, que nunca se confirma, un `DELETE` en SQL no falla sin `SET CONSTRAINTS ALL IMMEDIATE`.
