# Design

## Context

Ver `proposal.md` (Why). Ya existen, de HB-01 a HB-09: los 2 usuarios de BD, `scripts/migrate.sh`, `accounts/0002_privilegios` (permisos por defecto de `app_user` en cada tabla nueva), `f_unaccent`, `Medicamento`, `Entidad`/`Residente`, `Pauta`, los 2 grupos (`accounts/0003_grupos`), `MedicamentoAdmin` y el arnés de pytest (`conftest.py` vacío y `pruebas.ejecutar_sql`). La guía `docs/tickets/TK-01-esquema-inventario.md` trae el código de referencia, que nunca se ha ejecutado; donde contradice al readme, manda el readme.

## Goals / Non-Goals

**Goals:**

- Mismos nombres que las secciones 3.1 y 3.3, comprobados por tests de esquema y no solo a ojo (`\d movimiento`).
- Doble barrera de la inmutabilidad: *trigger* + privilegios.
- *Fixtures* estables para TK-02 y TK-03 (punto de integración 7).

**Non-Goals:**

- Servicios, selectores, vistas o API; permisos de grupo sobre los conteos (TK-06).

## Decisions

1. **Restricciones en `Meta.constraints` y lógica PL/pgSQL en `RunSQL`.** Las `CHECK` y `UNIQUE` en el modelo, para que `makemigrations --check` las vigile; los *triggers*, la vista, el `fillfactor` y el `REVOKE` en `inventario/0004_sql` y `conteos/0002_triggers`, cada `RunSQL` con su inversa (ADR-0005, ADR-0007).
2. **`ck_movimiento_entregado` con `apps.expresiones.no_vacio()`**, que genera `length(btrim(...)) > 0`, en lugar de la expresión regular de la guía: es el mismo helper de HB-05 a HB-07 y equivale al `btrim(entregado_por) <> ''` del DDL.
3. **Nombres que el readme no da.** `ck_movimiento_origen_entrada` (valores `FAMILIAR`, `HOGAR`, `OTRO` de la sección 3.2) y `ck_conteo_estado` (`EN_PROCESO`, `CERRADO`), con el prefijo `ck_` de ADR-0007, como trae la guía. `tipo` no lleva un `CHECK` propio: `ck_movimiento_por_tipo` rechaza cualquier otro valor.
4. **`corrige_a` como `ForeignKey` + `uq_movimiento_corrige`**, no `OneToOneField`, para conservar el nombre del DDL (readme, sección 6).
5. **`db_index=False`** en las FK de la tabla "Índices de FK que Django no debe crear"; `usuario_id` y `motivo_baja_id` conservan el índice de Django, porque la tabla no los cubre.
6. **Dependencia de `accounts/0002_privilegios`** en `inventario/0001` y `conteos/0001`, para que las tablas nazcan con los permisos de `app_user`; el `REVOKE UPDATE, DELETE, TRUNCATE ON movimiento` va después (ADR-0006). La sección 3.1 del readme solo nombra `UPDATE, DELETE`: la ficha de TK-01 incluye `TRUNCATE`, y se actualiza el DDL de 3.1.
7. **`tg_medicamento_baja` nace en `inventario/0004`**, aunque es del catálogo, porque consulta `existencia` (sección 3.3). El panel valida antes con `MedicamentoAdminForm.clean_activo()` (ADR-0005: el usuario nunca ve un `500`).
8. **Fixture `datos_demo`** ejecuta `cargar_mock.sql` adaptado (sin metacomandos de psql ni `BEGIN`/`COMMIT`, `%` escapados y `:'mock_json'` como parámetro), con todas las validaciones del script activas. Los tests no usan *factories* (CLAUDE.md, Mock-First).
9. **Tests de esquema contra el catálogo de PostgreSQL** (`pg_constraint`, `pg_index`, `pg_trigger`, `pg_attribute`, `pg_class.reloptions`) además de los casos inválidos de la guía, para cubrir los criterios 5 y 6 (nombres y sin índices duplicados) de forma automática. Se comprueban por columna inicial, porque Django pone un *hash* en los nombres de los índices que crea él.
10. **Test de migraciones reversibles en pytest** (readme, ficha de TK-01, "Pruebas"): `migrate conteos zero`, `migrate inventario zero` y `migrate` con `call_command`, en un test con `transaction=True, serialized_rollback=True`.
11. **Lectura de `.env` línea por línea** en `scripts/migrate.sh` y en el atajo de la documentación (`while IFS= read -r linea ...; export "$linea"`), en lugar de `. ./.env`, para admitir valores con espacios sin comillas. `make` usa `-include .env` **sin `export`** y `docker compose` lee `.env` por su cuenta: exportadas, las variables de `make` tenían prioridad para compose, y en Windows (GNU Make 3.81 de GnuWin32) los acentos llegaban mal a `web` ("GerontolÃ³gico"); comprobado en el cierre.
12. **`Makefile` con 18 *targets*:** los 17 de la guía más `actualizar`, que la guía pide sumar al conteo de `make help`; el criterio 3 del readme se actualiza de 17 a 18.
13. **Mensaje del panel:** el de la sección 5 del readme, "No se puede dar de baja: hay existencias de este medicamento", con punto final como los demás mensajes del panel.

## Risks / Trade-offs

- [El código de la guía nunca se ejecutó] → los tests congelados mandan; la implementación ajusta el código, no los tests.
- [`make` en Windows es GNU Make 3.81 (GnuWin32) y la receta usa `SHELL := /bin/bash`] → se comprueba `make help` y `make -n` en el equipo; si no corre, se documenta en la guía como requisito (Git Bash o WSL).
- [El test de migraciones con `transaction=True` vacía la base al terminar] → `serialized_rollback=True` repone el Hogar, los grupos, los motivos y las presentaciones semilla.
- [Con pocos datos PostgreSQL prefiere *Seq Scan*] → el test `lento` usa `enable_seqscan = off`; el año sintético se mide a mano (sección 5, paso 7).
- [La base de desarrollo tiene datos de prueba de HB-09] → la sección 5 recrea la base con `docker compose down -v` antes de cargar el mock (borra la base local).

## Migration Plan

`./scripts/migrate.sh` aplica `inventario/0001` a `0004` y `conteos/0001` y `0002`. Vuelta atrás: `./scripts/migrate.sh conteos zero` y `./scripts/migrate.sh inventario zero` (cada `RunSQL` tiene su inversa; el `REVOKE` se revierte con `GRANT UPDATE, DELETE`).
