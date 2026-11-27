# Design

## Context

HB-03 dejó `db` y `web` corriendo sin puertos publicados. `web` está en las redes `frontend` y `backend`, y escribe en el volumen `static`. Ningún servicio atiende al navegador. La motivación está en `proposal.md`, y el comportamiento, en `specs/`.

El código de la guía se ensayó en una copia desechable, con `nginx:1.30.7-alpine` en los puertos 8080 y 8443, un certificado autofirmado y un `web` con la configuración de la guía. Resultados:

- **Tests:** el rojo y el verde coinciden con la guía (4 fallan, 2 pasan y 1 se omite; después, 6 pasan y 1 se omite). Con un origen malicioso declarado como confiable, el test de CSRF falla, como se espera.
- **nginx:** `nginx -t`, la redirección, las 5 cabeceras con una sola CSP y una sola `X-Frame-Options`, las cabeceras en el `404`, los estáticos con `Expires` y `nc: bad address 'db'` dan el resultado esperado.
- **Producción:** `check --deploy` con `config.settings.prod` responde «no issues (2 silenced)».
- **CSP del panel:** las plantillas del panel de Django 5.2 no tienen scripts ni estilos en línea.

## Goals / Non-Goals

**Goals:**

- Un solo punto de entrada por HTTPS con las cabeceras de seguridad de la sección 2.5.
- La misma CSP en producción y en las pruebas que no pasan por nginx.

**Non-Goals:**

- Let's Encrypt en el VPS y límites de tasa de peticiones.
- La CSP con *nonces* o *hashes*: no hay scripts en línea que permitir (ADR-0002).

## Decisions

### 1. Imagen `nginx:1.30.7-alpine`, con versión fija

La ficha y ADR-0003 decían `nginx:stable-alpine`, una etiqueta de canal que choca con el criterio de revisión «imágenes y dependencias con versión fija» (readme 6). Por estabilidad, recreabilidad y seguridad se fija la versión de parche que hoy publica `stable-alpine` (mismo *digest*).

Como contradice un ADR aceptado, primero se creó [ADR-0025](../../../docs/adr/0025-despliegue-docker-compose-nginx-version-fija.md), que supersede a ADR-0003, y se actualizaron `readme.md` (§2.4.1 y la ficha de HB-04), sus anexos en `02-arquitectura.md` y `06-tickets-trabajo.md`, y la guía.

*Alternativas descartadas:* `stable-alpine` (cambia sin commit) y fijar por *digest* (no se lee la versión). `postgres:17-alpine` no cambia en este ticket.

### 2. La comparación de CSP también se puede correr en local

`test_la_csp_de_django_es_la_misma_que_la_de_nginx` se omite en `dtest`, porque `web` solo monta `app/` y `NGINX_CONF` resuelve a `/nginx/default.conf`. Sin cambiar `docker-compose.yml`, el cierre lo corre con el repositorio montado:

```bash
MSYS_NO_PATHCONV=1 docker compose run --rm -v ./nginx:/nginx:ro -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" web pytest config/tests -q
```

Así queda comprobado en local y en el CI. Se agrega a la sección 5 de la guía. En Git Bash hace falta `MSYS_NO_PATHCONV=1`: sin él, `/nginx` se convierte en una ruta de Windows, el montaje no llega y el test se vuelve a omitir sin avisar (comprobado en el cierre).

### 3. HTTP/2 se comprueba con el `curl` de un contenedor

Los `curl` de Git para Windows y de Windows (Schannel) no traen HTTP/2: muestran `HTTP/1.1 200 OK` donde la guía espera `HTTP/2 200`, y `--http2` responde «the installed libcurl version does not support this». No es un fallo de nginx. El cierre usa `curlimages/curl:8.23.0`, que sí trae HTTP/2, hacia el puerto 443 del equipo:

```bash
docker run --rm curlimages/curl:8.23.0 --http2 -skI --connect-to localhost:443:host.docker.internal:443 https://localhost/admin/login/
```

La guía lo aclara.

### 4. El certificado lo genera el desarrollador

`mkcert -install` instala una CA en el almacén de Windows y pide confirmación en una ventana. Lo ejecuta el usuario; los archivos `nginx/certs/local*.pem` no entran al repositorio (`.gitignore`).

### 5. El orden de las cabeceras lo decide nginx

Django sigue enviando `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` y CSP. nginx las oculta con `proxy_hide_header` y agrega las suyas con `always`. El `location /static/` no declara `add_header`, para no perder las del `server`.

## Risks / Trade-offs

- [Las correcciones de seguridad de `nginx` no llegan solas] → Se revisan las versiones estables y se actualiza la etiqueta con un commit (ADR-0025).
- [Sin certificado, `nginx` no arranca: `cannot load certificate`] → La CA de `mkcert` ya está instalada; el certificado se genera antes de levantar `nginx`.
- [El criterio 5 necesita navegador y un Administrador] → `createsuperuser` es interactivo y la base local está vacía desde HB-03. El usuario hace esa comprobación y la captura para el PR.
- [`SESSION_COOKIE_SECURE` en todos los entornos] → Abrir `web` por HTTP sin nginx deja de mantener la sesión. Es intencional: todos los entornos usan HTTPS.
