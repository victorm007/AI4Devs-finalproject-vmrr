# Spec Delta

## ADDED Requirements

### Requirement: Las claves foráneas impiden borrar lo que tiene historial

Ningún Medicamento, Entidad, usuario ni motivo de baja con Movimientos, Existencias o conteos DEBE (MUST) poder borrarse: Django lo impide con `PROTECT` y la base lo rechaza con sus claves foráneas, que se comprueban al confirmar la transacción (ADR-0027).

#### Scenario: Django impide borrar un Medicamento con historial (revisión de TK-01, hallazgo 3)

- **GIVEN** el dataset mock cargado
- **WHEN** se borra Eutirox con el ORM
- **THEN** Django lanza `ProtectedError` y Eutirox sigue registrado

#### Scenario: La base rechaza el borrado aunque se salte Django (revisión de TK-01, hallazgo 3)

- **GIVEN** el dataset mock cargado y las restricciones comprobadas al momento (`SET CONSTRAINTS ALL IMMEDIATE`)
- **WHEN** se ejecuta `DELETE FROM medicamento WHERE nombre_comercial = 'Eutirox'`
- **THEN** la base lo rechaza por una clave foránea

## MODIFIED Requirements

### Requirement: Destino activo en las Entradas y Transferencias

La base DEBE (MUST) rechazar un Movimiento con destino si el Medicamento está dado de baja o el Residente destino no está `ACTIVO`, salvo que sea una corrección (`tg_movimiento_validar_destino`).

#### Scenario: Entrada a un Residente egresado (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado y Carmen Torres Vega egresada
- **WHEN** se inserta una Entrada de Metformina para Carmen
- **THEN** la base la rechaza con "La entidad destino 103 no está activa"

#### Scenario: Transferencia a un Residente egresado (revisión de TK-01, hallazgo 9)

- **GIVEN** el dataset mock cargado y Carmen Torres Vega egresada
- **WHEN** se inserta una Transferencia de Paracetamol del Hogar a Carmen
- **THEN** la base la rechaza con "La entidad destino 103 no está activa"

#### Scenario: Entrada a un Residente fallecido (revisión de TK-01, hallazgo 9)

- **GIVEN** el dataset mock cargado y José Luis Ramírez Ortega fallecido
- **WHEN** se inserta una Entrada de Cozaar para José Luis
- **THEN** la base la rechaza con "La entidad destino 102 no está activa"

### Requirement: Fixtures de prueba con el dataset mock

Los tests DEBEN (MUST) disponer de `datos_demo` (carga el mock con sus validaciones), `demo` (accesos a Entidades, Medicamentos, motivos y al usuario `operador.demo`), `como_app_user` (el test corre como `app_user` y falla sin transacción envolvente), `ejecutar_sql` y `saldo`.

#### Scenario: El mock se carga en el test (TK-01, descripción técnica 9)

- **GIVEN** un test con `demo`
- **WHEN** consulta el Hogar, María (101), José Luis (102), Carmen (103), `operador.demo`, `demo.med["Eutirox"]` y `demo.motivo["CORRECCION"]`
- **THEN** existen, y `saldo(demo.carmen, demo.med["Eutirox"])` es 33

#### Scenario: El test corre como app_user (TK-01, descripción técnica 9)

- **GIVEN** un test con `como_app_user`
- **WHEN** consulta `current_user`
- **THEN** es `app_user`

#### Scenario: Sin transacción envolvente, como_app_user falla (TK-01, descripción técnica 9)

- **GIVEN** un test con `transaction=True`, sin transacción envolvente
- **WHEN** pide `como_app_user`
- **THEN** el test falla con "como_app_user necesita la transacción del test", en lugar de correr como `app_owner`

#### Scenario: ejecutar_sql con otro rol no deshace como_app_user (revisión de TK-01, hallazgo 11)

- **GIVEN** un test con `como_app_user`
- **WHEN** llama a `ejecutar_sql("SELECT 1", rol="app_user")` y después consulta `current_user`
- **THEN** sigue siendo `app_user`, no `app_owner`
