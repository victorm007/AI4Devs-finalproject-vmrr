# Tasks

## 1. Tests en rojo

- [x] 1.1 En `app/apps/entidades/tests/test_services.py`: reemplazar el `monkeypatch` del reintento por la restricción `ck_prueba_falla ... NOT VALID`; agregar el test del Residente con Entidad asignada, el de la falla al confirmar (`transaction=True`, `serialized_rollback=True`, `uq_prueba_apellido ... DEFERRABLE INITIALLY DEFERRED`) y la fecha de ingreso como texto en el test del objeto intacto. En `app/config/tests/test_configuracion.py`: `HOGAR_NOMBRE` de 151 (local y prod) y de 150 caracteres. Verificar con `dtest <archivo> -q` cada archivo por separado el rojo de cada test nuevo, y que el reintento y la falla al confirmar nacen en verde (regresión).
- [x] 1.2 Comprobar por mutación que la falla al confirmar sostiene la restauración de `_state`: quitar temporalmente esa línea de `services.py`, ver el test en rojo y deshacer el cambio (`git diff -- app/apps/entidades/services.py` vacío).
- [x] 1.3 Congelar los 2 archivos de tests con `sha256sum` en `<tmp>/HB-06-ajustes-2/congelados.sha256`.

## 2. Servicio

- [x] 2.1 `registrar_residente()`: comprobación con `_state.adding` y `pk`, y valores originales de todos los campos concretos; verificar con `dtest apps/entidades -q`.

## 3. Configuración

- [x] 3.1 `base.py` (largo máximo 150) y `prod.py` (mensaje que menciona que `web` no arranca); verificar con `dtest config/tests -q`.

## 4. Documentación

- [x] 4.1 `readme.md` 2.4 (aviso de espacios hasta TK-01) y su anexo en `02-arquitectura.md`; paso 2 de la guía de HB-06 con el código actual; paso 1 de la guía de TK-01 conservando el aviso de "obligatoria en producción"; Prompt y Respuesta en `06-tickets-trabajo.md`. Verificar con `git diff --stat`.

## 5. Cierre

- [x] 5.1 Verde completo: `sha256sum -c` de la huella, `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`, `dtest -m lento`, `python scripts/verificar.py` y `dj makemigrations --check --dry-run`; el Hogar sigue con `id = 1` y la base local con 0 Residentes.

## Workflow follow-up

- Commit y push solo cuando el usuario los pida, con un comentario en el PR #2 que marque como resueltos los hallazgos de la segunda revisión.
- Ejecutar `/openspec-verify-change hb-06-ajustes-revision-2` y `/openspec-archive-change hb-06-ajustes-revision-2`, sincronizando las specs.
