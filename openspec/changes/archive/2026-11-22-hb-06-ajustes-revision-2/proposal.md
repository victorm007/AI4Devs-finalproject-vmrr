# Ajustes de HB-06 tras la segunda revisión adversarial

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-06 · **Épica:** EP-01

## Why

La segunda revisión adversarial del PR #2 confirmó que los 11 hallazgos de la primera quedaron resueltos y no encontró bloqueantes. Dejó 5 sugerencias y 3 *nits*:

- el test del reintento usa `monkeypatch`, lo que roza ADR-0023;
- la comprobación de "ya registrado" dejó de rechazar un Residente que ya trae Entidad;
- la restauración del objeto es parcial y no tiene un test que la sostenga;
- la documentación de `HOGAR_NOMBRE` tiene 3 huecos;
- `HOGAR_NOMBRE` no limita su largo.

Son ajustes del mismo ticket, sin alcance nuevo.

## What Changes

- **Fallas reales en los tests** (sugerencias 1 y 3):
  - El reintento tras un fallo al guardar usa una restricción temporal `CHECK ... NOT VALID`, que rechaza el `INSERT` del Residente en PostgreSQL.
  - Un test nuevo cubre una falla al **confirmar**: una restricción temporal `UNIQUE ... DEFERRABLE INITIALLY DEFERRED` hace fallar el `COMMIT` después de un `save` correcto. Necesita `transaction=True` y `serialized_rollback=True`.
  - No queda ningún `monkeypatch`.
- **`registrar_residente()`** (sugerencia 2):
  - Rechaza con `ValueError` un Residente que ya trae Entidad (`pk` asignado), además del que ya está guardado (`_state.adding`).
  - Si el alta falla, restaura **todos** los campos del objeto recibido, también las fechas que `full_clean` convierte de texto a `date`.
- **`HOGAR_NOMBRE` con máximo 150 caracteres** (*nit* 6): un valor más largo da `ImproperlyConfigured` al cargar la configuración, en cualquier entorno, en lugar de un `DataError` en la migración. El mensaje de producción avisa que, sin la variable, `web` no arranca.
- **Documentación** (sugerencias 4 y 5 y *nit* 7):
  - el readme (2.4) avisa que, hasta TK-01, un `HOGAR_NOMBRE` con espacios rompe `migrate.sh`;
  - el paso 2 de la guía de HB-06 muestra el código actual;
  - la tarea de TK-01 conserva en `.env.example` el aviso de "obligatoria en producción".

**Fuera de alcance:** el *nit* 8 (los tests de configuración y las variables del subproceso), porque el test de control ya delata esa causa.

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `entidades`:
  - el alta rechaza un Residente con Entidad asignada;
  - el objeto recibido se restaura por completo, también si falla la confirmación de la transacción;
  - las fallas del reintento son reales.
- `infraestructura`: `HOGAR_NOMBRE` admite como máximo 150 caracteres.

## Impact

- **Código:** `app/apps/entidades/services.py` y `app/config/settings/base.py` y `prod.py`.
- **Tests:** `app/apps/entidades/tests/test_services.py` y `app/config/tests/test_configuracion.py`.
- **Documentación:** `readme.md` (2.4) con su anexo en `02-arquitectura.md`, las guías de HB-06 y TK-01, y el transcript `06`.
- **Puntos de integración:** no cambia ninguno.
- **ADR aplicables:**
  - [ADR-0004](../../../docs/adr/0004-configuracion-por-entorno-variables-db.md): configuración por entorno;
  - [ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md): mensajes claros antes de la última barrera;
  - [ADR-0011](../../../docs/adr/0011-capa-de-servicios-unica-via-de-escritura.md): la escritura pasa por `services.py`;
  - [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md): pruebas contra PostgreSQL real, sin mocks de la persistencia.
