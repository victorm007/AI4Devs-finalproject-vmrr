# Tasks

## 1. Tests en rojo

- [x] 1.1 Crear `app/apps/accounts/tests/test_grupos.py`, `test_login.py` y `test_admin_usuarios.py` (sección 3 de la guía, con un test por cada Scenario de `specs/accounts/spec.md` que se prueba con pytest, incluidos los que la guía no trae; `design.md`, decisión 7), y verificar con `dtest <archivo> -q`, uno por uno, que fallan por el motivo esperado y que solo `test_sin_sesion_el_panel_pide_login` pasa (regresión).
- [x] 1.2 Rojo: los tests anteriores siguen en verde (`dtest -m "not e2e and not lento" -q`: 107 pasan y 1 omitido en la línea base).

## 2. Bootstrap y django-axes

- [x] 2.1 Copiar `bootstrap.min.css` y `bootstrap.bundle.min.js` de `npm pack bootstrap@5.3.9` a `app/static/css/vendor/` y `app/static/js/vendor/` (decisión 1); verificar con `head -c 40` que empiezan con `@charset` o `/*!` y que la versión en la cabecera es 5.3.9.
- [x] 2.2 Agregar `django-axes==9.1.0` a `app/requirements.txt`, en orden alfabético, y reconstruir con `docker compose up -d --build web`; verificar con `docker compose exec web pip show django-axes`.

## 3. Configuración, rutas y plantillas

- [x] 3.1 En `config/settings/base.py`: `axes` en `INSTALLED_APPS`, el *middleware*, `AUTHENTICATION_BACKENDS`, los `AXES_*`, la sesión y `LOGIN_*` (paso 3 de la guía); aplicar las migraciones de `axes` con `./scripts/migrate.sh` y verificar con `dtest apps/accounts/tests/test_login.py -k "expira or bloqueo" -q`.
- [x] 3.2 `config/urls.py` y las plantillas `base.html`, `registration/login.html` y `registration/bloqueado.html` (paso 4), con el formato de djLint; verificar con `dtest apps/accounts/tests/test_login.py -k "pagina_de_login or raiz" -q` y `python scripts/verificar.py`.

## 4. Grupos y un solo grupo por usuario

- [x] 4.1 `0003_grupos.py` y `0004_un_grupo.py` (paso 5), aplicadas con `./scripts/migrate.sh`; verificar con `dtest apps/accounts/tests/test_grupos.py apps/accounts/tests/test_login.py -q` y `dpsql -c '\d usuario_groups'`.

## 5. Usuarios en el panel

- [x] 5.1 `apps/accounts/forms.py` y `apps/accounts/admin.py` (paso 6); verificar con `dtest apps/accounts -q`.
- [x] 5.2 Verde completo: `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`, sin cambios en los tests congelados (`sha256sum -c <tmp>/HB-08/congelados.sha256`).

## 6. Cierre

- [x] 6.1 Sección 5 de la guía: calidad (`ruff`, djLint, `dj check` y `dj makemigrations --check --dry-run`), los permisos por grupo con `dpsql` (15 y 5), `\d usuario_groups` y la reversión con `./scripts/migrate.sh accounts 0002` seguido de `./scripts/migrate.sh`.
- [x] 6.2 En el navegador, con `collectstatic`: `/` lleva al login, el login a 390 px sin desplazamiento horizontal y sin violaciones de CSP en la consola, el Administrador ve "Usuarios" y "Grupos" y un usuario de grupo no, y el bloqueo tras 5 intentos; desbloquear con `dj axes_reset`.
- [x] 6.3 Fijar las versiones en la documentación: Bootstrap 5.3.9 en ADR-0002 y `django-axes` 9.1.0 en ADR-0022 (como precisión, sin cambiar la decisión), y en el readme (sección 2.5 y la tabla de dependencias de TK-03), con sus anexos `02` y `06` sincronizados; verificar con `git diff --stat`.
- [x] 6.4 Anotar en la guía las diferencias (versiones de Bootstrap y `django-axes`, `npm pack`, tests añadidos y rama) y actualizar el estado del repositorio en `CLAUDE.md`; verificar con `git diff --stat`.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`). En el PR van las capturas del login en escritorio y a 390 px, y la versión fijada de `django-axes`.
- Ejecutar `/openspec-verify-change hb-08-login-grupos` y `/openspec-archive-change hb-08-login-grupos`, sincronizando las specs.
