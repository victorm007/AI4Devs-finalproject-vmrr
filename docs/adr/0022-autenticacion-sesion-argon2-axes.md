# ADR-0022 · Autenticación: usuario propio, Argon2, sesiones con expiración y django-axes

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Actualización:** 2026-11-23, HB-08: versión fija de `django-axes` (9.1.0) y bloqueo por usuario, sin cambiar la decisión
- **Capabilities afectadas:** `accounts`, `api`
- **Fuentes:** `readme.md` §2.2, §2.4.1, §2.5, §3.2 (D1 y antipatrones), §3.4, §4.2 y §6 (HB-03 y HB-08)

## Contexto

El sistema guarda datos personales de los Residentes (LFPDPPP) y lo usan pocas personas desde la red del hogar, en una PC o un celular que pueden quedarse con la sesión abierta. Las contraseñas no pueden quedar legibles, y hay que frenar los intentos de fuerza bruta.

## Decisión

- **Modelo de usuario propio** (`usuario`, sobre `AbstractUser`), definido desde el inicio del proyecto, como recomienda Django (HB-03).
- **Contraseñas con hash Argon2** (`django[argon2]`) y con los validadores de longitud y complejidad de Django. Las del dataset mock vienen en PBKDF2, porque PostgreSQL no puede calcular Argon2, y Django las rehace con Argon2 en el primer inicio de sesión.
- **Sesión de Django**, también para la API del MVP (sin tokens):
  - Expira tras 30 minutos de inactividad (`SESSION_COOKIE_AGE=1800`, `SESSION_SAVE_EVERY_REQUEST=True`) y al cerrar el navegador.
  - Cookies `HttpOnly` y `SameSite=Lax`, y en producción también `Secure`.
- **HTTPS en todos los entornos.** En producción: `SECURE_SSL_REDIRECT=True`, HSTS, `SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE`.
- **Fuerza bruta:** `django-axes` **9.1.0** (versión fija en `requirements.txt`) bloquea la cuenta 15 minutos tras 5 intentos fallidos y responde `429`. El bloqueo es por usuario y no por IP: detrás de nginx, sin el extra `ipware`, todos llegarían con la IP del proxy, así que se silencia el aviso `axes.W006`.
- **Página de inicio de sesión propia** en `/accounts/login/`, y cierre de sesión por `POST` (HB-08).

## Alternativas consideradas

- **Contraseñas legibles:** se descartaron por exponer las credenciales (antipatrón, §3.2); solo se guarda el hash.
- **Endpoints de inicio de sesión por API en el MVP:** quedan para la V2 (`GET /auth/csrf`, `POST /auth/login`, `POST /auth/logout` y `GET /auth/me`, §4.2).

## Consecuencias

**Positivas:**
- Un dispositivo olvidado con la sesión abierta queda protegido a los 30 minutos.
- La API del MVP no necesita su propio mecanismo de autenticación.

**Negativas:**
- `PBKDF2PasswordHasher` debe seguir en `PASSWORD_HASHERS`, después de Argon2, mientras existan contraseñas del mock sin rehacer (§3.4).
