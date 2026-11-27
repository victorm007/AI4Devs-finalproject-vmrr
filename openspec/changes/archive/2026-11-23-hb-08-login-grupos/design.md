# Design

## Context

HB-03 dejó `Usuario` (`AbstractUser`, tabla `usuario` y puente `usuario_groups`), Argon2 y los validadores de contraseña. HB-04 dejó nginx con HTTPS y la misma CSP en Django (`script-src 'self'; style-src 'self'; img-src 'self' data:`), y HB-05 y HB-06 dejaron los modelos del catálogo y de residentes. No hay plantillas, archivos estáticos, rutas propias ni `admin.py`. La motivación está en `proposal.md`, y el comportamiento, en `specs/accounts/spec.md`.

El código de la guía (`docs/tickets/HB-08-login-grupos.md`) nunca se ha ejecutado. Al leerlo contra el readme, los registros de paquetes y el entorno:

- **Bootstrap:** la guía descarga `bootstrap@5.3.3` de jsDelivr. La última 5.3 estable es **5.3.9** (`npm view bootstrap`), y el readme pide "Bootstrap 5.3".
- **`django-axes`:** la guía no fija la versión. La última estable es **9.1.0** (2026-11-22), que exige Django ≥ 5.2 y Python ≥ 3.11. La 9.0.0 (2026-10-30) trae los cambios que rompen compatibilidad, y ninguno afecta a la configuración de la guía.
- La guía indica la rama `feature/HB-08-login-grupos`; `CLAUDE.md` manda seguir en `feature/entrega-2-vmrr`.
- Faltan tests para parte de los criterios: los permisos exactos de cada grupo, la definición de `uq_usuario_un_grupo`, el formulario de cambio, la lista de grupos con `403`, el borrado de grupos, la cabecera CSP y la configuración del bloqueo (decisión 7).

## Goals / Non-Goals

**Goals:**

- Que la autorización del panel quede en el servidor: permisos de grupo, `403` y sin borrado.
- Que `base.html` cumpla la CSP desde el principio, porque todas las pantallas la heredan.

**Non-Goals:**

- Los modelos en el panel (HB-09), los permisos de inventario (TK-01) y la pantalla de inicio definitiva (TK-03).

## Decisions

### 1. Bootstrap 5.3.9 servido desde `static/`, obtenido con `npm pack` ([ADR-0002](../../../docs/adr/0002-renderizado-en-servidor-con-htmx.md))

`npm pack bootstrap@5.3.9` en un directorio temporal descarga el paquete y npm comprueba su `integrity`. De él se copian `dist/css/bootstrap.min.css` y `dist/js/bootstrap.bundle.min.js` a `app/static/css/vendor/` y `app/static/js/vendor/`, sin modificarlos. La guía usaba `curl` desde jsDelivr, sin comprobación de integridad. Los archivos de `static/vendor` no se reformatean, y djLint ya los excluye. Las referencias `sourceMappingURL` sin su `.map` no afectan: el almacenamiento de estáticos es el de por defecto, sin manifiesto.

### 2. `django-axes` 9.1.0, bloqueo por usuario ([ADR-0022](../../../docs/adr/0022-autenticacion-sesion-argon2-axes.md))

Configuración de la guía:

- `AxesStandaloneBackend` va primero en `AUTHENTICATION_BACKENDS`, y `AxesMiddleware`, al final;
- `AXES_FAILURE_LIMIT = 5`, `AXES_COOLOFF_TIME = timedelta(minutes=15)`, `AXES_LOCKOUT_PARAMETERS = ["username"]`, `AXES_RESET_ON_SUCCESS = True` y `AXES_LOCKOUT_TEMPLATE = "registration/bloqueado.html"`;
- `429`, que es el código por defecto.

No se instala el extra `ipware`: el bloqueo es por usuario, así que la IP (detrás de nginx, la del proxy) solo queda en el registro. Las tablas de `axes` las crea `app_owner` y heredan los privilegios por defecto de `app_user` (`accounts.0002_privilegios`). Los tests usan `force_login` o un `POST` al login, nunca `client.login()`, que no pasa la petición al *backend* de `axes`.

**Decidido durante la implementación (aprobado por el usuario):**

- `axes.W006`, que pide agregar `ip_address`, se silencia en `base.py` y en `prod.py` con su motivo.
- `AxesMiddleware` va después del de CSP, para que el `429` también lleve la política.
- `groups.add()` inserta con `ON CONFLICT DO NOTHING`, así que `uq_usuario_un_grupo` impide el segundo grupo sin lanzar error. El test de la restricción inserta directamente en la tabla puente.

**Opción descartada:** 9.0.0, para tener una versión con más tiempo publicada. Se queda 9.1.0, la última estable, que solo agrega correcciones sobre la 9.0.0.

### 3. Sesión, rutas y redirecciones

- **Sesión:** `SESSION_COOKIE_AGE = 1800`, `SESSION_SAVE_EVERY_REQUEST = True` y `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`.
- **Redirecciones:** `LOGIN_URL = "login"`, `LOGIN_REDIRECT_URL = "admin:index"` (TK-03 lo cambia) y `LOGOUT_REDIRECT_URL = "login"`.
- **Rutas:** `/` es un `RedirectView` a `login`; `/accounts/login/` es un `LoginView` con `redirect_authenticated_user=True`, y `/accounts/logout/` es un `LogoutView`, que en Django 5 solo acepta `POST`.

### 4. Los 2 grupos en una migración de datos ([ADR-0021](../../../docs/adr/0021-autorizacion-por-grupos-en-el-servidor.md))

`0003_grupos` es un `RunPython`. Primero fuerza `create_permissions` sobre los modelos del estado de la migración, porque Django crea los permisos al final de `migrate`. Después asigna a *Solo lectura* `view_*`, y a *Lectura y escritura* `view_*`, `add_*` y `change_*`, de `presentacion`, `principioactivo`, `medicamento`, `medicamentoprincipioactivo` y `residente`. La inversa borra los 2 grupos. `Entidad` no recibe permisos: el Hogar no se edita y los residentes se dan de alta con `registrar_residente()`. `Pauta` tampoco, porque no está en el panel.

### 5. `uq_usuario_un_grupo` en `RunSQL`

`0004_un_grupo`: `ALTER TABLE usuario_groups ADD CONSTRAINT uq_usuario_un_grupo UNIQUE (usuario_id)`, con su inversa. Django no declara restricciones sobre la tabla puente que genera. El "al menos uno" lo valida el formulario.

### 6. Usuarios y grupos en el panel ([ADR-0020](../../../docs/adr/0020-habilitadores-en-panel-admin.md))

- **Formularios:** `GrupoUnicoMixin` lo usan `UsuarioCreationForm` (sobre `AdminUserCreationForm`, de Django 5.1 en adelante) y `UsuarioChangeForm`. A quien no es superusuario le exige un solo grupo, con el mensaje literal, y le activa `is_staff`.
- **`UsuarioAdmin`:** grupos con casillas, `prefetch_related("groups")` en la lista y `has_delete_permission = False`.
- **`GrupoAdmin`:** sustituye al de Django, con `has_add_permission` y `has_delete_permission` en `False`.

Los 2 grupos no tienen permisos sobre `usuario` ni `group`, así que Django responde `403` a quien no es superusuario.

### 7. Tests ([ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md))

Los nombres son los de la guía: `test_grupos.py` (base de datos, sin marcador), `test_login.py` y `test_admin_usuarios.py` (`http`). Se conserva `test_login.py` porque la guía de TK-03 lo modifica con ese nombre. Además de los tests de la guía, se agregan:

- los permisos exactos de cada grupo (igualdad de conjuntos, no inclusión);
- la definición de `uq_usuario_un_grupo` en `pg_constraint`;
- el formulario de cambio con 2 grupos;
- la lista de grupos con `403` para un usuario de grupo;
- el borrado de un grupo con `403`;
- la cabecera CSP y la ausencia de `style=` en el login;
- la configuración de `django-axes` (límite, duración y parámetro).

**Comprobaciones manuales, sin pytest:**

- **Desplazamiento a 390 px y consola sin violaciones de CSP:** no hay Playwright hasta TK-03. Se comprueban en el navegador.
- **Capturas para el PR:** las toma el usuario, porque son de la definición de hecho.
- **djLint:** lo comprueba `python scripts/verificar.py`, el mismo verificador del *job* `lint`.
- **Reversión de las migraciones:** se comprueba con `./scripts/migrate.sh accounts 0002` y la vuelta.

## Risks / Trade-offs

- [`django-axes` 9.1.0 tiene un día publicado] → Solo agrega correcciones sobre la 9.0.0, que es compatible. Si diera problemas, se fija 9.0.0 sin cambiar la configuración.
- [`create_permissions` en una migración depende de un detalle interno: `models_module`] → Es el patrón que usará TK-01 (paso 7b de su guía). Los tests de permisos exactos lo detectan si cambia.
- [El login del panel (`/admin/login/`) sigue existiendo] → Pasa por el mismo `AuthenticationForm` y por `axes`. Lo usa `test_sin_sesion_el_panel_pide_login`.

## Migration Plan

`docker compose up -d --build web` instala `django-axes`, y `./scripts/migrate.sh` aplica `axes`, `accounts.0003_grupos` y `accounts.0004_un_grupo`. Reversión de este ticket: `./scripts/migrate.sh accounts 0002`. Las tablas de `axes` se quitan con `migrate axes zero`, si se retira el paquete.
