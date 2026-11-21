# ADR-0013 · La Existencia es un saldo materializado y conciliable

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `inventario`, `conteos`, `reportes`, `api`
- **Fuentes:** `readme.md` §3.2 (D4, normalización y antipatrones), §3.3 (consulta 1) y §6 (TK-01, punto de integración 8 y prueba de integración); `CLAUDE.md` ("Los movimientos son inmutables")

## Contexto

En rigor, el saldo de un Medicamento en una Entidad es la suma de sus Movimientos. Pero el DFD lo pide como almacén (D4), y sumar todo el historial en cada consulta no tiene sentido. Un dato derivado sin control, en cambio, termina con saldos que no cuadran.

## Decisión

- **`existencia.saldo` se guarda materializado**: una fila por Entidad y Medicamento (`uq_existencia`), en dosis, nunca negativa (`ck_existencia_saldo`).
- **Solo lo modifica `inventario/services.py`**, en la **misma transacción** que inserta el Movimiento y con la fila bloqueada (`SELECT ... FOR UPDATE`), ver [ADR-0011](0011-capa-de-servicios-unica-via-de-escritura.md) y [ADR-0014](0014-concurrencia-bloqueo-de-existencias.md).
- **La vista `v_conciliacion_existencia`** lista las Existencias cuyo saldo no coincide con la suma de sus Movimientos. Vacía significa que todo cuadra. Se comprueba en los tests (un *fixture* `autouse` de TK-02), en la prueba de integración y como verificación periódica.
- **El saldo no se indexa**, ni siquiera en `INCLUDE`, y la tabla se declara con `fillfactor = 90`, para que PostgreSQL pueda hacer actualizaciones *HOT* en la misma página sin reescribir los índices.
- **El reporte mensual no tiene tabla:** se calcula con consultas sobre `movimiento` y `existencia`.

## Alternativas consideradas

- **Calcular el saldo sumando el historial en cada consulta:** se descartó porque el DFD exige el almacén D4 y para no recorrer todo el historial en cada consulta (§3.2).

## Consecuencias

**Positivas:**
- Consultar el saldo es leer una fila.
- Es una excepción documentada y controlada a la 3FN (§3.2).

**Negativas:**
- Cualquier escritura del saldo fuera de `services.py` lo desincronizaría; la conciliación existe para detectarlo.
- El mock no escribe las Existencias a mano: las calcula sumando los Movimientos y las compara con las esperadas (§3.4).
