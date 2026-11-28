# inventario Specification

## Purpose
Guarda las Existencias de cada Entidad y los Movimientos inmutables que las explican (Entrada, Transferencia y Baja), con sus reglas en PostgreSQL como última barrera, la conciliación del saldo y los *fixtures* de prueba con el dataset mock.

## Requirements

### Requirement: Esquema de Existencias y Movimientos con los nombres del readme

Las tablas `motivo_baja`, `existencia` y `movimiento` DEBEN (MUST) tener las columnas, tipos, restricciones, índices y *triggers* de las secciones 3.1, 3.2 y 3.3 con sus nombres exactos: cantidades y saldos `numeric(10,2)`, fechas con hora `timestamptz` y `existencia` con `fillfactor = 90`.

#### Scenario: Restricciones, índices y triggers con sus nombres exactos (TK-01, criterio 5)

- **GIVEN** la base migrada
- **WHEN** se consulta la definición de `movimiento` (`\d movimiento`)
- **THEN** aparecen `ck_movimiento_por_tipo`, `ck_movimiento_cantidad`, `ck_movimiento_entregado`, `ck_movimiento_no_autocorrige` y `uq_movimiento_corrige`
- **AND** los índices `ix_movimiento_origen_med_fecha` y `ix_movimiento_dest_med_fecha` (parciales), `ix_movimiento_med_fecha` y `brin_movimiento_fecha` (BRIN)
- **AND** los *triggers* `tg_movimiento_inmutable` y `tg_movimiento_validar_destino`
- **AND** `existencia` tiene `uq_existencia`, `ck_existencia_saldo` e `ix_existencia_med_entidad`, y `medicamento` tiene `tg_medicamento_baja`

#### Scenario: Tipos de las cantidades y de las fechas (TK-01, descripción técnica 1)

- **GIVEN** la base migrada
- **WHEN** se consultan los tipos de `existencia.saldo` y `movimiento.cantidad`
- **THEN** ambos son `numeric(10,2)`
- **AND** `existencia.actualizado_en` y `movimiento.fecha_hora` son `timestamptz` con la hora actual como valor por omisión (`now()` en el DDL; `Now()` de Django genera `statement_timestamp()`), y `existencia.saldo` tiene valor por omisión 0

#### Scenario: Espacio para actualizar el saldo en la misma página (TK-01, descripción técnica 4)

- **GIVEN** la base migrada
- **WHEN** se consultan las opciones de almacenamiento de `existencia`
- **THEN** incluyen `fillfactor=90`

### Requirement: Sin índices duplicados sobre las FK

Ninguna FK de la tabla "Índices de FK que Django no debe crear" (sección 3.3) DEBE (MUST) tener un índice propio además del compuesto que la cubre.

#### Scenario: Cada FK cubierta solo por su índice compuesto (TK-01, criterio 6)

- **GIVEN** la base migrada
- **WHEN** se listan los índices cuya primera columna es `existencia.entidad_id`, `existencia.medicamento_id`, `movimiento.entidad_origen_id`, `movimiento.entidad_destino_id` o `movimiento.medicamento_id`
- **THEN** son solo `uq_existencia`, `ix_existencia_med_entidad`, `ix_movimiento_origen_med_fecha`, `ix_movimiento_dest_med_fecha` e `ix_movimiento_med_fecha`, respectivamente

### Requirement: Movimientos inmutables

La base DEBE (MUST) rechazar cualquier `UPDATE` o `DELETE` sobre `movimiento`, también del dueño de la tabla, con el mensaje "Los movimientos son inmutables: registre un movimiento de corrección".

#### Scenario: Modificar un Movimiento (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado
- **WHEN** se ejecuta `UPDATE movimiento SET cantidad = 1 WHERE id = 1`
- **THEN** la base lo rechaza con "Los movimientos son inmutables…"

#### Scenario: Borrar un Movimiento (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado
- **WHEN** se ejecuta `DELETE FROM movimiento WHERE id = 1`
- **THEN** la base lo rechaza con "Los movimientos son inmutables…"

### Requirement: Columnas por tipo de Movimiento

Cada Movimiento DEBE (MUST) cumplir `ck_movimiento_por_tipo`: una Entrada tiene destino y no origen ni motivo, una Transferencia tiene origen y destino distintos, y una Baja tiene origen y motivo; la cantidad es mayor que 0 (`ck_movimiento_cantidad`) y cada Movimiento se corrige una sola vez (`uq_movimiento_corrige`).

#### Scenario: Entrada sin destino (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado
- **WHEN** se inserta una Entrada sin `entidad_destino_id`
- **THEN** la base la rechaza por `ck_movimiento_por_tipo`

#### Scenario: Baja sin motivo (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado
- **WHEN** se inserta una Baja de María sin `motivo_baja_id`
- **THEN** la base la rechaza por `ck_movimiento_por_tipo`

#### Scenario: Transferencia a la misma Entidad (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado
- **WHEN** se inserta una Transferencia del Hogar al Hogar
- **THEN** la base la rechaza por `ck_movimiento_por_tipo`

#### Scenario: Cantidad cero (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado
- **WHEN** se inserta un Movimiento con `cantidad = 0`
- **THEN** la base lo rechaza por `ck_movimiento_cantidad`

#### Scenario: Segunda corrección del mismo Movimiento (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado, donde la entrada errónea de 600 Metformina de María ya tiene su corrección
- **WHEN** se inserta otra Baja `CORRECCION` que corrige el mismo Movimiento
- **THEN** la base la rechaza por `uq_movimiento_corrige`

### Requirement: Saldo nunca negativo

`existencia.saldo` DEBE (MUST) ser mayor o igual que 0 (`ck_existencia_saldo`), y cada Entidad DEBE (MUST) tener una sola Existencia por Medicamento (`uq_existencia`).

#### Scenario: Saldo negativo (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado
- **WHEN** se ejecuta `UPDATE existencia SET saldo = -1` sobre una Existencia
- **THEN** la base lo rechaza por `ck_existencia_saldo`

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

### Requirement: Conciliación de las Existencias

La vista `v_conciliacion_existencia` DEBE (MUST) listar las Existencias cuyo saldo no coincide con la suma de sus Movimientos; vacía significa que todo cuadra.

#### Scenario: El mock cuadra (TK-01, criterio 7)

- **GIVEN** el dataset mock cargado con `cargar_mock.sql`, sin errores
- **WHEN** se ejecuta `SELECT count(*) FROM v_conciliacion_existencia`
- **THEN** devuelve 0

#### Scenario: Un saldo que no cuadra aparece en la conciliación (TK-01, descripción técnica 4)

- **GIVEN** el dataset mock cargado
- **WHEN** se suma 1 al saldo de una Existencia sin registrar su Movimiento
- **THEN** `v_conciliacion_existencia` devuelve 1 renglón

### Requirement: Privilegios de app_user sobre los Movimientos

`app_user` DEBE (MUST) tener solo `SELECT` e `INSERT` sobre `movimiento`, sin `UPDATE`, `DELETE` ni `TRUNCATE`, y no DEBE (MUST) poder desactivar sus *triggers*; sobre las demás tablas conserva los 4 permisos, y el dueño de todas es `app_owner`.

#### Scenario: app_user solo lee e inserta Movimientos (TK-01, criterio 9)

- **GIVEN** la base migrada
- **WHEN** se consulta `has_table_privilege('app_user', 'movimiento', ...)`
- **THEN** `SELECT` e `INSERT` son verdaderos, y `UPDATE`, `DELETE` y `TRUNCATE` son falsos
- **AND** el dueño de todas las tablas es `app_owner`, y `app_user` tiene los 4 permisos sobre las demás

#### Scenario: app_user no reescribe el historial (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado y una conexión como `app_user`
- **WHEN** ejecuta `UPDATE`, `DELETE` o `TRUNCATE` sobre `movimiento`
- **THEN** la base responde `permission denied for table movimiento`

#### Scenario: app_user no desactiva los triggers (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado y una conexión como `app_user`
- **WHEN** ejecuta `ALTER TABLE movimiento DISABLE TRIGGER ALL`
- **THEN** la base responde `must be owner of table movimiento`

#### Scenario: app_user registra un Movimiento y lee la conciliación (TK-01, descripción técnica 5)

- **GIVEN** el dataset mock cargado y una conexión como `app_user`
- **WHEN** inserta una Entrada de 30 Eutirox para Carmen, origen `FAMILIAR`, entregada por "Rosa Torres", y consulta `v_conciliacion_existencia`
- **THEN** la inserción se guarda y la consulta responde sin error de permisos

### Requirement: Motivos de baja semilla

Las migraciones DEBEN (MUST) crear los 8 motivos de baja (`CONSUMO`, `CADUCIDAD`, `MERMA`, `ROTURA`, `DEVOLUCION_FAMILIA`, `DEFUNCION`, `EGRESO` y `CORRECCION`), activos y de forma idempotente.

#### Scenario: Los 8 motivos tras migrar (TK-01, descripción técnica 6)

- **GIVEN** la base migrada
- **WHEN** se consultan las claves de `motivo_baja`
- **THEN** son exactamente las 8 claves, todas activas

### Requirement: Permisos de los grupos sobre Existencias y Movimientos

Los grupos *Solo lectura* y *Lectura y escritura* DEBEN (MUST) tener `view_existencia`, `view_movimiento` y `view_motivobaja`, y *Lectura y escritura* además `add_movimiento`; nadie recibe `change_movimiento` ni `delete_movimiento`.

#### Scenario: Permisos de cada grupo (TK-01, descripción técnica 7)

- **GIVEN** la base migrada
- **WHEN** se listan los permisos de `inventario` de cada grupo
- **THEN** *Solo lectura* tiene `view_existencia`, `view_movimiento` y `view_motivobaja`
- **AND** *Lectura y escritura* tiene esos 3 y `add_movimiento`, sin `change_movimiento` ni `delete_movimiento`

### Requirement: Existencias y Movimientos fuera del panel

`Movimiento` y `Existencia` no DEBEN (MUST) estar registrados en `/admin/`: solo se escriben con el servicio de inventario.

#### Scenario: Movimiento y Existencia no están en el panel (TK-01, descripción técnica 8)

- **GIVEN** el panel `/admin/` configurado
- **WHEN** se consulta si `Movimiento` o `Existencia` están registrados
- **THEN** ninguno lo está

### Requirement: Migraciones reversibles de inventario

Las migraciones de `inventario` DEBEN (MUST) aplicarse en una base vacía y revertirse hasta `zero` sin errores, y volver a aplicarse.

#### Scenario: Revertir y volver a aplicar (TK-01, criterio 1)

- **GIVEN** la base migrada
- **WHEN** se ejecuta `migrate conteos zero`, `migrate inventario zero` y después `migrate`
- **THEN** las 3 terminan sin errores, las tablas desaparecen al revertir y vuelven al aplicar

#### Scenario: Sin migraciones pendientes (TK-01, criterio 2)

- **GIVEN** los modelos de `inventario` y `conteos`
- **WHEN** se ejecuta `makemigrations --check --dry-run`
- **THEN** no detecta cambios

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

### Requirement: Consultas de Movimientos por período con índice

Las consultas de Movimientos de una Entidad y un Medicamento en un período (consulta 2c de la sección 3.3) DEBEN (MUST) poder usar `ix_movimiento_origen_med_fecha` e `ix_movimiento_dest_med_fecha`, sin *Seq Scan* sobre `movimiento` con un año de datos.

#### Scenario: Salidas y entradas de un período usan su índice (TK-01, criterio 11)

- **GIVEN** el dataset mock cargado
- **WHEN** se ejecuta `EXPLAIN` de las salidas y de las entradas de una Entidad y un Medicamento en un mes
- **THEN** el plan usa `ix_movimiento_origen_med_fecha` y `ix_movimiento_dest_med_fecha`, respectivamente

#### Scenario: Un año de datos sintéticos (TK-01, criterio 11)

- **GIVEN** la base de desarrollo con 175,000 Movimientos sintéticos y `ANALYZE`
- **WHEN** se ejecuta `EXPLAIN (ANALYZE, BUFFERS)` de las salidas del Hogar de Paracetamol en marzo de 2025
- **THEN** el plan usa `ix_movimiento_origen_med_fecha` (o un *Bitmap* sobre él), nunca *Seq Scan on movimiento*

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
