# Spec Delta

## ADDED Requirements

### Requirement: Catálogo en el panel según el grupo

El panel `/admin/` DEBE (MUST) mostrar presentaciones, principios activos y medicamentos a los 2 grupos. *Solo lectura* los consulta y no da de alta ni cambia nada (`403`); *Lectura y escritura* da de alta y cambia. La autorización se valida en el servidor.

#### Scenario: Solo lectura consulta el catálogo (HB-09, criterio 1)

- **GIVEN** un usuario del grupo *Solo lectura* con sesión iniciada
- **WHEN** abre la lista de presentaciones, la de principios activos y la de medicamentos
- **THEN** cada lista responde `200`
- **AND** el alta de cada uno responde `403`

#### Scenario: Solo lectura no cambia un medicamento (HB-09, criterio 1)

- **GIVEN** un usuario del grupo *Solo lectura* y un medicamento registrado
- **WHEN** abre la página del medicamento
- **THEN** la ve en modo de consulta (`200`, sin el botón de guardar)
- **AND** si envía un cambio, la respuesta es `403` y el medicamento queda igual

#### Scenario: Lectura y escritura abre el alta del catálogo (HB-09, criterio 1; readme, sección 5)

- **GIVEN** un usuario del grupo *Lectura y escritura* con sesión iniciada
- **WHEN** abre el alta de una presentación, de un principio activo y de un medicamento
- **THEN** cada página responde `200`

### Requirement: Principios activos en la pantalla del medicamento

El alta y el cambio de un medicamento DEBEN (MUST) incluir sus principios activos en la misma pantalla, al menos uno, elegidos con un buscador (*autocomplete*) que ignora mayúsculas y acentos.

#### Scenario: Alta con su principio activo (HB-09, criterio 2)

- **GIVEN** un usuario de *Lectura y escritura* y el principio activo "Losartán"
- **WHEN** da de alta "Losartán", genérico, 50 mg, tableta, con el principio activo "Losartán"
- **THEN** el panel redirige (`302`)
- **AND** el medicamento queda registrado con "Losartán" como su único principio activo

#### Scenario: Sin principio activo, el formulario avisa (HB-09, criterio 2)

- **GIVEN** un usuario de *Lectura y escritura*
- **WHEN** da de alta un medicamento sin ningún principio activo
- **THEN** el formulario se vuelve a mostrar (`200`) con un aviso
- **AND** no se registra ningún medicamento

#### Scenario: El buscador de principios activos ignora los acentos (HB-09, descripción técnica)

- **GIVEN** un usuario de *Lectura y escritura* y el principio activo "Losartán"
- **WHEN** el buscador del campo principio activo pide "losartan"
- **THEN** la respuesta incluye "Losartán"

### Requirement: Reglas del catálogo como mensajes en el panel

Un alta o un cambio que viola una regla del catálogo DEBE (MUST) volver a mostrar el formulario (`200`) con el mensaje de la regla, sin guardar nada y nunca con un error `500`.

#### Scenario: Medicamento duplicado sin acentos (HB-09, criterio 3)

- **GIVEN** el medicamento "Losartán" 50 mg en tableta, registrado desde el panel
- **WHEN** un usuario de *Lectura y escritura* da de alta "LOSARTAN" 50 MG en tableta
- **THEN** la respuesta es `200` con el mensaje "Ya existe un medicamento con ese nombre, presentación y concentración"
- **AND** sigue habiendo un solo medicamento

#### Scenario: Principio activo duplicado sin acentos (readme, sección 5, "Validaciones incluidas")

- **GIVEN** el principio activo "Losartán"
- **WHEN** un usuario de *Lectura y escritura* da de alta el principio activo "LOSARTAN"
- **THEN** la respuesta es `200` con el mensaje "Ya existe ese principio activo"
- **AND** sigue habiendo un solo principio activo

### Requirement: Baja lógica del catálogo, sin borrado

En el panel, la baja de un medicamento o de una presentación DEBE (MUST) ser lógica (`activo`). Nadie, ni el Administrador, DEBE (MUST) poder borrar presentaciones, principios activos ni medicamentos, y las listas no ofrecen la acción "Eliminar".

#### Scenario: Desmarcar activo da de baja el medicamento (HB-09, criterio 4)

- **GIVEN** un medicamento activo, con su principio activo
- **WHEN** un usuario de *Lectura y escritura* guarda el medicamento con `activo` desmarcado
- **THEN** el panel redirige (`302`)
- **AND** el medicamento sigue registrado con `activo = False`

#### Scenario: Nadie borra del catálogo (HB-09, criterio 4)

- **GIVEN** una presentación, un principio activo y un medicamento registrados
- **WHEN** el Administrador o un usuario de *Lectura y escritura* abre la página de borrado de cualquiera de ellos
- **THEN** la respuesta es `403`
- **AND** el registro sigue en la base

#### Scenario: Sin la acción "Eliminar" en las listas (readme, sección 5, "Controles")

- **GIVEN** el Administrador con sesión iniciada y un medicamento registrado
- **WHEN** abre la lista de medicamentos
- **THEN** la lista no ofrece la acción "Eliminar"

### Requirement: Búsqueda del catálogo sin mayúsculas ni acentos en el panel

La búsqueda de la lista de medicamentos DEBE (MUST) ignorar mayúsculas y acentos y encontrar el medicamento por su nombre comercial o por el nombre de cualquiera de sus principios activos, comparando sobre `f_unaccent(lower(...))`.

#### Scenario: Por nombre comercial (HB-09, criterio 5)

- **GIVEN** el medicamento "Losartán" registrado
- **WHEN** un usuario busca "losartan" en la lista de medicamentos
- **THEN** la lista incluye "Losartán"

#### Scenario: Por principio activo (HB-09, criterio 5)

- **GIVEN** el medicamento "Cozaar" con el principio activo "Losartán"
- **WHEN** un usuario busca "COZAAR" y después "losartan"
- **THEN** en las 2 búsquedas la lista incluye "Cozaar"
- **AND** al buscar "paracetamol" la lista no incluye "Cozaar"

### Requirement: Lista de medicamentos sin consultas N+1

La lista de medicamentos del panel DEBE (MUST) hacer el mismo número de consultas sin importar cuántos medicamentos muestre.

#### Scenario: Mismo número de consultas con 1 y con 3 medicamentos (HB-09, descripción técnica)

- **GIVEN** la lista de medicamentos con 1 medicamento, y luego con 3 en presentaciones distintas
- **WHEN** un usuario de *Lectura y escritura* la abre en los 2 casos
- **THEN** el número de consultas es el mismo

### Requirement: Panel del catálogo compatible con la CSP

Las páginas del catálogo en el panel DEBEN (MUST) cargarse sin `<script>` en línea ni atributos `style`, y con la cabecera `Content-Security-Policy`, también el alta del medicamento con su buscador de principios activos.

#### Scenario: Alta del medicamento sin código en línea (HB-09, definición de hecho)

- **GIVEN** un usuario de *Lectura y escritura*
- **WHEN** abre el alta de un medicamento
- **THEN** la respuesta trae la cabecera `Content-Security-Policy`
- **AND** no tiene `<script>` sin `src` ni atributos `style`

#### Scenario: Sin violaciones de CSP en el navegador (HB-09, definición de hecho)

- **GIVEN** la aplicación detrás de nginx, con `collectstatic`
- **WHEN** se da de alta un medicamento en `https://localhost/admin/` usando el buscador de principios activos y el botón **+**
- **THEN** la consola del navegador no muestra violaciones de CSP
