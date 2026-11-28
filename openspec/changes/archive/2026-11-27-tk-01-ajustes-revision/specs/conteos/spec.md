# Spec Delta

## MODIFIED Requirements

### Requirement: Conteo cerrado inmutable

La base DEBE (MUST) rechazar cualquier cambio al encabezado de un conteo `CERRADO` y cualquier alta, cambio o baja de sus renglones, también si el cambio saca un renglón del conteo cerrado o lo mete en él (`tg_conteo_cerrado` y `tg_detalle_conteo_cerrado`).

#### Scenario: Cambiar el encabezado de un conteo cerrado (TK-01, prueba 3.3)

- **GIVEN** el conteo 1 de María, `CERRADO`
- **WHEN** se ejecuta `UPDATE conteo_fisico SET nota = 'x' WHERE id = 1`
- **THEN** la base lo rechaza con "está cerrado y no se puede modificar"

#### Scenario: Agregar un renglón a un conteo cerrado (TK-01, criterio 8)

- **GIVEN** el conteo 1 de María, `CERRADO`
- **WHEN** se inserta un renglón de Paracetamol en el conteo 1
- **THEN** la base lo rechaza con "El conteo 1 está cerrado"

#### Scenario: Borrar el encabezado de un conteo cerrado (revisión de TK-01, hallazgo 2)

- **GIVEN** el conteo 1 de María, `CERRADO`
- **WHEN** se ejecuta `DELETE FROM conteo_fisico WHERE id = 1`
- **THEN** la base lo rechaza con "está cerrado y no se puede modificar"

#### Scenario: Cambiar o borrar un renglón de un conteo cerrado (revisión de TK-01, hallazgo 2)

- **GIVEN** el conteo 1 de María, `CERRADO`, con su renglón de Metformina
- **WHEN** se cambia su `cantidad_fisica` o se borra el renglón
- **THEN** la base lo rechaza con "El conteo 1 está cerrado"

#### Scenario: Sacar un renglón de un conteo cerrado (revisión de TK-01, hallazgo 2)

- **GIVEN** el conteo 1 de María, `CERRADO`, y el conteo 2 del Hogar, `EN_PROCESO`
- **WHEN** se cambia el `conteo_id` del renglón de Metformina del conteo 1 al 2
- **THEN** la base lo rechaza con "El conteo 1 está cerrado"
- **AND** el renglón sigue en el conteo 1

#### Scenario: Meter un renglón en un conteo cerrado (revisión de TK-01, hallazgo 2)

- **GIVEN** el conteo 2 del Hogar, `EN_PROCESO`, con su renglón de Omeprazol, y el conteo 1, `CERRADO`
- **WHEN** se cambia el `conteo_id` de ese renglón al 1
- **THEN** la base lo rechaza con "El conteo 1 está cerrado"
