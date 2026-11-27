# Spec Delta

## MODIFIED Requirements

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

- **GIVEN** un Residente válido sin guardar, y una restricción diferida de la base que solo se comprueba al confirmar la transacción y que su alta viola
- **WHEN** se registra, el Residente se guarda y falla la confirmación
- **THEN** el error de la base llega al llamador y no queda ninguna Entidad nueva
- **AND** el Residente recibido vuelve a estar sin guardar y sin Entidad, y un segundo intento sin esa restricción lo registra
