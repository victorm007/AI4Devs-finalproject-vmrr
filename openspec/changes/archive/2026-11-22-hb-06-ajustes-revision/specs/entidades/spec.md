# Spec Delta

## MODIFIED Requirements

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

### Requirement: Alta atómica de Residentes

`registrar_residente()` DEBE (MUST) crear la Entidad y el Residente en una sola transacción, siempre con estado `ACTIVO`, sin fecha de baja y con los nombres normalizados. Si los datos son inválidos o el alta falla, NO DEBE (MUST NOT) dejar una Entidad suelta ni alterar el Residente recibido, y los datos inválidos DEBEN (MUST) dar un error de validación con un mensaje claro. DEBE (MUST) funcionar con los permisos de `app_user`.

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

- **GIVEN** un Residente sin guardar con estado `EGRESADO`, fecha de baja e ingreso anterior al nacimiento
- **WHEN** se registra y falla la validación
- **THEN** el Residente recibido conserva su estado `EGRESADO`, su fecha de baja y sus nombres
- **AND** sigue sin Entidad

#### Scenario: Un fallo al guardar permite reintentar (revisión de HB-06, sugerencia 2)

- **GIVEN** un Residente válido sin guardar, y una falla de la base al guardar el Residente después de crear su Entidad
- **WHEN** se registra
- **THEN** el error llega al llamador y no queda ninguna Entidad nueva
- **AND** el Residente recibido sigue sin Entidad, y un segundo intento sin la falla lo registra
