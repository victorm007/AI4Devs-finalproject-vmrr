# ADR-0006 · Dos usuarios de base de datos con privilegios mínimos

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `accounts`, `inventario`, `conteos`
- **Fuentes:** `readme.md` §2.4, §2.5, §2.6, §3.1, §3.4 y §6 (TK-01 punto 5, decisiones de diseño de la habilitación, HB-01, HB-03 y punto de integración 4); `CLAUDE.md` ("Dos usuarios de BD")

## Contexto

La inmutabilidad de los Movimientos solo es real si la aplicación **no** se conecta como dueña de las tablas: el dueño puede volver a darse permisos (`GRANT`) o desactivar el *trigger* (`ALTER TABLE ... DISABLE TRIGGER`). Además, si alguien roba las credenciales de la aplicación, no debe poder reescribir el historial.

## Decisión

Hay 2 usuarios de PostgreSQL, con el **mismo nombre en todos los entornos** (solo cambian las contraseñas), para que las migraciones sean deterministas:

| Usuario | Lo usa | Puede | No puede |
|---|---|---|---|
| `app_owner` | `migrate`, la carga del mock y los tests | Crear y modificar tablas; es dueño de la base y del esquema `public` | — |
| `app_user` | La aplicación (`web`) en tiempo de ejecución | `SELECT`, `INSERT`, `UPDATE` y `DELETE` en las tablas | `UPDATE`, `DELETE` ni `TRUNCATE` en `movimiento`; crear o alterar tablas; desactivar *triggers* |

- **Existen desde el primer día** (HB-01 y HB-03), no desde TK-01.
- **HB-01:** `db/init/01_roles.sh` crea los 2 usuarios al crear el volumen. Es idempotente. Con `GRANT app_user TO app_owner`, los tests pueden actuar como `app_user` (`SET ROLE`). En desarrollo y CI, `app_owner` tiene `CREATEDB` para que `pytest` cree la base de tests; en producción no.
- **HB-03:** la migración `accounts/0002_privilegios` da a `app_user` los permisos sobre todas las tablas, también las futuras (`ALTER DEFAULT PRIVILEGES`). `scripts/migrate.sh` ejecuta `migrate` como `app_owner`; el contenedor `web` arranca con `DB_USER=app_user`.
- **TK-01:** en su migración, después de crear `movimiento`, ejecuta `REVOKE UPDATE, DELETE, TRUNCATE ON movimiento FROM app_user`.

## Alternativas consideradas

- **Crear los usuarios en TK-01:** se adelantaron a la habilitación para que la aplicación nunca corra como dueña de las tablas y para que el CI, que ya los espera, funcione desde el primer ticket con código (§6).

## Consecuencias

**Positivas:**
- Con las credenciales de la aplicación no se puede reescribir el historial (§2.5). Un test en CI verifica estos permisos.

**Negativas:**
- **Nunca se usa `select_for_update()` sobre `Movimiento`:** `FOR UPDATE` exige el permiso de `UPDATE`, que `app_user` no tiene, y fallaría solo en producción ([ADR-0014](0014-concurrencia-bloqueo-de-existencias.md)).
- Las migraciones nunca se ejecutan con `manage.py migrate` desde `web`, sino con `scripts/migrate.sh`.
- El mock se carga con `app_owner`, porque crea una vista temporal y reajusta secuencias (§3.4).
- Los tests que deben comportarse como la aplicación corren como `app_user` ([ADR-0023](0023-pruebas-contra-postgresql-real.md)).
