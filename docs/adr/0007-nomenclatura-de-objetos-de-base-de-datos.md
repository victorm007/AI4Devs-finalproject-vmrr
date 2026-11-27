# ADR-0007 · Nombres explícitos y con prefijo para los objetos de la base de datos

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`
- **Fuentes:** `readme.md` §3.1, §3.3 ("Implementación en Django y verificación") y §6 (TK-01 y criterios de revisión de BD); `CLAUDE.md` ("Nomenclatura de objetos de la BD" y "Detalles que rompen cosas si se olvidan")

## Contexto

Las restricciones de la base de datos son la última barrera ([ADR-0005](0005-postgresql-ultima-barrera-de-integridad.md)). Cuando una falla, su nombre tiene que decir qué regla se violó. Además, Django rechaza nombres de índice de más de 30 caracteres (error `models.E034`).

## Decisión

- Tablas, restricciones, índices, funciones, *triggers* y vistas usan **los nombres exactos** de las §3.1 y §3.3. Los modelos declaran `Meta.db_table` con el nombre en español.
- Los nombres llevan un prefijo según el tipo de objeto:

  | Prefijo | Objeto | Ejemplo |
  |---|---|---|
  | `uq_` | Restricción o índice único | `uq_existencia`, `uq_medicamento_nombre_pres_conc` |
  | `ck_` | *Check constraint* | `ck_existencia_saldo` |
  | `ex_` | Restricción de exclusión | `ex_pauta_sin_traslape` |
  | `fk_` | Clave foránea declarada a mano | `fk_residente_entidad` |
  | `ix_` | Índice normal, compuesto o GIN | `ix_medicamento_nombre_trgm` |
  | `brin_` | Índice BRIN | `brin_movimiento_fecha` |
  | `fn_` / `tg_` | Función y *trigger* | `fn_movimiento_inmutable`, `tg_movimiento_inmutable` |
  | `v_` | Vista | `v_conciliacion_existencia` |

- Para respetar el límite de 30 caracteres, los nombres usan abreviaturas como `med` y `dest`; por ejemplo, `ix_movimiento_dest_med_fecha`.
- Las restricciones declaradas en `Meta.constraints` llevan los mismos nombres del DDL, para que los errores sean reconocibles.

## Alternativas consideradas

El diseño no documenta alternativas.

## Consecuencias

**Positivas:**
- Un error de la base de datos dice qué regla se violó, y el servicio puede traducirlo a una excepción de dominio.

**Negativas:**
- Hay que revisar en cada PR que los nombres coincidan con las §3.1 y §3.3; es un criterio bloqueante de la revisión de BD (§6).
