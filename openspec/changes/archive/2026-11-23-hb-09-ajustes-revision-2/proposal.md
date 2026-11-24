# Al menos un principio activo, validado en el formulario

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-09 · **Épica:** EP-01

## Why

El hallazgo 4 de la revisión adversarial de HB-09 quedó pendiente. Hoy la regla "al menos un principio activo" (readme, sección 3.2, D2, y paso 3 de la guía de HB-09) depende solo del *inline* del panel (`min_num`). Su aviso es el genérico de Django, y la regla no se puede reutilizar fuera de `/admin/`, por ejemplo en `POST /medicamentos` de la V2. El usuario decidió conservar la regla y validarla en el formulario, no en la base, para mantener la flexibilidad: en el alta y en el cambio, con un mensaje legible antes de guardar.

## What Changes

- **Regla reutilizable** en `apps/catalogo/validadores.py`. Rechaza una lista vacía de principios activos con el mensaje "Un medicamento debe tener al menos un principio activo." y un código propio. Es la misma regla que usarán `POST` y `PATCH /medicamentos` en la V2.
- **Formulario del panel:** el conjunto de renglones de principios activos del medicamento aplica esa regla en el alta y en el cambio. Reemplaza el aviso genérico de `min_num`/`validate_min`. El *inline* sigue mostrando un renglón vacío para capturar.
- **Documentación viva:**
  - **readme:**
    - D2 (sección 3.2): dónde se valida la regla y por qué no está en la base;
    - nota para la V2 en la sección 4, junto a la tabla de endpoints;
    - ficha de HB-09: criterio 2 actualizado.
  - **Anexos** de `03-modelo-datos.md`, `04-api.md` y `06-tickets-trabajo.md`.
  - **`openapi.yaml`:** la descripción de `principios_activos_ids` en `MedicamentoCrear` y `MedicamentoActualizar`.
  - **Guía de HB-09:** paso 3, y el hallazgo 4 pasa a atendido.
  - **Transcripto:** entrada 24 en `06-tickets-trabajo.md`.

**Fuera de alcance:**

- la API de escritura de medicamentos, que es V2;
- una restricción o *trigger* en la base para "al menos uno": se descarta para mantener la flexibilidad (decisión del usuario).

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `catalogo`: "Principios activos en la pantalla del medicamento" pasa a exigir el mensaje legible en el alta y en el cambio. Además, la regla queda disponible para la V2 de la API.

## Impact

- **Código:**
  - nuevos: `app/apps/catalogo/validadores.py` y `app/apps/catalogo/forms.py` (el conjunto de renglones);
  - modificado: `app/apps/catalogo/admin.py` (el *inline* usa ese conjunto y deja de forzar `validate_min`). Sin migraciones.
- **Tests:** `app/apps/catalogo/tests/test_admin.py` (modificado) y `app/apps/catalogo/tests/test_formularios.py` (nuevo).
- **Documentación:**
  - `readme.md`;
  - `03-modelo-datos.md`, `04-api.md` y `06-tickets-trabajo.md`;
  - `docs/api/openapi.yaml`;
  - `docs/tickets/HB-09-admin-catalogo-residentes.md`.
- **Puntos de integración:** TK-01, en su punto 8, agregará a `MedicamentoAdmin` el formulario de la baja con existencias. Es un formulario del medicamento, no del conjunto de renglones, así que no choca.
- **ADR aplicables:**
  - [ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md): esta regla no tiene barrera en la base, por decisión explícita;
  - [ADR-0019](../../../docs/adr/0019-api-rest-solo-lectura-openapi-design-first.md): el contrato es *design-first*;
  - [ADR-0020](../../../docs/adr/0020-habilitadores-en-panel-admin.md): habilitadores en el panel.
