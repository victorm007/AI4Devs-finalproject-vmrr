# ADR-0009 · Bajas lógicas y `ON DELETE RESTRICT` en todas las claves foráneas

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `accounts`, `catalogo`, `entidades`, `inventario`
- **Fuentes:** `readme.md` §2.5 (privacidad), §3.1, §3.2 (D1, D2, D3, D5 y antipatrones), §3.3, §5 (controles del panel) y §6 (TK-01); `CLAUDE.md` ("Bajas lógicas" y "Protección de datos históricos")

## Contexto

Los Movimientos, las Existencias, las Pautas y los conteos hacen referencia a Medicamentos, Entidades, usuarios y motivos de Baja. Borrar físicamente uno de ellos rompería el historial y dejaría claves foráneas sin destino. La LFPDPPP también pide conservar el historial de los Residentes egresados o fallecidos.

## Decisión

- **Todas las claves foráneas son `ON DELETE RESTRICT`** (`on_delete=models.PROTECT` en Django): no se puede borrar físicamente ningún registro con historial.
- **La Baja es lógica:**

  | Registro | Cómo se da de Baja |
  |---|---|
  | Medicamento, presentación, motivo de Baja | `activo = false` |
  | Residente | `estado` `EGRESADO` o `FALLECIDO`, con `fecha_baja` (`ck_residente_baja`) |
  | Usuario | `is_active = false` |

- **No se da de Baja un Medicamento con Existencias:** lo rechazan el formulario de `MedicamentoAdmin` y, como última barrera, el *trigger* `tg_medicamento_baja`.
- La unicidad del Medicamento incluye a los inactivos: en lugar de duplicar uno, se reactiva.
- Las Entradas y Transferencias exigen un destino activo, pero un Residente egresado sí puede ceder o dar de Baja sobrantes. Las correcciones quedan exentas de la regla de destino activo.
- El panel `/admin/` no permite borrar (`has_delete_permission = False`), y ningún grupo tiene permisos `delete_*`.

## Alternativas consideradas

- **Borrado físico del historial:** se descartó porque se pierde la trazabilidad y quedan FK rotas (antipatrón, §3.2).

## Consecuencias

**Positivas:**
- El historial de Movimientos, Pautas y conteos nunca pierde sus referencias.
- Cumple la LFPDPPP: los Residentes egresados o fallecidos quedan inactivos en lugar de borrados (§2.5).

**Negativas:**
- Las búsquedas y formularios deben filtrar los registros inactivos. Por ejemplo, el índice `ix_medicamento_nombre_trgm` solo cubre el catálogo vigente (`WHERE activo`).
