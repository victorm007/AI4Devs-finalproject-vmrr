# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado del repositorio

Proyecto final de AI4Devs: inventario de medicamentos para un hogar gerontológico (una sede, ~20 residentes, 1 a 3 usuarios). El equipo y la documentación trabajan en español.

**Todavía no hay código de la aplicación.** Solo existen la documentación (incluidos los ADR de `docs/adr/` y la configuración de OpenSpec en `openspec/`), el contrato de la API, el dataset mock, el CI y la configuración de Claude Code (`.claude/`: hooks de secretos, de formato y de verificación, skill `/commit` y subagente `adversarial-reviewer`) y el verificador `scripts/verificar.py`. `app/` contiene únicamente `fixtures/mock/`; no existen aún `manage.py`, `docker-compose.yml`, `Makefile`, `db/init/` ni el resto de `scripts/`. Los comandos de Django y Docker de abajo son los **previstos** en el diseño, y el código de `docs/tickets/` nunca se ha ejecutado: compruébalos antes de darlos por buenos.

`readme.md` es la fuente de verdad del diseño. Sus secciones: 1 producto, 2 arquitectura, 3 modelo de datos, 4 API, 5 historias (HU-01 a HU-03), 6 tickets (TK-01 a TK-07, orden de ejecución, puntos de integración, criterios de revisión), 7 proceso de PR y criterios de *merge*.

## Stack Tecnológico Estricto

* **Backend:** Python 3.12, Django 5.2 LTS.
* **API:** Django REST Framework, con endpoints de solo lectura en el MVP. El contrato es `docs/api/openapi.yaml`, **OpenAPI 3.2 escrito a mano** (*design-first*) y fuente de verdad; drf-spectacular solo genera un esquema 3.0/3.1 para la documentación interactiva (Swagger UI), según la sección 4.7.
* **Base de Datos:** PostgreSQL 17.
* **Frontend:** Plantillas Django renderizadas en servidor (SSR), Bootstrap 5, HTMX (2.0.x). Cero frameworks SPA (CSR) -React/Vue/Angular-.
* **Testing y Linting:** pytest, pytest-django, pytest-cov, jsonschema (contratos de la API), Playwright, ruff (Python) y djLint 1.50.4 (plantillas, perfil `django`; versión congelada). No hay formateador de CSS ni de JS: solo hay los de Bootstrap y HTMX, minificados en `static/*/vendor/`, y no se reformatean.

## Flujo de Trabajo: TDD y Mock-First (OBLIGATORIO)

* **TDD (Test-Driven Development):** Siempre que la tarea lo permita, DEBES seguir el ciclo Red-Green-Refactor. Antes de escribir código de producción en `services.py`, vistas o modelos, escribe los tests correspondientes basados en los criterios de aceptación del ticket. Asegúrate de que fallen primero.
* **Mock-First / Fixture-Driven:** El proyecto cuenta con un dataset base riguroso (`app/fixtures/mock/demo.json` y `cargar_mock.sql`). NO inventes datos de prueba aleatorios usando librerías como Faker a menos que sea estrictamente necesario para un caso límite aislado. Basa el desarrollo de la UI y los tests de integración en el fixture compartido `datos_demo`.

### Reglas de Arquitectura (Monolito Modular MVT)
Monolito Django 5.2 (Python 3.12) con PostgreSQL 17, renderizado en el servidor con plantillas, Bootstrap 5 y HTMX (sin SPA), detrás de Nginx y Gunicorn en Docker Compose. Apps previstas en `app/apps/`: `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes`, `api`.

* **Lógica de Negocio Aislada:** Las reglas de inventario (entradas, transferencias, bajas) viven EXCLUSIVAMENTE en la capa de servicios (`services.py`). Prohibido poner lógica de negocio en las vistas o sobrescribir el método `save()` de los modelos.
* **Transacciones y Concurrencia:** Toda operación de escritura en inventario debe ejecutarse dentro de `transaction.atomic()`. Para evitar saldos negativos o *deadlocks*, bloquea con `select_for_update()` las filas de `Existencia` (en orden de `entidad_id`) antes de aplicar cambios. **Nunca** sobre `Movimiento`: es solo de inserción y `app_user` no tiene el permiso de `UPDATE` que `FOR UPDATE` exige.
* **Bajas Lógicas:** Los catálogos (medicamentos, motivos de baja) y las entidades (residentes) usan bajas lógicas (`activo = False` o `estado = 'EGRESADO'/'FALLECIDO'`) para preservar la integridad del historial.

Reglas de diseño que cruzan varias capas:

- **Una sola vía de escritura.** Solo `apps/inventario/services.py` escribe en `movimiento` y `existencia`, dentro de una transacción. Las lecturas reutilizables van en `selectors.py`; las vistas no contienen lógica.
- **Los movimientos son inmutables.** Los errores se corrigen con el movimiento inverso (`corrige_a`), una sola vez. `existencia.saldo` es un dato derivado materializado: debe ser igual a la suma de los movimientos, y la vista `v_conciliacion_existencia` lista lo que no cuadra.
- **Las entidades son un supertipo.** `entidad` (el Hogar o un residente) es la dueña de los saldos; `residente` es su subtipo. Las entradas y transferencias exigen destino activo; un residente egresado sí puede ceder o dar de baja sobrantes.
- **La base de datos es la última barrera, no el mensaje al usuario.** Las reglas también viven en `CHECK`, `EXCLUDE` y *triggers*, pero el servicio o el formulario las valida antes, para que el usuario nunca vea un `500` por una regla de negocio.
- **Las pantallas son la aplicación; la API no.** En el MVP la API REST son solo 3 `GET` (`/existencias`, `/medicamentos`, `/reportes/mensual`). `docs/api/openapi.yaml` marca cada operación con `x-alcance: MVP` o `V2`, y las otras 31 son diseño para después. El catálogo y los residentes se operan desde `/admin/` en el MVP (sección 5).
- **El conteo físico no ajusta existencias.** Guarda una foto del saldo en cada renglón, y la base calcula la diferencia. Cada diferencia se resuelve con un movimiento normal, para que quede la causa (mecánica en HU-03).

Detalles que rompen cosas si se olvidan:
- Django rechaza nombres de índice de más de 30 caracteres (`models.E034`); de ahí abreviaturas como `ix_movimiento_dest_med_fecha`. Tablas, restricciones e índices usan los nombres exactos de las secciones 3.1 y 3.3.
- Los índices trigram solo se usan si el ORM genera exactamente `f_unaccent(lower(campo))`.
- Las cantidades son `Decimal` (en dosis), nunca `float`.

### Decisiones de Arquitectura (ADRs)
Las decisiones estructurales e irreversibles del sistema están documentadas en `docs/adr/` (índice en `docs/adr/README.md`).
- **Cumplimiento obligatorio:** Ninguna propuesta de OpenSpec, ticket ni cambio de código puede contradecir un ADR en estado `Aceptado` (por ejemplo: privilegios de `app_user`, inmutabilidad de `movimiento`, prohibición de SPA/JS en línea, uso exacto de `f_unaccent(lower(...))`, o conteos sin autoajuste).
- **Supersedencia:** Si un requisito futuro exige cambiar una decisión aceptada, primero se crea un nuevo ADR (`docs/adr/NNNN-*.md`) que marque el anterior como `Supersedido por ADR-NNNN` y se actualiza `readme.md` antes de modificar código o specs.
- **Revisión:** El subagente `adversarial-reviewer` debe validar cada PR contra los ADRs aplicables además de las specs de OpenSpec.

### OpenSpec
Cada ticket se implementa como un cambio de OpenSpec (`openspec/changes/<id-del-ticket>-...`). `openspec/config.yaml` define sus fuentes (historias en la sección 5 del readme, tickets en la sección 6 y sus guías, arquitectura y convenciones de BD en este archivo, y los ADR) y las reglas de cada artefacto:
- **`proposal.md`:** bajo el título, la línea `**Historia:** HU-NN · **Ticket:** TK-NN · **Épica:** EP-NN`, con los IDs exactos del readme (los tickets HB no tienen historia: `— (habilitador de EP-NN)`).
- **`specs/<capability>/spec.md`:** cada criterio de aceptación (Gherkin de la historia y casillas de la ficha del ticket) se convierte en un `#### Scenario:` con viñetas `**GIVEN**` / `**WHEN**` / `**THEN**` / `**AND**`. Los requisitos usan "DEBE (MUST)", porque `openspec validate --strict` exige SHALL o MUST. Las capabilities son las 8 apps.
- **`tasks.md`:** mock-first y TDD: por grupo, primero los tests en rojo con los datos del mock, después la implementación; cada tarea, con su comando de verificación.
- Los encabezados que lee el validador y las palabras clave GIVEN/WHEN/THEN/AND/SHALL/MUST van en inglés; el resto, en español. Valida con `openspec validate <cambio> --strict`.

## Estándares y Convenciones de Base de Datos
- **Dos Usuarios de BD:** El sistema usa `app_owner` para DDL/migraciones y `app_user` para ejecución de la app (DML). Asume siempre que `app_user` NO tiene permisos de `TRUNCATE`, `UPDATE` o `DELETE` en tablas inmutables como `movimiento`, ni puede alterar tablas o apagar triggers.
  - Consecuencia: **nunca uses `select_for_update()` sobre `Movimiento`**, porque `FOR UPDATE` exige permiso de `UPDATE` y fallaría solo en producción. Sobre `Existencia` sí se usa, bloqueando siempre en orden de `entidad_id` para evitar *deadlocks*.
  - Los tests que deben comportarse como la aplicación corren como `app_user` (ver "Permisos reales en tests").
- **Delegación a PostgreSQL:** La base de datos es la barrera final. Usa `CheckConstraint`, `UniqueConstraint`, `GeneratedField` e índices trigram a nivel esquema. Las validaciones en la app son para dar mensajes claros al usuario, no sustituyen las restricciones de la BD.
- **Protección de Datos Históricos:** TODAS las claves foráneas (`ForeignKey`) deben usar `on_delete=models.PROTECT` en Django (que equivale a `ON DELETE RESTRICT` en PostgreSQL). Nunca permitas borrados en cascada en tablas transaccionales.
- **Tipos de Datos Sensibles:**
  - Para fechas con hora, usa siempre `timestamptz` (en Django, `DateTimeField` con `USE_TZ = True`). Para fechas de calendario, `date`.
  - Para cantidades y saldos en dosis (`existencia.saldo`, `movimiento.cantidad`, `detalle_conteo.*`), usa `numeric(10,2)` (`DecimalField(max_digits=10, decimal_places=2)`). La dosis por toma de una pauta es `numeric(6,2)` (sección 3.2). NUNCA uses `Float` ni `Integer` para cantidades.
- **Nomenclatura de objetos de la BD:** Define nombres explícitos (en `Meta.constraints`, `Meta.indexes` o en `RunSQL`) usando estos prefijos, como en las secciones 3.1 y 3.3:
  - `uq_`: restricción o índice único (ej. `uq_existencia`, `uq_medicamento_nombre_pres_conc`).
  - `ck_`: *check constraint* (ej. `ck_existencia_saldo`).
  - `ex_`: restricción de exclusión (ej. `ex_pauta_sin_traslape`).
  - `fk_`: clave foránea declarada a mano (ej. `fk_residente_entidad`).
  - `ix_`: índices normales, compuestos o GIN (ej. `ix_medicamento_nombre_trgm`).
  - `brin_`: índices BRIN (ej. `brin_movimiento_fecha`).
  - `fn_` / `tg_`: funciones y *triggers* (ej. `fn_movimiento_inmutable`, `tg_movimiento_inmutable`).
  - `v_`: vistas (ej. `v_conciliacion_existencia`).
- **Búsquedas de Texto:** Toda búsqueda por texto (ej. nombres) se hace sin mayúsculas ni acentos, sobre la expresión `f_unaccent(lower(campo))` (extensiones `unaccent` y `pg_trgm`). Las búsquedas parciales ("contiene") usan índices GIN con `pg_trgm`; los índices para ordenar (ej. `ix_residente_nombre`) son B-tree sobre la misma expresión. En el ORM de Django, las búsquedas deben emular exactamente esa expresión para garantizar que el planificador use el índice.

## Vocabulario de Dominio Estricto (Ubiquitous Language)
Claude, NUNCA inventes sinónimos. Usa exclusivamente estos términos en variables, modelos, URLs, respuestas JSON, comentarios, textos visibles y documentación (incluidos `readme.md` y `docs/api/openapi.yaml`):
- **Residente:** Persona que vive en el hogar. NUNCA uses "Paciente" ni "Cliente".
- **Entidad:** Supertipo que engloba tanto al "Hogar" como a los "Residentes".
- **Medicamento:** El producto farmacéutico. NUNCA uses "Droga", "Fármaco" o "Producto".
- **Existencia:** El saldo actual disponible de un medicamento. NUNCA uses "Stock" ni "Inventario" para referirte a la cantidad (el módulo `inventario` sí se llama así).
- **Movimiento:** Registro inmutable de un cambio en las existencias. Sus tipos son **Entrada, Transferencia y Baja** (`Movimiento.Tipo`). Una **corrección** no es un tipo: es el movimiento inverso que referencia al original con `corrige_a` (por ejemplo, una baja con motivo `CORRECCION`). NUNCA uses "Transacción" ni "Operación" para nombrarlo; la transacción de base de datos (`transaction.atomic()`) sí se llama así.
- **Pauta:** Indicación de dosis y frecuencia de un medicamento para un residente, con vigencia. NUNCA uses "Receta" ni "Prescripción".
- **Baja:** La acción de retirar medicamentos (por caducidad, merma, consumo) o desactivar un registro. NUNCA uses "Eliminar" ni "Delete" para reglas de negocio.

## Frontend y Vistas
* **HTML + HTMX:** Usa HTMX para interactividad sin recargar la página (`hx-get`, `hx-target`). Evita JavaScript en línea para cumplir con la CSP de Nginx.
* **Responsive:** Tarjetas `list-group` en celular, tabla en escritorio. Sin desplazamiento horizontal en 390px.
* **Autorización:** Todo acceso se valida en el backend, nunca solo ocultando botones:
  * **Pantallas:** grupos de Django (`Solo lectura` vs `Lectura y escritura`) con `LoginRequiredMixin` y `PermissionRequiredMixin`.
  * **API del MVP:** `IsAuthenticated` de DRF, porque sus 3 endpoints son de solo lectura (sección 4.2).
  * **`/admin/`:** los permisos de modelo de Django asignados a cada grupo (sección 5).

## Documentación del proceso
El entregable del curso exige mostrar los prompts usados con IA, y por eso cada fase tiene un transcript numerado en la raíz (`01-` a `07-`):

- Después de cada intercambio relevante, actualiza `readme.md`, agrega `## Prompt N — Usuario` y `## Respuesta N — Claude` al transcript de la fase, y sincroniza su `## Anexo` con la sección del readme.
- Los anexos de `04` a `07` se regeneran con un script a partir del readme (no se reescriben a mano; en `04-api.md` se conserva la sección de ejemplos con curl que sigue al anexo). Los de `02` y `03` tienen otro formato: se les aplica el mismo cambio dentro del anexo.
- Las respuestas ya registradas son historia: no se reescriben aunque una decisión cambie después.
- Los prompts marcados "no registres" no se agregan a ningún transcript.
- `prompts.md` lo edita el usuario, con su propia valoración del impacto: no lo modifiques, pero inclúyelo en los commits si tiene cambios.
- `diagramas/` guarda los PNG que el usuario genera a partir del Mermaid del readme (ver `diagramas/diagrama.md`).
- Nunca omitas los formateos de `ruff` ni `djLint`. El entorno ejecutará validaciones automáticas tras cada modificación de archivo.

## Tickets y pruebas

Orden de ejecución: tickets de habilitación HB-01 a HB-09 (semanas 1 y 2: contenedores, conexión con los 2 usuarios de BD, catálogo, residentes, pautas, login y `/admin/`) → TK-01 (BD) → TK-02 (backend) y TK-03 (frontend) → prueba de integración → backlog (TK-04 a TK-07). Las guías paso a paso están en `docs/tickets/` (`HB-*.md` y `TK-*.md`), y `integracion.md` tiene la prueba conjunta.

Los tests usan el dataset real del mock (`app/fixtures/mock/`, sección 3.4), no *factories*, porque los criterios de aceptación están escritos con esos datos. `conftest.py` y `pruebas.py` (con `ejecutar_sql`) nacen en HB-03; los *fixtures* compartidos (`datos_demo`, `demo`, `como_app_user`) y el helper `saldo` los agrega TK-01, y los demás tickets los usan sin modificarlos. Antes de TK-01 no existe el mock completo: los tests de HB-05 a HB-09 crean sus propios datos mínimos.

## Estrategia de Pruebas Estricta (Testing Rules)
- **Framework: solo pytest.** Todos los tests se escriben como funciones de pytest, con *fixtures* y marcadores (`lento`, `e2e`), sobre `pytest-django`, `pytest-cov` y `pytest-playwright`. No se usan clases `TestCase` de Django ni de `unittest`: las transacciones reales se piden con `@pytest.mark.django_db(transaction=True)` y el número de consultas se comprueba con el *fixture* `django_assert_num_queries`.
- **Entorno de Pruebas:** Todos los tests deben ser compatibles con PostgreSQL 17 real. Prohibido asumir SQLite o mocking de base de datos para la capa de persistencia. Las pruebas se ejecutan en una DB temporal/pruebas separada.
- **Permisos Reales en Tests:** Toda prueba de los servicios de inventario corre como `app_user`, para validar que la app no requiere permisos elevados:
  - En los tests normales, con el fixture compartido `como_app_user` (`SET LOCAL ROLE app_user` dentro de la transacción del test).
  - En los tests de concurrencia (`transaction=True`, con hilos), `SET LOCAL` no aplica porque no hay transacción envolvente: cada hilo hace `SET ROLE app_user` al abrir su conexión y la cierra al terminar (guía de TK-02).
- **Concurrencia Obligatoria:** Las pruebas de `services.py` deben incluir validación explícita contra *deadlocks* y condiciones de carrera usando `@pytest.mark.django_db(transaction=True)` y `threading` (múltiples hilos apuntando a la misma base).
- **Verificación de Índices:** Si escribes consultas complejas o selectores (`buscar_existencias`), debes escribir tests que evalúen el plan de ejecución (`EXPLAIN`) para garantizar que PostgreSQL usa los índices correctos (ej. `ix_medicamento_nombre_trgm`). Se marcan `lento` y corren en el CI nocturno.
- **Pruebas de Integración:** Todo flujo crítico debe incluir un test de integración que atraviese la ruta completa: Vista → Servicio → Base de Datos → Validación de la vista de conciliación (`v_conciliacion_existencia`).
- **Contratos API:** Los tests de la API REST deben validar el JSON de respuesta contra el esquema `docs/api/openapi.yaml` usando `jsonschema`.
- **Umbrales de cobertura:** el CI (*job* `tests`) exige **≥ 80 % en `apps/`**. Además, cada ticket fija su propio umbral (por ejemplo, **≥ 90 % en `services.py`** en TK-02), que verifica el autor y anota en la plantilla del PR (sección 7.3).

## Comandos
**Usa el `Makefile` de la raíz** para las tareas recurrentes; `make help` lista los comandos. **Todavía no existe:** lo crea TK-01 (guía, paso 1), sobre `docker-compose.yml` (HB-01 a HB-04) y `scripts/migrate.sh` (HB-03). Si un `make` no cubre lo que necesitas, usa los comandos directos de abajo, que son exactamente lo que ejecuta cada *target*. El CI no usa `make`.

| Tarea | `make` | Comando directo |
|---|---|---|
| Levantar / detener | `make up` / `make down` | `docker compose up -d --build` / `docker compose down` |
| Borrar la base local y recrearla | `make reset` | `docker compose down -v`, `up` y `./scripts/migrate.sh` |
| Migraciones (siempre como `app_owner`) | `make migrate` | `./scripts/migrate.sh` |
| Cargar el mock | `make mock` | ver el bloque de abajo |
| Toda la suite / un solo test | `make test` / `make test T=ruta::test` | `dtest -q` / `dtest ruta::test` |
| Lo que corre el CI en cada PR | `make test-ci` | `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80` |
| Playwright | `make e2e` | ver el bloque de abajo |
| Verificación estática (lo mismo que el *job* `lint`) | — | `python scripts/verificar.py` (`--corregir` formatea primero; usa el contenedor `web` si está corriendo) |
| Lint / formato | `make lint` / `make format` | `ruff check .`, `ruff format --check .`, `djlint . --check` y `djlint . --lint` en `web` (formatear: `ruff format .` y `djlint . --reformat`) |
| Migraciones pendientes | `make check-migrations` | `dj makemigrations --check --dry-run` |
| Contrato OpenAPI | `make openapi` | `npx @redocly/cli lint docs/api/openapi.yaml` |

Reglas del `Makefile`: las recetas van indentadas con tabulador; lee `.env` con `-include`, así que los valores no deben llevar `$`, `#` ni comillas; en Windows hay que instalar `make` (Git Bash no lo trae).

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
docker compose exec web djlint . --check && docker compose exec web djlint . --lint   # plantillas (desde HB-08)
dj makemigrations --check --dry-run

# Cargar el mock (solo en una base recién migrada, y con app_owner)
docker compose cp app/fixtures/mock/. db:/tmp/mock/
dpsql -v ON_ERROR_STOP=1 -f /tmp/mock/cargar_mock.sql
```

CI (`.github/workflows/ci.yml`): el *job* `lint` corre `python scripts/verificar.py --modo local`, el mismo verificador del hook de commits. Cada *job* se activa cuando existe lo que necesita: `lint` e `imagen` con `app/manage.py` (HB-02), `tests` con `app/conftest.py` (HB-03) y `e2e` con `app/e2e/` (TK-03); antes se saltan, y un *job* saltado cuenta como aprobado. Sus nombres son los que exige la protección de `main`: no los renombres sin leer la nota de la sección 7.3. `tests` exige cobertura ≥ 80 % sobre `apps/`.

## Git

- **Ramas:** la rama es por unidad de trabajo, no por petición. Antes de tocar código, mira en qué rama estás: si ya es una rama de trabajo —cualquiera que no sea `main`—, sigue en ella en vez de crear otra. Solo desde `main` se crea una nueva, con el prefijo `feature/` (`git checkout -b feature/<slug>`, por ejemplo `feature/TK-01-esquema-inventario`). Nunca commitear directo en `main`.
- **Commits:** solo cuando el usuario lo pida, con la skill `/commit`. Los mensajes van en español (`docs: ...`, `feat(inventario): ...`). No incluyas `.idea/`.
- **Push y PR: solo cuando el usuario lo pida, con la skill `/push`** (`/push pr` crea o actualiza el PR). La skill no fuerza, no toca `main`, se detiene si el remoto tiene commits que no están en local y corre `scripts/verificar.py` antes de subir. El PR se abre **una sola vez, al terminar la unidad de trabajo**, no al cerrar cada petición. Entonces van, en este orden:
  1. `git push` y `gh pr create`, con la plantilla `.github/pull_request_template.md` y una descripción completa de los cambios en el cuerpo del PR.
  2. El pase del subagente `adversarial-reviewer` (`.claude/agents/`) sobre ese PR, como lo último antes de dar la unidad por terminada. Tiene solo lectura (sin Bash), así que al invocarlo pásale la lista de archivos cambiados y el diff. Siempre contrasta el cambio contra los ADR aceptados que apliquen (`docs/adr/`); mientras `openspec/specs/` no tenga specs, también contra los criterios de aceptación de las secciones 5 y 6 del readme y la guía del ticket.
- Cuando abras el PR, no repitas ese resumen en el chat: la sesión se va a perder, el PR no. Responde solo con la URL del PR.

<!--
RECORDATORIO (pendiente): regla de capabilities. OpenSpec ya está inicializado (`openspec/config.yaml`) y las
capabilities son las 8 apps (estructura plana en `openspec/specs/<capability>/`). Se activa cuando exista la primera
spec. Borrador para entonces, ya traducido a Django:

- Un cambio que toque rutas, controladores, validadores o transformers de una capability se cierra en el mismo commit
  con el contrato OpenAPI y la spec de esa capability al día.
- Mapeo a Django:
  - Rutas        -> `urls.py` (URL dispatcher).
  - Controladores -> vistas: `views.py` (vistas de pantallas) y, en la API, las vistas de DRF de `apps/api/views.py`.
  - Validadores  -> `forms.py` (pantallas), `validate_<campo>()`/`validate()` de los serializers (API) y `validators.py`
                    (validadores reutilizables). Las reglas de negocio se validan además en `services.py`, y la BD es la
                    última barrera (CHECK, triggers).
  - Transformers -> `serializers.py` de DRF (API). En las pantallas no hay transformer: la vista arma el contexto con
                    `selectors.py` y la plantilla lo presenta.
- OJO al activarla: aquí el contrato `docs/api/openapi.yaml` se escribe a mano (design-first, sección 4.7), así que SÍ
  hay que actualizar ese fichero; no se genera solo. Definir también dónde vive la "spec" o el README de cada capability
  (probablemente `openspec/specs/<capability>/`, en lugar de `docs/capabilities/<nombre>/README.md`).
-->

**Datos que no salen del proyecto:** el hook `PreToolUse` `.claude/hooks/bloquear_secretos.py` (registrado en `.claude/settings.json` para Bash y PowerShell) revisa cada `git commit` (lo que está en staging y, si el comando trae `-a` o un `git add`, también los cambios sin preparar y los archivos no rastreados) y cada `git push` (los commits que aún no están en el remoto). Bloquea si entra alguna de estas cuatro cosas:
1. Un secreto: clave o token con forma reconocible (clave privada, AWS, GitHub, Anthropic, OpenAI, Slack, Google, Stripe, JWT), una asignación `PASSWORD`/`SECRET`/`TOKEN`/`API_KEY` con valor real, una URL con usuario y contraseña o un hash de contraseña.
2. Un correo cuyo dominio no sea de ejemplo (`example.com`, `example.org`, `example.net`, `.example`, `.test`, `.invalid`, `localhost`) ni un `noreply` de GitHub o Anthropic.
3. Datos personales que no sean de ejemplo: CURP, RFC, teléfono, NSS o número de tarjeta válido.
4. Un archivo `.env` o `.env.*` (salvo `.env.example`, `.sample`, `.template`, `.dist`).

Cuenta como ejemplo y no bloquea: valores con marcadores como `demo`, `ejemplo`, `cambia-esto`, `${VAR}` o `<valor>`; datos personales y hashes dentro de `app/fixtures/mock/`; cualquier línea con el comentario `secreto-ok`, y los valores de `.claude/hooks/secretos-permitidos.txt`. Los tokens con forma reconocible solo se exceptúan con `secreto-ok` o esa lista.

Cuando bloquea, **no se desactiva, no se salta y no se reescribe el comando para esquivarlo**: se sustituye el dato por uno inventado (correo en `example.com`, clave de mentira), se saca el `.env` del índice o, si de verdad es un ejemplo, se marca con `secreto-ok` o se agrega a la lista de permitidos, y se vuelve a intentar. Cada bloqueo añade una línea a `.claude/logs/secretos-bloqueados.log` con la fecha, la operación, el archivo, la línea y la categoría, nunca el valor. Ese registro es local (está en `.gitignore`) y no se commitea. Si la revisión falla, el hook bloquea por precaución. Solo cubre los comandos que ejecuta Claude, no los que el usuario corre en su terminal.

**Formato y verificación del código** (también en `.claude/settings.json`; los 2 llaman a `scripts/verificar.py`, el mismo verificador del *job* `lint` del CI):
- **`PostToolUse` (`Edit|Write`), `.claude/hooks/formatear_codigo.py`:** al escribir un `.py` o `.html` dentro de `app/`, lo formatea con ruff o djLint (`verificar.py --corregir <archivo>`). Si el formateador lo cambió, avisa para volver a leerlo antes de la siguiente edición; si quedan errores de lint que no se corrigen solos, los devuelve para arreglarlos. Sin ruff ni djLint disponibles, solo lo avisa.
- **`PreToolUse` (`Bash|PowerShell`), `.claude/hooks/verificar_antes_commit.py`:** antes de cada `git commit` que incluya código de `app/` (`.py`, `.html` o `pyproject.toml`), corre el verificador completo y niega el commit si hay errores o si no se pudo verificar (sin ruff ni djLint: falla cerrada). Los commits de solo documentación pasan sin verificar. Revisa el árbol de trabajo, así que conviene no dejar cambios sin preparar. Se corrige el código (`python scripts/verificar.py --corregir` para el formato) y se reintenta; no se salta.
- **Solo comandos git reales:** el hook de secretos y el de verificación reconocen un `git commit` o `git push` con `.claude/hooks/comandos_git.py`, que separa el comando como lo haría el shell. Reaccionan al commit o push que se va a ejecutar, también con `git -C <ruta>`, `cd <ruta> &&` o un mensaje en heredoc, pero no al texto "git commit" dentro de un `echo`, un `grep`, un comentario o el cuerpo de un heredoc.
- **Dónde busca ruff y djLint:** primero en el contenedor `web` si está corriendo, con las versiones de `requirements-dev.txt`; si no, las instaladas en el equipo. Antes de que exista `app/manage.py` (HB-02) no hay nada que verificar.
