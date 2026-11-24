# Ajustes de la revisión adversarial de HB-09

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-09 · **Épica:** EP-01

## Why

La revisión adversarial del commit `6c345f0` (PR #2) no encontró bloqueantes, pero sí 2 hallazgos mayores y varios menores. Los mayores: la búsqueda del panel no separa palabras ni recorta espacios ("María Hernández" o "losartan " no encuentran nada), y desde el panel se pueden crear presentaciones duplicadas sin acentos ("Tableta" junto a "tableta"). Ese segundo hueco permite registrar 2 veces el mismo medicamento sin que `uq_medicamento_nombre_pres_conc` lo detecte. Antes de HB-09 no era alcanzable, porque nadie daba de alta presentaciones.

## What Changes

- **Presentación sin duplicados en la base:** el `UNIQUE` literal de `presentacion.nombre` (HB-05) se reemplaza por el índice único por expresión `uq_presentacion_nombre` sobre `f_unaccent(lower(nombre))`, con mensaje, igual que `uq_principio_activo_nombre`. Va en una migración nueva de `catalogo`, reversible.
- **Búsqueda por palabras:** el término se divide en palabras. Cada palabra debe aparecer en alguno de los campos, y todas las palabras deben coincidir. Los espacios sobrantes no cuentan, y un término vacío no filtra.
- **Sin presentaciones dadas de baja en el alta** de un medicamento. Al editar uno, se conserva la suya aunque esté inactiva.
- **Configuración del panel comprobada:** un *ModelAdmin* con el *mixin* de búsqueda y sin campos de búsqueda da un error de `check` (`panel.E001`), en lugar de devolver todas las filas.
- **Más pruebas:**
  - el alta de un medicamento y de un residente como `app_user`;
  - el `403` de *Solo lectura* al cambiar una presentación o un principio activo, y la búsqueda de esas 2 listas;
  - la CSP sin `<style>` ni atributos `on*=`, en el alta, la lista y la página de cambio de medicamentos y de residentes.
- **Documentación viva:**
  - el readme (secciones 3.1, 3.2 y la ficha de HB-09) y su anexo en `03-modelo-datos.md` y en `06-tickets-trabajo.md`;
  - ADR-0017 y las guías de HB-05 y HB-09;
  - los transcriptos del proceso.

**Fuera de alcance** (quedan anotados en la guía de HB-09):

- el mínimo de un principio activo para guardar un medicamento que no tiene ninguno (hallazgo 4);
- las reglas de transición de estado del residente y los residentes duplicados (hallazgo 5);
- los títulos del panel sin test, `SinBorrarMixin` en `accounts` y la frase de `CLAUDE.md` (hallazgo 10).

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `catalogo`:
  - agrega la presentación sin duplicados sin acentos y solo las presentaciones activas en el alta;
  - agrega la búsqueda por palabras y la configuración comprobada del panel;
  - agrega el alta con los permisos de `app_user`;
  - amplía los escenarios de la búsqueda y de la CSP.
- `entidades`:
  - agrega la búsqueda de residentes por palabras;
  - agrega el alta de un residente con los permisos de `app_user`;
  - agrega la CSP en las páginas de residentes.

## Impact

- **Código:**
  - `app/apps/catalogo/models.py`, más la migración `catalogo/0004_presentacion_unica`;
  - `app/apps/panel.py` y `app/apps/catalogo/admin.py`.
- **Tests:**
  - `app/apps/catalogo/tests/test_modelos.py`;
  - `app/apps/catalogo/tests/test_admin.py`;
  - `app/apps/entidades/tests/test_admin.py`.
- **Documentación:**
  - `readme.md` (3.1, 3.2 y la ficha de HB-09), con los anexos de `03-modelo-datos.md` y `06-tickets-trabajo.md`;
  - ADR-0017;
  - `docs/tickets/HB-05-catalogo.md` y `docs/tickets/HB-09-admin-catalogo-residentes.md`;
  - `CLAUDE.md` (estado) y las entradas del transcripto `06-tickets-trabajo.md`.
- **Diagrama:** el PNG del modelo de datos en `diagramas/` se regenera desde el Mermaid del readme. Lo genera el usuario.
- **Puntos de integración:**
  - punto 6: la búsqueda sigue usando `sin_acentos()`;
  - el mock (`cargar_mock.sql`) ya une las presentaciones con `f_unaccent(lower(...))`, así que no cambia.
- **ADR aplicables:**
  - [ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md): la base es la última barrera;
  - [ADR-0007](../../../docs/adr/0007-nomenclatura-de-objetos-de-base-de-datos.md): prefijo `uq_`;
  - [ADR-0009](../../../docs/adr/0009-bajas-logicas-y-on-delete-restrict.md): los formularios no ofrecen registros dados de baja;
  - [ADR-0017](../../../docs/adr/0017-busqueda-sin-acentos-con-trigram.md): unicidad del catálogo sin mayúsculas ni acentos; se extiende a `presentacion`;
  - [ADR-0020](../../../docs/adr/0020-habilitadores-en-panel-admin.md): habilitadores en el panel;
  - [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md): pruebas con los permisos reales.
