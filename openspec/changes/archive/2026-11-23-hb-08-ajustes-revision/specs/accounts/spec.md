# Spec Delta

## MODIFIED Requirements

### Requirement: Inicio y cierre de sesión

El sistema DEBE (MUST) ofrecer una página de inicio de sesión propia en `/accounts/login/`, llevar a ella desde la raíz y cerrar la sesión solo con `POST`. Con credenciales correctas se entra al panel, y con incorrectas se ve "Usuario o contraseña incorrectos".

#### Scenario: La raíz lleva al login (HB-08, criterio 1)

- **GIVEN** un visitante sin sesión
- **WHEN** abre `/`
- **THEN** es redirigido a `/accounts/login/`

#### Scenario: Credenciales correctas (HB-08, criterio 1)

- **GIVEN** un usuario de *Lectura y escritura*
- **WHEN** inicia sesión con su usuario y su contraseña
- **THEN** es redirigido al panel `/admin/`

#### Scenario: Credenciales incorrectas (HB-08, criterio 1)

- **GIVEN** un usuario de *Lectura y escritura*
- **WHEN** inicia sesión con una contraseña incorrecta
- **THEN** la página de login responde `200` con el mensaje "Usuario o contraseña incorrectos."

#### Scenario: Cerrar sesión solo con POST (HB-08, descripción técnica)

- **GIVEN** un usuario con sesión iniciada
- **WHEN** pide `/accounts/logout/` con `GET`
- **THEN** la respuesta es `405`
- **AND** con `POST` la sesión se cierra y es redirigido al login

#### Scenario: Sin sesión, el panel pide iniciarla (HB-08, regresión)

- **GIVEN** un visitante sin sesión
- **WHEN** abre `/admin/`
- **THEN** es redirigido al login del panel

#### Scenario: Barra con sesión iniciada (revisión de HB-08, hallazgo 1)

- **GIVEN** un usuario de *Lectura y escritura* con sesión iniciada
- **WHEN** se dibuja una página que hereda `base.html`
- **THEN** la barra muestra su nombre y un formulario `POST` a `/accounts/logout/` con el token CSRF y el botón "Cerrar sesión"
- **AND** muestra el enlace "Administración" al panel, porque tiene `is_staff`
- **AND** no tiene `<script>` en línea ni atributos `style`

### Requirement: Un solo grupo por usuario

Un usuario NO DEBE (MUST NOT) pertenecer a 2 grupos: lo impide `uq_usuario_un_grupo` en la base. El formulario del panel DEBE (MUST) avisar con "Elige exactamente un grupo: Solo lectura o Lectura y escritura." si a quien no es Administrador se le elige ninguno o más de uno, y activarle `is_staff`. El Administrador no necesita grupo.

#### Scenario: La base rechaza un segundo grupo (HB-08, criterio 3)

- **GIVEN** un usuario del grupo "Solo lectura"
- **WHEN** se le agrega "Lectura y escritura"
- **THEN** la base lo rechaza por `uq_usuario_un_grupo`, definida como `UNIQUE (usuario_id)` sobre `usuario_groups`

#### Scenario: Alta con un grupo (HB-08, criterio 3)

- **GIVEN** el Administrador con sesión en el panel
- **WHEN** da de alta un usuario con el grupo "Solo lectura"
- **THEN** el usuario queda con ese único grupo y con `is_staff`, para entrar al panel
- **AND** su contraseña se guarda con Argon2

#### Scenario: Alta sin grupo o con 2 (HB-08, criterio 3)

- **GIVEN** el Administrador con sesión en el panel
- **WHEN** da de alta un usuario sin grupo, o con los 2 grupos
- **THEN** el formulario responde `200` con el aviso "Elige exactamente un grupo: Solo lectura o Lectura y escritura."
- **AND** el usuario no se crea

#### Scenario: Cambio a 2 grupos (HB-08, criterio 3)

- **GIVEN** un usuario de "Solo lectura" y el Administrador con sesión en el panel
- **WHEN** el Administrador edita el usuario y le marca los 2 grupos
- **THEN** el formulario avisa "Elige exactamente un grupo: Solo lectura o Lectura y escritura."
- **AND** el usuario conserva solo "Solo lectura"

#### Scenario: El Administrador no necesita grupo (revisión de HB-08, hallazgo 3)

- **GIVEN** el Administrador con sesión en el panel
- **WHEN** edita su propio usuario sin marcar ningún grupo
- **THEN** el cambio se guarda y sigue siendo superusuario, sin grupos

#### Scenario: El cambio activa is_staff (revisión de HB-08, hallazgo 3)

- **GIVEN** un usuario sin `is_staff` y sin grupo
- **WHEN** el Administrador lo edita y le asigna "Lectura y escritura"
- **THEN** el usuario queda con ese grupo y con `is_staff`

#### Scenario: Un grupo inválido da un solo aviso (revisión de HB-08, hallazgo 10)

- **GIVEN** el Administrador con sesión en el panel
- **WHEN** da de alta un usuario con un grupo que no existe
- **THEN** el formulario muestra en "Grupo" solo el error de opción inválida de Django, sin "Elige exactamente un grupo"

### Requirement: Solo el Administrador gestiona usuarios y grupos

Solo el Administrador (superusuario) DEBE (MUST) ver y gestionar "Usuarios" y ver "Grupos" en el panel; los demás reciben `403`. Nadie DEBE (MUST) poder borrar usuarios (la baja es `is_active = False`), ni crear, cambiar o borrar grupos a mano: su nombre y sus permisos solo los cambia una migración.

#### Scenario: Un usuario de grupo no ve usuarios ni grupos (HB-08, criterio 4)

- **GIVEN** un usuario de "Lectura y escritura" o de "Solo lectura" con sesión en el panel
- **WHEN** abre la lista de usuarios o la de grupos
- **THEN** la respuesta es `403`

#### Scenario: Nadie borra usuarios (HB-08, criterio 4)

- **GIVEN** el Administrador con sesión en el panel
- **WHEN** abre la página para borrar un usuario
- **THEN** la respuesta es `403`

#### Scenario: Los grupos no se crean ni se borran a mano (HB-08, descripción técnica)

- **GIVEN** el Administrador con sesión en el panel
- **WHEN** abre la página para crear un grupo, o la de borrar "Solo lectura"
- **THEN** la respuesta es `403`

#### Scenario: Los grupos no se cambian a mano (revisión de HB-08, hallazgo 5)

- **GIVEN** el Administrador con sesión en el panel
- **WHEN** envía el formulario de "Solo lectura" con otro nombre
- **THEN** la respuesta es `403` y el grupo conserva su nombre y sus 5 permisos
- **AND** la página del grupo se puede consultar (`200`) en modo de solo lectura

### Requirement: Bloqueo por intentos fallidos y expiración de la sesión

Tras 5 contraseñas incorrectas de un usuario, la cuenta DEBE (MUST) quedar bloqueada 15 minutos, aun con la contraseña correcta, con `429` y un mensaje de cuenta bloqueada. El bloqueo se cuenta por usuario: no afecta a los demás. La sesión DEBE (MUST) expirar tras 30 minutos de inactividad y al cerrar el navegador.

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
- **WHEN** se consulta su sesión
- **THEN** expira en 1800 segundos y al cerrar el navegador

#### Scenario: Mensaje de bloqueo (revisión de HB-08, hallazgo 6)

- **GIVEN** un usuario bloqueado
- **WHEN** intenta iniciar sesión
- **THEN** la página dice "Demasiados intentos fallidos. La cuenta queda bloqueada 15 minutos: espera y vuelve a intentarlo."

#### Scenario: app_user escribe en las tablas de axes (revisión de HB-08, hallazgo 11)

- **GIVEN** la base migrada
- **WHEN** `app_user`, el usuario de base de datos de la aplicación, registra un intento fallido en `axes_accessattempt`
- **THEN** el registro se guarda: `app_user` tiene permiso de escritura en las tablas de `axes`
