# ADR-0023 · Pruebas contra PostgreSQL real, con el dataset mock y los permisos de la aplicación

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes`, `api`
- **Fuentes:** `readme.md` §2.6, §3.3 (verificación), §3.4, §4.7 y §6 (puntos de integración 7 y 8, prueba de integración, definición de hecho común y criterios de revisión); `CLAUDE.md` ("Flujo de trabajo: TDD y Mock-First", "Tickets y pruebas" y "Estrategia de pruebas estricta")

## Contexto

Buena parte de las reglas vive en PostgreSQL: restricciones, *triggers*, exclusiones, columnas generadas y privilegios. Una base simulada no las ejercitaría. Además, los criterios de aceptación de las historias están escritos sobre el dataset mock, y la aplicación corre con un usuario de privilegios mínimos.

## Decisión

- **pytest y pytest-django contra PostgreSQL 17 real.** Están prohibidos SQLite y los *mocks* de la capa de persistencia.
- **Base de pruebas aparte:** `pytest-django` crea `test_<POSTGRES_DB>` en el mismo servidor, le aplica las migraciones y la borra al terminar. Cada test corre en una transacción que se revierte. Por eso `app_owner` tiene `CREATEDB` en desarrollo y CI.
- **Datos del mock, no *factories*:** el *fixture* compartido `datos_demo` carga `app/fixtures/mock/`. No se usan datos aleatorios (como Faker) salvo para un caso límite aislado.
- **Permisos reales:** las pruebas de los servicios de inventario corren como `app_user`. En los tests normales, con `como_app_user` (`SET LOCAL ROLE app_user`). En los de concurrencia (`transaction=True`, con hilos), cada hilo hace `SET ROLE app_user` al abrir su conexión.
- **Concurrencia obligatoria** en `services.py`: tests con hilos contra condiciones de carrera y *deadlocks*.
- **Planes de ejecución:** las consultas complejas tienen tests con `EXPLAIN` que comprueban el índice usado. Se marcan `lento` y corren en el CI nocturno.
- **Integración:** el flujo crítico se prueba de punta a punta (vista → servicio → base de datos), y al final la vista `v_conciliacion_existencia` debe estar vacía.
- **Contratos de la API:** las respuestas se validan contra `docs/api/openapi.yaml` con `jsonschema`.
- **Extremo a extremo** con Playwright (Python).
- **Cobertura:** el CI exige al menos 80 % en `apps/`, y cada ticket fija su propio umbral (por ejemplo, 90 % en `services.py` en TK-02).
- **TDD** siempre que la tarea lo permita: primero los tests, a partir de los criterios de aceptación, y se comprueba que fallen.
- `conftest.py` y `pruebas.py` nacen en HB-03. Los *fixtures* compartidos y el helper `saldo` los agrega TK-01, y los demás tickets los usan sin modificarlos.

## Alternativas consideradas

- ***Factories* de datos:** se descartaron porque los criterios de aceptación están escritos con los datos del mock (`CLAUDE.md`).
- **SQLite o una base simulada:** prohibidos, porque no ejecutarían las reglas que viven en PostgreSQL (`CLAUDE.md`).

## Consecuencias

**Positivas:**
- Un test que pasa demuestra que la aplicación funciona con los permisos que tendrá en producción.
- La base de desarrollo nunca se toca: en CI, el servidor de PostgreSQL es un contenedor nuevo en cada *job* (§2.6).

**Negativas:**
- Las pruebas necesitan un PostgreSQL disponible, en local o en CI.
- Antes de TK-01 no existe el mock completo: los tests de HB-05 a HB-09 crean sus propios datos mínimos.
