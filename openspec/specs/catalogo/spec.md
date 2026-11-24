# catalogo Specification

## Purpose

Define el catálogo de Medicamentos: presentaciones, principios activos y medicamentos, sin duplicados aunque cambien mayúsculas o acentos, y con búsqueda por nombre que usa su índice.

## Requirements

### Requirement: Búsqueda sin mayúsculas ni acentos

La base DEBE (MUST) tener instaladas las extensiones `btree_gist`, `pg_trgm` y `unaccent`, y la función `f_unaccent`, que quita los acentos y se puede usar en índices.

#### Scenario: Extensiones instaladas (HB-05, criterio 1)

- **GIVEN** la base migrada
- **WHEN** se listan las extensiones
- **THEN** aparecen `btree_gist`, `pg_trgm` y `unaccent`

#### Scenario: f_unaccent quita los acentos (HB-05, criterio 1)

- **GIVEN** la base migrada
- **WHEN** se evalúa `f_unaccent(lower('Losartán ÁCIDO Ñandú'))`
- **THEN** el resultado es `losartan acido nandu`

#### Scenario: Búsqueda desde el ORM con el índice trigram (HB-05, criterio 5)

- **GIVEN** la búsqueda parcial de Medicamentos activos por nombre comercial desde el ORM
- **WHEN** se obtiene su plan de ejecución
- **THEN** el plan usa `ix_medicamento_nombre_trgm`

### Requirement: Medicamento sin duplicados

No DEBEN (MUST NOT) existir 2 Medicamentos con el mismo nombre comercial, presentación y concentración, sin distinguir mayúsculas ni acentos, aunque uno esté dado de baja. El formulario DEBE (MUST) avisarlo con un mensaje antes de llegar a la base.

#### Scenario: Duplicado rechazado por la base (HB-05, criterio 3)

- **GIVEN** el Medicamento "Losartán" 50 mg en tableta
- **WHEN** se guarda "LOSARTAN" 50 MG en tableta
- **THEN** la base lo rechaza por `uq_medicamento_nombre_pres_conc`

#### Scenario: El formulario avisa el duplicado (HB-05, criterio 3)

- **GIVEN** el Medicamento "Losartán" 50 mg en tableta
- **WHEN** se valida "losartan" 50 mg en tableta con `full_clean()`
- **THEN** el error es un mensaje de validación que empieza con "Ya existe un medicamento", no una excepción de la base

#### Scenario: Otra concentración no es duplicado (HB-05, descripción técnica)

- **GIVEN** el Medicamento "Losartán" 50 mg en tableta
- **WHEN** se guarda "Losartán" 100 mg en tableta
- **THEN** se guarda y existen 2 Medicamentos

### Requirement: Principio activo sin duplicados

No DEBEN (MUST NOT) existir 2 principios activos con el mismo nombre sin distinguir mayúsculas ni acentos.

#### Scenario: Principio activo duplicado (HB-05, descripción técnica)

- **GIVEN** el principio activo "Ácido acetilsalicílico"
- **WHEN** se guarda "acido acetilsalicilico"
- **THEN** la base lo rechaza por `uq_principio_activo_nombre`

### Requirement: Textos obligatorios y tipo válido

La base DEBE (MUST) rechazar los nombres y concentraciones que sean solo espacios, y un tipo de Medicamento distinto de `GENERICO` u `ORIGINAL`.

#### Scenario: Nombre comercial solo con espacios (HB-05, criterio 4)

- **GIVEN** la base migrada
- **WHEN** se inserta un Medicamento cuyo nombre comercial es solo espacios
- **THEN** la base lo rechaza por `ck_medicamento_textos`

#### Scenario: Tipo fuera de GENERICO y ORIGINAL (HB-05, criterio 4)

- **GIVEN** la base migrada
- **WHEN** se inserta un Medicamento con tipo `OTRO`
- **THEN** la base lo rechaza por `ck_medicamento_tipo`

#### Scenario: Principio activo y presentación vacíos (HB-05, criterio 4)

- **GIVEN** la base migrada
- **WHEN** se inserta un principio activo solo con espacios o una presentación sin nombre
- **THEN** la base los rechaza por `ck_principio_activo_nombre` y `ck_presentacion_nombre`

### Requirement: Esquema con los nombres del readme

Las tablas, restricciones e índices del catálogo DEBEN (MUST) llevar los nombres exactos de las secciones 3.1 y 3.3. Las FK de la tabla puente NO DEBEN (MUST NOT) tener índices propios, porque ya los cubren el `UNIQUE` y `ix_mpa_principio_medicamento`.

#### Scenario: Índices con su definición (HB-05, criterio 2)

- **GIVEN** la base migrada
- **WHEN** se consulta la definición de cada índice
- **THEN** `ix_medicamento_nombre_trgm` es GIN sobre `f_unaccent(lower(...))` con `gin_trgm_ops` y `WHERE activo`
- **AND** `ix_principio_activo_trgm` es GIN sobre `f_unaccent(lower(...))` con `gin_trgm_ops`
- **AND** `ix_mpa_principio_medicamento` cubre `(principio_activo_id, medicamento_id)`
- **AND** `uq_medicamento_nombre_pres_conc` es único e incluye `presentacion_id`

#### Scenario: Sin índices duplicados en la tabla puente (HB-05, descripción técnica)

- **GIVEN** la tabla `medicamento_principio_activo`
- **WHEN** se listan sus índices
- **THEN** solo existen su llave primaria, `uq_mpa_medicamento_principio` e `ix_mpa_principio_medicamento`

### Requirement: Presentaciones semilla

Las migraciones DEBEN (MUST) crear las 8 presentaciones semilla y poder revertirse por completo.

#### Scenario: Las 8 presentaciones (HB-05, criterio 6)

- **GIVEN** la base migrada
- **WHEN** se listan las presentaciones
- **THEN** son tableta, cápsula, jarabe, gotas, ampolleta, parche, crema e inhalador

#### Scenario: migrate catalogo zero revierte todo (HB-05, criterio 6)

- **GIVEN** la base migrada
- **WHEN** se ejecuta `./scripts/migrate.sh catalogo zero`
- **THEN** desaparecen las tablas del catálogo, `f_unaccent` y las 3 extensiones
- **AND** `./scripts/migrate.sh` las vuelve a crear

### Requirement: La aplicación registra en el catálogo

`app_user` DEBE (MUST) poder registrar en las tablas del catálogo sin ser su dueño.

#### Scenario: app_user registra un principio activo (HB-05, descripción técnica)

- **GIVEN** una sesión que actúa como `app_user`
- **WHEN** inserta un principio activo
- **THEN** el registro queda guardado

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
