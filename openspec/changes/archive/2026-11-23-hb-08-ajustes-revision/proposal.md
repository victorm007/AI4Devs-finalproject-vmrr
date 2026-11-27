# Ajustes de HB-08 tras la revisión adversarial

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-08 · **Épica:** EP-01

## Why

La revisión adversarial de HB-08 en el PR #2 no encontró bloqueantes, pero sí 4 hallazgos importantes y 7 menores. Varios tests comprueban la configuración y no el comportamiento, por ejemplo que el bloqueo sea por usuario, la razón para silenciar `axes.W006`. Además, `GrupoAdmin` deja cambiar el nombre y los permisos de los grupos, y renombrar "Solo lectura" rompería TK-01. Conviene resolverlo antes de que HB-09, TK-01 y TK-03 dependan de estos grupos y de `base.html`.

## What Changes

- **Tests de comportamiento** (hallazgos 1, 2, 3, 7, 10 y 11):
  - la barra de `base.html` con sesión iniciada, con el cierre de sesión por `POST` y su token CSRF;
  - los 5 fallos de un usuario no bloquean a otro, el bloqueo termina a los 15 minutos y la sesión dura 1800 segundos;
  - el 5.º intento fallido ya responde `429`;
  - el Administrador se edita sin grupo, y el formulario de cambio activa `is_staff`;
  - el `403` también para *Solo lectura*;
  - `app_user` escribe en las tablas de `axes`.
- **Grupos de solo consulta** (hallazgo 5): `GrupoAdmin` tampoco permite cambiarlos. El Administrador los ve, pero su nombre y sus permisos solo los cambia una migración.
- **Un solo aviso por casilla inválida** (hallazgo 10): si el grupo elegido no es válido, el formulario muestra solo el error de Django, sin repetir "Elige exactamente un grupo".
- **Mensaje de bloqueo** (hallazgo 6): `bloqueado.html` dice que se espere 15 minutos, y ya no pide al Administrador que "restablezca" la cuenta.
- **Documentación** (hallazgos 4, 6, 9 y 11):
  - el riesgo de bloquear a cualquier usuario, incluido el Administrador, y lo que `axes` guarda (ADR-0022, consecuencias);
  - el *glob* de djLint para `static/*/vendor`;
  - el paso 2 de la guía con `npm pack` y 5.3.9;
  - el registro de HB-08 en `06-tickets-trabajo.md`.

**Fuera de alcance:** la CSP de las páginas del panel con sesión (hallazgo 8). Ya es un criterio de calidad de HB-09 ("Sin errores de CSP en el panel"), el ticket del panel.

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `accounts`: la barra con sesión cierra la sesión por `POST`; el bloqueo se cuenta por usuario y termina a los 15 minutos; el Administrador no necesita grupo y el cambio activa `is_staff`; los grupos no se cambian a mano, y una casilla inválida da un solo aviso.

## Impact

- **Archivos modificados:**
  - código: `app/apps/accounts/admin.py`, `app/apps/accounts/forms.py`, `app/templates/registration/bloqueado.html` y `app/pyproject.toml` (solo `[tool.djlint]`);
  - tests: `test_login.py`, `test_admin_usuarios.py` y `test_grupos.py`;
  - documentación: `docs/adr/0022-…`, las guías de HB-08 y HB-09, y `06-tickets-trabajo.md`.
- **Esquema:** sin cambios en la base ni migraciones.
- **Puntos de integración:** TK-01 busca los grupos por nombre, y ahora ese nombre no se puede cambiar desde el panel.
- **ADR aplicables:**
  - [ADR-0020](../../../docs/adr/0020-habilitadores-en-panel-admin.md): habilitadores en el panel;
  - [ADR-0021](../../../docs/adr/0021-autorizacion-por-grupos-en-el-servidor.md): los grupos y sus permisos los crea una migración;
  - [ADR-0022](../../../docs/adr/0022-autenticacion-sesion-argon2-axes.md): bloqueo por usuario;
  - [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md): pruebas contra PostgreSQL real.
