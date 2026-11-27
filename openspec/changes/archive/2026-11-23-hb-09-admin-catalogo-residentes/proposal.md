# Catálogo y residentes en el panel `/admin/`

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-09 · **Épica:** EP-01

## Why

Los modelos del catálogo (HB-05) y de residentes (HB-06) y los 2 grupos con sus permisos (HB-08) ya existen, pero no hay ninguna pantalla para capturarlos: el catálogo de medicamentos y los residentes no se pueden dar de alta ni consultar (readme.md, sección 6, HB-09). En el MVP se operan desde el panel `/admin/` de Django, con los "Controles" de la sección 5, para dedicar las semanas siguientes a HU-01, HU-02 y HU-03.

## What Changes

- **Catálogo en el panel:** se registran `Presentacion`, `PrincipioActivo` y `Medicamento`. El medicamento lleva sus principios activos en la misma pantalla (*inline* de la tabla puente, al menos uno, con *autocomplete*).
- **Residentes en el panel:** se registra `Residente`. El alta pasa por `registrar_residente()` y no pide el estado; el egreso o la defunción se registran cambiando `estado` y `fecha_baja`. `Entidad` no se registra: el Hogar es fijo.
- **Controles de la sección 5:**
  - sin la acción "Eliminar" para nadie, ni el Administrador: la baja es lógica (`activo` o `estado`);
  - búsqueda sin mayúsculas ni acentos sobre `f_unaccent(lower(...))`, también por principio activo;
  - filtros por estado, tipo y presentación, y sin consultas N+1 en las listas;
  - las reglas de la base (duplicado sin acentos, fecha de baja) aparecen como mensaje junto al formulario, nunca como un `500`.
- **Permisos por grupo:** *Solo lectura* consulta (`200`) y no da de alta ni cambia (`403`); *Lectura y escritura* da de alta y cambia.
- **Reglas comunes** del panel en `apps/panel.py`, y títulos del panel en `config/urls.py`.

**Fuera de alcance:**

- el mensaje al desmarcar `activo` en un medicamento con existencias y el *trigger* `tg_medicamento_baja` (TK-01, punto 8, porque necesitan la tabla `existencia`);
- existencias, movimientos y conteos, que nunca se registran en el panel (TK-01);
- las pautas en el panel o en pantallas propias (historia de pautas, EP-05);
- las pantallas propias del catálogo y de residentes con Bootstrap y HTMX (V2).

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `catalogo`: agrega la consulta y la edición del catálogo en `/admin/` por grupo, el principio activo en línea, la baja lógica sin borrado, los mensajes de las reglas y la búsqueda sin acentos en el panel.
- `entidades`: agrega los residentes en `/admin/`: alta con el servicio y sin estado, egreso y defunción validados, búsqueda sin acentos, sin borrado y sin el Hogar en el panel.

## Impact

- **Archivos nuevos:** `app/apps/panel.py`, `app/apps/catalogo/admin.py`, `app/apps/entidades/admin.py` y los tests `app/apps/catalogo/tests/test_admin.py` y `app/apps/entidades/tests/test_admin.py`.
- **Archivos modificados:** `app/config/urls.py` (títulos del panel). Sin migraciones.
- **Puntos de integración:**
  - punto 5: usa los 2 grupos y sus permisos de HB-08 (`0003_grupos`); TK-01 les agrega los de inventario;
  - punto 6: la búsqueda usa `sin_acentos()` (`f_unaccent(lower(campo))`) de HB-05;
  - TK-01 (su punto 8) agrega a `MedicamentoAdmin` el formulario que rechaza la baja con existencias y extiende `apps/catalogo/tests/test_admin.py`.
- **ADR aplicables:**
  - [ADR-0008](../../../docs/adr/0008-supertipo-entidad-subtipo-residente.md): el Hogar no se edita; el alta crea entidad y residente juntos;
  - [ADR-0009](../../../docs/adr/0009-bajas-logicas-y-on-delete-restrict.md): bajas lógicas, sin borrado;
  - [ADR-0011](../../../docs/adr/0011-capa-de-servicios-unica-via-de-escritura.md): el alta de residentes pasa por `services.py`;
  - [ADR-0017](../../../docs/adr/0017-busqueda-sin-acentos-con-trigram.md): búsqueda sobre `f_unaccent(lower(campo))`;
  - [ADR-0020](../../../docs/adr/0020-habilitadores-en-panel-admin.md): habilitadores en `/admin/` y sus controles;
  - [ADR-0021](../../../docs/adr/0021-autorizacion-por-grupos-en-el-servidor.md): autorización por grupos en el servidor;
  - [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md): pruebas contra PostgreSQL real.
