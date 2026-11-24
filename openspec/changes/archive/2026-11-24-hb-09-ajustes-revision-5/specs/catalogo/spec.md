# Spec Delta

## MODIFIED Requirements

### Requirement: Principios activos en la pantalla del medicamento

El alta y el cambio de un medicamento DEBEN (MUST) incluir sus principios activos en la misma pantalla, al menos uno, elegidos con un buscador (*autocomplete*) que ignora mayúsculas y acentos. Sin ninguno, el formulario no guarda y muestra el mensaje "Un medicamento debe tener al menos un principio activo.", tanto en el alta como en el cambio. La regla se valida fuera de la base y se puede reutilizar fuera del panel: en la V2, el esquema de `POST` y `PATCH /medicamentos` rechaza la lista vacía con `errores[].codigo = CAMPO_VACIO` y el mismo mensaje.

#### Scenario: Alta con su principio activo (HB-09, criterio 2)

- **GIVEN** un usuario de *Lectura y escritura* y el principio activo "Losartán"
- **WHEN** da de alta "Losartán", genérico, 50 mg, tableta, con el principio activo "Losartán"
- **THEN** el panel redirige (`302`)
- **AND** el medicamento queda registrado con "Losartán" como su único principio activo

#### Scenario: Sin principio activo, el formulario avisa (HB-09, criterio 2)

- **GIVEN** un usuario de *Lectura y escritura*
- **WHEN** da de alta un medicamento sin ningún principio activo
- **THEN** el formulario se vuelve a mostrar (`200`) con el mensaje "Un medicamento debe tener al menos un principio activo."
- **AND** no se registra ningún medicamento

#### Scenario: Cambio sin principio activo (revisión de HB-09, hallazgo 4)

- **GIVEN** un medicamento registrado sin principios activos (por ejemplo, cargado fuera del panel)
- **WHEN** un usuario de *Lectura y escritura* lo guarda desde el panel sin elegir ninguno, con el renglón vacío o sin renglones
- **THEN** el formulario se vuelve a mostrar (`200`) con el mensaje "Un medicamento debe tener al menos un principio activo."
- **AND** el medicamento queda igual
- **AND** al elegir un principio activo, el mismo cambio se guarda (`302`)

#### Scenario: La regla se puede reutilizar fuera del panel (revisión de HB-09, hallazgo 4)

- **GIVEN** la regla de al menos un principio activo
- **WHEN** se valida una lista vacía de principios activos fuera del panel, por ejemplo desde código que guarda sin pasar por un formulario
- **THEN** se rechaza con el mensaje "Un medicamento debe tener al menos un principio activo." y el código `sin_principio_activo`
- **AND** una lista con un principio activo se acepta
- **AND** sin colección (`None`) se rechaza con el mismo mensaje y código, como caso defensivo
- **AND** un texto o una secuencia de bytes (`str`, `bytes`, `bytearray`, `memoryview`) en lugar de una colección es un error de programación (`TypeError`), no una regla de negocio

#### Scenario: El buscador de principios activos ignora los acentos (HB-09, descripción técnica)

- **GIVEN** un usuario de *Lectura y escritura* y el principio activo "Losartán"
- **WHEN** el buscador del campo principio activo pide "losartan"
- **THEN** la respuesta incluye "Losartán"
