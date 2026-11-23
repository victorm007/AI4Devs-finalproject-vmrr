# Design

## Context

Comprobado por nginx el 2026-11-23: tras 5 fallos, un 6.º intento responde `429`, sube `failures_since_start` de 5 a 6 y renueva `attempt_time`. Como `AXES_COOLOFF_TIME` se cuenta desde el último intento, cada intento reinicia la espera. También se comprobó que `AXES_DISABLE_ACCESS_LOG` es `False`: `axes_accesslog` registra cada login, también los correctos, y se limpia con `axes_reset_logs`, no con `axes_reset`. La motivación está en `proposal.md`, y el comportamiento, en `specs/accounts/spec.md`.

## Goals / Non-Goals

**Goals:**

- Que los tests de sesión y de bloqueo fallen si cambia el comportamiento, no solo la configuración.
- Que el mensaje y la documentación digan lo que de verdad hace `axes`.

**Non-Goals:**

- Cambiar el comportamiento de `axes` o desactivar su registro de accesos.

## Decisions

### 1. Tests de la sesión real

- **Duración guardada:** tras un login por `POST`, la `expire_date` de la fila de `django_session` queda a 1800 ± 60 segundos de ahora.
- **Renovación:** se adelanta esa `expire_date` (por ejemplo, a ahora + 100 s), se abre `/admin/` y vuelve a quedar a 1800 ± 60 s. Eso prueba `SESSION_SAVE_EVERY_REQUEST`.
- **Cierre del navegador:** la cookie `sessionid` de la respuesta del login no tiene `max-age` ni `expires`. Eso prueba `SESSION_EXPIRE_AT_BROWSER_CLOSE`.

Sustituyen al test actual "la sesión dura 30 minutos". El de configuración se conserva.

### 2. Bordes del bloqueo

- **14 minutos:** `attempt_time` se pasa a hace 14 minutos y el login con la contraseña correcta sigue en `429`.
- **Reinicio:** con `attempt_time` a hace 14 minutos, un intento más responde `429` y deja `attempt_time` a menos de 1 minuto de ahora.

Los 2 nacen en verde: documentan el comportamiento actual de `axes`.

### 3. Mensaje

`bloqueado.html`: "Demasiados intentos fallidos. La cuenta queda bloqueada 15 minutos: espera sin volver a intentarlo, porque cada intento reinicia la espera. Si olvidaste tu contraseña, pide al Administrador que te asigne una nueva." Es el único test en rojo de este cambio: el texto actual es otro.

### 4. Documentación

- **ADR-0022:** las consecuencias negativas nombran `axes_accesslog` (`axes_reset_logs`) y dicen que cada intento reinicia el bloqueo, lo que también facilita mantener bloqueada una cuenta.
- **ADR-0021, decisión, y readme** (D1, columna de `is_staff`, y nivel `ADMINISTRADOR`): el Administrador gestiona usuarios y consulta grupos, porque los grupos son de solo consulta.

Son precisiones que no cambian la decisión, y llevan la línea "Actualización" en el ADR. El anexo de `02` y el de `03` reciben el mismo cambio si contienen esas líneas.

## Risks / Trade-offs

- [El test de renovación depende del reloj] → Margen de ±60 s, el mismo criterio de los tests de `attempt_time`.
