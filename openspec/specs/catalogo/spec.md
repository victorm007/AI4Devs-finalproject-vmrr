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

El alta y el cambio de un medicamento DEBEN (MUST) incluir sus principios activos en la misma pantalla, al menos uno, elegidos con un buscador (*autocomplete*) que ignora mayúsculas y acentos. Sin ninguno, el formulario no guarda y muestra el mensaje "Un medicamento debe tener al menos un principio activo.", tanto en el alta como en el cambio. La regla se valida fuera de la base, así que se puede reutilizar fuera del panel, por ejemplo desde código que guarda sin pasar por un formulario. Aparte, en la V2, el esquema de `POST` y `PATCH /medicamentos` exige lo mismo por su cuenta: rechaza la lista vacía con `errores[].codigo = CAMPO_VACIO` y el mismo mensaje.

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

### Requirement: Lista de medicamentos sin consultas N+1

La lista de medicamentos del panel DEBE (MUST) hacer el mismo número de consultas sin importar cuántos medicamentos muestre.

#### Scenario: Mismo número de consultas con 1 y con 3 medicamentos (HB-09, descripción técnica)

- **GIVEN** la lista de medicamentos con 1 medicamento, y luego con 3 en presentaciones distintas
- **WHEN** un usuario de *Lectura y escritura* la abre en los 2 casos
- **THEN** el número de consultas es el mismo

### Requirement: Panel del catálogo compatible con la CSP

Las páginas del catálogo en el panel DEBEN (MUST) cargarse sin `<script>` en línea, sin etiquetas `<style>` y sin atributos `style` ni manejadores `on*=`, y con la cabecera `Content-Security-Policy`. Esto incluye el alta del medicamento con su buscador de principios activos, la lista y la página de cambio.

#### Scenario: Alta del medicamento sin código en línea (HB-09, definición de hecho)

- **GIVEN** un usuario de *Lectura y escritura*
- **WHEN** abre el alta de un medicamento
- **THEN** la respuesta trae la cabecera `Content-Security-Policy`
- **AND** no tiene `<script>` sin `src`, etiquetas `<style>`, atributos `style` ni manejadores `on*=`

#### Scenario: Lista y cambio del medicamento sin código en línea (revisión de HB-09, hallazgo 7)

- **GIVEN** un usuario de *Lectura y escritura* y un medicamento registrado
- **WHEN** abre la lista de medicamentos y la página de cambio de ese medicamento
- **THEN** ninguna de las 2 tiene `<script>` sin `src`, etiquetas `<style>`, atributos `style` ni manejadores `on*=`

#### Scenario: Sin violaciones de CSP en el navegador (HB-09, definición de hecho)

- **GIVEN** la aplicación detrás de nginx, con `collectstatic`
- **WHEN** se da de alta un medicamento en `https://localhost/admin/` usando el buscador de principios activos y el botón **+**
- **THEN** la consola del navegador no muestra violaciones de CSP

### Requirement: Presentación sin duplicados

No DEBEN (MUST NOT) existir 2 presentaciones con el mismo nombre sin distinguir mayúsculas ni acentos. El panel lo avisa con un mensaje antes de guardar, y la base lo rechaza por `uq_presentacion_nombre`.

#### Scenario: La base rechaza una presentación duplicada sin acentos (revisión de HB-09, hallazgo 2)

- **GIVEN** la presentación semilla "cápsula"
- **WHEN** se inserta directamente en la base la presentación "CAPSULA"
- **THEN** la base la rechaza por `uq_presentacion_nombre`

#### Scenario: El panel avisa de una presentación duplicada (revisión de HB-09, hallazgo 2)

- **GIVEN** un usuario de *Lectura y escritura* y la presentación semilla "tableta"
- **WHEN** da de alta la presentación "Tableta"
- **THEN** el formulario se vuelve a mostrar (`200`) con el mensaje "Ya existe esa presentación"
- **AND** sigue habiendo 8 presentaciones
- **AND** una presentación nueva, como "supositorio", sí se guarda

#### Scenario: Índice con su definición (revisión de HB-09, hallazgo 2)

- **GIVEN** la base migrada
- **WHEN** se consulta la definición de `uq_presentacion_nombre`
- **THEN** es un índice único sobre `f_unaccent(lower(nombre))`
- **AND** la columna `presentacion.nombre` ya no tiene la restricción `UNIQUE` literal

### Requirement: Solo presentaciones activas en el alta de un medicamento

El alta de un medicamento en el panel DEBE (MUST) ofrecer solo las presentaciones activas. Al cambiar un medicamento cuya presentación está dada de baja, esa presentación se sigue ofreciendo, para poder guardarlo.

#### Scenario: El alta no ofrece una presentación dada de baja (revisión de HB-09, hallazgo 3)

- **GIVEN** la presentación "parche" dada de baja (`activo = False`)
- **WHEN** un usuario de *Lectura y escritura* abre el alta de un medicamento
- **THEN** el campo presentación no ofrece "parche" y sí ofrece "tableta"
- **AND** si envía el alta con "parche", el formulario avisa (`200`) y no se registra el medicamento

#### Scenario: El cambio conserva la presentación dada de baja (revisión de HB-09, hallazgo 3)

- **GIVEN** un medicamento en "parche", que después se da de baja
- **WHEN** un usuario de *Lectura y escritura* abre y guarda ese medicamento sin cambiar la presentación
- **THEN** el campo presentación ofrece "parche"
- **AND** el panel redirige (`302`)

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

### Requirement: Alta del catálogo con los permisos de app_user

El alta de un medicamento con su principio activo desde el panel DEBE (MUST) funcionar con los permisos del rol de la aplicación, `app_user`, incluido el registro de cambios del panel.

#### Scenario: Alta de un medicamento como app_user (revisión de HB-09, hallazgo 6)

- **GIVEN** la conexión de la prueba actuando como `app_user`, y un usuario de *Lectura y escritura*
- **WHEN** da de alta "Losartán" 50 mg en tableta con el principio activo "Losartán"
- **THEN** el panel redirige (`302`)
- **AND** el medicamento y la entrada del historial de cambios del panel quedan guardados

### Requirement: Solo lectura no cambia presentaciones ni principios activos

Un usuario de *Solo lectura* DEBE (MUST) recibir `403` al enviar el cambio de una presentación o de un principio activo, y el registro queda igual. Las listas de presentaciones y de principios activos buscan sin mayúsculas ni acentos.

#### Scenario: 403 al cambiar una presentación o un principio activo (revisión de HB-09, hallazgo 8)

- **GIVEN** un usuario de *Solo lectura*, la presentación "tableta" y el principio activo "Losartán"
- **WHEN** abre la página de cada uno y envía un cambio de nombre
- **THEN** la página se ve en modo de consulta (`200`)
- **AND** el envío responde `403` y el nombre queda igual

#### Scenario: Búsqueda en las listas de presentaciones y principios activos (revisión de HB-09, hallazgo 8)

- **GIVEN** la presentación semilla "cápsula" y el principio activo "Losartán"
- **WHEN** un usuario busca "capsula" en la lista de presentaciones y "LOSARTAN" en la de principios activos
- **THEN** cada lista muestra exactamente ese registro
