# pautas Specification

## Purpose

Define la Pauta de un Residente para un Medicamento: dosis, frecuencia y vigencia sin traslapes, registrable solo para Residentes y Medicamentos activos. Es informativa: no mueve Existencias.

## Requirements

### Requirement: Esquema de la Pauta con los nombres del readme

La tabla `pauta` DEBE (MUST) tener las restricciones `ck_pauta_dosis`, `ck_pauta_frecuencia`, `ck_pauta_fechas` y `ex_pauta_sin_traslape`, los índices `ix_pauta_vigente` e `ix_pauta_residente_inicio` y el *trigger* `tg_pauta_validar`, con los nombres y definiciones de las secciones 3.1 y 3.3, `dosis` `numeric(6,2)` y `frecuencia_horas` `smallint`.

#### Scenario: Restricciones, índices y trigger con sus nombres exactos (HB-07, criterio 1)

- **GIVEN** la base migrada
- **WHEN** se consulta la definición de `pauta` (`\d pauta`)
- **THEN** aparecen `ck_pauta_dosis`, `ck_pauta_frecuencia`, `ck_pauta_fechas` y `ex_pauta_sin_traslape` sobre `(residente_id WITH =, medicamento_id WITH =, daterange(fecha_inicio, fecha_fin, '[]') WITH &&)` con `gist`
- **AND** `ix_pauta_vigente` sobre `(residente_id, medicamento_id) WHERE fecha_fin IS NULL`
- **AND** `ix_pauta_residente_inicio` sobre `(residente_id, fecha_inicio DESC)`
- **AND** `tg_pauta_validar`, `BEFORE INSERT` y por fila, que ejecuta `fn_pauta_validar()`

#### Scenario: Sin índice propio sobre residente_id (HB-07, descripción técnica)

- **GIVEN** la base migrada
- **WHEN** se listan los índices de `pauta`
- **THEN** ninguno tiene `residente_id` como única columna: lo cubre `ix_pauta_residente_inicio`

#### Scenario: Tipos de la dosis y de la frecuencia (HB-07, descripción técnica)

- **GIVEN** la base migrada
- **WHEN** se consultan las columnas de `pauta`
- **THEN** `dosis` es `numeric(6,2)` y `frecuencia_horas` es `smallint`

### Requirement: Dosis, frecuencia y fechas válidas

La base DEBE (MUST) rechazar una Pauta con dosis menor o igual a 0, con frecuencia fuera de 1 a 168 horas o con fecha de fin anterior a la de inicio.

#### Scenario: Dosis 0 (HB-07, criterio 2)

- **GIVEN** un Residente activo y un Medicamento activo
- **WHEN** se registra una Pauta con dosis 0
- **THEN** la base la rechaza por `ck_pauta_dosis`

#### Scenario: Frecuencia 0 o 169 (HB-07, criterio 2)

- **GIVEN** un Residente activo y un Medicamento activo
- **WHEN** se registra una Pauta con frecuencia de 0 o de 169 horas
- **THEN** la base la rechaza por `ck_pauta_frecuencia`

#### Scenario: Fin anterior al inicio (HB-07, criterio 2)

- **GIVEN** un Residente activo y un Medicamento activo
- **WHEN** se registra una Pauta que empieza el 1 de febrero de 2026 y termina el 31 de enero de 2026
- **THEN** la base la rechaza por `ck_pauta_fechas`

### Requirement: Vigencias sin traslape

Un Residente NO DEBE (MUST NOT) tener 2 Pautas del mismo Medicamento con vigencias que se traslapen, contando ambos extremos. Cambiar una Pauta es cerrar la vigente y registrar otra.

#### Scenario: Dos Pautas traslapadas se rechazan (HB-07, criterio 3)

- **GIVEN** una Pauta vigente desde el 1 de febrero de 2026, sin fecha de fin
- **WHEN** se registra otra del mismo Residente y Medicamento desde el 1 de marzo de 2026
- **THEN** la base la rechaza por `ex_pauta_sin_traslape`

#### Scenario: El mismo día de fin e inicio se traslapa (HB-07, criterio 3)

- **GIVEN** una Pauta del 1 al 28 de febrero de 2026
- **WHEN** se registra otra del mismo Residente y Medicamento desde el 28 de febrero de 2026
- **THEN** la base la rechaza por `ex_pauta_sin_traslape`

#### Scenario: Cerrar la vigente permite registrar la nueva (HB-07, criterio 3)

- **GIVEN** una Pauta vigente desde el 1 de febrero de 2026
- **WHEN** se cierra con fecha de fin el 28 de febrero de 2026
- **AND** se registra otra del mismo Residente y Medicamento desde el 1 de marzo de 2026, con dosis 0.5
- **THEN** quedan 2 Pautas, la cerrada y la nueva

#### Scenario: La validación del modelo avisa el traslape (HB-07, guía)

- **GIVEN** una Pauta vigente desde el 1 de febrero de 2026
- **WHEN** se valida, sin guardarla, otra del mismo Residente y Medicamento desde el 1 de marzo de 2026
- **THEN** la validación falla con el mensaje "Ya hay una pauta vigente de este medicamento para el residente en esas fechas. Cierra la anterior antes de registrar la nueva."

### Requirement: Solo Residentes y Medicamentos activos

La base DEBE (MUST) rechazar el registro de una Pauta de un Residente que no esté `ACTIVO` o de un Medicamento dado de Baja.

#### Scenario: Residente egresado (HB-07, criterio 4)

- **GIVEN** un Residente `EGRESADO` y un Medicamento activo
- **WHEN** se registra una Pauta del Residente
- **THEN** la base la rechaza con el mensaje "El residente <id> no está activo"

#### Scenario: Medicamento dado de Baja (HB-07, criterio 4)

- **GIVEN** un Residente activo y un Medicamento dado de Baja
- **WHEN** se registra una Pauta del Medicamento
- **THEN** la base la rechaza con el mensaje "El medicamento <id> está dado de baja"

#### Scenario: app_user registra una Pauta válida (HB-07, criterios de revisión de BD)

- **GIVEN** un Residente activo y un Medicamento activo
- **WHEN** `app_user`, el usuario de base de datos de la aplicación, inserta una Pauta válida
- **THEN** la Pauta queda registrada: `app_user` tiene el permiso de `INSERT` en `pauta` y el *trigger* puede leer `residente` y `medicamento`

### Requirement: Migraciones reversibles

Las migraciones de `pautas` DEBEN (MUST) revertirse por completo y volver a aplicarse.

#### Scenario: migrate pautas zero revierte todo (HB-07, criterio 5)

- **GIVEN** la base migrada
- **WHEN** se ejecuta `./scripts/migrate.sh pautas zero`
- **THEN** desaparecen la tabla `pauta`, `fn_pauta_validar` y `tg_pauta_validar`
- **AND** `./scripts/migrate.sh` las vuelve a crear sin errores
