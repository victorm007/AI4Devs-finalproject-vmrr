# Esquema de Existencias, Movimientos y conteos físicos (D4, D5 y conteos)

**Historia:** HU-01, HU-02, HU-03 · **Ticket:** TK-01 · **Épica:** EP-02 (base también de EP-03 y EP-04)

## Why

Las 3 historias del MVP dependen de que el saldo sea confiable, y todavía no existen las tablas que lo guardan (readme.md, sección 6, TK-01). Este ticket lleva a migraciones las tablas D4, D5 y de conteos de la sección 3, para que PostgreSQL sea la última barrera: aunque un error de código intente dejar un saldo negativo o editar un Movimiento, la base lo rechaza. Además deja los *fixtures* con el mock que usan TK-02 y TK-03, y el `Makefile` que fija cómo se lee `.env`.

## What Changes

- **Apps `inventario` y `conteos`** con los modelos `MotivoBaja`, `Existencia` y `Movimiento` (`Movimiento.Tipo` y `Movimiento.OrigenEntrada`), `ConteoFisico` y `DetalleConteo`, con los tipos y nombres de la sección 3.2: cantidades `numeric(10,2)`, `diferencia` como columna generada, todas las FK con `PROTECT` y `db_index=False` en las que cubre un índice compuesto.
- **Restricciones** con los nombres del DDL: `uq_existencia`, `ck_existencia_saldo`, `ck_movimiento_por_tipo`, `ck_movimiento_cantidad`, `ck_movimiento_entregado`, `ck_movimiento_no_autocorrige`, `uq_movimiento_corrige`, `ck_conteo_periodo`, `ck_conteo_cierre`, `uq_detalle_conteo`, `ck_detalle_fisica` y `ck_detalle_sistema`.
- **Índices** de la sección 3.3 sobre `existencia`, `movimiento`, `conteo_fisico` y `detalle_conteo`, incluidos los parciales, el `INCLUDE` y `brin_movimiento_fecha`.
- **Migraciones `RunSQL`** reversibles: `tg_movimiento_inmutable`, `tg_movimiento_validar_destino`, `tg_conteo_cerrado`, `tg_detalle_conteo_cerrado`, `tg_medicamento_baja`, `fillfactor = 90` en `existencia`, la vista `v_conciliacion_existencia` y `REVOKE UPDATE, DELETE, TRUNCATE ON movimiento FROM app_user`.
- **Migraciones de datos:** los 8 motivos de baja (`CONSUMO` … `CORRECCION`) y los permisos de los 2 grupos sobre los modelos nuevos (`view_existencia`, `view_movimiento`, `view_motivobaja`, y `add_movimiento` para *Lectura y escritura*; nadie recibe `change_movimiento` ni `delete_movimiento`).
- **Panel:** ninguno de los modelos nuevos se registra en `/admin/`, y el formulario de `MedicamentoAdmin` rechaza desmarcar `activo` si el Medicamento tiene Existencias, con el mensaje de la sección 5.
- **Fixtures de prueba compartidos:** `datos_demo`, `demo`, `como_app_user` y el helper `saldo`, junto a `ejecutar_sql` (HB-03).
- **`Makefile` de la raíz** con `make help` y los atajos de desarrollo local, y lectura de `.env` que admite valores con espacios sin comillas: `HOGAR_NOMBRE` queda sin comentar en `.env.example`.

**Fuera de alcance:** la lógica de negocio (TK-02), las pantallas y la API, los usuarios de base de datos (HB-01 y HB-03) y las tablas de catálogo, entidades y pautas (HB-05 a HB-07). Los permisos de grupo sobre los conteos llegan con TK-06.

## Capabilities

### New Capabilities

- `inventario`: Existencias y Movimientos inmutables con sus reglas en la base de datos, motivos de baja, conciliación del saldo, privilegios de `app_user` sobre `movimiento`, permisos de los grupos y los *fixtures* de prueba con el mock.
- `conteos`: conteos físicos con la foto del saldo, diferencia calculada por la base y conteo cerrado inmutable.

### Modified Capabilities

- `catalogo`: el panel rechaza con un mensaje la baja de un Medicamento con Existencias, y la base la rechaza como última barrera.
- `infraestructura`: `Makefile` de desarrollo local y lectura de `.env` con valores con espacios en `scripts/migrate.sh`, los atajos, `make` y `docker compose`.

## Impact

- **Archivos nuevos:** `Makefile`; `app/apps/inventario/` y `app/apps/conteos/` (modelos, migraciones `inventario/0001` a `0004` y `conteos/0001` y `0002`, y `tests/test_esquema.py`).
- **Archivos modificados:** `app/conftest.py`, `app/pruebas.py`, `app/config/settings/base.py`, `app/apps/catalogo/admin.py`, `app/apps/accounts/tests/test_privilegios.py`, `app/apps/catalogo/tests/test_admin.py`, `scripts/migrate.sh`, `.env.example`, y la documentación del atajo de `.env` (`readme.md`, `CLAUDE.md` y las guías).
- **Puntos de integración** (readme, sección 6): provee el 1 (modelos), el 3 (restricciones ↔ excepciones), el 4 (privilegios de `app_user` sobre `movimiento`), el 5 (permisos de los grupos), el 7 (*fixtures*) y el 8 (vista de conciliación); consume el 11 (`Entidad.activa`, HB-06).
- **ADR aplicables:**
  - [ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md): PostgreSQL como última barrera;
  - [ADR-0006](../../../docs/adr/0006-dos-usuarios-de-base-de-datos.md): 2 usuarios de base de datos;
  - [ADR-0007](../../../docs/adr/0007-nomenclatura-de-objetos-de-base-de-datos.md): nombres con prefijo;
  - [ADR-0009](../../../docs/adr/0009-bajas-logicas-y-on-delete-restrict.md): Bajas lógicas y `PROTECT`;
  - [ADR-0010](../../../docs/adr/0010-cantidades-en-dosis-y-tipos-de-fecha.md): cantidades en dosis y tipos de fecha;
  - [ADR-0011](../../../docs/adr/0011-capa-de-servicios-unica-via-de-escritura.md): modelos sin lógica; solo `services.py` escribirá (TK-02);
  - [ADR-0012](../../../docs/adr/0012-movimientos-inmutables-y-correccion.md): Movimientos inmutables y corrección;
  - [ADR-0013](../../../docs/adr/0013-existencia-materializada-y-conciliable.md): Existencia materializada y conciliable;
  - [ADR-0015](../../../docs/adr/0015-conteo-fisico-no-ajusta-existencias.md): el conteo no ajusta Existencias;
  - [ADR-0018](../../../docs/adr/0018-indices-guiados-por-consultas.md): índices guiados por consultas;
  - [ADR-0020](../../../docs/adr/0020-habilitadores-en-panel-admin.md): habilitadores en `/admin/`;
  - [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md): pruebas contra PostgreSQL real.
