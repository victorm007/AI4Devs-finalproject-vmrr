# Spec Delta

## MODIFIED Requirements

### Requirement: Bloqueo por intentos fallidos y expiración de la sesión

Tras 5 contraseñas incorrectas de un usuario, la cuenta DEBE (MUST) quedar bloqueada 15 minutos, aun con la contraseña correcta, con `429` y un mensaje de cuenta bloqueada. El bloqueo se cuenta por usuario: no afecta a los demás. Cada intento durante el bloqueo lo reinicia. La sesión DEBE (MUST) expirar tras 30 minutos de inactividad y al cerrar el navegador.

#### Scenario: El sexto intento responde 429 (HB-08, criterio 5)

- **GIVEN** un usuario de "Lectura y escritura"
- **WHEN** inicia sesión 5 veces con una contraseña incorrecta y después con la correcta
- **THEN** el sexto intento responde `429` con un mensaje que dice que la cuenta está bloqueada
- **AND** el quinto intento fallido ya responde `429` (revisión de HB-08, hallazgo 7)

#### Scenario: Configuración del bloqueo y de la sesión (HB-08, descripción técnica)

- **GIVEN** la configuración del proyecto
- **WHEN** se leen los ajustes de `django-axes` y de la sesión
- **THEN** el límite es 5 intentos, el bloqueo dura 15 minutos y se cuenta por usuario
- **AND** la sesión dura 1800 segundos, se renueva con cada petición y expira al cerrar el navegador

#### Scenario: El bloqueo de un usuario no afecta a otro (revisión de HB-08, hallazgo 2)

- **GIVEN** 2 usuarios que entran desde la misma IP
- **WHEN** el primero falla 5 veces y el segundo inicia sesión con su contraseña
- **THEN** el segundo entra al panel

#### Scenario: El bloqueo termina a los 15 minutos (revisión de HB-08, hallazgo 2)

- **GIVEN** un usuario bloqueado por 5 intentos fallidos
- **WHEN** pasan más de 15 minutos desde el último intento e inicia sesión con su contraseña
- **THEN** entra al panel

#### Scenario: La sesión dura 30 minutos (revisión de HB-08, hallazgo 2)

- **GIVEN** un usuario que acaba de iniciar sesión
- **WHEN** se consulta su sesión en la base y la cookie que recibió
- **THEN** la sesión guardada expira en 1800 segundos
- **AND** la cookie `sessionid` no tiene `max-age` ni `expires`, así que el navegador la borra al cerrarse (2.ª revisión de HB-08, hallazgo 1)

#### Scenario: Cada petición renueva la sesión (2.ª revisión de HB-08, hallazgo 1)

- **GIVEN** un usuario con sesión iniciada a la que le quedan menos de 30 minutos
- **WHEN** abre otra página
- **THEN** la expiración de su sesión vuelve a quedar a 1800 segundos

#### Scenario: El bloqueo sigue antes de los 15 minutos (2.ª revisión de HB-08, hallazgo 5)

- **GIVEN** un usuario bloqueado cuyo último intento fue hace 14 minutos
- **WHEN** inicia sesión con su contraseña
- **THEN** la respuesta sigue siendo `429`

#### Scenario: Cada intento durante el bloqueo lo reinicia (2.ª revisión de HB-08, hallazgo 5)

- **GIVEN** un usuario bloqueado cuyo último intento fue hace 14 minutos
- **WHEN** vuelve a intentarlo
- **THEN** responde `429` y la cuenta de los 15 minutos empieza de nuevo desde ese intento

#### Scenario: Mensaje de bloqueo (revisión de HB-08, hallazgo 6)

- **GIVEN** un usuario bloqueado
- **WHEN** intenta iniciar sesión
- **THEN** la página dice "Demasiados intentos fallidos. La cuenta queda bloqueada 15 minutos: espera sin volver a intentarlo, porque cada intento reinicia la espera. Si olvidaste tu contraseña, pide al Administrador que te asigne una nueva."

#### Scenario: app_user escribe en las tablas de axes (revisión de HB-08, hallazgo 11)

- **GIVEN** la base migrada
- **WHEN** `app_user`, el usuario de base de datos de la aplicación, registra un intento fallido en `axes_accessattempt`
- **THEN** el registro se guarda: `app_user` tiene permiso de escritura en las tablas de `axes`
- **AND** también puede actualizarlos y borrarlos, como hace `axes` al reiniciar los intentos tras un login correcto (2.ª revisión de HB-08, hallazgo 2)
