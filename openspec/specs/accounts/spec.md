# accounts Specification

## Purpose

Define el modelo de usuario propio y sus contraseñas, el inicio y cierre de sesión con la plantilla común, los 2 grupos con sus permisos y un solo grupo por usuario, la gestión de usuarios en el panel solo por el Administrador, y el bloqueo por intentos fallidos con la expiración de la sesión.

## Requirements

### Requirement: Modelo de usuario propio

El proyecto DEBE (MUST) usar el modelo `accounts.Usuario`, guardado en la tabla `usuario`, desde la primera migración.

#### Scenario: Modelo y tablas del usuario (HB-03, descripción técnica)

- **GIVEN** la configuración del proyecto
- **WHEN** se consulta el modelo de usuario activo
- **THEN** `AUTH_USER_MODEL` es `accounts.Usuario`
- **AND** su tabla es `usuario` y la de sus grupos es `usuario_groups`

### Requirement: Contraseñas con Argon2

Las contraseñas nuevas DEBEN (MUST) guardarse con Argon2, y un *hash* PBKDF2 como los del dataset mock DEBE (MUST) seguir validándose.

#### Scenario: Contraseña nueva con Argon2 (HB-03, criterio 5)

- **GIVEN** un usuario nuevo con la contraseña `Prueba-larga-2026`
- **WHEN** se guarda
- **THEN** su *hash* empieza con `argon2$`
- **AND** la contraseña se valida

#### Scenario: Hash PBKDF2 del mock (HB-03, criterio 5)

- **GIVEN** un usuario cuyo *hash* es PBKDF2-SHA256, como los del dataset mock
- **WHEN** se valida su contraseña
- **THEN** la validación es correcta

### Requirement: Longitud mínima de la contraseña

Una contraseña DEBE (MUST) tener al menos 10 caracteres.

#### Scenario: Contraseña de 9 y de 10 caracteres (HB-03, descripción técnica)

- **GIVEN** los validadores de contraseña del proyecto
- **WHEN** se valida una contraseña de 9 caracteres y otra de 10
- **THEN** la de 9 se rechaza con el código `password_too_short`
- **AND** la de 10 se acepta

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

### Requirement: Página de login accesible y compatible con la CSP

La página de login DEBE (MUST) tener un `<label>` en cada campo, usar solo recursos propios (Bootstrap 5.3 desde `static/`, sin CDN), no tener JavaScript ni estilos en línea y enviar la política CSP. DEBE (MUST) usarse a 390 px sin desplazamiento horizontal.

#### Scenario: Recursos propios y etiquetas (HB-08, criterio 6)

- **GIVEN** un visitante sin sesión
- **WHEN** abre `/accounts/login/`
- **THEN** la página carga `css/vendor/bootstrap.min.css` desde `static/`, sin ninguna referencia a un CDN
- **AND** los campos usuario y contraseña tienen su `<label>`
- **AND** no hay `<script>` en línea ni atributos `style`
- **AND** la respuesta trae la cabecera `Content-Security-Policy`

#### Scenario: Login a 390 px y sin violaciones de CSP (HB-08, criterio 6)

- **GIVEN** la aplicación detrás de nginx, con `collectstatic`
- **WHEN** se abre `https://localhost/accounts/login/` en el navegador, en escritorio y a 390 px
- **THEN** no hay desplazamiento horizontal
- **AND** la consola no muestra violaciones de CSP

### Requirement: Los 2 grupos y sus permisos

DEBEN (MUST) existir exactamente los grupos *Solo lectura*, con `view_*`, y *Lectura y escritura*, con `view_*`, `add_*` y `change_*`, sobre los modelos del catálogo (presentación, principio activo, medicamento y su tabla puente) y de residentes. Desde TK-01 tienen además los de inventario: los 2 grupos `view_existencia`, `view_movimiento` y `view_motivobaja`, y *Lectura y escritura* también `add_movimiento`. Ningún grupo recibe `delete_*` ni permisos sobre usuarios o grupos.

#### Scenario: Exactamente 2 grupos (HB-08, criterio 2)

- **GIVEN** la base migrada
- **WHEN** se listan los grupos
- **THEN** son exactamente "Solo lectura" y "Lectura y escritura"

#### Scenario: Permisos de Solo lectura (HB-08, criterio 2)

- **GIVEN** la base migrada
- **WHEN** se listan los permisos de "Solo lectura"
- **THEN** son exactamente los 8 `view_*`: los de `presentacion`, `principioactivo`, `medicamento`, `medicamentoprincipioactivo` y `residente`, y los de `existencia`, `movimiento` y `motivobaja` (TK-01)

#### Scenario: Permisos de Lectura y escritura (HB-08, criterio 2)

- **GIVEN** la base migrada
- **WHEN** se listan los permisos de "Lectura y escritura"
- **THEN** son exactamente 19: los 15 `view_*`, `add_*` y `change_*` de esos 5 modelos, y `view_existencia`, `view_movimiento`, `view_motivobaja` y `add_movimiento` (TK-01)
- **AND** ninguno es `delete_*` ni `change_movimiento`, ni se refiere a usuarios o grupos

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
- **THEN** la respuesta es `403` y el grupo conserva su nombre y sus 8 permisos (5 de HB-08 y 3 de TK-01)
- **AND** la página del grupo se puede consultar (`200`) en modo de solo lectura

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

### Requirement: Plantillas con el formato de djLint

Las plantillas `base.html`, `login.html` y `bloqueado.html` DEBEN (MUST) pasar `djlint --check` y `djlint --lint`, y desde este ticket el CI las revisa.

#### Scenario: djLint sin cambios ni errores (HB-08, criterio 7)

- **GIVEN** las 3 plantillas
- **WHEN** se ejecuta `python scripts/verificar.py`, el mismo verificador del *job* `lint`
- **THEN** djLint no propone cambios ni reporta errores

### Requirement: Migraciones reversibles

Las migraciones `0003_grupos` y `0004_un_grupo` DEBEN (MUST) revertirse por completo y volver a aplicarse.

#### Scenario: Revertir a 0002 y volver (HB-08, criterios de revisión de BD)

- **GIVEN** la base migrada
- **WHEN** se ejecuta `./scripts/migrate.sh accounts 0002` y después `./scripts/migrate.sh`
- **THEN** desaparecen los 2 grupos y `uq_usuario_un_grupo`, y vuelven a crearse sin errores
