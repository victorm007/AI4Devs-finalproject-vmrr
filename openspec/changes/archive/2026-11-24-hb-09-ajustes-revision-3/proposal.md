# Ajustes de la segunda revisión adversarial de HB-09

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-09 · **Épica:** EP-01

## Why

La segunda revisión adversarial (commit `25b4219`, PR #2) no encontró bloqueantes. Dejó 2 hallazgos mayores: la búsqueda con varios principios activos no tiene test, y la guía de HB-09 ya no se puede seguir en el paso 3. Además dejó 8 menores. El usuario pidió atender los mayores y los menores baratos (3, 4, 5, 7, 9 y 10), y anotar el 6 y el 8.

## What Changes

- **Tests de la búsqueda:**
  - un medicamento con 2 principios activos encontrado una sola vez con "losartan hidroclorotiazida";
  - `%` y `_` buscados como texto.
- **Tope de 8 palabras** en la búsqueda del panel. Las demás se ignoran.
- **`panel.E002`:** la comprobación del sistema detecta un campo de búsqueda que no existe, y nombra el campo.
- **La regla "al menos un principio activo":**
  - sin colección (`None`) se rechaza como la lista vacía;
  - un texto es `TypeError`;
  - queda documentado que la V2 traduce `sin_principio_activo` a `CAMPO_VACIO`.
- **Test de presentaciones inactivas:** también comprueba el `<option>` del HTML, no solo la lista interna del campo.
- **Documentación viva:**
  - la guía de HB-09:
    - el paso 3 se puede seguir completo, con el *import* y el código de `forms.py` y `validadores.py`;
    - la sección 5 nombra la migración 0004;
    - lleva las notas de los hallazgos 6 y 8;
  - ADR-0005, con los 3 índices únicos por expresión;
  - la nota de la V2 en el readme (sección 4) y su anexo en `04-api.md`;
  - `openapi.yaml`;
  - `CLAUDE.md`;
  - la entrada 25 del transcripto.

**Fuera de alcance**, solo anotado en la guía:

- **hallazgo 6:** el botón **+** permite crear una presentación inactiva que después no se puede elegir;
- **hallazgo 8:** la consulta de duplicados sin acentos antes de aplicar la `0004` en el servidor del hogar.

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `catalogo`:
  - búsqueda: tope de palabras, comodines literales y varios principios activos;
  - configuración comprobada: campo inexistente;
  - regla de principio activo: `None`, texto y traducción para la V2.

## Impact

- **Código:** `app/apps/panel.py` y `app/apps/catalogo/validadores.py`.
- **Tests:** `app/apps/catalogo/tests/test_admin.py` y `app/apps/catalogo/tests/test_formularios.py`.
- **Documentación:**
  - `docs/tickets/HB-09-admin-catalogo-residentes.md`;
  - `docs/adr/0005-postgresql-ultima-barrera-de-integridad.md`;
  - `readme.md` y `04-api.md`;
  - `docs/api/openapi.yaml`;
  - `CLAUDE.md` y `06-tickets-trabajo.md`.
- **Sin migraciones.**
- **ADR aplicables:**
  - [ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md): se precisa su lista de índices únicos por expresión;
  - [ADR-0017](../../../docs/adr/0017-busqueda-sin-acentos-con-trigram.md): búsqueda sobre `f_unaccent(lower(...))`;
  - [ADR-0019](../../../docs/adr/0019-api-rest-solo-lectura-openapi-design-first.md): el contrato de la V2;
  - [ADR-0020](../../../docs/adr/0020-habilitadores-en-panel-admin.md): habilitadores en el panel.
