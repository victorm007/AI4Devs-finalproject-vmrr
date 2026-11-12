# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado del repositorio

Proyecto final de AI4Devs: inventario de medicamentos para un hogar gerontológico (una sede, ~20 residentes, 1 a 3 usuarios). El equipo y la documentación trabajan en español.

**Todavía no hay código de la aplicación.** Solo existen la documentación, el contrato de la API, el dataset mock y el CI. `app/` contiene únicamente `fixtures/mock/`; no existen aún `manage.py`, `docker-compose.yml`, `db/init/` ni `scripts/`. Los comandos de Django y Docker de abajo son los **previstos** en el diseño, y el código de `docs/tickets/` nunca se ha ejecutado: compruébalos antes de darlos por buenos.

`readme.md` es la fuente de verdad del diseño. Sus secciones: 1 producto, 2 arquitectura, 3 modelo de datos, 4 API, 5 historias (HU-01 a HU-03), 6 tickets (TK-01 a TK-07, orden de ejecución, puntos de integración, criterios de revisión), 7 proceso de PR y criterios de *merge*.

## Comandos

Disponible hoy:

```bash
npx @redocly/cli lint docs/api/openapi.yaml   # 0 errores y 2 advertencias intencionales (sección 4)
```

Previstos, una vez exista el código (sección 1.4 del readme y `docs/tickets/`):

```bash
# Atajos, desde la raíz (Git Bash o Linux)
set -a && . ./.env && set +a
dj()    { docker compose exec web python manage.py "$@"; }     # corre como app_user
dtest() { docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" web pytest "$@"; }
dpsql() { docker compose exec db psql -U app_owner -d "$POSTGRES_DB" "$@"; }

docker compose up -d --build                  # al crear el volumen, db/init/01_roles.sh crea los 2 usuarios de BD
./scripts/migrate.sh                          # las migraciones SIEMPRE corren como app_owner, nunca con `dj migrate`

dtest -q                                      # toda la suite
dtest apps/inventario/tests/test_services.py::test_nombre   # un solo test
dtest -m "not e2e and not lento"              # lo que corre CI en cada PR
docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" \
    -e DJANGO_ALLOW_ASYNC_UNSAFE=true web pytest -m e2e e2e/ -q     # Playwright

docker compose exec web ruff check . && docker compose exec web ruff format --check .
dj makemigrations --check --dry-run

# Cargar el mock (solo en una base recién migrada, y con app_owner)
docker compose cp app/fixtures/mock/. db:/tmp/mock/
dpsql -v ON_ERROR_STOP=1 -f /tmp/mock/cargar_mock.sql
```

CI (`.github/workflows/ci.yml`): los *checks* `lint`, `tests` y `e2e` se saltan mientras no exista `app/manage.py`. Sus nombres son los que exige la protección de `main`: no los renombres sin leer la nota de la sección 7.3. `tests` exige cobertura ≥ 80 % sobre `apps/`.

## Arquitectura

Monolito Django 5.2 (Python 3.12) con PostgreSQL 17, renderizado en el servidor con plantillas, Bootstrap 5 y HTMX (sin SPA), detrás de Nginx y Gunicorn en Docker Compose. Apps previstas en `app/apps/`: `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes`, `api`.

Reglas de diseño que cruzan varias capas:

- **Una sola vía de escritura.** Solo `apps/inventario/services.py` escribe en `movimiento` y `existencia`, dentro de una transacción. Las lecturas reutilizables van en `selectors.py`; las vistas no contienen lógica.
- **Los movimientos son inmutables.** Los errores se corrigen con el movimiento inverso (`corrige_a`), una sola vez. `existencia.saldo` es un dato derivado materializado: debe ser igual a la suma de los movimientos, y la vista `v_conciliacion_existencia` lista lo que no cuadra.
- **Las entidades son un supertipo.** `entidad` (el Hogar o un residente) es la dueña de los saldos; `residente` es su subtipo. Las entradas y transferencias exigen destino activo; un residente egresado sí puede ceder o dar de baja sobrantes.
- **Dos usuarios de base de datos.** `app_owner` es dueño de las tablas y corre migraciones, mock y tests. `app_user` es el de la aplicación y no tiene `UPDATE`, `DELETE` ni `TRUNCATE` sobre `movimiento`.
  - Consecuencia: **nunca uses `select_for_update()` sobre `Movimiento`**, porque `FOR UPDATE` exige permiso de `UPDATE` y fallaría solo en producción. Sobre `Existencia` sí se usa, bloqueando siempre en orden de `entidad_id` para evitar *deadlocks*.
  - Los tests que deben comportarse como la aplicación usan `SET LOCAL ROLE app_user` (*fixture* `como_app_user`).
- **La base de datos es la última barrera, no el mensaje al usuario.** Las reglas también viven en `CHECK`, `EXCLUDE` y *triggers*, pero el servicio o el formulario las valida antes, para que el usuario nunca vea un `500` por una regla de negocio.
- **Las pantallas son la aplicación; la API no.** En el MVP la API REST son solo 3 `GET` (`/existencias`, `/medicamentos`, `/reportes/mensual`). `docs/api/openapi.yaml` (OpenAPI 3.2) marca cada operación con `x-alcance: MVP` o `V2`, y las otras 31 son diseño para después. El catálogo y los residentes se operan desde `/admin/` en el MVP (sección 5).
- **El conteo físico no ajusta existencias.** Guarda una foto del saldo en cada renglón, y la base calcula la diferencia. Cada diferencia se resuelve con un movimiento normal, para que quede la causa (mecánica en HU-03).

Detalles que rompen cosas si se olvidan:

- Django rechaza nombres de índice de más de 30 caracteres (`models.E034`); de ahí abreviaturas como `ix_movimiento_dest_med_fecha`. Tablas, restricciones e índices usan los nombres exactos de las secciones 3.1 y 3.3.
- Los índices trigram solo se usan si el ORM genera exactamente `f_unaccent(lower(campo))`.
- Las cantidades son `Decimal` (`numeric(10,2)`, en dosis), nunca `float`.

## Tickets y pruebas

Orden de ejecución: habilitadores de la semana 1 → TK-01 (BD) → TK-02 (backend) y TK-03 (frontend) → prueba de integración → backlog (TK-04 a TK-07). Las guías paso a paso están en `docs/tickets/`, y `integracion.md` tiene la prueba conjunta.

Los tests usan el dataset real del mock (`app/fixtures/mock/`, sección 3.4), no *factories*, porque los criterios de aceptación están escritos con esos datos. Los *fixtures* compartidos (`datos_demo`, `demo`, `como_app_user`) y los helpers de `pruebas.py` los crea TK-01; los demás tickets los usan sin modificarlos.

## Documentación del proceso

El entregable del curso exige mostrar los prompts usados con IA, y por eso cada fase tiene un transcript numerado en la raíz (`01-` a `07-`):

- Después de cada intercambio relevante, actualiza `readme.md`, agrega `## Prompt N — Usuario` y `## Respuesta N — Claude` al transcript de la fase, y sincroniza su `## Anexo` con la sección del readme.
- Los anexos de `04` a `07` se regeneran con un script a partir del readme (no se reescriben a mano; en `04-api.md` se conserva la sección de ejemplos con curl que sigue al anexo). Los de `02` y `03` tienen otro formato: se les aplica el mismo cambio dentro del anexo.
- Las respuestas ya registradas son historia: no se reescriben aunque una decisión cambie después.
- Los prompts marcados "no registres" no se agregan a ningún transcript.
- `prompts.md` lo edita el usuario, con su propia valoración del impacto: no lo modifiques, pero inclúyelo en los commits si tiene cambios.
- `diagramas/` guarda los PNG que el usuario genera a partir del Mermaid del readme (ver `diagramas/diagrama.md`).

## Estrategia de Pruebas Estricta (Testing Rules)
- **Entorno de Pruebas:** Todos los tests deben ser compatibles con PostgreSQL 17 real. Prohibido asumir SQLite o mocking de base de datos para la capa de persistencia.
- **Permisos Reales en Tests:** Toda prueba de los servicios de inventario debe correr utilizando el fixture compartido `como_app_user` (que ejecuta `SET LOCAL ROLE app_user` en la transacción) para validar que la app no requiere permisos elevados.
- **Concurrencia Obligatoria:** Las pruebas de `services.py` deben incluir validación explícita contra *deadlocks* y condiciones de carrera usando `TransactionTestCase` (o `transaction=True`) y `threading` (múltiples hilos apuntando a la misma base).
- **Verificación de Índices:** Si escribes consultas complejas o selectores (`buscar_existencias`), debes escribir tests que evalúen el plan de ejecución (`EXPLAIN`) para garantizar que PostgreSQL usa los índices correctos (ej. `ix_medicamento_nombre_trgm`).
- **Pruebas de Integración:** Todo flujo crítico debe incluir un test de integración que atraviese la ruta completa: Controlador/Vista -> Servicio -> Base de Datos -> Validación de vista de conciliación (`v_conciliacion_existencia`).
- **Contratos API:** Los tests de la API REST deben validar el JSON de respuesta contra el esquema `docs/api/openapi.yaml` usando `jsonschema`[cite: 1].
- **Umbrales:** Cobertura exigida en CI: ≥ 80% en `apps/` y ≥ 90% en la capa `services.py`

## Git

Haz commit y push solo cuando se pida. Los mensajes van en español (`docs: ...`, `feat(inventario): ...`) y el trabajo va en ramas `feature/*`, nunca directo en `main`. No incluyas `.idea/`. Los PR usan `.github/pull_request_template.md`.
