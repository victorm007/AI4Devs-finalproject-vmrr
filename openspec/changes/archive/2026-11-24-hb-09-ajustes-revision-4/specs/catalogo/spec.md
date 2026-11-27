# Spec Delta

## MODIFIED Requirements

### Requirement: Configuración de la búsqueda del panel comprobada

Un registro del panel que usa la búsqueda sin acentos sin declarar los campos donde buscar, que declara un campo que no existe, o que los declara como un texto en lugar de una tupla, DEBE (MUST) producir un error de configuración en la comprobación del sistema, en lugar de devolver todas las filas.

#### Scenario: Sin campos de búsqueda, error de configuración (revisión de HB-09, hallazgo 9)

- **GIVEN** un registro del panel con la búsqueda sin acentos y sin campos declarados
- **WHEN** se ejecuta su comprobación del sistema
- **THEN** devuelve el error `panel.E001`
- **AND** los registros de presentaciones, principios activos, medicamentos y residentes no devuelven errores

#### Scenario: Un campo de búsqueda que no existe (segunda revisión de HB-09, hallazgo 7)

- **GIVEN** un registro del panel con la búsqueda sin acentos y el campo `principio_activos__nombre`, mal escrito
- **WHEN** se ejecuta su comprobación del sistema
- **THEN** devuelve el error `panel.E002`, que nombra el campo

#### Scenario: Campos declarados como texto (tercera revisión de HB-09, hallazgo 6)

- **GIVEN** un registro del panel con `campos_sin_acentos = "nombre"` (un texto, no una tupla)
- **WHEN** se ejecuta su comprobación del sistema
- **THEN** devuelve un solo error `panel.E003`, y ningún `panel.E002` por cada letra

#### Scenario: Una relación inversa válida (tercera revisión de HB-09, hallazgo 7)

- **GIVEN** un registro de principios activos con los campos `nombre` y `medicamentos__nombre_comercial`
- **WHEN** se ejecuta su comprobación del sistema
- **THEN** no devuelve `panel.E002`


### Requirement: Principios activos en la pantalla del medicamento

El alta y el cambio de un medicamento DEBEN (MUST) incluir sus principios activos en la misma pantalla, al menos uno, elegidos con un buscador (*autocomplete*) que ignora mayúsculas y acentos. Sin ninguno, el formulario no guarda y muestra el mensaje "Un medicamento debe tener al menos un principio activo.", tanto en el alta como en el cambio. La regla se valida fuera de la base y se puede reutilizar fuera del panel: en la V2, `POST` y `PATCH /medicamentos` traducen su código `sin_principio_activo` a `errores[].codigo = CAMPO_VACIO`.

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
- **WHEN** se valida una lista vacía de principios activos, como la que llegaría en `POST /medicamentos` de la V2
- **THEN** se rechaza con el mensaje "Un medicamento debe tener al menos un principio activo." y el código `sin_principio_activo`
- **AND** una lista con un principio activo se acepta
- **AND** sin colección (`None`) se rechaza con el mismo mensaje y código, como caso defensivo
- **AND** un texto o una secuencia de bytes (`str`, `bytes`, `bytearray`, `memoryview`) en lugar de una colección es un error de programación (`TypeError`), no una regla de negocio

#### Scenario: El buscador de principios activos ignora los acentos (HB-09, descripción técnica)

- **GIVEN** un usuario de *Lectura y escritura* y el principio activo "Losartán"
- **WHEN** el buscador del campo principio activo pide "losartan"
- **THEN** la respuesta incluye "Losartán"
