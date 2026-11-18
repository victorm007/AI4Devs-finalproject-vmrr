# HB-04 · Guía paso a paso: Nginx con HTTPS local

> **Ticket:** [readme, sección 6, HB-04](../../readme.md#tickets-de-habilitación-hb-01-a-hb-09) · **Tipo:** infraestructura · **Estimación:** 2 puntos · **Rama:** `feature/HB-04-nginx`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket y en las secciones 2.4.1 y 2.5 del readme. Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.

**Resultado al terminar:** <https://localhost> responde a través de Nginx, el único contenedor que publica puertos (80 y 443). Nginx termina HTTPS con un certificado de `mkcert`, redirige 80 → 443, sirve `/static/` sin pasar por Django, aplica las cabeceras de seguridad (HSTS, CSP, `X-Frame-Options`) y reenvía el resto a `web`. Django sabe que la petición original fue HTTPS y acepta formularios desde `https://localhost`. Ya puedes entrar al panel en <https://localhost/admin/> con el Administrador de HB-03.

---

## 0. Antes de empezar

### 0.1 Lee primero (20 min)

| Qué | Dónde | Para qué |
|---|---|---|
| Contenedor `nginx` y flujos 1 a 3 | readme, sección 2.4.1 | Puertos, volúmenes, red `frontend` y cabeceras `X-Forwarded-*` |
| Cifrado en tránsito y vulnerabilidades web | readme, sección 2.5 | HTTPS, HSTS, CSP y `X-Frame-Options` |
| Instalación local | readme, sección 1.4, paso 2 | Comandos de `mkcert` |
| Django detrás de un proxy | <https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header> | Por qué `SECURE_PROXY_SSL_HEADER` solo es seguro si `web` no está expuesto |

### 0.2 Requisitos previos

- HB-03 integrado en `main`: `./scripts/migrate.sh` aplicado y un Administrador creado con `createsuperuser`.
- [`mkcert`](https://github.com/FiloSottile/mkcert) instalado (Windows: `winget install FiloSottile.mkcert` o `choco install mkcert`).
- Los puertos 80 y 443 de tu equipo libres (`netstat -ano | grep -E ":(80|443) "` sin resultados en Git Bash).

### 0.3 Crea la rama

```bash
git switch main && git pull
git switch -c feature/HB-04-nginx
set -a && . ./.env && set +a
dj() { docker compose exec web python manage.py "$@"; }
dtest() { docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" web pytest "$@"; }
```

---

## 1. Archivos que vas a crear o modificar

```
AI4Devs-finalproject-vmrr/
├── .env.example                   # MODIFICAR: CSRF_TRUSTED_ORIGINS
├── .gitignore                     # MODIFICAR: certificados locales
├── docker-compose.yml             # MODIFICAR: servicio nginx
├── nginx/
│   ├── default.conf               # NUEVO: proxy inverso, HTTPS y cabeceras de seguridad
│   └── certs/.gitkeep             # NUEVO: la carpeta se versiona; los certificados no
└── app/
    ├── config/middleware.py       # NUEVO: cabecera CSP desde Django (la misma que nginx)
    ├── config/settings/base.py    # MODIFICAR: Django detrás de nginx y política CSP
    ├── config/settings/prod.py    # MODIFICAR: ajustes que solo aplican en producción
    └── config/tests/
        ├── __init__.py            # ya existe: lo creó HB-03 (con test_conexion.py)
        └── test_proxy.py          # NUEVO
```

---

## 2. Tareas paso a paso

El orden sigue TDD (`CLAUDE.md`): primero los tests en rojo, después la implementación.

### Paso 1. Tests en rojo (≈ 20 min)

Escribe `app/config/tests/test_proxy.py` (sección 3.1) y ejecútalo **antes** de tocar la configuración:

```bash
dtest config/tests/test_proxy.py -q
# 4 failed, 2 passed, 1 skipped
```

| Tests | Antes de implementar | Por qué |
|---|---|---|
| `test_reconoce_https_por_la_cabecera_de_nginx`, `test_las_cookies_solo_viajan_por_https`, `test_acepta_formularios_desde_el_origen_de_nginx`, `test_django_envia_la_politica_csp` | Fallan | Falta la configuración del paso 5 |
| `test_sin_la_cabecera_la_peticion_no_es_https`, `test_rechaza_formularios_desde_otro_origen` | Pasan | Django ya lo hace por defecto: son tests de regresión |
| `test_la_csp_de_django_es_la_misma_que_la_de_nginx` | Se omite | El contenedor `web` no ve `nginx/default.conf`: un test omitido no es un rojo, y la comparación real ocurre en el CI |

Las pruebas con `curl` de la sección 3.2 se comprueban en el paso 6, con `nginx` ya levantado.

### Paso 2. Certificado local (≈ 10 min)

```bash
mkdir -p nginx/certs && touch nginx/certs/.gitkeep
mkcert -install                       # instala la CA local en tu equipo (una sola vez)
mkcert -cert-file nginx/certs/local.pem -key-file nginx/certs/local-key.pem localhost 127.0.0.1
```

Agrega a `.gitignore`:

```text
# Certificados locales (mkcert): nunca se versionan
nginx/certs/*
!nginx/certs/.gitkeep
```

### Paso 3. Configuración de Nginx (≈ 45 min)

`nginx/default.conf`:

```nginx
# Proxy inverso (readme, sección 2.4.1): único punto de entrada del sistema.
upstream web {
    server web:8000;   # Gunicorn, solo visible en la red interna "frontend"
}

# 80 -> 443: nunca se sirve nada por HTTP
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    http2 on;
    server_name _;

    ssl_certificate     /etc/nginx/certs/local.pem;
    ssl_certificate_key /etc/nginx/certs/local-key.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    server_tokens off;            # no revela la versión de nginx
    client_max_body_size 2m;      # el sistema no recibe archivos grandes

    # Cabeceras de seguridad (readme, sección 2.5). "always" las agrega también en errores.
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "same-origin" always;
    # Solo recursos propios: sin CDN ni scripts en línea (HTMX y Bootstrap se sirven desde /static/)
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'" always;

    # Archivos estáticos: los sirve nginx directamente, sin pasar por Django
    location /static/ {
        alias /static/;
        expires 7d;
        access_log off;
    }

    location / {
        proxy_pass http://web;
        proxy_set_header Host              $host;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        # Django también envía estas 4 cabeceras: se ocultan para que solo quede la de nginx
        proxy_hide_header X-Frame-Options;
        proxy_hide_header X-Content-Type-Options;
        proxy_hide_header Referrer-Policy;
        proxy_hide_header Content-Security-Policy;
    }
}
```

> **Cuidado con `add_header`:** si un `location` declara su propio `add_header`, deja de heredar los del `server`. Por eso `location /static/` usa `expires` (que no es `add_header`) y no declara cabeceras.

### Paso 4. Servicio `nginx` en `docker-compose.yml` (≈ 15 min)

```yaml
  nginx:
    image: nginx:stable-alpine
    restart: unless-stopped
    ports:
      - "80:80"      # solo redirige a 443
      - "443:443"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
      - static:/static:ro          # lo que escribe collectstatic en web
    depends_on: [web]
    networks: [frontend]           # sin ruta a db: no está en la red backend
```

### Paso 5. Django detrás de Nginx (≈ 30 min)

**5.1 En `app/config/settings/base.py`**, al final:

```python
# Detrás de nginx (readme, sección 2.4.1). web no publica puertos: solo nginx puede
# poner X-Forwarded-Proto, así que es seguro confiar en esa cabecera.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = lista_del_entorno("CSRF_TRUSTED_ORIGINS", "https://localhost")
# Todos los entornos usan HTTPS (mkcert en local): las cookies solo viajan cifradas
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Política CSP: la misma cadena que add_header Content-Security-Policy de nginx/default.conf
# (un test lo comprueba). Django la envía siempre para que las pruebas que no pasan por nginx
# (live_server de Playwright, TK-03) la apliquen igual que el navegador real.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
)
MIDDLEWARE += ["config.middleware.ContentSecurityPolicyMiddleware"]
```

**5.1b `app/config/middleware.py`:**

```python
"""Cabecera Content-Security-Policy desde Django (readme, sección 2.5).

Detrás de nginx, nginx oculta esta cabecera (proxy_hide_header) y envía la suya, que es
idéntica. Sin nginx (live_server de las pruebas de Playwright), es la única: así los e2e
detectan un script o un estilo en línea igual que el navegador en producción.
"""

from django.conf import settings


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        respuesta.headers.setdefault("Content-Security-Policy", settings.CONTENT_SECURITY_POLICY)
        return respuesta
```

**5.2 En `app/config/settings/prod.py`**, al final:

```python
# nginx ya redirige 80 -> 443 y envía HSTS: Django no los repite
# (dos cabeceras HSTS distintas confunden a los navegadores).
SECURE_SSL_REDIRECT = False
SILENCED_SYSTEM_CHECKS = [
    "security.W004",  # SECURE_HSTS_SECONDS: lo pone nginx
    "security.W008",  # SECURE_SSL_REDIRECT: lo hace nginx
]
```

**5.3 Agrega a `.env.example`** (y a tu `.env`):

```dotenv
# Orígenes desde los que Django acepta formularios (HTTPS de nginx). En el VPS: https://<dominio>
CSRF_TRUSTED_ORIGINS=https://localhost
```

y en el `environment` de `web` (en `docker-compose.yml`):

```yaml
      CSRF_TRUSTED_ORIGINS: ${CSRF_TRUSTED_ORIGINS:-https://localhost}
```

### Paso 6. Levanta, recopila estáticos y prueba (≈ 30 min)

```bash
docker compose up -d --build
docker compose exec nginx nginx -t                  # syntax is ok / test is successful
dj collectstatic --noinput                          # copia los estáticos del admin al volumen static
```

Abre <https://localhost/admin/> en el navegador: el candado no muestra advertencias (CA de `mkcert`) y entras con tu Administrador. Abre las herramientas del navegador (F12) → Consola: no debe haber errores de CSP.

Pon los tests en verde y comprueba que el test de regresión de CSRF detecta el fallo:

```bash
dtest config/tests/test_proxy.py -q     # 6 passed, 1 skipped

# Con el origen malicioso como confiable, el test debe fallar
docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" \
    -e CSRF_TRUSTED_ORIGINS=https://sitio-malicioso.example \
    web pytest config/tests/test_proxy.py -k rechaza -q
# 1 failed
```

---

## 3. Tests requeridos

### 3.1 `app/config/tests/test_proxy.py`

```python
"""Django detrás de nginx (readme, sección 2.4.1): HTTPS por cabecera, CSRF y CSP."""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client, RequestFactory

pytestmark = pytest.mark.infra
NGINX_CONF = Path(settings.BASE_DIR).parent / "nginx" / "default.conf"


def test_reconoce_https_por_la_cabecera_de_nginx():
    peticion = RequestFactory().get("/", HTTP_X_FORWARDED_PROTO="https")
    assert peticion.is_secure()


def test_sin_la_cabecera_la_peticion_no_es_https():
    assert not RequestFactory().get("/").is_secure()


def test_las_cookies_solo_viajan_por_https():
    assert settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE


@pytest.mark.django_db
def test_acepta_formularios_desde_el_origen_de_nginx():
    cliente = Client(enforce_csrf_checks=True)
    pagina = cliente.get("/admin/login/", secure=True)
    token = pagina.cookies["csrftoken"].value
    respuesta = cliente.post(
        "/admin/login/",
        {"username": "nadie", "password": "Prueba-no-existe", "csrfmiddlewaretoken": token},
        secure=True,
        HTTP_ORIGIN="https://localhost",
    )
    assert respuesta.status_code == 200  # credenciales inválidas, pero CSRF aceptado (no 403)


@pytest.mark.django_db
def test_rechaza_formularios_desde_otro_origen():
    cliente = Client(enforce_csrf_checks=True)
    token = cliente.get("/admin/login/", secure=True).cookies["csrftoken"].value
    respuesta = cliente.post(
        "/admin/login/",
        {"username": "nadie", "password": "Prueba-no-existe", "csrfmiddlewaretoken": token},
        secure=True,
        HTTP_ORIGIN="https://sitio-malicioso.example",
    )
    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_django_envia_la_politica_csp():
    respuesta = Client().get("/admin/login/", secure=True)
    assert respuesta.headers["Content-Security-Policy"] == settings.CONTENT_SECURITY_POLICY


def test_la_csp_de_django_es_la_misma_que_la_de_nginx():
    # En el contenedor web solo existe app/: el test corre en el CI, que tiene el repositorio completo
    if not NGINX_CONF.exists():
        pytest.skip("nginx/default.conf no está al alcance (contenedor web); lo comprueba el CI")
    politica = re.search(r'add_header Content-Security-Policy "([^"]+)"', NGINX_CONF.read_text())
    assert politica and politica.group(1) == settings.CONTENT_SECURITY_POLICY
```

```bash
dtest config/tests -q     # incluye test_conexion.py de HB-03
```

### 3.2 Pruebas con `curl` (van en el PR)

| # | Prueba | Resultado esperado |
|---|---|---|
| 1 | `http://localhost/` | `301` a `https://localhost/` |
| 2 | `https://localhost/admin/login/` | `200`, con `Strict-Transport-Security`, `X-Frame-Options: DENY`, `Content-Security-Policy` y `X-Content-Type-Options` |
| 3 | `https://localhost/static/admin/css/base.css` | `200`, servido por nginx (`Expires` presente) |
| 4 | Puertos publicados | Solo `nginx` (80 y 443); `web` y `db`, ninguno |
| 5 | Página de error | La cabecera `Server` dice `nginx`, sin versión |

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| `nginx` es el único contenedor con puertos publicados | Sección 5, paso 4 |
| `nginx` no tiene ruta a `db` (solo red `frontend`) | Sección 5, paso 5 |
| Certificados fuera del repositorio | `git status` no muestra `*.pem` |
| Cabeceras de seguridad también en errores (`always`) | `curl -skI https://localhost/no-existe` las muestra |
| Sin errores de CSP en el panel `/admin/` | Consola del navegador |
| Django y nginx envían la misma política CSP, y llega una sola cabecera | `test_la_csp_de_django_es_la_misma_que_la_de_nginx` (CI) y `curl -skI https://localhost/admin/login/ \| grep -ci content-security-policy` responde `1` |
| `nginx -t` sin errores | Paso 6 |

---

## 5. Verificación: comandos y resultado esperado

```bash
# 1. Configuración de nginx
docker compose exec nginx nginx -t

# 2. Redirección y cabeceras
curl -sI http://localhost/ | grep -iE "^(HTTP|location)"
# HTTP/1.1 301 Moved Permanently
# Location: https://localhost/
curl -skI https://localhost/admin/login/ | grep -iE "^(HTTP|strict|x-frame|content-security|x-content|server)"
# HTTP/2 200
# server: nginx
# strict-transport-security: max-age=31536000
# x-frame-options: DENY
# x-content-type-options: nosniff
# content-security-policy: default-src 'self'; ...

# 3. Estáticos servidos por nginx
curl -skI https://localhost/static/admin/css/base.css | grep -iE "^(HTTP|expires)"
# HTTP/2 200
# expires: ...

# 4. Puertos publicados
docker compose ps --format "table {{.Service}}\t{{.Ports}}"
# nginx   0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
# web     8000/tcp            (sin flecha: no publicado)
# db      5432/tcp            (sin flecha: no publicado)

# 5. nginx no alcanza a db
docker compose exec nginx sh -c 'nc -z -w 2 db 5432 && echo "alcanza db" || echo "sin ruta a db"'
# sin ruta a db

# 6. Tests y configuración de producción
dtest config/tests -q
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.prod web python manage.py check --deploy
# Sin advertencias de seguridad salvo, si tu SECRET_KEY de desarrollo es corta, security.W009
```

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] La descripción del PR incluye las cabeceras del paso 2 y la tabla de puertos del paso 4 de la sección 5.
- [ ] Captura del panel `/admin/` en <https://localhost> con el candado y la consola sin errores de CSP.

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `bind: address already in use` en el puerto 80 o 443 | Otro programa usa el puerto (IIS, Skype, otro contenedor) | Ciérralo, o en desarrollo publica `8443:443` y usa `https://localhost:8443` (agrega ese origen a `CSRF_TRUSTED_ORIGINS`) |
| `cannot load certificate "/etc/nginx/certs/local.pem"` | Falta el paso 2 o los nombres no coinciden | Paso 2, con los nombres exactos |
| `403 CSRF verification failed` al entrar al admin | `CSRF_TRUSTED_ORIGINS` no incluye el origen exacto (con puerto, si lo hay) | Paso 5.3 |
| El panel carga sin estilos | Falta `collectstatic` o el volumen `static` no está montado en nginx | Paso 6 y `docker compose exec nginx ls /static/admin` |
| `Permission denied` en `collectstatic` | El volumen `static` se creó antes con otro dueño | `docker compose exec -u root web chown -R django /app/staticfiles` |
| Bucle de redirecciones | `SECURE_SSL_REDIRECT=True` sin `X-Forwarded-Proto` | Usa la configuración de los pasos 3 y 5 tal cual |
| `502 Bad Gateway` | `web` no está corriendo o falló al arrancar | `docker compose logs web` |
| El navegador marca el certificado como no confiable | Falta `mkcert -install` en ese equipo o navegador | Paso 2 (Firefox puede pedir reiniciarlo) |
