# Tasks

## 1. Tests en rojo

- [x] 1.1 Agregar a `app/apps/entidades/tests/test_modelos.py` los tests de la Entidad sin su Residente, de las consultas con `select_related` y de `nombre_completo` con espacios; agregar a `test_services.py` los de nombres normalizados, nombre de solo espacios, mensaje de `ck_residente_nombres`, objeto intacto tras un error de validación y reintento tras un fallo de escritura (`monkeypatch`); aplicar los *nits* 9, 10 y 11; crear `app/config/tests/test_configuracion.py` (`infra`) con producción sin y con `HOGAR_NOMBRE` y desarrollo sin ella. Verificar con `dtest <archivo> -q` cada archivo por separado que cada test nuevo falla por su motivo y que los existentes siguen en verde.
- [x] 1.2 Congelar los 3 archivos de tests con `sha256sum` en `<tmp>/HB-06-ajustes/congelados.sha256`.

## 2. Modelos y migración

- [x] 2.1 Hacer que `Entidad.activa` y `Entidad.__str__` capturen `Residente.DoesNotExist`, documentar `select_related("residente")`, quitar espacios en `nombre_completo` y agregar `violation_error_message` a `ck_residente_nombres`; generar `0004` con `dj makemigrations entidades` y verificar con `dj sqlmigrate entidades 0004` que no cambia la base y con `dtest apps/entidades/tests/test_modelos.py -q` que pasan sus tests.

## 3. Servicio

- [x] 3.1 Reescribir `registrar_residente()` (`_state.adding`, normalización, restauración ante cualquier excepción); verificar con `dtest apps/entidades -q`.

## 4. HOGAR_NOMBRE en producción

- [x] 4.1 `base.py` (variable vacía = valor por defecto), `prod.py` (`ImproperlyConfigured` sin la variable) y `docker-compose.yml` (`${HOGAR_NOMBRE:-}`); recrear `web` con `docker compose up -d web` y verificar con `dtest config/tests -q` y `docker compose config | grep HOGAR_NOMBRE` (vacía con el `.env` actual).
- [x] 4.2 Actualizar `.env.example`, la guía de HB-04 (`-e HOGAR_NOMBRE=...` en `check --deploy`) y verificar con `docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.prod -e HOGAR_NOMBRE="Hogar de prueba" web python manage.py check --deploy` que no hay advertencias.

## 5. Documentación

- [x] 5.1 Corregir la sección 7 de la guía de HB-06 y anotar los ajustes en la guía; actualizar `readme.md` (2.4, primera instalación, y el punto de integración 11 de la sección 6), con su anexo en `02-arquitectura.md` y `06-tickets-trabajo.md`; verificar con `git diff --stat`.

## 6. Cierre

- [x] 6.1 Verde completo: `sha256sum -c` de la huella, `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`, `python scripts/verificar.py` y `dj makemigrations --check --dry-run`.
- [x] 6.2 Reversión: `./scripts/migrate.sh entidades 0003` y `./scripts/migrate.sh`, con el Hogar intacto (`id = 1`).

## Workflow follow-up

- Commit y push solo cuando el usuario los pida (`/commit` y `/push`), y comentario en el PR #2 con la tabla de la revisión actualizada.
- Ejecutar `/openspec-verify-change hb-06-ajustes-revision` y `/openspec-archive-change hb-06-ajustes-revision`, sincronizando las specs.
