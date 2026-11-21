# ADR-0008 · Entidad como supertipo del Hogar y de cada Residente

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `entidades`, `inventario`, `conteos`, `pautas`
- **Fuentes:** `readme.md` §2.5 (privacidad), §3.1, §3.2 (D3, normalización y antipatrones) y §6 (punto de integración 11); `CLAUDE.md` ("Las entidades son un supertipo")

## Contexto

Las Existencias pertenecen a una Entidad: el Hogar o un Residente. Los Movimientos van de una Entidad a otra, y el conteo físico se hace por Entidad. Esas tablas necesitan una clave foránea real hacia "la Entidad", sin que la base pierda la capacidad de validarla.

## Decisión

- **`entidad`** es el **supertipo** de todo lo que puede poseer Existencias, y su columna `tipo` (`HOGAR` o `RESIDENTE`) es el discriminador. `existencia`, `movimiento` y `conteo_fisico` tienen una sola FK real hacia `entidad`.
- **`residente`** es el **subtipo**, con la misma clave que su Entidad (relación 1:0..1). La FK compuesta `fk_residente_entidad` (`entidad_id`, `tipo`) → `entidad (id, tipo)`, junto con `uq_entidad_id_tipo` y `ck_residente_tipo`, impide subtipos incoherentes.
- **Un solo Hogar:** el índice único parcial `uq_entidad_un_hogar` (`tipo` `WHERE tipo = 'HOGAR'`). El Hogar lo crea una migración de datos, y la aplicación no permite cambiar su tipo ni darlo de Baja.
- `entidad.nombre` solo se usa para el Hogar (`ck_entidad_nombre`). El nombre del Residente vive desglosado en 4 campos atómicos y el nombre para mostrar se compone al vuelo, sin guardarlo.
- **Una Entidad está activa** si es el Hogar, que siempre lo está, o un Residente con estado `ACTIVO`. El estado no se duplica en `entidad`. `Entidad.activa` y `Entidad.__str__` son un contrato entre tickets (punto de integración 11).
- Las Pautas apuntan a `residente`, nunca al Hogar.
- **Minimización de datos (LFPDPPP):** del Residente solo se guardan su nombre y sus fechas de nacimiento, de ingreso y de Baja.

## Alternativas consideradas

- **Asociación polimórfica** (`entidad_tipo` + `entidad_id` sin FK): se descartó porque la base de datos no puede validar esa referencia y quedan referencias huérfanas (antipatrón, §3.2).

## Consecuencias

**Positivas:**
- Todas las FK son reales y las valida PostgreSQL.
- El modelo está en 3FN: los datos del Residente no se repiten en `movimiento` ni en `pauta` (§3.2).

**Negativas:**
- Dar de alta un Residente exige crear 2 filas (`entidad` y `residente`) de forma coherente.
