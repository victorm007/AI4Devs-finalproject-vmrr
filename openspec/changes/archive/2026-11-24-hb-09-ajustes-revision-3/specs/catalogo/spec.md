# Spec Delta

## MODIFIED Requirements

### Requirement: Búsqueda del catálogo sin mayúsculas ni acentos en el panel

La búsqueda de la lista de medicamentos DEBE (MUST) ignorar mayúsculas y acentos y encontrar el medicamento por su nombre comercial o por el nombre de cualquiera de sus principios activos, comparando sobre `f_unaccent(lower(...))`. El término se divide en palabras: cada palabra debe aparecer en alguno de esos campos, y los espacios sobrantes no cuentan. Se usan como mucho las primeras 8 palabras, y los comodines `%` y `_` se buscan como texto literal.

#### Scenario: Por nombre comercial (HB-09, criterio 5)

- **GIVEN** el medicamento "Losartán" registrado
- **WHEN** un usuario busca "losartan" en la lista de medicamentos
- **THEN** la lista incluye "Losartán"

#### Scenario: Por principio activo (HB-09, criterio 5)

- **GIVEN** el medicamento "Cozaar" con el principio activo "Losartán"
- **WHEN** un usuario busca "COZAAR" y después "losartan"
- **THEN** en las 2 búsquedas la lista incluye "Cozaar"
- **AND** al buscar "paracetamol" la lista no incluye "Cozaar"

#### Scenario: Varias palabras y espacios sobrantes (revisión de HB-09, hallazgo 1)

- **GIVEN** el medicamento "Cozaar" con el principio activo "Losartán"
- **WHEN** un usuario busca "cozaar losartan" y después "losartan " con un espacio al final
- **THEN** en las 2 búsquedas la lista incluye "Cozaar"
- **AND** al buscar "cozaar paracetamol" la lista no lo incluye, porque una palabra no coincide
- **AND** al buscar solo un espacio, la lista muestra todos los medicamentos

#### Scenario: Cada palabra puede coincidir con un principio activo distinto (segunda revisión de HB-09, hallazgo 1)

- **GIVEN** el medicamento "Hyzaar" con los principios activos "Losartán" e "Hidroclorotiazida"
- **WHEN** un usuario busca "losartan hidroclorotiazida"
- **THEN** la lista incluye "Hyzaar" una sola vez

#### Scenario: Los comodines se buscan como texto (segunda revisión de HB-09, hallazgo 1)

- **GIVEN** medicamentos registrados, ninguno con `%` ni `_` en su nombre ni en sus principios activos
- **WHEN** un usuario busca "%" y después "_"
- **THEN** en las 2 búsquedas la lista queda vacía

#### Scenario: Tope de 8 palabras (segunda revisión de HB-09, hallazgo 9)

- **GIVEN** el medicamento "Cozaar" con el principio activo "Losartán"
- **WHEN** un usuario busca 8 veces "cozaar" seguido de "paracetamol" (9 palabras)
- **THEN** la lista incluye "Cozaar", porque la novena palabra no se usa

### Requirement: Configuración de la búsqueda del panel comprobada

Un registro del panel que usa la búsqueda sin acentos sin declarar los campos donde buscar, o que declara un campo que no existe, DEBE (MUST) producir un error de configuración en la comprobación del sistema, en lugar de devolver todas las filas.

#### Scenario: Sin campos de búsqueda, error de configuración (revisión de HB-09, hallazgo 9)

- **GIVEN** un registro del panel con la búsqueda sin acentos y sin campos declarados
- **WHEN** se ejecuta su comprobación del sistema
- **THEN** devuelve el error `panel.E001`
- **AND** los registros de presentaciones, principios activos, medicamentos y residentes no devuelven errores

#### Scenario: Un campo de búsqueda que no existe (segunda revisión de HB-09, hallazgo 7)

- **GIVEN** un registro del panel con la búsqueda sin acentos y el campo `principio_activos__nombre`, mal escrito
- **WHEN** se ejecuta su comprobación del sistema
- **THEN** devuelve el error `panel.E002`, que nombra el campo

### Requirement: Principios activos en la pantalla del medicamento

El alta y el cambio de un medicamento DEBEN (MUST) incluir sus principios activos en la misma pantalla, al menos uno, elegidos con un buscador (*autocomplete*) que ignora mayúsculas y acentos. Sin ninguno, el formulario no guarda y muestra el mensaje "Un medicamento debe tener al menos un principio activo.", tanto en el alta como en el cambio. La regla se valida fuera de la base y se puede reutilizar fuera del panel.

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
- **AND** sin colección (`None`) se rechaza con el mismo mensaje y código
- **AND** un texto en lugar de una colección es un error de programación (`TypeError`), no una regla de negocio
- **AND** la V2 traduce el código `sin_principio_activo` a `errores[].codigo = CAMPO_VACIO`

#### Scenario: El buscador de principios activos ignora los acentos (HB-09, descripción técnica)

- **GIVEN** un usuario de *Lectura y escritura* y el principio activo "Losartán"
- **WHEN** el buscador del campo principio activo pide "losartan"
- **THEN** la respuesta incluye "Losartán"
