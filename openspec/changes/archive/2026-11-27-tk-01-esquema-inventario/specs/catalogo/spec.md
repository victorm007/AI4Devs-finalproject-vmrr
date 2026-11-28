# Spec Delta

## ADDED Requirements

### Requirement: Sin baja de un Medicamento con Existencias

El formulario del Medicamento en `/admin/` DEBE (MUST) rechazar desmarcar `activo` si alguna Entidad tiene Existencias de ese Medicamento, con el mensaje "No se puede dar de baja: hay existencias de este medicamento" (`200`, sin guardar y nunca un `500`). La base DEBE (MUST) rechazar esa misma baja aunque se salte el formulario (`tg_medicamento_baja`).

#### Scenario: El panel avisa al dar de baja un Medicamento con Existencias (TK-01, criterio 8; readme, sección 5, "Controles")

- **GIVEN** el dataset mock cargado, con 33 dosis de Eutirox de Carmen
- **WHEN** el Administrador desmarca `activo` de Eutirox en el panel y guarda, con su principio activo
- **THEN** la respuesta es `200` con el mensaje "No se puede dar de baja: hay existencias de este medicamento"
- **AND** Eutirox sigue activo

#### Scenario: Un Medicamento sin saldo sí se da de baja (readme, sección 3.4, guion de la demo, paso 7)

- **GIVEN** el dataset mock cargado, con Tempra en saldo 0 en el Hogar
- **WHEN** el Administrador desmarca `activo` de Tempra en el panel y guarda
- **THEN** la baja se guarda y Tempra queda inactivo

#### Scenario: La base rechaza la baja aunque se salte el formulario (TK-01, criterio 8)

- **GIVEN** el dataset mock cargado
- **WHEN** se ejecuta `UPDATE medicamento SET activo = false` sobre Eutirox
- **THEN** la base lo rechaza con "No se puede dar de baja el medicamento …: tiene existencias"
