# Spec Delta

## MODIFIED Requirements

### Requirement: Dosis, frecuencia y fechas válidas

La base DEBE (MUST) rechazar una Pauta con dosis menor o igual a 0, con frecuencia fuera de 1 a 168 horas o con fecha de fin anterior a la de inicio. La validación del modelo DEBE (MUST) avisar cada caso con un mensaje en español, nunca con un error de base de datos.

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

#### Scenario: Mensajes de la dosis y la frecuencia (revisión de HB-07, hallazgo 2)

- **GIVEN** un Residente activo y un Medicamento activo
- **WHEN** se valida, sin guardarla, una Pauta con dosis 0, o con frecuencia de 0 o de 169 horas
- **THEN** la validación falla con "La dosis debe ser mayor que 0." o con "La frecuencia debe estar entre 1 y 168 horas.", según el caso

#### Scenario: Fin anterior al inicio en la validación del modelo (revisión de HB-07, hallazgo 1)

- **GIVEN** un Residente activo y un Medicamento activo
- **WHEN** se valida, sin guardarla, una Pauta que empieza el 1 de febrero de 2026 y termina el 31 de enero de 2026
- **THEN** la validación falla en `fecha_fin` con el mensaje "La fecha de fin no puede ser anterior a la de inicio."
- **AND** no se produce un error de base de datos

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

#### Scenario: Medicamentos distintos del mismo Residente (revisión de HB-07, hallazgo 7)

- **GIVEN** una Pauta vigente desde el 1 de febrero de 2026
- **WHEN** se registra otra del mismo Residente, de otro Medicamento, con las mismas fechas
- **THEN** quedan registradas las 2 Pautas

#### Scenario: El mismo Medicamento para Residentes distintos (revisión de HB-07, hallazgo 7)

- **GIVEN** una Pauta vigente desde el 1 de febrero de 2026
- **WHEN** se registra otra del mismo Medicamento, para otro Residente activo, con las mismas fechas
- **THEN** quedan registradas las 2 Pautas

#### Scenario: app_user cierra la vigente (revisión de HB-07, hallazgo 7)

- **GIVEN** una Pauta vigente desde el 1 de febrero de 2026
- **WHEN** `app_user`, el usuario de base de datos de la aplicación, le pone fecha de fin el 28 de febrero de 2026
- **THEN** la Pauta queda cerrada en esa fecha
