# Alcance de la restauración al confirmar (HB-06)

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-06 · **Épica:** EP-01

## Why

La revisión adversarial de `0e70a01` dejó un *nit*: el docstring de `registrar_residente()` ya aclara que la restauración tras un fallo al confirmar solo aplica si el servicio abre la transacción, pero la spec de `entidades` promete esa restauración sin reserva. El panel `/admin/` (HB-09) llamará al servicio dentro de su propia transacción, así que la spec debe decir lo mismo que el código.

## What Changes

- El requisito "Alta atómica de Residentes" limita la garantía de no alterar el Residente a las fallas ocurridas antes de que el servicio retorne, y dice que dentro de una transacción externa la confirmación queda fuera de ella.
- El Scenario "Un fallo al confirmar permite reintentar" precisa que el Residente se registra sin una transacción externa, que es lo que prueba `test_un_fallo_al_confirmar_permite_reintentar`.
- El comentario junto al `try` de `registrar_residente()` aclara que, dentro de un `atomic` externo, lo que se revierte es el *savepoint* del servicio (segundo *nit* de la misma revisión).
- No cambia el comportamiento ni los tests.

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `entidades`: alcance de la restauración del Residente cuando falla la confirmación.

## Impact

- **Spec:** `openspec/specs/entidades/spec.md`. Solo un comentario en `app/apps/entidades/services.py`, sin cambio de comportamiento: el código ya hace lo descrito, y el docstring lo dice desde `0e70a01`.
- **Puntos de integración:** el punto 11 no cambia. HB-09 debe tenerlo en cuenta: dentro del `atomic` del panel, si falla la confirmación, el objeto queda como guardado.
- **ADR aplicables:** [ADR-0011](../../../docs/adr/0011-capa-de-servicios-unica-via-de-escritura.md) (la escritura pasa por `services.py`).
