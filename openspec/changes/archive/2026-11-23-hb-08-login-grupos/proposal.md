# Login, grupos y usuarios

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-08 · **Épica:** EP-01

## Why

Todavía no se puede iniciar sesión fuera del panel, no existen los 2 grupos ni la regla de un solo grupo por usuario, y no hay protección contra la fuerza bruta (readme.md, sección 6, HB-08). Lo necesitan HB-09 (los grupos entran al panel con sus permisos), TK-01 (asigna a esos grupos los permisos de inventario) y TK-03 (sus pantallas heredan `base.html` y exigen sesión).

## What Changes

- **Inicio y cierre de sesión:** página propia en `/accounts/login/` y cierre de sesión solo por `POST`. La raíz `/` lleva al login, y con credenciales correctas se entra al panel.
- **Plantilla común `base.html`** con Bootstrap 5.3 servido desde `static/`, sin CDN ni JavaScript o estilos en línea (CSP de HB-04). La heredan `login.html`, `bloqueado.html` y todas las pantallas que vienen.
- **Los 2 grupos**, en una migración de datos: **Solo lectura** con `view_*` y **Lectura y escritura** con `view_*`, `add_*` y `change_*`, sobre los modelos del catálogo y de residentes. Nadie recibe `delete_*` ni permisos sobre usuarios.
- **Un solo grupo por usuario:** `uq_usuario_un_grupo` en una migración `RunSQL`. El formulario del panel avisa si se elige ninguno o más de uno.
- **Usuarios en el panel:** `UsuarioAdmin` exige exactamente un grupo a quien no es Administrador, le activa `is_staff` y no permite borrar usuarios. Los grupos no se crean ni se borran a mano. Solo el Administrador ve "Usuarios" y "Grupos".
- **Seguridad de la sección 2.5:** `django-axes` bloquea la cuenta 15 minutos tras 5 intentos fallidos (`429` con un mensaje), y la sesión expira tras 30 minutos de inactividad y al cerrar el navegador.
- **djLint en el CI:** con las primeras plantillas, el *job* `lint` empieza a revisarlas.

**Fuera de alcance:**

- el catálogo y los residentes en `/admin/` (HB-09);
- los permisos de los modelos de inventario (TK-01) y de pautas (historia de pautas);
- la pantalla de existencias como inicio tras el login (TK-03);
- HTMX (TK-03).

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `accounts`: agrega el inicio y cierre de sesión, la plantilla común, los 2 grupos con sus permisos, un solo grupo por usuario, la gestión de usuarios solo por el Administrador, el bloqueo por intentos fallidos y la expiración de la sesión.

## Impact

- **Archivos nuevos:**
  - `app/templates/base.html`, `app/templates/registration/login.html` y `bloqueado.html`;
  - `app/static/css/vendor/bootstrap.min.css` y `app/static/js/vendor/bootstrap.bundle.min.js`;
  - `app/apps/accounts/admin.py` y `forms.py`, y las migraciones `0003_grupos` y `0004_un_grupo`;
  - los tests `test_grupos.py`, `test_login.py` y `test_admin_usuarios.py`.
- **Archivos modificados:** `app/config/settings/base.py`, `app/config/urls.py` y `app/requirements.txt` (`django-axes`).
- **Puntos de integración:**
  - punto 5: TK-01 asigna los permisos de inventario sobre los grupos que crea este ticket;
  - TK-03 hereda `base.html`, cambia `LOGIN_REDIRECT_URL` y la raíz, y modifica `test_login.py`;
  - HB-09 registra el catálogo y los residentes en el panel para los 2 grupos.
- **ADR aplicables:**
  - [ADR-0002](../../../docs/adr/0002-renderizado-en-servidor-con-htmx.md): renderizado en el servidor, sin JavaScript en línea;
  - [ADR-0009](../../../docs/adr/0009-bajas-logicas-y-on-delete-restrict.md): la baja del usuario es `is_active = False`;
  - [ADR-0020](../../../docs/adr/0020-habilitadores-en-panel-admin.md): habilitadores en `/admin/`;
  - [ADR-0021](../../../docs/adr/0021-autorizacion-por-grupos-en-el-servidor.md): autorización por grupos en el servidor;
  - [ADR-0022](../../../docs/adr/0022-autenticacion-sesion-argon2-axes.md): sesión, Argon2 y `django-axes`;
  - [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md): pruebas contra PostgreSQL real;
  - [ADR-0024](../../../docs/adr/0024-calidad-estatica-con-verificador-unico.md): djLint en el verificador único.
