# Design

## Context

HB-08 dejó el login, `base.html`, los 2 grupos, `UsuarioAdmin` y `GrupoAdmin` (sin alta ni borrado) y `django-axes` 9.1.0 con bloqueo por usuario. La motivación de estos ajustes está en `proposal.md` y en el comentario de la revisión adversarial del PR #2; el comportamiento, en `specs/accounts/spec.md`.

## Goals / Non-Goals

**Goals:**

- Que los tests demuestren el comportamiento que justifica las decisiones de HB-08: bloqueo por usuario, el Administrador sin grupo y el cierre de sesión desde la barra.
- Que el nombre y los permisos de los grupos solo los cambie una migración ([ADR-0021](../../../docs/adr/0021-autorizacion-por-grupos-en-el-servidor.md)).

**Non-Goals:**

- La CSP de las páginas del panel con sesión: es de HB-09.
- Un límite de tasa en nginx contra el bloqueo malicioso. Se documenta como riesgo (decisión 4).

## Decisions

### 1. Grupos de solo consulta

`GrupoAdmin.has_change_permission` devuelve `False`. El Administrador, como superusuario, sigue teniendo permiso de ver: la lista y la página del grupo responden `200` en modo de solo lectura, y un `POST` de cambio responde `403`. Se descartó `readonly_fields = ("name", "permissions")`, porque deja un formulario de cambio que no cambia nada.

### 2. Un solo aviso por casilla inválida

`GrupoUnicoMixin.clean()` agrega `MENSAJE_GRUPO` solo si `groups` no tiene ya un error. Si el valor no es válido, Django ya rechazó la opción y `cleaned_data` no tiene `groups`.

### 3. Tests nuevos

Van en los archivos de HB-08, con sus mismas convenciones.

**Nacen en rojo:**

- **Grupos que no se cambian:** hoy el `POST` de cambio de un grupo responde `302` y lo guarda.
- **Aviso único:** hoy aparecen los 2 errores en "Grupo".
- **Texto de `bloqueado.html`:** hoy no contiene el mensaje nuevo.

**Nacen en verde (regresión).** Protegen el comportamiento actual:

- **La barra de `base.html` con sesión:** se dibuja con `render_to_string` y una petición con usuario autenticado. Aún no hay pantallas propias que la usen.
- **Bloqueo:** los fallos de un usuario no bloquean a otro; el bloqueo termina cuando se pasa `attempt_time` de `AccessAttempt` a hace 16 minutos; el 5.º intento ya responde `429`.
- **Sesión:** `get_expiry_age() == 1800` y `get_expire_at_browser_close()`.
- **Formularios:** el Administrador se edita sin grupo, y el cambio activa `is_staff`.
- **El `403` con *Solo lectura*.**
- **`app_user` escribe en `axes_accessattempt`,** con `ejecutar_sql(..., rol="app_user")`.

Los tests de configuración de HB-08 (`settings`) se conservan: documentan los valores.

### 4. Mensaje y riesgo del bloqueo

`bloqueado.html`: "Demasiados intentos fallidos. La cuenta queda bloqueada 15 minutos: espera y vuelve a intentarlo. Si olvidaste tu contraseña, pide al Administrador que te asigne una nueva."

ADR-0022 suma 2 consecuencias negativas a su decisión, sin cambiarla:

- **Bloqueo malicioso:** quien conozca un nombre de usuario puede mantener bloqueada su cuenta, también la del Administrador, repitiendo 5 fallos cada 15 minutos. Se desbloquea con `python manage.py axes_reset`.
- **Datos que guarda `axes`:** el nombre escrito en el login, la IP y el *user-agent*, también cuando alguien escribe su contraseña en el campo de usuario.

### 5. Documentación

- **`[tool.djlint]`:** `extend_exclude` cambia `static/vendor` por `static/css/vendor,static/js/vendor`.
- **Guía de HB-08:** el paso 2 pasa a `npm pack bootstrap@5.3.9`.
- **`06-tickets-trabajo.md`:** registra HB-08 y estos ajustes.

## Risks / Trade-offs

- [El bloqueo malicioso sigue siendo posible] → Lo acepta ADR-0022. Para una red de hogar con pocos usuarios basta `axes_reset`. Un límite de tasa en nginx sería un ticket aparte.
- [El test que vence el bloqueo cambia `attempt_time` en la base, en lugar de esperar 15 minutos] → Es el mismo cálculo de `axes`: el intento queda fuera de la ventana de `AXES_COOLOFF_TIME`.
