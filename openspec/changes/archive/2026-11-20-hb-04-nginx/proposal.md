# Nginx con HTTPS local

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-04 · **Épica:** EP-01

## Why

El sistema todavía no tiene punto de entrada: `web` no publica puertos y nadie puede abrir la aplicación desde el navegador. El login (HB-08) y el panel (HB-09) deben probarse desde la semana 1 por HTTPS y con la CSP real (readme.md, secciones 2.4.1, 2.5 y 6, HB-04; ADR-0025).

## What Changes

- Se agrega el servicio `nginx` (`nginx:1.30.7-alpine`, versión fija según ADR-0025; red `frontend`, puertos 80 y 443), el único que publica puertos.
- `nginx/default.conf`:
  - redirige 80 → 443 y termina TLS 1.2+ con el certificado de `mkcert` (`nginx/certs/`, fuera del repositorio);
  - sirve `/static/` desde el volumen `static` y reenvía el resto a `web:8000` con `X-Forwarded-For` y `X-Forwarded-Proto`;
  - aplica HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options`, `Referrer-Policy` y una `Content-Security-Policy` de solo recursos propios, y oculta las que repite Django.
- Django envía la misma política CSP (`CONTENT_SECURITY_POLICY` y `config.middleware.ContentSecurityPolicyMiddleware`), para que las pruebas sin nginx la apliquen.
- Django detrás del proxy:
  - `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS` desde el entorno y *cookies* `Secure`;
  - en `prod.py` se silencian los avisos de HSTS y de redirección, porque los hace nginx.
- Se agrega `app/config/tests/test_proxy.py`, con el marcador `infra`.

**Fuera de alcance:** el certificado de Let's Encrypt del VPS (despliegue), el login propio, `base.html` y los grupos (HB-08), y los e2e con Playwright (TK-03).

## Capabilities

### New Capabilities

<!-- Ninguna: todo pertenece a infraestructura. -->

### Modified Capabilities

- `infraestructura`: se agregan el proxy inverso con HTTPS, las cabeceras de seguridad, los estáticos servidos por nginx, Django detrás del proxy y la política CSP compartida.

## Impact

- **Archivos nuevos:**
  - `nginx/default.conf` y `nginx/certs/.gitkeep`;
  - `app/config/middleware.py` y `app/config/tests/test_proxy.py`.
- **Archivos modificados:** `docker-compose.yml`, `.env.example`, `.gitignore`, `app/config/settings/base.py` y `app/config/settings/prod.py`.
- **Puntos de integración:**
  - no cambia ningún contrato de la tabla de la sección 6;
  - `docker-compose.yml` y `.env.example` siguen siendo de los tickets HB;
  - HB-08 y TK-03 dependen de este ticket: la CSP prohíbe scripts y estilos en línea, y los e2e la reciben desde Django.
- **ADR aplicables:**
  - [ADR-0002](../../../docs/adr/0002-renderizado-en-servidor-con-htmx.md): CSP sin JavaScript en línea;
  - [ADR-0025](../../../docs/adr/0025-despliegue-docker-compose-nginx-version-fija.md), que supersede a ADR-0003: `nginx`, `web` y `db`, `nginx:1.30.7-alpine` fija y `nginx` sin ruta a `db`;
  - [ADR-0004](../../../docs/adr/0004-configuracion-por-entorno-variables-db.md): configuración por entorno;
  - [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md): pruebas contra PostgreSQL real.
