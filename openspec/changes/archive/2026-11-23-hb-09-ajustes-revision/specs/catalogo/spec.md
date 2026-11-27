# Spec Delta

## ADDED Requirements

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

Un registro del panel que usa la búsqueda sin acentos sin declarar los campos donde buscar DEBE (MUST) producir un error de configuración en la comprobación del sistema, en lugar de devolver todas las filas.

#### Scenario: Sin campos de búsqueda, error de configuración (revisión de HB-09, hallazgo 9)

- **GIVEN** un registro del panel con la búsqueda sin acentos y sin campos declarados
- **WHEN** se ejecuta su comprobación del sistema
- **THEN** devuelve el error `panel.E001`
- **AND** los registros de presentaciones, principios activos, medicamentos y residentes no devuelven errores

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

## MODIFIED Requirements

### Requirement: Búsqueda del catálogo sin mayúsculas ni acentos en el panel

La búsqueda de la lista de medicamentos DEBE (MUST) ignorar mayúsculas y acentos y encontrar el medicamento por su nombre comercial o por el nombre de cualquiera de sus principios activos, comparando sobre `f_unaccent(lower(...))`. El término se divide en palabras: cada palabra debe aparecer en alguno de esos campos, y los espacios sobrantes no cuentan.

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
