# Entidades: el Hogar y los Residentes (D3)

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-06 · **Épica:** EP-01

## Why

Todavía no existen las Entidades (readme.md, sección 6, HB-06). Son las dueñas de las Existencias: el Hogar o un Residente. Lo necesitan:

- las pautas (HB-07), que apuntan a `residente`;
- el login y los grupos (HB-08) y el panel (HB-09), que dan de alta Residentes;
- el inventario (TK-01), con las FK de `existencia`, `movimiento` y `conteo_fisico` hacia `entidad`;
- el servicio de movimientos (TK-02) y la pantalla de Existencias (TK-03), que consumen `Entidad.activa` y `Entidad.__str__`.

## What Changes

- **App `entidades`** con `Entidad` (supertipo) y `Residente` (subtipo, con la misma clave), con las tablas y columnas de la sección 3.2 (D3).
- **Restricciones**, con los nombres de las secciones 3.1 y 3.3:
  - de `entidad`: `uq_entidad_un_hogar`, `uq_entidad_id_tipo`, `ck_entidad_tipo`, `ck_entidad_nombre` y `ck_entidad_nombre_no_vacio`;
  - de `residente`: `ck_residente_tipo`, `ck_residente_estado`, `ck_residente_baja`, `ck_residente_fechas`, `ck_residente_nombres` y `ck_residente_nacimiento`.
- **Índice** `ix_residente_nombre`, sobre `f_unaccent(lower(...))` de apellido y nombre.
- **FK compuesta** `fk_residente_entidad (entidad_id, tipo) → entidad (id, tipo)` en una migración `RunSQL`, porque Django no declara FK compuestas.
- **Migración de datos** que crea el Hogar con el nombre de `HOGAR_NOMBRE` (por defecto, "Hogar Gerontológico Demo").
- **Punto de integración 11:** `Entidad.activa` (el Hogar siempre; un Residente solo si su estado es `ACTIVO`) y `Entidad.__str__` (nombre del Hogar o nombre completo del Residente).
- **`services.registrar_residente()`**, que da de alta la Entidad y el Residente en una sola transacción.
- **Configuración:** el setting `HOGAR_NOMBRE`, leído del entorno, y su variable en `.env.example` y en `docker-compose.yml`.

**Fuera de alcance:**

- el panel `/admin/` de Residentes y la regla de que el Hogar no se da de Baja (HB-09);
- las pautas (HB-07);
- las Existencias, los Movimientos y la regla de destino activo (TK-01 y TK-02);
- cargar el dataset mock de Residentes (TK-01).

## Capabilities

### New Capabilities

- `entidades`: el Hogar (único) y los Residentes como Entidades dueñas de Existencias, con subtipo coherente, fechas y nombres válidos, estado activo derivado y alta atómica.

### Modified Capabilities

<!-- Ninguna. -->

## Impact

- **Archivos nuevos:** `app/apps/entidades/` con `apps.py`, `models.py`, `services.py`, las migraciones `0001_initial`, `0002_fk_compuesta` y `0003_hogar`, y `tests/test_modelos.py` y `tests/test_services.py`.
- **Archivos modificados:** `app/config/settings/base.py` (`INSTALLED_APPS` y `HOGAR_NOMBRE`), `.env.example` y `docker-compose.yml` (`HOGAR_NOMBRE` en `web`).
- **Puntos de integración:**
  - provee el punto 11 (`Entidad.activa` y `Entidad.__str__`), que consumen TK-01, TK-02 y TK-03;
  - los nombres de tablas, restricciones e índices son los de las secciones 3.1 y 3.3, que usan TK-01 y el mock (el Hogar con `id = 1` en una base nueva);
  - consume el punto 6 de HB-05 (`f_unaccent` y `apps/expresiones.py`).
- **ADR aplicables:**
  - [ADR-0004](../../../docs/adr/0004-configuracion-por-entorno-variables-db.md): configuración por entorno (`HOGAR_NOMBRE`);
  - [ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md): PostgreSQL como última barrera;
  - [ADR-0006](../../../docs/adr/0006-dos-usuarios-de-base-de-datos.md): 2 usuarios de base de datos;
  - [ADR-0007](../../../docs/adr/0007-nomenclatura-de-objetos-de-base-de-datos.md): nombres con prefijo;
  - [ADR-0008](../../../docs/adr/0008-supertipo-entidad-subtipo-residente.md): supertipo `entidad` y subtipo `residente`;
  - [ADR-0009](../../../docs/adr/0009-bajas-logicas-y-on-delete-restrict.md): Bajas lógicas y `PROTECT`;
  - [ADR-0011](../../../docs/adr/0011-capa-de-servicios-unica-via-de-escritura.md): la escritura pasa por `services.py`;
  - [ADR-0017](../../../docs/adr/0017-busqueda-sin-acentos-con-trigram.md): `f_unaccent(lower(...))`;
  - [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md): pruebas contra PostgreSQL real.
