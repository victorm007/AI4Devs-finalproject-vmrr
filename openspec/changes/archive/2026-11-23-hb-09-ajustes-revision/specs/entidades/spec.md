# Spec Delta

## ADDED Requirements

### Requirement: Alta de residentes con los permisos de app_user

El alta de un residente desde el panel DEBE (MUST) funcionar con los permisos del rol de la aplicación, `app_user`: crea su entidad, el residente y la entrada del historial de cambios del panel.

#### Scenario: Alta de un residente como app_user (revisión de HB-09, hallazgo 6)

- **GIVEN** la conexión de la prueba actuando como `app_user`, y un usuario de *Lectura y escritura*
- **WHEN** da de alta a María Guadalupe Hernández López
- **THEN** el panel redirige (`302`)
- **AND** existen su entidad `RESIDENTE`, la residente `ACTIVO` y la entrada del historial de cambios del panel

### Requirement: Páginas de residentes compatibles con la CSP

Las páginas de residentes en el panel DEBEN (MUST) cargarse sin `<script>` en línea, sin etiquetas `<style>` y sin atributos `style` ni manejadores `on*=`, y con la cabecera `Content-Security-Policy`.

#### Scenario: Alta, lista y cambio de residentes sin código en línea (revisión de HB-09, hallazgo 7)

- **GIVEN** un usuario de *Lectura y escritura* y la residente María Guadalupe Hernández López
- **WHEN** abre el alta de un residente, la lista de residentes y la página de cambio de María
- **THEN** cada respuesta trae la cabecera `Content-Security-Policy`
- **AND** ninguna tiene `<script>` sin `src`, etiquetas `<style>`, atributos `style` ni manejadores `on*=`

## MODIFIED Requirements

### Requirement: Búsqueda de residentes sin mayúsculas ni acentos en el panel

La búsqueda de la lista de residentes DEBE (MUST) ignorar mayúsculas y acentos en los nombres y los apellidos, comparando sobre `f_unaccent(lower(...))`. El término se divide en palabras: cada palabra debe aparecer en alguno de los nombres o apellidos, y los espacios sobrantes no cuentan.

#### Scenario: "hernandez" encuentra "Hernández" (HB-09, criterio 5)

- **GIVEN** la residente María Guadalupe Hernández López
- **WHEN** un usuario busca "hernandez" en la lista de residentes
- **THEN** la lista incluye "Hernández"
- **AND** al buscar "torres" la lista no la incluye

#### Scenario: Nombre y apellido juntos (revisión de HB-09, hallazgo 1)

- **GIVEN** la residente María Guadalupe Hernández López
- **WHEN** un usuario busca "maria hernandez" y después " hernandez " con espacios sobrantes
- **THEN** en las 2 búsquedas la lista la incluye
- **AND** al buscar "maria torres" la lista no la incluye, porque una palabra no coincide
