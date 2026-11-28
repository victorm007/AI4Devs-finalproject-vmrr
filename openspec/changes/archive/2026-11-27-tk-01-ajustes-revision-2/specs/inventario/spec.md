# Spec Delta

## ADDED Requirements

### Requirement: Sin índices sobre las FK que ninguna consulta usa

Las FK `movimiento.motivo_baja_id` y `movimiento.usuario_id` NO DEBEN (MUST NOT) tener índice: ninguna consulta de la sección 3.3 filtra por ellas, y cada índice encarece las escrituras de `movimiento` (ADR-0018). La FK sigue protegiendo el historial (ADR-0027).

#### Scenario: Las FK de motivo y usuario de movimiento sin índice (segunda revisión de TK-01, bloqueante 1)

- **GIVEN** la base migrada
- **WHEN** se listan los índices cuya primera columna es `movimiento.motivo_baja_id` o `movimiento.usuario_id`
- **THEN** no hay ninguno

## MODIFIED Requirements

### Requirement: Las claves foráneas impiden borrar lo que tiene historial

Ningún Medicamento, Entidad, usuario ni motivo de baja con Movimientos, Existencias o conteos DEBE (MUST) poder borrarse: Django lo impide con `PROTECT` y la base lo rechaza con sus claves foráneas, que se comprueban al confirmar la transacción (ADR-0027). La causa del rechazo DEBE (MUST) ser el historial, no otra referencia como los principios activos o las Pautas.

#### Scenario: Django impide borrar un Medicamento con historial (revisión de TK-01, hallazgo 3)

- **GIVEN** el dataset mock cargado
- **WHEN** se borra Eutirox con el ORM
- **THEN** Django lanza `ProtectedError` y Eutirox sigue registrado
- **AND** entre los objetos protegidos están sus Movimientos y su Existencia

#### Scenario: Django impide borrar la Entidad, el usuario o el motivo de baja con historial (segunda revisión de TK-01, mayor 2)

- **GIVEN** el dataset mock cargado
- **WHEN** se borran con el ORM el Hogar, `operador.demo` o el motivo `CONSUMO`
- **THEN** Django lanza `ProtectedError` y el registro sigue en la base
- **AND** entre los objetos protegidos hay Movimientos

#### Scenario: La base rechaza el borrado aunque se salte Django (revisión de TK-01, hallazgo 3)

- **GIVEN** el dataset mock cargado, sin las referencias que no son historial (principios activos, Pautas y grupo del usuario), y las restricciones comprobadas al momento (`SET CONSTRAINTS ALL IMMEDIATE`)
- **WHEN** se borra con SQL Eutirox, el Hogar, `operador.demo` o el motivo `CONSUMO`
- **THEN** la base lo rechaza por la clave foránea de una tabla del historial: `movimiento`, `existencia`, `conteo_fisico` o `detalle_conteo`
- **AND** el registro sigue en la base

### Requirement: Migraciones reversibles de inventario

Las migraciones de `inventario` DEBEN (MUST) aplicarse en una base vacía y revertirse hasta `zero` sin errores, y volver a aplicarse. Si una comprobación falla a la mitad, la base DEBE (MUST) quedar migrada para los tests siguientes.

#### Scenario: Revertir y volver a aplicar (TK-01, criterio 1)

- **GIVEN** la base migrada
- **WHEN** se ejecuta `migrate conteos zero`, `migrate inventario zero` y después `migrate`
- **THEN** las 3 terminan sin errores, las tablas desaparecen al revertir y vuelven al aplicar

#### Scenario: Sin migraciones pendientes (TK-01, criterio 2)

- **GIVEN** los modelos de `inventario` y `conteos`
- **WHEN** se ejecuta `makemigrations --check --dry-run`
- **THEN** no detecta cambios
