# ADR-0012 · Movimientos inmutables, corregidos con el Movimiento inverso

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `inventario`, `reportes`, `api`
- **Fuentes:** `readme.md` §2.5, §3.1, §3.2 (D5), §4.1, §5 (HU-01) y §6 (TK-01 y TK-02); `CLAUDE.md` ("Los movimientos son inmutables" y vocabulario de dominio)

## Contexto

El Movimiento es la trazabilidad mínima del sistema: quién trajo cada Medicamento, a quién pertenece y en qué se usó. Si un Movimiento se pudiera editar o borrar, el historial dejaría de ser confiable y el saldo dejaría de poder conciliarse.

## Decisión

- Los Movimientos son de 3 tipos: **Entrada, Transferencia y Baja** (`Movimiento.Tipo`). La restricción `ck_movimiento_por_tipo` fija qué columnas son obligatorias o prohibidas en cada tipo:

  | Tipo | Origen | Destino | Motivo | Origen de la Entrada y "entregado por" |
  |---|---|---|---|---|
  | `ENTRADA` | NULL | Obligatorio | NULL | Obligatorios, salvo en una corrección |
  | `TRANSFERENCIA` | Obligatorio | Obligatorio y distinto del origen | NULL | NULL |
  | `BAJA` | Obligatorio | NULL | Obligatorio | NULL |

- La cantidad es siempre positiva (`ck_movimiento_cantidad`); el sentido lo dan el origen y el destino. Cada Movimiento guarda el usuario y la fecha y hora.
- **Inmutabilidad con doble barrera:** `app_user` no tiene `UPDATE`, `DELETE` ni `TRUNCATE` sobre `movimiento`, y el *trigger* `tg_movimiento_inmutable` rechaza cualquier modificación.
- **Corrección:** se registra el Movimiento inverso, que referencia al original con `corrige_a`. **Una corrección no es un tipo de Movimiento.**

  | Movimiento original | Corrección |
  |---|---|
  | Entrada a X | Baja desde X con motivo `CORRECCION` |
  | Baja desde X | Entrada a X, sin origen de la Entrada ni "entregado por" |
  | Transferencia de X a Y | Transferencia de Y a X |

- **Cada Movimiento se corrige una sola vez** (`uq_movimiento_corrige`), y ninguno se corrige a sí mismo (`ck_movimiento_no_autocorrige`). Si 2 usuarios corrigen el mismo Movimiento a la vez, el `IntegrityError` se traduce a `MovimientoYaCorregido`.
- El motivo `CORRECCION` solo lo usa la corrección: las Bajas normales no pueden elegirlo.
- En la API V2, los Movimientos no tienen `PUT`, `PATCH` ni `DELETE` (`405`) y se corrigen con `POST /movimientos/{id}/correccion`.

## Alternativas consideradas

El diseño no documenta alternativas.

## Consecuencias

**Positivas:**
- El historial conserva el error, su corrección y el Movimiento correcto (como en el mock, §3.4).
- Aunque alguien robe las credenciales de la aplicación, no puede reescribir el historial (§2.5).

**Negativas:**
- Si el saldo ya no alcanza (por ejemplo, la Entrada errónea ya se consumió), la corrección falla con `ExistenciaInsuficiente` (§6, TK-02).
- No se puede bloquear un Movimiento con `select_for_update()` ([ADR-0014](0014-concurrencia-bloqueo-de-existencias.md)).
