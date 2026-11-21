# Catálogo de medicamentos (D2)

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-05 · **Épica:** EP-01

## Why

Todavía no existe el catálogo de medicamentos (readme.md, sección 6, HB-05). Lo necesitan:

- los residentes (HB-06) y las pautas (HB-07);
- el panel (HB-09);
- el inventario (TK-01).

La búsqueda sin mayúsculas ni acentos que usará la pantalla de existencias (TK-03) depende de la función `f_unaccent` y de los índices trigram que crea este ticket.

## What Changes

- **App `catalogo`.** Su primera migración instala las extensiones `btree_gist`, `pg_trgm` y `unaccent`, y crea la función `f_unaccent` (sección 3.1). Depende de `accounts.0002_privilegios`.
- **Modelos** `Presentacion`, `PrincipioActivo`, `Medicamento` y la tabla puente `MedicamentoPrincipioActivo`, con las tablas y columnas de la sección 3.2 (D2).
- **Restricciones en `Meta.constraints`**, que el panel valida antes de llegar a la base:
  - únicas por la expresión `f_unaccent(lower(...))` y con mensaje: `uq_medicamento_nombre_pres_conc` y `uq_principio_activo_nombre`;
  - de valores: `ck_medicamento_tipo`, `ck_medicamento_textos`, `ck_principio_activo_nombre` y `ck_presentacion_nombre`;
  - de la tabla puente: `uq_mpa_medicamento_principio`.
- **Índices:**
  - `ix_medicamento_nombre_trgm`: GIN parcial con `WHERE activo`;
  - `ix_principio_activo_trgm`;
  - `ix_mpa_principio_medicamento`.

  Las FK de la tabla puente no llevan índices duplicados.
- **Migración de datos** con las 8 presentaciones semilla.
- **`apps/expresiones.py`** con `sin_acentos()`, la expresión exacta de los índices, y `no_vacio()`.

**Fuera de alcance:**

- el panel `/admin/` del catálogo (HB-09);
- la baja lógica con saldo, que se rechaza si hay Existencias (TK-02);
- las búsquedas desde la pantalla (TK-03);
- residentes y pautas (HB-06 y HB-07).

## Capabilities

### New Capabilities

- `catalogo`: catálogo de Medicamentos, presentaciones y principios activos, con unicidad sin mayúsculas ni acentos, textos obligatorios y búsqueda por índice trigram.

### Modified Capabilities

<!-- Ninguna. -->

## Impact

- **Archivos nuevos:**
  - `app/apps/expresiones.py`;
  - `app/apps/catalogo/`: `apps.py`, `models.py`, las migraciones `0001_extensiones`, `0002_modelos` y `0003_presentaciones`, y `tests/test_modelos.py`.
- **Archivos modificados:** `app/config/settings/base.py` (`INSTALLED_APPS`).
- **Puntos de integración:**
  - provee el punto 6 (búsqueda sin acentos: `f_unaccent` e índices trigram), que consume TK-03;
  - los nombres de tablas, restricciones e índices son los de las secciones 3.1 y 3.3, que usan TK-01 y el mock (`cargar_mock.sql` busca la presentación con `f_unaccent(lower(...))`).
- **ADR aplicables:**
  - [ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md): PostgreSQL como última barrera;
  - [ADR-0006](../../../docs/adr/0006-dos-usuarios-de-base-de-datos.md): 2 usuarios de base de datos;
  - [ADR-0007](../../../docs/adr/0007-nomenclatura-de-objetos-de-base-de-datos.md): nombres con prefijo;
  - [ADR-0009](../../../docs/adr/0009-bajas-logicas-y-on-delete-restrict.md): bajas lógicas y `PROTECT`;
  - [ADR-0017](../../../docs/adr/0017-busqueda-sin-acentos-con-trigram.md): `f_unaccent(lower(...))` y trigram;
  - [ADR-0018](../../../docs/adr/0018-indices-guiados-por-consultas.md): índices guiados por consultas;
  - [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md): pruebas contra PostgreSQL real.
