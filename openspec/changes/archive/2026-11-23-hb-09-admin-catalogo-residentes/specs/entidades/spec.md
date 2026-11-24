# Spec Delta

## ADDED Requirements

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
