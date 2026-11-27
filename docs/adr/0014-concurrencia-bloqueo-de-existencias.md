# ADR-0014 · Concurrencia: transacciones y bloqueo de Existencias en orden fijo

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `inventario`, `conteos`
- **Fuentes:** `readme.md` §2.1, §2.4.1, §2.5, §2.6, §5 (HU-01, requisitos no funcionales) y §6 (TK-02 puntos 3 y 4, punto de integración 4 y criterios de revisión de backend); `CLAUDE.md` ("Transacciones y concurrencia" y "Dos usuarios de BD")

## Contexto

Hasta 3 usuarios pueden registrar Movimientos a la vez. 2 Bajas simultáneas que juntas superan la Existencia no deben dejar un saldo negativo. 2 Transferencias cruzadas (Hogar → Residente y Residente → Hogar) no deben bloquearse mutuamente (*deadlock*). Una Transferencia debe descontar del origen y abonar al destino en un solo paso.

## Decisión

- **Toda escritura del inventario corre dentro de `transaction.atomic()`.** Si falla el abono al destino, se revierte también el descuento del origen.
- **Bloqueo de las filas de `Existencia`:**
  1. Se crean las filas que falten sin carrera: `bulk_create(ignore_conflicts=True)` (`INSERT ... ON CONFLICT DO NOTHING`).
  2. Se bloquean con `select_for_update()` **en orden fijo de `entidad_id`**, para evitar *deadlocks*.
  3. Con la fila ya bloqueada se valida el saldo (`ExistenciaInsuficiente` si no alcanza), se actualiza y se inserta el Movimiento, todo en la misma transacción.
- **Nunca se usa `select_for_update()` sobre `Movimiento`:** PostgreSQL exige el permiso de `UPDATE` para `FOR UPDATE`, y `app_user` no lo tiene ([ADR-0006](0006-dos-usuarios-de-base-de-datos.md)). La carrera en la corrección la resuelve la restricción `uq_movimiento_corrige` ([ADR-0012](0012-movimientos-inmutables-y-correccion.md)).
- El nivel de aislamiento es el de PostgreSQL por defecto, *read committed*.

## Alternativas consideradas

- **Bloquear el Movimiento original al corregirlo:** se descartó porque `app_user` no tiene permiso de `UPDATE` sobre `movimiento` y fallaría solo en producción (§6, TK-02).

## Consecuencias

**Positivas:**
- 2 Bajas simultáneas que juntas superan la Existencia aplican solo una, y el saldo nunca es negativo (§2.6).
- 20 Transferencias cruzadas simultáneas terminan todas, sin *deadlocks*, y los saldos cuadran (criterio de TK-02).

**Negativas:**
- Las pruebas de `services.py` deben incluir tests de concurrencia con hilos y `transaction=True` ([ADR-0023](0023-pruebas-contra-postgresql-real.md)).
- Bloquear en un orden distinto del fijo es un defecto bloqueante en la revisión de backend (§6).
