# ADR-0016 · Pautas informativas, con vigencia y sin traslapes

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `pautas`, `entidades`, `catalogo`
- **Fuentes:** `readme.md` §2.2, §3.1, §3.2 (D6 y antipatrones), §3.3 (consulta 3 y *triggers*), §5 (EP-05) y §6 (decisiones de diseño de la habilitación, HB-07); `CLAUDE.md` (vocabulario de dominio: Pauta)

## Contexto

El hogar necesita registrar la dosis, la frecuencia, las indicaciones y la vigencia de cada Medicamento por Residente. Es información útil, pero no bloquea el inventario, y las pantallas tienen prioridad *Could*. Aun así, el dataset mock inserta Pautas y TK-01 lo carga.

## Decisión

- La **Pauta es informativa:** no mueve Existencias ni registra la administración por turno.
- Pertenece a un Residente (`residente_id` → `residente`), nunca al Hogar, y a un Medicamento. Guarda:
  - `dosis` por toma: `numeric(6,2)` y mayor que 0.
  - `frecuencia_horas`: entre 1 y 168.
  - `si_necesario`: Pauta "en caso necesario" (PRN), en la que la frecuencia es el intervalo mínimo.
  - Las indicaciones y la vigencia (`fecha_inicio` y `fecha_fin`, nula si está vigente).
- **Sin vigencias traslapadas** para el mismo Residente y Medicamento: la restricción de exclusión `ex_pauta_sin_traslape` (`EXCLUDE USING gist` con `daterange(fecha_inicio, fecha_fin, '[]')`), que requiere la extensión `btree_gist`.
- **Cambiar una Pauta** es cerrar la vigente (`fecha_fin`) y crear una nueva, para conservar el historial.
- Solo se registran Pautas para Residentes y Medicamentos activos (`tg_pauta_validar`).
- **En el MVP solo se entrega el esquema** (HB-07); las pantallas se definirán si hay tiempo después de EP-04.

## Alternativas consideradas

- **Columnas repetidas** (`dosis1`, `dosis2`…): se descartaron por rígidas; hay una fila por Pauta, con vigencia (antipatrón, §3.2).

## Consecuencias

**Positivas:**
- El mock y TK-01 pueden cargar Pautas desde la semana 2 sin esperar sus pantallas.
- Los índices `ix_pauta_vigente` e `ix_pauta_residente_inicio` atienden la consulta más frecuente (las Pautas vigentes de un Residente) y el historial (§3.3).

**Negativas:**
- Hasta que existan las pantallas, las Pautas no se pueden capturar desde la aplicación.
