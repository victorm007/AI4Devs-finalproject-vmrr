# Design

## Context

Son ajustes solo de documentación tras la sexta revisión de HB-09 (ver `proposal.md`). El código de `app/` no cambia.

## Goals / Non-Goals

**Goals:**
- Que la nota de la V2 y la spec no digan que el esquema "aplica" o "reutiliza" la regla. El esquema exige lo mismo por su cuenta y comparte el mensaje.
- Que la guía de HB-09, seguida tal cual, ejecute `test_formularios.py` en el rojo y en el verde.

**Non-Goals:** cambiar el contrato, la regla o los tests del repositorio.

## Decisions

### 1. `test_formularios.py` se ejecuta aparte en el paso 1

El archivo importa `validadores.py` y `forms.py` al inicio, así que falla en la recolección hasta el paso 3. En el mismo comando que los demás, pytest se interrumpiría por ese error y no correría el resto. Por eso el paso 1 lo ejecuta aparte, con su error esperado. **Alternativa descartada:** pasar los *imports* dentro de cada test, como en la sección 3.1. Dejaría la guía distinta del archivo del repositorio.

### 2. Una versión base en la sección 3.4

Hay 4 tests: la regla con la lista vacía y con un principio activo, y el conjunto de renglones sin ninguno y con uno. El archivo completo está en `app/apps/catalogo/tests/test_formularios.py`.

## Risks / Trade-offs

- [La guía duplica los tests del repositorio] → el bloque de la sección 3.4 se comprueba con el código actual: pasa, y ruff no marca nada.
