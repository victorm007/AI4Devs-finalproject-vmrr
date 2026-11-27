# Spec Delta

## ADDED Requirements

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

DEBEN (MUST) existir exactamente los grupos *Solo lectura*, con `view_*`, y *Lectura y escritura*, con `view_*`, `add_*` y `change_*`, sobre los modelos del catálogo (presentación, principio activo, medicamento y su tabla puente) y de residentes. Ningún grupo recibe `delete_*` ni permisos sobre usuarios o grupos.

#### Scenario: Exactamente 2 grupos (HB-08, criterio 2)

- **GIVEN** la base migrada
- **WHEN** se listan los grupos
- **THEN** son exactamente "Solo lectura" y "Lectura y escritura"

#### Scenario: Permisos de Solo lectura (HB-08, criterio 2)

- **GIVEN** la base migrada
- **WHEN** se listan los permisos de "Solo lectura"
- **THEN** son exactamente los 5 `view_*` de `presentacion`, `principioactivo`, `medicamento`, `medicamentoprincipioactivo` y `residente`

#### Scenario: Permisos de Lectura y escritura (HB-08, criterio 2)

- **GIVEN** la base migrada
- **WHEN** se listan los permisos de "Lectura y escritura"
- **THEN** son exactamente los 15 `view_*`, `add_*` y `change_*` de esos 5 modelos
- **AND** ninguno es `delete_*` ni se refiere a usuarios o grupos

### Requirement: Un solo grupo por usuario

Un usuario NO DEBE (MUST NOT) pertenecer a 2 grupos: lo impide `uq_usuario_un_grupo` en la base. El formulario del panel DEBE (MUST) avisar con "Elige exactamente un grupo: Solo lectura o Lectura y escritura." si a quien no es Administrador se le elige ninguno o más de uno.

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

### Requirement: Solo el Administrador gestiona usuarios y grupos

Solo el Administrador (superusuario) DEBE (MUST) ver y gestionar "Usuarios" y "Grupos" en el panel; los demás reciben `403`. Nadie DEBE (MUST) poder borrar usuarios (la baja es `is_active = False`), ni crear o borrar grupos a mano.

#### Scenario: Un usuario de grupo no ve usuarios ni grupos (HB-08, criterio 4)

- **GIVEN** un usuario de "Lectura y escritura" con sesión en el panel
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

### Requirement: Bloqueo por intentos fallidos y expiración de la sesión

Tras 5 contraseñas incorrectas de un usuario, la cuenta DEBE (MUST) quedar bloqueada 15 minutos, aun con la contraseña correcta, con `429` y un mensaje de cuenta bloqueada. La sesión DEBE (MUST) expirar tras 30 minutos de inactividad y al cerrar el navegador.

#### Scenario: El sexto intento responde 429 (HB-08, criterio 5)

- **GIVEN** un usuario de "Lectura y escritura"
- **WHEN** inicia sesión 5 veces con una contraseña incorrecta y después con la correcta
- **THEN** el sexto intento responde `429` con un mensaje que dice que la cuenta está bloqueada

#### Scenario: Configuración del bloqueo y de la sesión (HB-08, descripción técnica)

- **GIVEN** la configuración del proyecto
- **WHEN** se leen los ajustes de `django-axes` y de la sesión
- **THEN** el límite es 5 intentos, el bloqueo dura 15 minutos y se cuenta por usuario
- **AND** la sesión dura 1800 segundos, se renueva con cada petición y expira al cerrar el navegador

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
