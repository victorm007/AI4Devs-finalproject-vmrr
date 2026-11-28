# Spec Delta

## Purpose

Guarda los conteos físicos de una Entidad por período, con la foto del saldo registrado en cada renglón y la diferencia calculada por la base; un conteo cerrado no se modifica y el conteo nunca ajusta Existencias.

## ADDED Requirements

### Requirement: Esquema de los conteos con los nombres del readme

Las tablas `conteo_fisico` y `detalle_conteo` DEBEN (MUST) tener las columnas, tipos, restricciones, índices y *triggers* de las secciones 3.1, 3.2 y 3.3 con sus nombres exactos: cantidades `numeric(10,2)` y `diferencia` generada y guardada (`cantidad_fisica − cantidad_sistema`).

#### Scenario: Restricciones, índices y triggers con sus nombres exactos (TK-01, criterio 5)

- **GIVEN** la base migrada
- **WHEN** se consulta la definición de `detalle_conteo` (`\d detalle_conteo`) y de `conteo_fisico`
- **THEN** `detalle_conteo` tiene `uq_detalle_conteo`, `ck_detalle_fisica`, `ck_detalle_sistema`, `ix_detalle_medicamento_conteo` (con `INCLUDE (cantidad_fisica, cantidad_sistema, diferencia)`), `ix_detalle_con_diferencia` (parcial, `diferencia <> 0`) y `tg_detalle_conteo_cerrado`
- **AND** `conteo_fisico` tiene `ck_conteo_periodo`, `ck_conteo_cierre`, `ix_conteo_entidad_periodo` (`entidad_id, periodo_fin DESC`) y `tg_conteo_cerrado`
- **AND** `diferencia` es `numeric(10,2)` generada y guardada

#### Scenario: Sin índices duplicados sobre las FK (TK-01, criterio 6)

- **GIVEN** la base migrada
- **WHEN** se listan los índices cuya primera columna es `detalle_conteo.conteo_id`, `detalle_conteo.medicamento_id` o `conteo_fisico.entidad_id`
- **THEN** son solo `uq_detalle_conteo`, los 2 índices `ix_detalle_*` e `ix_conteo_entidad_periodo`, respectivamente

### Requirement: Período y cierre coherentes

Un conteo DEBE (MUST) tener `periodo_fin` mayor o igual que `periodo_inicio` (`ck_conteo_periodo`), y `cerrado_en` DEBE (MUST) estar presente si y solo si el conteo está `CERRADO` (`ck_conteo_cierre`).

#### Scenario: Período al revés (TK-01, prueba 3.3)

- **GIVEN** el dataset mock cargado
- **WHEN** se inserta un conteo con `periodo_fin` anterior a `periodo_inicio`
- **THEN** la base lo rechaza por `ck_conteo_periodo`

#### Scenario: Cerrar sin fecha de cierre (TK-01, prueba 3.3)

- **GIVEN** el conteo 2 del Hogar, `EN_PROCESO`
- **WHEN** se ejecuta `UPDATE conteo_fisico SET estado = 'CERRADO' WHERE id = 2` sin `cerrado_en`
- **THEN** la base lo rechaza por `ck_conteo_cierre`

### Requirement: Conteo cerrado inmutable

La base DEBE (MUST) rechazar cualquier cambio al encabezado de un conteo `CERRADO` y cualquier alta, cambio o baja de sus renglones (`tg_conteo_cerrado` y `tg_detalle_conteo_cerrado`).

#### Scenario: Cambiar el encabezado de un conteo cerrado (TK-01, prueba 3.3)

- **GIVEN** el conteo 1 de María, `CERRADO`
- **WHEN** se ejecuta `UPDATE conteo_fisico SET nota = 'x' WHERE id = 1`
- **THEN** la base lo rechaza con "está cerrado y no se puede modificar"

#### Scenario: Agregar un renglón a un conteo cerrado (TK-01, criterio 8)

- **GIVEN** el conteo 1 de María, `CERRADO`
- **WHEN** se inserta un renglón de Paracetamol en el conteo 1
- **THEN** la base lo rechaza con "El conteo 1 está cerrado"

### Requirement: Un renglón por Medicamento y diferencia calculada

Cada conteo DEBE (MUST) tener un solo renglón por Medicamento (`uq_detalle_conteo`), y `diferencia` DEBE (MUST) calcularla la base, sin que nadie la escriba.

#### Scenario: Segundo renglón del mismo Medicamento (TK-01, prueba 3.3)

- **GIVEN** el conteo 2 del Hogar con su renglón de Omeprazol
- **WHEN** se inserta otro renglón de Omeprazol en el conteo 2
- **THEN** la base lo rechaza por `uq_detalle_conteo`

#### Scenario: Diferencia del mock (TK-01, prueba 3.3)

- **GIVEN** el dataset mock cargado
- **WHEN** se consulta la diferencia de Omeprazol en el conteo 2
- **THEN** es -1.00 (58 contadas contra 59 registradas)

#### Scenario: Capturar un renglón pendiente (TK-01, prueba 3.3; readme, sección 2.6)

- **GIVEN** el conteo 2 del Hogar, con Losartán pendiente
- **WHEN** se captura Losartán con 18 dosis físicas y 20 registradas
- **THEN** la diferencia es -2

#### Scenario: Escribir la diferencia a mano (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado
- **WHEN** se ejecuta `UPDATE detalle_conteo SET diferencia = 0`
- **THEN** la base lo rechaza porque `diferencia` es una columna generada

### Requirement: Conteos fuera del panel

`ConteoFisico` y `DetalleConteo` no DEBEN (MUST) estar registrados en `/admin/`.

#### Scenario: Los conteos no están en el panel (TK-01, descripción técnica 8)

- **GIVEN** el panel `/admin/` configurado
- **WHEN** se consulta si `ConteoFisico` o `DetalleConteo` están registrados
- **THEN** ninguno lo está

### Requirement: Migraciones reversibles de conteos

Las migraciones de `conteos` DEBEN (MUST) revertirse hasta `zero` sin errores y volver a aplicarse.

#### Scenario: Revertir y volver a aplicar (TK-01, criterio 1)

- **GIVEN** la base migrada
- **WHEN** se ejecuta `migrate conteos zero` y después `migrate`
- **THEN** ambas terminan sin errores, y `conteo_fisico` y `detalle_conteo` desaparecen al revertir y vuelven al aplicar
