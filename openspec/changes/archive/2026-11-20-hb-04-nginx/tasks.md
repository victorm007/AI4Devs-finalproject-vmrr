# Tasks

## 1. Tests en rojo

- [x] 1.1 Escribir `app/config/tests/test_proxy.py` (sección 3.1 de la guía) y verificar con `dtest config/tests/test_proxy.py --collect-only -q` que se recolectan 7 tests.
- [x] 1.2 Rojo: `dtest config/tests/test_proxy.py -q` da `4 failed, 2 passed, 1 skipped`, y cada fallo es por la configuración que falta (`403`, `KeyError`, `is_secure` falso, *cookies* sin `Secure`).

## 2. Certificado local

- [x] 2.1 Crear `nginx/certs/.gitkeep` y agregar a `.gitignore` los certificados locales; verificar con `git check-ignore nginx/certs/local.pem`.
- [x] 2.2 Con la CA de `mkcert` ya instalada por el usuario, generar `nginx/certs/local.pem` y `local-key.pem` para `localhost` y `127.0.0.1`, y verificar con `git status --short nginx/` que solo aparece `.gitkeep`.

## 3. Configuración de nginx y servicio en Compose

- [x] 3.1 Crear `nginx/default.conf` y el servicio `nginx` en `docker-compose.yml`; verificar con `docker compose up -d --build` y `docker compose exec nginx nginx -t`.

## 4. Django detrás de nginx

- [x] 4.1 Agregar a `base.py` `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`, las *cookies* `Secure`, `CONTENT_SECURITY_POLICY` y el *middleware*; crear `app/config/middleware.py`; ajustar `prod.py`, `.env.example`, `.env` y el `environment` de `web`; verificar con `dtest config/tests -q` (10 passed, 1 skipped).
- [x] 4.2 Verde completo: `docker compose run --rm -v ./nginx:/nginx:ro ... web pytest config/tests -q` (11 passed) y `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`.

## 5. Cierre

- [x] 5.1 Comprobar la huella con `sha256sum -c <tmp>/HB-04/congelados.sha256`.
- [x] 5.2 `dj collectstatic --noinput` y los pasos 1 a 6 de la sección 5 de la guía, cada uno con su resultado esperado; regresión de CSRF con `CSRF_TRUSTED_ORIGINS=https://sitio-malicioso.example` (1 failed).
- [x] 5.3 Verificar el certificado de confianza con `curl -sI --ssl-no-revoke https://localhost/admin/login/` sin `-k`, y HTTP/2 con `docker run --rm curlimages/curl:8.23.0 --http2 -skI --connect-to localhost:443:host.docker.internal:443 https://localhost/admin/login/`.
- [x] 5.4 Corregir la guía (HTTP/2 con el `curl` de un contenedor y la comparación de CSP en local) y actualizar el estado del repositorio en `CLAUDE.md`; verificar con `git diff --stat`.
- [x] 5.5 Verificar la definición de hecho: `python scripts/verificar.py` y `dj makemigrations --check --dry-run` sin errores, y `docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.prod web python manage.py check --deploy` sin advertencias.

## Workflow follow-up

- El usuario crea su Administrador con `dj createsuperuser`, entra a <https://localhost/admin/> y adjunta al PR la captura con el candado y la consola sin errores de CSP (criterio 5).
- Commit y push solo cuando el usuario los pida (`/commit` y `/push`). Antes de archivar, comprobar en el PR #2 que el *job* `tests` corre `test_la_csp_de_django_es_la_misma_que_la_de_nginx` sin omitirlo.
