# Pautas de los Residentes: solo el esquema (D6)

**Historia:** — (habilitador de EP-05) · **Ticket:** HB-07 · **Épica:** EP-05

## Why

Todavía no existe la tabla `pauta` (readme.md, sección 6, HB-07). Las pantallas de Pautas son *Could*, pero el dataset mock (sección 3.4) inserta 3 Pautas y TK-01 lo carga en sus tests: sin esta tabla, la carga del mock falla. Por eso el esquema es *Must* y va antes de TK-01.

## What Changes

- **App `pautas`** con el modelo `Pauta` (sección 3.2, D6): `dosis` `numeric(6,2)`, `frecuencia_horas` `smallint`, `si_necesario`, `indicaciones` y la vigencia `fecha_inicio` / `fecha_fin` (vacía = vigente), además de quién la registró y cuándo.
- **Restricciones**, con los nombres de la sección 3.1: `ck_pauta_dosis`, `ck_pauta_frecuencia`, `ck_pauta_fechas` y la de exclusión `ex_pauta_sin_traslape` (`daterange(fecha_inicio, fecha_fin, '[]')`, sobre `btree_gist`).
- **Índices** de la sección 3.3: `ix_pauta_vigente` (parcial, `WHERE fecha_fin IS NULL`) e `ix_pauta_residente_inicio`, sin índice propio sobre `residente_id`.
- **Migración `RunSQL`** con `fn_pauta_validar` y `tg_pauta_validar` (sección 3.3): solo se registran Pautas de Residentes activos con Medicamentos activos.

**Fuera de alcance:**

- las pantallas de Pautas y su historia (EP-05, *Could*);
- el registro de `Pauta` en `/admin/`;
- cargar las Pautas del dataset mock (TK-01).

## Capabilities

### New Capabilities

- `pautas`: la Pauta de un Residente para un Medicamento, con dosis, frecuencia y vigencia sin traslapes, registrable solo para Residentes y Medicamentos activos.

### Modified Capabilities

<!-- Ninguna. -->

## Impact

- **Archivos nuevos:** `app/apps/pautas/` con `__init__.py`, `apps.py`, `models.py`, las migraciones `0001_initial` y `0002_trigger`, y `tests/test_esquema.py`.
- **Archivos modificados:** `app/config/settings/base.py` (`"apps.pautas"` en `INSTALLED_APPS`).
- **Puntos de integración:**
  - TK-01 depende de `Pauta` (readme, sección 6, ficha de TK-01) para cargar el mock;
  - consume `Medicamento` (HB-05), `Residente` (HB-06), `Usuario` y los privilegios por defecto de `app_user` (HB-03), y la extensión `btree_gist` (HB-05);
  - los nombres de la tabla, las restricciones, los índices, la función y el *trigger* son los de las secciones 3.1 y 3.3.
- **ADR aplicables:**
  - [ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md): PostgreSQL como última barrera;
  - [ADR-0006](../../../docs/adr/0006-dos-usuarios-de-base-de-datos.md): 2 usuarios de base de datos;
  - [ADR-0007](../../../docs/adr/0007-nomenclatura-de-objetos-de-base-de-datos.md): nombres con prefijo;
  - [ADR-0009](../../../docs/adr/0009-bajas-logicas-y-on-delete-restrict.md): Bajas lógicas y `PROTECT`;
  - [ADR-0010](../../../docs/adr/0010-cantidades-en-dosis-y-tipos-de-fecha.md): cantidades en dosis y tipos de fecha;
  - [ADR-0016](../../../docs/adr/0016-pautas-informativas-con-vigencia.md): Pautas informativas, con vigencia y sin traslapes;
  - [ADR-0018](../../../docs/adr/0018-indices-guiados-por-consultas.md): índices guiados por consultas;
  - [ADR-0020](../../../docs/adr/0020-habilitadores-en-panel-admin.md): sin registro en `/admin/` en este ticket;
  - [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md): pruebas contra PostgreSQL real.
