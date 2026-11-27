# Design

## Context

Son ajustes solo de documentación tras la cuarta revisión de HB-09 (ver `proposal.md`). El código de `app/` no cambia, salvo el *docstring* de `validadores.py`.

## Goals / Non-Goals

**Goals:**
- Que la guía de HB-09, seguida tal cual, cumpla lo que dice en cada paso, rojo incluido.
- Que la regla de la V2 se describa con una sola capa.

**Non-Goals:** los hallazgos 4 y 6 (proposal, "Fuera de alcance").

## Decisions

### 1. El *import* dentro del test

En la sección 3.1, `SIN_PRINCIPIO_ACTIVO` se importa dentro de `test_sin_principio_activo_el_formulario_avisa`, igual que en el test real. Con el *import* al inicio, el módulo fallaría en la recolección hasta el paso 3, y el paso 1 no se cumpliría.

### 2. Una sola capa en la V2

`principios_activos_ids` tiene `minItems: 1`: la lista vacía nunca llega a `exigir_principio_activo()`. La documentación dice que el esquema la rechaza con `CAMPO_VACIO` y el mensaje de la regla, y que la función protege a quien guarde sin pasar por el esquema. **Alternativa descartada:** quitar `minItems` del contrato para que la regla sea la única capa. Restaría validación al contrato, que es *design-first* ([ADR-0019](../../../docs/adr/0019-api-rest-solo-lectura-openapi-design-first.md)).

### 3. Los tests del paso 3b en la guía

La sección 3.3 trae una versión base de los tests de `uq_presentacion_nombre`: la base de datos y `full_clean()`. Los tests completos están en `app/apps/catalogo/tests/test_modelos.py`.

## Risks / Trade-offs

- [La guía duplica el código y los tests del repositorio] → en cada ajuste se comprueba que los bloques coinciden con los archivos y que los tests base pasan contra el código actual.
