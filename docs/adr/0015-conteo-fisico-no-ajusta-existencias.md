# ADR-0015 · El conteo físico no ajusta las Existencias

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `conteos`, `inventario`, `reportes`
- **Fuentes:** `readme.md` §3.1, §3.2 (conteos físicos y normalización), §3.3 y §5 (HU-03, "Por qué no ajusta solo"); `CLAUDE.md` ("El conteo físico no ajusta existencias")

## Contexto

En cada corte, el hogar compara lo que hay en el anaquel contra lo registrado. Las diferencias revelan faltantes o mermas, y hace falta saber su causa y quién la resolvió.

## Decisión

- Un **conteo físico** (`conteo_fisico`) es de una Entidad y un período a demanda. Tiene 2 estados: `EN_PROCESO`, que permite contar en varias sesiones, y `CERRADO`.
- Cada renglón (`detalle_conteo`, uno por Medicamento) guarda:
  - `cantidad_fisica`: las dosis contadas.
  - `cantidad_sistema`: una **foto** del saldo registrado en el momento de contar. Es un hecho histórico, no una redundancia.
  - `diferencia`: una columna **generada por la base de datos** (`cantidad_fisica − cantidad_sistema`), que nunca se escribe a mano.
- **El conteo no ajusta las Existencias.** Cada diferencia se resuelve con un Movimiento normal: una Baja con su motivo real (merma, rotura, consumo no registrado…) o una Entrada por sobrante, con origen `OTRO`. La nota del Movimiento indica el conteo de origen.
- **Un conteo cerrado es inmutable:** lo impiden los *triggers* `tg_conteo_cerrado` y `tg_detalle_conteo_cerrado`. Para cerrar hace falta al menos un renglón, pero no que todas las diferencias estén resueltas.

## Alternativas consideradas

- **Ajuste automático del saldo:** se descartó porque escondería la causa de la diferencia y movería saldos sin un responsable ni un motivo (§5, HU-03).

## Consecuencias

**Positivas** (§5):
- De cada diferencia queda quién la resolvió, cuándo y por qué.
- El saldo sigue siendo la suma de los Movimientos, así que la conciliación se mantiene ([ADR-0013](0013-existencia-materializada-y-conciliable.md)).
- El reporte mensual muestra las mermas con su motivo.
- El conteo es la evidencia de lo que se encontró, y los Movimientos, de cómo se resolvió.

**Negativas:**
- Resolver una diferencia exige un paso más: registrar el Movimiento desde el renglón.
