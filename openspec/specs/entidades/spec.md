# entidades Specification

## Purpose

Define las Entidades dueñas de Existencias: el Hogar, único, y cada Residente como subtipo coherente, con fechas y nombres válidos, estado activo derivado y alta atómica.

## Requirements

### Requirement: Un solo Hogar

La migración DEBE (MUST) crear la Entidad Hogar, con el nombre de `HOGAR_NOMBRE`, y la base NO DEBE (MUST NOT) admitir un segundo Hogar. En una base nueva, el Hogar tiene `id = 1`.

#### Scenario: La migración crea un solo Hogar (HB-06, criterio 1)

- **GIVEN** la base migrada
- **WHEN** se consultan las Entidades de tipo `HOGAR`
- **THEN** existe una sola, con el nombre de `HOGAR_NOMBRE`
- **AND** su `id` es 1 en una base nueva

#### Scenario: Un segundo Hogar viola la restricción (HB-06, criterio 1)

- **GIVEN** la base migrada, con su Hogar
- **WHEN** se inserta otra Entidad de tipo `HOGAR`
- **THEN** la base la rechaza por `uq_entidad_un_hogar`

### Requirement: Subtipo coherente con el supertipo

Solo una Entidad de tipo `RESIDENTE` DEBE (MUST) tener fila en `residente`. La clave foránea compuesta `fk_residente_entidad` lo garantiza en la base.

#### Scenario: Un Residente no puede colgar del Hogar (HB-06, criterio 2)

- **GIVEN** la base migrada, con su Hogar
- **WHEN** se inserta una fila de `residente` con el `entidad_id` del Hogar
- **THEN** la base la rechaza por `fk_residente_entidad`

#### Scenario: La FK compuesta no borra en cascada (HB-06, descripción técnica)

- **GIVEN** la base migrada
- **WHEN** se consulta la definición de `fk_residente_entidad`
- **THEN** es `FOREIGN KEY (entidad_id, tipo) REFERENCES entidad (id, tipo) ON DELETE RESTRICT`
- **AND** existe `uq_entidad_id_tipo` sobre `(id, tipo)`

### Requirement: Restricciones de la Entidad

La base DEBE (MUST) rechazar un tipo de Entidad distinto de `HOGAR` y `RESIDENTE`, un nombre en un Residente, un Hogar sin nombre y un nombre que sea solo espacios.

#### Scenario: Entidades inválidas (HB-06, criterio 3)

- **GIVEN** la base migrada
- **WHEN** se inserta una Entidad `HOGAR` sin nombre, o una `RESIDENTE` con nombre
- **THEN** la base la rechaza por `ck_entidad_nombre`

#### Scenario: Tipo de Entidad desconocido (HB-06, criterio 3)

- **GIVEN** la base migrada
- **WHEN** se inserta una Entidad de tipo `OTRO`
- **THEN** la base la rechaza por `ck_entidad_tipo`

#### Scenario: Nombre del Hogar solo con espacios (HB-06, criterio 3)

- **GIVEN** la base migrada, con su Hogar
- **WHEN** se actualiza el nombre del Hogar a solo espacios
- **THEN** la base lo rechaza por `ck_entidad_nombre_no_vacio`

### Requirement: Restricciones del Residente

La base DEBE (MUST) rechazar un Residente con estado desconocido, con fecha de baja incoherente con su estado, con fechas fuera de orden, con nombre o primer apellido vacíos y con un tipo distinto de `RESIDENTE`.

#### Scenario: Estado y fecha de baja incoherentes (HB-06, criterio 3)

- **GIVEN** un Residente `ACTIVO`
- **WHEN** se le pone el estado `EGRESADO` sin fecha de baja, o una fecha de baja siendo `ACTIVO`
- **THEN** la base lo rechaza por `ck_residente_baja`

#### Scenario: Baja anterior al ingreso (HB-06, criterio 3)

- **GIVEN** un Residente que ingresó el 2025-01-10
- **WHEN** se le pone el estado `EGRESADO` con fecha de baja 2000-01-01
- **THEN** la base lo rechaza por `ck_residente_fechas`

#### Scenario: Estado desconocido (HB-06, criterio 3)

- **GIVEN** un Residente `ACTIVO`
- **WHEN** se le pone el estado `PERDIDO` con fecha de baja (un valor que cabe en `varchar(10)`, para que lo rechace el `CHECK` y no el largo de la columna)
- **THEN** la base lo rechaza por `ck_residente_estado`

#### Scenario: Fechas de nacimiento e ingreso inválidas (HB-06, criterio 3)

- **GIVEN** un Residente nacido el 1935-07-22
- **WHEN** se le pone una fecha de nacimiento anterior a 1900, o un ingreso anterior al nacimiento
- **THEN** la base lo rechaza por `ck_residente_nacimiento`

#### Scenario: Nombre o apellido solo con espacios (HB-06, criterio 3)

- **GIVEN** un Residente registrado
- **WHEN** se le pone un primer nombre de solo espacios
- **THEN** la base lo rechaza por `ck_residente_nombres`

#### Scenario: Tipo distinto de RESIDENTE (HB-06, criterio 3)

- **GIVEN** un Residente registrado
- **WHEN** se le pone el tipo `HOGAR`
- **THEN** la base lo rechaza por `ck_residente_tipo`

### Requirement: Entidad activa y nombre para mostrar

El Hogar DEBE (MUST) estar siempre activo, y un Residente solo si su estado es `ACTIVO`. El nombre para mostrar DEBE (MUST) ser el del Hogar o el nombre completo del Residente, sin los nombres vacíos ni espacios de más. Una Entidad `RESIDENTE` sin su Residente NO DEBE (MUST NOT) provocar un error: no está activa y se muestra como `Entidad <id>`. Si las Entidades se leen junto con su Residente, saber si están activas y mostrar su nombre NO DEBE (MUST NOT) hacer consultas adicionales a la base.

#### Scenario: Activa según el estado (HB-06, criterio 4)

- **GIVEN** el Hogar y un Residente registrado
- **WHEN** el Residente pasa de `ACTIVO` a `EGRESADO` o a `FALLECIDO`, con fecha de baja
- **THEN** la Entidad del Hogar y la del Residente `ACTIVO` están activas
- **AND** la del Residente `EGRESADO` o `FALLECIDO` no lo está

#### Scenario: Nombre para mostrar (HB-06, criterio 4)

- **GIVEN** el Hogar y el Residente "Carmen Torres Vega", sin segundo nombre
- **WHEN** se muestra el nombre de cada Entidad
- **THEN** el del Hogar es el de `HOGAR_NOMBRE`
- **AND** el del Residente es "Carmen Torres Vega", sin espacios de más

#### Scenario: Nombres con espacios en los extremos (revisión de HB-06, nit 7)

- **GIVEN** un Residente sin guardar con primer nombre " Ana " y primer apellido "Ruiz "
- **WHEN** se muestra su nombre completo
- **THEN** es "Ana Ruiz", sin espacios dobles ni en los extremos

#### Scenario: Entidad Residente sin su Residente (revisión de HB-06, sugerencia 1)

- **GIVEN** una Entidad de tipo `RESIDENTE` sin fila en `residente`
- **WHEN** se pregunta si está activa y se muestra su nombre
- **THEN** no está activa
- **AND** su nombre es `Entidad <id>`, sin lanzar un error

#### Scenario: Sin consultas extra al leer las Entidades con su Residente (revisión de HB-06, sugerencia 1)

- **GIVEN** el Hogar y 2 Residentes registrados
- **WHEN** se leen todas las Entidades junto con su Residente, y de cada una se pregunta si está activa y se muestra su nombre
- **THEN** se hace una sola consulta a la base

### Requirement: Índice de búsqueda por nombre

La base DEBE (MUST) tener el índice `ix_residente_nombre` sobre `f_unaccent(lower(...))` del primer apellido y el primer nombre, para buscar y ordenar sin mayúsculas ni acentos.

#### Scenario: Definición del índice (HB-06, descripción técnica)

- **GIVEN** la base migrada
- **WHEN** se consulta la definición de `ix_residente_nombre`
- **THEN** usa `f_unaccent(lower(...))` sobre `primer_apellido` y sobre `primer_nombre`

### Requirement: Alta atómica de Residentes

`registrar_residente()` DEBE (MUST) crear la Entidad y el Residente en una sola transacción, siempre con estado `ACTIVO`, sin fecha de baja y con los nombres normalizados. Si el alta falla antes de que el servicio retorne, NO DEBE (MUST NOT) dejar una Entidad suelta ni alterar el Residente recibido, y los datos inválidos DEBEN (MUST) dar un error de validación claro. Una confirmación en una transacción externa queda fuera de esa garantía. DEBE (MUST) funcionar con los permisos de `app_user`.

#### Scenario: Alta correcta (HB-06, criterio 5)

- **GIVEN** un Residente sin guardar, con nombre, apellido y fechas válidas
- **WHEN** se registra
- **THEN** se crea una Entidad de tipo `RESIDENTE` y su Residente
- **AND** el estado es `ACTIVO` y no tiene fecha de baja

#### Scenario: Datos inválidos no dejan una Entidad suelta (HB-06, criterio 5)

- **GIVEN** un Residente sin guardar, con ingreso anterior al nacimiento
- **WHEN** se registra
- **THEN** lanza un error de validación con el mensaje "ingreso no puede ser anterior"
- **AND** el número de Entidades no cambia

#### Scenario: No se registra dos veces (HB-06, descripción técnica)

- **GIVEN** un Residente ya registrado
- **WHEN** se intenta registrar de nuevo
- **THEN** el servicio lo rechaza con `ValueError`

#### Scenario: Un Residente con Entidad asignada no se registra (segunda revisión de HB-06, sugerencia 2)

- **GIVEN** un Residente sin guardar al que se le asignó la Entidad de otro Residente ya registrado
- **WHEN** se registra
- **THEN** el servicio lo rechaza con `ValueError`
- **AND** el número de Entidades y de Residentes no cambia

#### Scenario: Alta como app_user (HB-06, criterio 5)

- **GIVEN** una sesión que actúa como `app_user`
- **WHEN** registra un Residente
- **THEN** el Residente queda guardado

#### Scenario: Nombres normalizados (revisión de HB-06, nit 6)

- **GIVEN** un Residente sin guardar con primer nombre "  Ana ", primer apellido " Ruiz", segundo nombre "" y segundo apellido "   "
- **WHEN** se registra
- **THEN** en la base quedan "Ana" y "Ruiz"
- **AND** el segundo nombre y el segundo apellido quedan vacíos (`NULL`)

#### Scenario: Nombre solo con espacios (revisión de HB-06, sugerencia 3)

- **GIVEN** un Residente sin guardar con primer nombre de solo espacios
- **WHEN** se registra
- **THEN** lanza un error de validación sobre el primer nombre, no un error de la base
- **AND** el número de Entidades no cambia

#### Scenario: Mensaje claro de nombres vacíos (revisión de HB-06, sugerencia 3)

- **GIVEN** un Residente sin guardar con primer apellido de solo espacios
- **WHEN** se validan sus restricciones sin pasar por el servicio
- **THEN** el error dice "El primer nombre y el primer apellido no pueden quedar vacíos."

#### Scenario: Datos inválidos no alteran el Residente recibido (revisión de HB-06, sugerencia 2)

- **GIVEN** un Residente sin guardar con estado `EGRESADO`, fecha de baja, nombres con espacios y la fecha de ingreso escrita como texto, anterior al nacimiento
- **WHEN** se registra y falla la validación
- **THEN** el Residente recibido conserva su estado `EGRESADO`, su fecha de baja, sus nombres con espacios y la fecha de ingreso como el mismo texto
- **AND** sigue sin Entidad

#### Scenario: Un fallo al guardar permite reintentar (revisión de HB-06, sugerencia 2)

- **GIVEN** un Residente válido sin guardar, y una restricción de la base, desconocida para la aplicación, que rechaza guardarlo después de crear su Entidad
- **WHEN** se registra
- **THEN** el error de la base llega al llamador y no queda ninguna Entidad nueva
- **AND** el Residente recibido sigue sin Entidad, y un segundo intento sin esa restricción lo registra

#### Scenario: Un fallo al confirmar permite reintentar (segunda revisión de HB-06, sugerencia 3)

- **GIVEN** un Residente válido sin guardar, registrado sin una transacción externa (el servicio abre y confirma la suya), y una restricción diferida de la base que solo se comprueba al confirmar y que su alta viola
- **WHEN** se registra, el Residente se guarda y falla la confirmación
- **THEN** el error de la base llega al llamador y no queda ninguna Entidad nueva
- **AND** el Residente recibido vuelve a estar sin guardar y sin Entidad, y un segundo intento sin esa restricción lo registra

### Requirement: Migraciones reversibles

Las migraciones de la app DEBEN (MUST) poder revertirse por completo y volver a aplicarse.

#### Scenario: migrate entidades zero revierte todo (HB-06, criterio 6)

- **GIVEN** la base migrada
- **WHEN** se ejecuta `./scripts/migrate.sh entidades zero`
- **THEN** desaparecen el Hogar y las tablas `residente` y `entidad`
- **AND** `./scripts/migrate.sh` las vuelve a crear, con el Hogar

### Requirement: Residentes en el panel según el grupo

El panel `/admin/` DEBE (MUST) mostrar los residentes a los 2 grupos. *Solo lectura* los consulta y no da de alta ni cambia nada (`403`); *Lectura y escritura* da de alta y cambia. La autorización se valida en el servidor.

#### Scenario: Solo lectura consulta los residentes (HB-09, criterio 1)

- **GIVEN** un usuario del grupo *Solo lectura* con sesión iniciada
- **WHEN** abre la lista de residentes
- **THEN** la respuesta es `200`
- **AND** el alta de un residente responde `403`

#### Scenario: Solo lectura no cambia un residente (HB-09, criterio 1)

- **GIVEN** un usuario del grupo *Solo lectura* y la residente María Guadalupe Hernández López
- **WHEN** abre su página
- **THEN** la ve en modo de consulta (`200`, sin el botón de guardar)
- **AND** si envía un cambio a "Egresado", la respuesta es `403` y la residente sigue `ACTIVO`

### Requirement: Alta de residentes en el panel

El alta de un residente en el panel DEBE (MUST) crear su entidad `RESIDENTE` y el residente juntos, siempre `ACTIVO` y sin fecha de baja, y su formulario no pide el estado ni la fecha de baja.

#### Scenario: El alta crea la entidad y el residente activo (HB-09, criterio 6)

- **GIVEN** un usuario de *Lectura y escritura*
- **WHEN** da de alta a María Guadalupe Hernández López, nacida el 1938-04-12 e ingresada el 2023-02-01
- **THEN** el panel redirige (`302`)
- **AND** existe su entidad de tipo `RESIDENTE`
- **AND** la residente queda `ACTIVO` y sin fecha de baja

#### Scenario: El alta no pide el estado (HB-09, descripción técnica)

- **GIVEN** un usuario de *Lectura y escritura*
- **WHEN** abre el alta de un residente
- **THEN** la respuesta es `200`
- **AND** el formulario no tiene los campos estado ni fecha de baja

### Requirement: Egreso y defunción en el panel

El egreso o la defunción DEBEN (MUST) registrarse cambiando `estado` y `fecha_baja` en la página del residente. Si las fechas no cumplen las reglas, el formulario se vuelve a mostrar (`200`) con el mensaje de la regla, sin guardar y nunca con un `500`.

#### Scenario: Egresar sin fecha de baja da un mensaje (HB-09, criterio 3)

- **GIVEN** la residente María Guadalupe Hernández López, activa
- **WHEN** un usuario de *Lectura y escritura* la cambia a "Egresado" sin fecha de baja
- **THEN** la respuesta es `200` con el mensaje "La fecha de baja es obligatoria"
- **AND** la residente sigue `ACTIVO`

#### Scenario: Fecha de baja anterior al ingreso (readme, sección 5, "Validaciones incluidas")

- **GIVEN** la residente María Guadalupe Hernández López, ingresada el 2023-02-01
- **WHEN** un usuario de *Lectura y escritura* la cambia a "Egresado" con fecha de baja 2023-01-31
- **THEN** la respuesta es `200` con el mensaje "La fecha de baja no puede ser anterior al ingreso."
- **AND** la residente sigue `ACTIVO`

#### Scenario: Egreso o defunción con fecha de baja (HB-09, descripción técnica)

- **GIVEN** la residente María Guadalupe Hernández López, activa
- **WHEN** un usuario de *Lectura y escritura* la cambia a "Egresado" o a "Fallecido" con fecha de baja 2026-02-01
- **THEN** el panel redirige (`302`)
- **AND** su entidad ya no está activa

### Requirement: Búsqueda de residentes sin mayúsculas ni acentos en el panel

La búsqueda de la lista de residentes DEBE (MUST) ignorar mayúsculas y acentos en los nombres y los apellidos, comparando sobre `f_unaccent(lower(...))`.

#### Scenario: "hernandez" encuentra "Hernández" (HB-09, criterio 5)

- **GIVEN** la residente María Guadalupe Hernández López
- **WHEN** un usuario busca "hernandez" en la lista de residentes
- **THEN** la lista incluye "Hernández"
- **AND** al buscar "torres" la lista no la incluye

### Requirement: Sin borrado de residentes y sin el Hogar en el panel

Nadie, ni el Administrador, DEBE (MUST) poder borrar residentes desde el panel: el egreso y la defunción son bajas lógicas. El Hogar, que crean las migraciones, DEBE (MUST) quedar fuera del panel.

#### Scenario: Nadie borra residentes (HB-09, criterio 4)

- **GIVEN** la residente María Guadalupe Hernández López
- **WHEN** el Administrador o un usuario de *Lectura y escritura* abre su página de borrado
- **THEN** la respuesta es `403`
- **AND** la residente sigue en la base

#### Scenario: El Hogar no se edita en el panel (HB-09, descripción técnica)

- **GIVEN** el panel `/admin/` configurado
- **WHEN** se revisan los modelos registrados
- **THEN** `Entidad` no está registrada
