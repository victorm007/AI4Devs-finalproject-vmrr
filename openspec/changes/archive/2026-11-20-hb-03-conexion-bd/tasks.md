# Tasks

## 1. Preparación: dependencias y arnés de pytest

- [x] 1.1 Agregar `Django[argon2]` y `psycopg[binary]` a `app/requirements.txt` con las versiones de `design.md`, y verificar con `docker compose up -d --build web` y `docker compose exec web pip show psycopg argon2-cffi`.
- [x] 1.2 Agregar a `app/pyproject.toml` la configuración de pytest y de cobertura, y crear `app/conftest.py` y `app/pruebas.py`; verificar con `dtest --markers` que aparecen `lento`, `http`, `integracion`, `infra` y `e2e`.

## 2. Tests en rojo

- [x] 2.1 Escribir `app/config/tests/test_conexion.py`, `app/apps/accounts/tests/test_privilegios.py` y `app/apps/accounts/tests/test_usuario.py` con sus `__init__.py`, y verificar con `dtest --collect-only -q` que se recolectan 12 tests.
- [x] 2.2 Rojo: ejecutar `dtest <archivo> -q` por archivo y verificar que ninguno de los 12 pasa, por el motivo esperado.

## 3. Conexión desde variables `DB_*`

- [x] 3.1 Configurar `DATABASES` en `app/config/settings/base.py` y las variables `DB_*` de `web` en `docker-compose.yml`, y verificar con `dtest config/tests -q` (4 passed).

## 4. `scripts/migrate.sh`

- [x] 4.1 Crear `scripts/migrate.sh` y verificar su sintaxis con `sh -n scripts/migrate.sh`.

## 5. App `accounts` y modelo `Usuario`

- [x] 5.1 Crear la app `accounts` y el modelo `Usuario`, configurar `INSTALLED_APPS`, `AUTH_USER_MODEL`, `PASSWORD_HASHERS` y `AUTH_PASSWORD_VALIDATORS`, generar `0001_initial` con `dj makemigrations accounts`, y verificar con `dtest apps/accounts/tests/test_usuario.py -q` (4 passed).

## 6. Privilegios de `app_user`

- [x] 6.1 Crear `accounts/0002_privilegios`, aplicar con `./scripts/migrate.sh`, y verificar con `dtest apps/accounts/tests/test_privilegios.py -q` (4 passed).
- [x] 6.2 Verde: verificar con `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80` que pasan los 12 tests y la cobertura alcanza el 80 %.

## 7. Cierre

- [x] 7.1 Comprobar la huella con `sha256sum -c <tmp>/HB-03/congelados.sha256`.
- [x] 7.2 Aplicar `git add` y `git update-index --chmod=+x` a `scripts/migrate.sh`, y verificar `100755` con `git ls-files -s`.
- [x] 7.3 Desde cero: `docker compose down -v` y `up -d --build`; verificar que `dj migrate` falla con `permission denied for schema public`, que `./scripts/migrate.sh` aplica `0001` y `0002`, y `dj showmigrations accounts`.
- [x] 7.4 Ejecutar los pasos 3 a 6 de la sección 5 de la guía (`current_user`, dueños, permisos, suite y reversión de `0002`) y verificar el resultado esperado de cada uno.
- [x] 7.5 Corregir en la guía el `%%I`, el test de longitud mínima y la comprobación de `dj migrate`, y actualizar el estado del repositorio en `CLAUDE.md`; verificar con `git diff --stat`.
- [x] 7.6 Verificar la definición de hecho: `python scripts/verificar.py` y `dj makemigrations --check --dry-run` sin errores, y `git grep -n -i password app/config` solo con `os.environ`.

## Workflow follow-up

- Subir la rama con `--force-with-lease` cuando el usuario lo pida, y comprobar en el PR #2 que el *job* `tests` pasa y que el paso `Crear app_owner y app_user` termina sin `connection refused`.
- Después de esa comprobación, ejecutar `/openspec-verify-change hb-03-conexion-bd` y `/openspec-archive-change hb-03-conexion-bd`, sincronizando las specs.
- `dj createsuperuser` lo ejecuta el usuario con sus propios datos.
