# ADR-0017 · Búsqueda sin mayúsculas ni acentos con `f_unaccent` e índices trigram

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `catalogo`, `entidades`, `inventario`, `api`
- **Fuentes:** `readme.md` §2.3, §3.1, §3.3 (consultas 1 y 3, "Implementación en Django y verificación"), §4.1 y §6 (HB-05 y punto de integración 6); `CLAUDE.md` ("Búsquedas de texto" y "Detalles que rompen cosas si se olvidan")

## Contexto

Los usuarios buscan Medicamentos por nombre comercial o por principio activo, y Residentes por nombre, escribiendo sin acentos: "losartan" debe encontrar "Losartán". Una búsqueda parcial sin acentos no escala sin índice, y la búsqueda con mayor valor es la de Existencias por Medicamento o principio activo.

## Decisión

- Se usan las extensiones **`unaccent`** y **`pg_trgm`**, y una envoltura **`f_unaccent(text)`** declarada `IMMUTABLE`, porque solo así se puede usar en un índice.
- **Toda búsqueda por texto** se hace sobre la expresión `f_unaccent(lower(campo))`:
  - Las **búsquedas parciales** ("contiene") usan índices **GIN con `gin_trgm_ops`**: `ix_medicamento_nombre_trgm` (solo el catálogo vigente, `WHERE activo`) e `ix_principio_activo_trgm`.
  - Los índices **para ordenar** son B-tree sobre la misma expresión, como `ix_residente_nombre`.
- **El ORM debe generar exactamente `f_unaccent(lower(campo))`**, con una expresión anotada (`Func(Lower(...), function='f_unaccent')`), para que el planificador use el índice. La expresión común vive en `apps/expresiones.py` (`sin_acentos()`).
- La búsqueda exige **al menos 3 caracteres**, como requiere trigram. En la API, `q` con menos de 3 responde `400` con `LONGITUD_INVALIDA`.
- La búsqueda por nombre o principio activo une las 2 ramas con **`UNION` en lugar de `OR`**, para que cada rama use su propio índice.
- La unicidad del catálogo tampoco distingue mayúsculas ni acentos (`uq_medicamento_nombre_pres_conc` y `uq_principio_activo_nombre`).
- **Precisión (HB-09), sin cambiar la decisión:** el mínimo de 3 caracteres y la `UNION` son de la búsqueda de Existencias (consulta 1, `q` de la API y la pantalla de HU-02). La búsqueda del panel `/admin/` ([ADR-0020](0020-habilitadores-en-panel-admin.md), `apps/panel.py`) usa la misma expresión `f_unaccent(lower(campo))`, pero une los campos con `OR` y no exige mínimo. Busca también entre los Medicamentos dados de baja, que el índice parcial `ix_medicamento_nombre_trgm` no cubre, en un catálogo de cientos de filas.

## Alternativas consideradas

El diseño no documenta alternativas.

## Consecuencias

**Positivas:**
- "losartan" encuentra Losartán y Cozaar por nombre y principio activo, y Hyzaar por su combinación (guion de la demo, §3.4).

**Negativas:**
- Si el ORM genera una expresión distinta, PostgreSQL ignora el índice en silencio. Por eso hay tests que revisan el plan de ejecución (`EXPLAIN`); están marcados `lento` y corren en el CI nocturno ([ADR-0023](0023-pruebas-contra-postgresql-real.md)).
