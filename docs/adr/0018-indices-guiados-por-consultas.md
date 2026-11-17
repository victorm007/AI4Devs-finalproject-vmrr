# ADR-0018 · Índices guiados por las consultas frecuentes

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes`
- **Fuentes:** `readme.md` §3.3 (volumen esperado, principios aplicados, consultas 1 a 3, DDL de índices, índices de FK y verificación) y §6 (criterios de revisión de BD)

## Contexto

El catálogo y las Entidades son pequeños: unos 300 Medicamentos y 21 Entidades. La tabla que crece es `movimiento`: de 60,000 a 175,000 filas por año si se registran las Bajas por consumo. Le siguen `detalle_conteo` y `pauta`. Cada índice encarece las escrituras.

## Decisión

- **Cada índice atiende una consulta concreta.** No se indexa "por si acaso". Las 3 consultas frecuentes son: Existencias por Medicamento o principio activo, detalles del conteo físico, y Pautas por Residente.
- **Sin índices redundantes:** Django crea un índice por cada `ForeignKey`. Cuando un índice compuesto ya empieza por esa columna, la FK se declara con `db_index=False` (lista de la §3.3).
- **Orden de columnas:** primero las de igualdad (`=`) y después las de rango u orden (fecha).
- **Índices parciales e `INCLUDE`** donde reducen el tamaño o permiten *index-only scans*. Por ejemplo, `ix_movimiento_origen_med_fecha` excluye las Entradas, que no tienen origen, e `ix_detalle_medicamento_conteo` incluye las cantidades del conteo.
- **BRIN** sobre `movimiento.fecha_hora` (`brin_movimiento_fecha`) para el reporte mensual: la tabla solo recibe inserciones en orden cronológico, el caso ideal, y el índice ocupa unos KB.
- No se indexan columnas que cambian en cada Movimiento, como `existencia.saldo` ([ADR-0013](0013-existencia-materializada-y-conciliable.md)).
- Los índices se declaran en `Meta.indexes` (`GinIndex`, `Index` con `condition` e `include`, `BrinIndex`).
- **Verificación:**
  - `EXPLAIN (ANALYZE, BUFFERS)` sobre un año de datos sintéticos (unos 175,000 Movimientos).
  - Un test de integración con `assertNumQueries` y el plan de las consultas clave.
  - En producción, `pg_stat_statements` para detectar consultas lentas y `pg_stat_user_indexes` para encontrar índices sin uso.

## Alternativas consideradas

El diseño no documenta alternativas.

## Consecuencias

**Positivas:**
- Las escrituras de `movimiento` cargan solo los índices que alguna consulta usa.

**Negativas:**
- Una consulta frecuente nueva necesita revisar si algún índice la atiende. Los índices duplicados son un defecto bloqueante en la revisión de BD (§6).
