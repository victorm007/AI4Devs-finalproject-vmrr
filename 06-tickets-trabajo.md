# 06 - Tickets de trabajo (sesión con Claude)

> Transcripción de la sesión de definición de los tickets de trabajo con Claude, que actúa como Tech Lead experimentado.

---

## Prompt 1 — Usuario

Excelente especificación de historias de usuario. Ahora trabajemos en la sección 6 de tickets de trabajo.

Como Tech Lead experimentado, a partir de las historias de usuario que acabas de crear, crea 3 tickets de trabajo principales para el desarrollo: uno de backend, uno de frontend y uno de bases de datos.

Da todo el detalle requerido para desarrollar la tarea de inicio a fin, teniendo en cuenta las buenas prácticas al respecto.

Incluye en cada ticket:
- Descripción técnica.
- Criterios de aceptación.
- Definición de hecho (*definition of done*).
- Estimación en *story points*.

---

## Respuesta 1 — Claude

Escribí la sección 6 del `readme.md` con los 3 tickets del camino crítico del MVP: el esquema que guarda los saldos, la lógica que los mueve y la pantalla que los muestra.

| Ticket | Tipo | Historia | Puntos |
|---|---|---|---|
| TK-01 | Base de datos: esquema de existencias, movimientos y conteos, con restricciones, *triggers* e índices | HU-01, HU-02, HU-03 | 5 |
| TK-02 | Backend: servicio de movimientos (entradas, transferencias, bajas y correcciones) | HU-01 | 5 |
| TK-03 | Frontend: pantalla de consulta de existencias con filtros en vivo y diseño para celular | HU-02 | 3 |

**Cada ticket incluye:**
- Encabezado con tipo, historia, prioridad, estimación, rama y dependencias.
- Contexto: por qué existe el ticket.
- Descripción técnica con archivos, modelos, firmas de funciones y fragmentos de código.
- Lo que queda fuera de alcance.
- Criterios de aceptación verificables, con los datos del mock.
- Pruebas, definición de hecho y riesgos.

Además, al inicio de la sección hay una tabla de dependencias entre tickets y una **definición de hecho común** (lint, CI, cobertura, PR revisado, sin secretos ni datos personales en logs, documentación actualizada).

**Puntos técnicos que vale la pena revisar:**
- **TK-01:** las restricciones usan los mismos nombres del DDL de la sección 3, y cada una tiene un test que provoca su violación. Agregué la vista `v_conciliacion_existencia`, que lista los saldos que no cuadran con la suma de los movimientos.
- **TK-02:** el bloqueo de saldos crea la fila que falte sin carreras (`INSERT ... ON CONFLICT DO NOTHING`) y bloquea siempre en el mismo orden, para que dos transferencias cruzadas no provoquen un *deadlock*. Las excepciones usan los mismos `code` del contrato de la API.
- **TK-03:** la búsqueda se lanza 300 ms después de dejar de escribir, los filtros quedan en la URL, y en el celular los resultados son tarjetas en lugar de tabla. La consulta queda en un selector que reutilizará `GET /existencias`.

**Decisiones a validar:**
1. **Los 3 tickets suman 13 de los 21 puntos de las historias.** Lo que falta (pantallas de movimientos, endpoint de existencias y módulo de conteos) queda como tickets del backlog sin documentar aquí.
2. **El `REVOKE` sobre `movimiento` va en un script del despliegue** (`scripts/db_privilegios.sql`), no en una migración, porque el nombre del rol de la aplicación cambia por entorno. El *trigger* protege aunque el script no se haya ejecutado.
3. **La consulta de existencias será la página de inicio** después del login.

---

## Prompt 2 — Usuario

Para que un desarrollador junior pueda hacer el ticket sin bloqueos, detalla cada ticket con:
- Tareas específicas paso a paso.
- Archivos y estructura de código a crear.
- Tests requeridos con ejemplos.
- Criterios de calidad.
- Comandos y pasos específicos para la verificación.

---

## Respuesta 2 — Claude

Creé una guía paso a paso por ticket en `docs/tickets/` y la enlacé desde cada ticket de la sección 6. Las puse en archivos aparte porque cada una tiene entre 800 y 1,100 líneas, y así el readme sigue siendo legible.

| Guía | Contenido principal |
|---|---|
| [`TK-01-esquema-inventario.md`](docs/tickets/TK-01-esquema-inventario.md) | Usuarios `app_owner`/`app_user`, modelos completos, 5 migraciones, fixture que carga el mock en pytest, tests de cada restricción y de privilegios |
| [`TK-02-servicio-movimientos.md`](docs/tickets/TK-02-servicio-movimientos.md) | Excepciones y `services.py` completos, conceptos de bloqueo explicados, tests de reglas y de concurrencia con hilos |
| [`TK-03-pantalla-existencias.md`](docs/tickets/TK-03-pantalla-existencias.md) | Selector, formulario, vista, plantillas HTMX y *responsive*, filtro `dosis`, tests de vista y Playwright |

**Cada guía tiene la misma estructura:**
0. Antes de empezar: qué leer, requisitos previos con comandos para comprobarlos, rama y atajos de terminal.
1. Archivos a crear o modificar, en árbol.
2. Tareas paso a paso, con tiempo estimado y código de referencia.
3. Tests requeridos, con el código de los casos principales.
4. Criterios de calidad y cómo se comprueba cada uno.
5. Comandos de verificación con su resultado esperado.
6. Lista para el *pull request*.
7. "Si te bloqueas": síntomas frecuentes, causa y solución.

**Al bajar al detalle encontré 6 problemas que habrían bloqueado a un junior, y los corregí:**
1. **4 nombres de índice pasaban de 30 caracteres**, el límite de Django (error `models.E034`). Los renombré en las secciones 3.3 y 6 (por ejemplo, `ix_existencia_med_entidad`) y agregué la nota en 3.3.
2. **`SELECT ... FOR UPDATE` exige permiso de `UPDATE`**, y `app_user` no lo tiene sobre `movimiento`. La corrección se protege con `uq_movimiento_corrige`, y los tests de TK-02 corren como `app_user` para detectar este tipo de error.
3. **Los grupos no tenían permisos sobre los modelos nuevos**, porque se crearon en la semana 1. Sin una migración que los asigne, la pantalla de TK-03 respondería `403` a todos. La agregué a TK-01.
4. **El mock cargaba a los usuarios demo sin `is_staff`**, pero la sección 5 dice que entran a `/admin/`. Corregí `cargar_mock.sql`.
5. **La regla de HU-01 "solo entidades activas"** contradecía el *trigger* y el caso de uso de sobrantes: un egresado debe poder ceder o dar de baja lo que le quedó. La precisé: el **destino** debe estar activo.
6. **`floatformat` muestra `0.50`**, no `0.5`. TK-03 usa un filtro propio, `dosis`.

**Decisiones a validar:**
1. **Las guías están en `docs/tickets/`**, enlazadas desde el readme, en lugar de dentro del readme.
2. **Los tests cargan el mock real** (`cargar_mock.sql` adaptado desde Python) en lugar de *factories*: los criterios de aceptación ya están escritos con esos datos.
3. **`corrige_a` es `ForeignKey` con `UniqueConstraint`**, y no `OneToOneField`, para conservar el nombre `uq_movimiento_corrige` del DDL.
4. **El código de las guías no se ejecutó**, porque el proyecto Django todavía no existe. Revisé los nombres, los datos del mock y las versiones de Django y PostgreSQL contra la documentación del proyecto. El primer PR de cada ticket confirmará los detalles.

---

## Prompt 3 — Usuario

Ahora define (si no lo está ya):
- Tecnologías y librerías a utilizar, en el apartado de Descripción técnica.
- Dependencias entre tickets y orden de ejecución.
- Puntos de integración entre frontend, backend y base de datos.
- Criterios de revisión de código.

Asegúrate de que los 3 tickets se integren perfectamente al final.

---

## Respuesta 3 — Claude

Ya estaban la tabla de dependencias y la definición de hecho común. Agregué lo que faltaba en la sección 6 del `readme.md`:

1. **Tecnologías y librerías:** una tabla al inicio de la descripción técnica de cada ticket, con versión y uso, y qué dependencias nuevas agrega. TK-01 no agrega ninguna; TK-02 agrega `pytest-cov` (desarrollo); TK-03 agrega `django-htmx` y `pytest-playwright` (desarrollo).
2. **Orden de ejecución:** diagrama y reglas. TK-01 va primero y sin paralelo. TK-02 y TK-03 pueden ir en paralelo; con un solo desarrollador, TK-02 primero. Se integran en el orden TK-01 → TK-02 → TK-03. Incluye una tabla de los archivos que tocan varios tickets, con la regla para evitar conflictos en cada uno.
3. **Puntos de integración:** 11 contratos entre capas, con quién los provee, quién los consume, el contrato y cómo se verifica. Cada guía indica al inicio qué puntos provee y cuáles consume.
4. **Criterios de revisión de código:** tabla por ámbito (alcance, tests, integración, seguridad, datos, BD, backend, frontend, legibilidad y documentación) con su severidad, y la convención [bloqueante] / [sugerencia] / [nit].
5. **Prueba de integración final:** 5 escenarios que registran movimientos con el servicio y comprueban la pantalla, todos como `app_user` y con la conciliación vacía al terminar. El código y la verificación completa desde una instalación limpia están en `docs/tickets/integracion.md`.

**Problema de integración que encontré y corregí:** el *fixture* `demo` lo creaba TK-02, pero los tests de TK-03 lo usan. Así TK-03 no podía avanzar en paralelo con TK-02, y al integrar los 2 habrían chocado en `conftest.py`. Moví `demo`, `como_app_user` y `saldo` a TK-01, que ya creaba `datos_demo`. TK-02 ahora solo los usa.

**Decisiones a validar:**
1. **La prueba de integración la escribe quien integra el último ticket** (normalmente TK-03), y desde ahí corre en CI en cada PR.
2. **La revisión con un solo desarrollador** es una autorrevisión al día siguiente con la lista, más una revisión asistida por IA registrada en el PR.
3. **Las versiones de las dependencias nuevas** no están fijadas en el readme: cada guía indica cómo elegir la última estable y anotarla en el PR.

---

## Prompt 4 — Usuario

Confirmo las 3 decisiones.

---

## Respuesta 4 — Claude

Quedan confirmadas, y el `readme.md` ya las refleja tal cual, así que no hizo falta cambiarlo:
1. La prueba de integración la escribe quien integra el último ticket (normalmente TK-03) y desde ahí corre en CI en cada PR.
2. Con un solo desarrollador, la revisión es una autorrevisión al día siguiente con la lista de criterios, más una revisión asistida por IA registrada en el PR.
3. Las versiones de las dependencias nuevas se eligen al hacer cada ticket (la última estable) y se anotan en su PR.

---

## Prompt 5 — Usuario

Para el problema del Makefile, quiero contemplarlo porque es más legible para las personas. ¿Cómo se podría contemplar? No toques nada, solo propón los cambios.

(Después de ver la propuesta:) Sí, por favor, aplícalo. Me parece bien.

---

## Respuesta 5 — Claude

Propuse un `Makefile` en la raíz como **atajo** sobre los comandos ya documentados, no como reemplazo, y lo apliqué así:

- **Se crea en TK-01** (paso 1.8 de su guía), junto con `docker-compose.yml` y `scripts/migrate.sh`, porque envuelve esos archivos. Hoy solo funcionarían `make help` y `make openapi`.
- **17 *targets*:** `help`, `up`, `down`, `reset`, `migrate`, `superuser`, `static`, `mock`, `test` (con `T=ruta::test` para uno solo), `test-ci`, `e2e`, `lint`, `format`, `check-migrations`, `shell`, `psql` y `openapi`. `make help` los lista leyendo los comentarios `##`.
- **Solo para desarrollo local:** el CI sigue con los comandos directos, porque en GitHub Actions no hay `docker compose exec`.
- **Los comandos directos se conservan** en la documentación como "lo que ejecuta cada *target*".

**Documentación actualizada:**
- Sección 1.4: `make` en los requisitos (en Windows hay que instalarlo; Git Bash no lo trae), los pasos de instalación y de pruebas con `make` y el comando equivalente al lado, y `make reset` para volver a empezar.
- Sección 2.3: el `Makefile` en la estructura de archivos.
- TK-01: punto 10 en la descripción técnica y un criterio de aceptación (`make help` lista los 17 comandos, y `make migrate`, `make test` y `make mock` hacen lo mismo que sus comandos directos).
- `CLAUDE.md`: tabla `make` ↔ comando directo y las reglas del `Makefile`.

**Lo probé** con el `make` instalado en el equipo (GNU Make 3.81): `make help` lista los 17 comandos y `make -n test T=...` arma el comando esperado. La prueba encontró un error que corregí: la expresión regular de `help` no aceptaba dígitos, así que `e2e` no aparecía en la lista.

**Reglas que quedan documentadas:** las recetas se indentan con tabulador; el `Makefile` lee `.env` con `-include`, así que las contraseñas de desarrollo no deben llevar `$`, `#` ni comillas.

---

## Prompt 6 — Usuario

Sí, crea el (los) ticket(s) de la semana 1 con el mismo nivel de detalle. Si un ticket abarca demasiadas tareas o detalles, pártelo en más tickets, y actualiza también la planificación. Esta sería mi propuesta de tickets en ese caso:

- **Ticket 1 (Setup base):** basado en la sección de infraestructura, crea el archivo `docker-compose.yml` configurando únicamente el servicio de PostgreSQL y sus volúmenes. No toques nada más.
- **Ticket 2 (App container):** crea el `Dockerfile` para Django y agrégalo como servicio al `docker-compose.yml`, vinculándolo a la red de PostgreSQL.
- **Ticket 3 (Integración):** configura las variables de entorno en el `settings.py` de Django para que consuman el `DATABASE_URL` definido en la infraestructura.
- **Ticket 4 (Habilitación):** sección 5, habilitadores en el panel `/admin/` de Django.

Recuerda que los tickets deben llevar, para desarrollar la tarea: descripción técnica, criterios de aceptación, definición de hecho (*definition of done*) y estimación en *story points*. Para que un desarrollador junior pueda hacer el ticket sin bloqueos, detalla cada ticket con (donde aplique): tareas específicas paso a paso, archivos y estructura de código a crear, tests requeridos con ejemplos, criterios de calidad y comandos o pasos específicos para la verificación.

(Respuestas a mis 2 preguntas:) Adelantar los 2 usuarios de base de datos a la semana 1, y usar las variables `DB_*` en lugar de `DATABASE_URL`.

---

## Respuesta 6 — Claude

Antes de escribir, te pregunté por 2 choques con el diseño:
- **Usuarios de base de datos:** en cuanto existiera `app/manage.py`, el CI correría con `app_owner` y `db/init/01_roles.sh`, que solo creaba TK-01. Elegiste adelantarlos a la semana 1.
- **`DATABASE_URL`:** el CI, los atajos `dtest` y `migrate.sh` cambian solo `DB_USER` y `DB_PASSWORD` para usar `app_owner`. Elegiste mantener las variables `DB_*`.

Con esas respuestas, tu propuesta quedó en **9 tickets de habilitación (HB-01 a HB-09, 23 puntos)**. Usan el prefijo HB para no renumerar TK-01 a TK-07, que ya se citan en todo el diseño:

| Ticket | Alcance | Puntos | De tu propuesta |
|---|---|---|---|
| HB-01 | Servicio `db`, volumen `pgdata` y los 2 usuarios de BD | 2 | Ticket 1 |
| HB-02 | Proyecto Django, `Dockerfile` y servicio `web` | 3 | Ticket 2 |
| HB-03 | Conexión con `DB_*`, `web` como `app_user`, `migrate.sh`, modelo `Usuario` y privilegios | 3 | Ticket 3 |
| HB-04 | Nginx con HTTPS local | 2 | Nuevo |
| HB-05 | Catálogo (D2), extensiones, `f_unaccent` e índices trigram | 3 | Ticket 4, partido |
| HB-06 | Entidades: Hogar y residentes (D3) | 3 | Ticket 4, partido |
| HB-07 | Esquema de pautas (D6) | 2 | Nuevo |
| HB-08 | Login, `base.html`, grupos, usuarios y `django-axes` | 3 | Ticket 4, partido |
| HB-09 | Catálogo y residentes en `/admin/` | 2 | Ticket 4, partido |

**Por qué cambió tu propuesta:**
- **El Ticket 4 era demasiado grande:** los habilitadores necesitan antes los modelos de D1 a D3, las extensiones, la función `f_unaccent`, los grupos y el login. Lo partí en 5 tickets.
- **El modelo `Usuario` va en HB-03:** Django exige `AUTH_USER_MODEL` antes del primer `migrate`, y ese ticket ejecuta el primero.
- **2 tickets nuevos, porque había huecos:** ningún ticket creaba Nginx (TK-03 y la prueba de integración usan `https://localhost`), ni la tabla `pauta`, que el mock inserta y TK-01 carga en sus tests.
- **HB-02 no se conecta a la base:** Django arranca sin `DATABASES` (backend `dummy`), para respetar tu división entre contenedor (Ticket 2) e integración (Ticket 3).

**Cada ticket** tiene en la sección 6 su descripción técnica, criterios de aceptación, definición de hecho y estimación, y en `docs/tickets/HB-*.md` una guía con tareas paso a paso, archivos, código de referencia, tests con ejemplos, criterios de calidad, comandos de verificación y problemas frecuentes.

**Otros cambios para que todo cuadre:**
- **CI:** cada *job* se activa cuando existe lo que necesita: `lint` e `imagen` con `app/manage.py`, `tests` con `app/conftest.py` y `e2e` con `app/e2e/`. Así los primeros tickets no fallan por tests o pruebas de Playwright que todavía no existen.
- **TK-01** ya no crea los usuarios de BD ni los privilegios generales. Recibe el *trigger* `tg_medicamento_baja` y la validación de esa baja en el panel, que ningún ticket creaba porque necesitan la tabla `existencia`.
- **Sección 3.1:** nombres para 4 restricciones que el DDL no nombraba: `ck_medicamento_tipo`, `uq_mpa_medicamento_principio`, `ck_entidad_tipo` y `ck_residente_estado`.
- **Sección 2.5:** `django-axes` y la expiración de sesión quedan en HB-08; no estaban en ningún ticket.
- **Planificación (sección 5):** semana 1, HB-01 a HB-04; semana 2, HB-05 a HB-09; semana 3, TK-01; las historias se recorren media semana. El MVP pasa de 26 a 49 puntos, y el reporte mensual queda como margen de la semana 6.

---

## Prompt 7 — Usuario

¿Qué formateadores para el código de Python, las plantillas de Django y los archivos de CSS y JS tenemos incluidos?

---

## Respuesta 7 — Claude

Solo hay formateador para Python. Las plantillas de Django, el CSS y el JS no tienen ninguno en el diseño.

| Tipo de archivo | Formateador | Dónde está previsto |
|---|---|---|
| Python | **ruff** (`ruff format` y `ruff check`) | Configurado en HB-02 (`pyproject.toml`); lo exigen el *job* `lint` del CI, la plantilla del PR y la definición de hecho de cada ticket |
| Plantillas de Django | Ninguno | — |
| CSS y JS | Ninguno | — |

Tampoco hay `.editorconfig` ni `pre-commit`. Todo el CSS y JS previsto es de terceros y ya viene minificado (Bootstrap 5.3.3 en HB-08 y HTMX 2.0.4 en TK-03, en `static/*/vendor/`), y la CSP de nginx impide el JS en línea.

**Recomendación:** djLint para las plantillas (es un paquete de Python, así que entra en `requirements-dev.txt` y en `pyproject.toml` sin agregar Node), y nada para CSS y JS mientras no haya archivos propios: reformatear los minificados de terceros los rompería y llenaría los diffs.

---

## Prompt 8 — Usuario

Agrégalos, por favor.

---

## Respuesta 8 — Claude

Agregué **djLint** (perfil `django`) para las plantillas. CSS y JS siguen sin formateador, y la definición de hecho común explica por qué.

**Antes de documentarlo, lo probé:** instalé djLint en un entorno temporal y lo corrí sobre las plantillas de las guías de HB-08 y TK-03. El lint pasó (salvo un `<button>` sin `type`, que corregí), pero el formato no, así que reemplacé esas plantillas por la versión que deja `djlint --reformat`: 2 espacios de sangría y un atributo por línea cuando la etiqueta no cabe en 120 caracteres. Los tests de esas guías siguen siendo válidos, porque solo buscan textos y atributos que no cambiaron.

**Dónde quedó:**
- **HB-02:** `djlint` en `requirements-dev.txt` y `[tool.djlint]` en `pyproject.toml`. Ignora H030 y H031 (piden `<meta>` de descripción, que no aplica a una app interna) y excluye `staticfiles/`, `static/vendor/`, `htmlcov/` y `test-results/`. Su regla H021, que rechaza los `style="..."`, coincide con la CSP.
- **CI (*job* `lint`):** instala ruff y djLint con la versión de `requirements-dev.txt` y corre `djlint . --check` y `djlint . --lint`. Sin plantillas, djLint termina con código 2, así que ese paso se salta mientras no exista ningún `.html` (hasta HB-08).
- **`Makefile` (TK-01):** `make lint` y `make format` incluyen djLint. `djlint --reformat` termina con 1 cuando cambia un archivo, y en `make format` eso no cuenta como error.
- **HB-08 y TK-03:** plantillas formateadas, nota de cómo reformatear, criterio de calidad, comando de verificación y una fila en "Si te bloqueas".
- **readme:** sección 1.4 (`make lint` y `make format`), 2.3 (estructura), 2.4 (CI), definición de hecho común, ficha de HB-02 y HB-08, archivos compartidos y criterio de *merge* "Calidad estática" de la sección 7.3. También la plantilla del PR y `CLAUDE.md`.

El diagrama de infraestructura de la sección 2.4 sigue diciendo "ruff + pytest": no lo cambié para no dejar desactualizado el PNG de `diagramas/`.

---

## Prompt 9 — Usuario

1. Cámbialo: los diagramas se renderizan en GitHub.
2. Usemos la última versión estable y congelémosla ahí, con la 1.49.9 de djLint.

---

## Respuesta 9 — Claude

1. **Diagrama de infraestructura (sección 2.4):** el nodo del CI dice ahora "ruff + djLint + pytest + build de imagen". Apliqué el mismo cambio en el anexo de `02-arquitectura.md`.
2. **djLint congelado en 1.49.9:** HB-02 lo fija en `requirements-dev.txt` y lo saca de la consulta de versiones de su paso 1. La nota del paso aclara que, a diferencia de las demás, esa versión no se actualiza al hacer el ticket: subirla cambia el formato esperado y va en un PR propio que reformatee todas las plantillas. También lo indican la ficha de HB-02 (sección 6) y `CLAUDE.md`.

Repetí la prueba con djLint 1.49.9: las plantillas de las guías de HB-08 y TK-03 pasan `--check` y `--lint`, la regla H021 sigue rechazando los estilos en línea y, sin plantillas, el código de salida sigue siendo 2 (el CI salta ese paso).

---

## Prompt 10 — Usuario

Ya inicialicé OpenSpec. Quiero configurarlo para que tome lo siguiente:
1. La fuente de las historias de usuario y de los tickets, de las secciones correspondientes del `readme.md`.
2. La arquitectura, el stack tecnológico, los ADR y las convenciones de la BD (`CLAUDE.md`).
3. Reglas:
   - Todo `proposal.md` debe incluir el ID exacto de la historia de usuario y del ticket en su encabezado.
   - Todo criterio de aceptación debe convertirse en escenarios GIVEN/WHEN/THEN en `specs/`.
   - Cada tarea de `tasks.md` debe respetar la arquitectura mock-first / TDD definida en `CLAUDE.md`.

---

## Respuesta 10 — Claude

Configuré `openspec/config.yaml` (OpenSpec 2.1, esquema `spec-driven`), que inyecta su contexto y sus reglas en las instrucciones de cada artefacto:

- **`context`:** apunta a las fuentes de verdad sin copiarlas, para que no se desincronicen. Historias en la sección 5 del readme; tickets en la sección 6 y en `docs/tickets/`; modelo de datos en la 3 y API en la 4 con `openapi.yaml`; arquitectura y stack en la 2 y en `CLAUDE.md`; ADR en `docs/adr/`; convenciones de BD, TDD y pruebas en `CLAUDE.md`. También fija las 8 capabilities (una por app de Django), el vocabulario de dominio y que todo se escribe en español.
- **`rules.proposal`:** bajo el título va `**Historia:** HU-NN · **Ticket:** TK-NN · **Épica:** EP-NN`, con los IDs exactos de la tabla de tickets. Un cambio implementa un solo ticket y su nombre empieza por el ID. Los tickets HB no tienen historia: `— (habilitador de EP-NN)`.
- **`rules.specs`:** cada escenario Gherkin de la historia ("Dado/Cuando/Entonces/Y" → GIVEN/WHEN/THEN/AND) y cada casilla de "Criterios de aceptación" del ticket se convierte en un `#### Scenario:`, con el origen en su nombre, sin inventar comportamiento.
- **`rules.design`:** cita y respeta los ADR aceptados, y usa los nombres exactos de la sección 3 y las convenciones de BD.
- **`rules.tasks`:** mock-first y TDD. Por grupo, primero los tests en rojo con `datos_demo`, después la implementación; PostgreSQL real, `app_user`, concurrencia, `EXPLAIN` y contrato de la API; cada tarea con su comando de verificación de la guía del ticket; el último grupo comprueba la definición de hecho.
- **`operations`:** `apply` trabaja tarea por tarea, de rojo a verde, y corre `scripts/verificar.py`; `archive` comprueba la definición de hecho y el readme. Commit y push solo por petición.

**Lo probé** con un cambio temporal, que borré después. GIVEN/WHEN/THEN/AND en viñetas pasan `openspec validate --strict`. Pero un requisito escrito solo con "DEBE" falla en modo estricto, porque el validador exige SHALL o MUST. Por eso la regla pide "DEBE (MUST)", y los encabezados que lee el validador quedan en inglés. `openspec instructions` muestra el contexto y las reglas en proposal, tasks y apply.

**Para que todo coincida:**
- `CLAUDE.md` tiene un apartado "OpenSpec" con estas reglas, y el estado del repositorio menciona `openspec/`. El recordatorio de capabilities ya no dice que OpenSpec no existe.
- `adversarial-reviewer` y la skill `/push` contrastan también contra los escenarios del cambio del ticket. Ahora la condición es "mientras `openspec/specs/` no tenga specs", porque la carpeta ya existe.
- Agregué `openspec/` a la estructura de ficheros del readme (apartado 2.3).

---

## Prompt 11 — Usuario

¿Con qué framework vamos a escribir las pruebas? ¿Exclusivamente con pytest?

(Tras la respuesta:) Arregla la inconsistencia en el `CLAUDE.md` y el `readme.md`: usemos la implementación de `@pytest.mark.django_db(transaction=True)`, igual que en las guías, y `django_assert_num_queries`. Usemos pytest, que es claramente mejor para el mantenimiento y la extensibilidad.

---

## Respuesta 11 — Claude

Sí: el diseño usa solo pytest como framework y ejecutor, con pytest-django (base de pruebas, `client`, `transaction=True`, `django_assert_num_queries`), pytest-cov (cobertura), pytest-playwright (extremo a extremo) y jsonschema (contratos de la API, una biblioteca, no un framework). Ninguna guía escribe clases `TestCase`. La inconsistencia estaba en 2 APIs de estilo `unittest` de Django que aún se mencionaban: `TransactionTestCase` y `assertNumQueries`.

**Corregido:**
- **`CLAUDE.md`:** la regla "Concurrencia obligatoria" pide `@pytest.mark.django_db(transaction=True)` con `threading`, y una regla nueva, "Framework", fija que todo se escribe con pytest: funciones, *fixtures* y marcadores, sin clases `TestCase`.
- **readme 2.6:** "Herramientas" dice que se usa solo pytest y nombra las 2 formas de pytest-django; la fila de concurrencia de la tabla usa `transaction=True` con hilos.
- **readme 3.3:** la verificación de índices usa `django_assert_num_queries`.
- **readme 6 (TK-02):** el test de concurrencia queda solo con `@pytest.mark.django_db(transaction=True)`.
- **ADR-0018:** decía `assertNumQueries`. Lo corregí como error de documentación: la decisión (verificar los índices con el plan y el número de consultas) no cambia, así que no hace falta un ADR nuevo.

Los anexos de `02`, `03` y `06` quedaron sincronizados.

---

## Prompt 12 — Usuario

¿En nuestro arnés de pruebas y en las convenciones tenemos huecos?

(Tras la respuesta, con 8 huecos y 3 menores:) Sí, arréglalos.

---

## Respuesta 12 — Claude

Encontré 8 huecos, y 3 hacían que un test pasara sin comprobar lo que decía. Los arreglé todos, más 2 de los menores:

| # | Hueco | Arreglo |
|---|---|---|
| 1 | El chequeo de CSP de los e2e no podía fallar: la CSP solo la ponía nginx, y `live_server` no pasa por nginx | La política vive en `CONTENT_SECURITY_POLICY` y la envía un *middleware* de Django (HB-04); nginx oculta la de Django y deja una sola cabecera; un test del CI compara las 2 |
| 2 | `como_app_user` hacía `SET LOCAL` aunque no hubiera transacción, y PostgreSQL lo ignoraba: el test corría como `app_owner` sin aviso | El *fixture* falla si no hay transacción envolvente y comprueba `current_user` (TK-01) |
| 3 | Los e2e corrían como `app_owner` | `app/e2e/conftest.py` hace `SET ROLE app_user` en las conexiones del servidor de pruebas (TK-03) |
| 4 | `CLAUDE.md` pedía `transaction=True` sin `serialized_rollback=True`, y el vaciado final borraría los datos semilla | Forma completa en `CLAUDE.md` y en el readme (2.6 y TK-02) |
| 5 y 6 | La cobertura contaba migraciones y tests, y el CI medía ramas pero los comandos locales no | `[tool.coverage]` en `pyproject.toml` (HB-03): solo `apps/`, con ramas, sin migraciones ni tests; el CI ya no pasa `--cov-branch` |
| 7 | Sin arnés de contrato: `jsonschema` no estaba en ninguna lista y el CI no hacía el lint de `openapi.yaml` | TK-05 agrega `jsonschema` y un *helper* en `pruebas.py`; nuevo *job* `contrato` con Redocly CLI 2.79.0, que probé: 0 errores |
| 8 | Los hooks y scripts no tenían lint ni tests | `ruff.toml` en la raíz, `verificar.py --herramientas`, 46 tests en `tests/` y nuevo *job* `herramientas`; el hook de commits también los revisa si hay ruff en el equipo |

**Menores arreglados:** `--strict-markers` y `testpaths`, con `e2e` registrado desde HB-03, y `timeout-minutes` en todos los *jobs* del CI. Queda pendiente, por decisión anterior, automatizar la reversibilidad de las migraciones y los umbrales propios de cada ticket.

**Comprobaciones:** los 46 tests de las herramientas pasan, el lint nuevo detectó (y corregí) un error de sintaxis que yo mismo había introducido en el hook, y el hook de commits niega una herramienta mal formateada con ruff disponible y la deja pasar sin él. Para que el lint pase, corregí el hook de secretos (una variable `l` y el formato de sus expresiones regulares, sin cambiar su comportamiento: el escaneo del repositorio sigue en 0 hallazgos).

`contrato` y `herramientas` no son *checks* obligatorios (readme 7.3, regla 7). Actualicé `CLAUDE.md`, el readme (2.3, 2.4, 2.5, 2.6, 4.7, 6 y 7.3), las guías HB-02, HB-03, HB-04, HB-08, TK-01 y TK-03, el CI y `.gitignore`.

---

## Prompt 13 — Usuario

En las desviaciones en HB-06-entidades.md, ¿en qué ticket se revisará "poner el nombre real" y cómo lo recordaremos?

(Tras la respuesta, que proponía asignarlo a TK-01:) Hazlo con la opción TK-01, es decir 1, 2 y 3.

---

## Respuesta 13 — Claude

No estaba asignado a ningún ticket: la nota de HB-06 decía "en otro ticket" sin nombrarlo. El despliegue en el servidor del hogar no tiene ficha, y HB-09 no registra `Entidad` en `/admin/`, así que el nombre del Hogar tampoco se corrige desde el panel. Lo asigné a **TK-01**, que crea el `Makefile` y fija cómo se lee `.env`:

1. **Ficha de TK-01 (readme, sección 6):** un criterio de aceptación nuevo, que exige que un valor con espacios y sin comillas en `.env` funcione con `make`, con `scripts/migrate.sh` y los atajos, y con `docker compose`, con `HOGAR_NOMBRE` sin comentar en `.env.example`. También lo agregué a la descripción técnica (punto 10). La tabla "Archivos que tocan varios tickets" decía que los TK no modifican `.env.example`; ahora permite a TK-01 descomentar esa línea.
2. **Guía de TK-01, paso 1:** la tarea "Valores con espacios en `.env`", con la lectura línea por línea que sustituye a `. ./.env`. La probé con `bash --posix` y con el `sh` de BusyBox; `. ./.env` falla con el código 127 y `make` lee bien el valor. Agregué también la comprobación del nombre del Hogar en la sección 5.
3. **Nota de HB-06:** ahora apunta a TK-01. Cuando se cree el cambio de OpenSpec de TK-01, el criterio nuevo se convierte en un Scenario por la regla de `openspec/config.yaml`, así que no se podrá archivar sin cumplirlo.

---

## Prompt 14 — Usuario

(Tras la revisión adversarial de HB-06 en el PR #2, sin bloqueantes y con 5 sugerencias y 6 *nits*:) Atiéndelas.

(Tras el plan, con 3 decisiones:) Sí, apruebo.

---

## Respuesta 14 — Claude

Lo hice como un cambio de OpenSpec propio, `hb-06-ajustes-revision`, con `implementar-ticket`: tests congelados por su huella, rojo comprobado y verde con `implementer`. Atendí las 5 sugerencias y los *nits* 6, 7, 9, 10 y 11; el 8 ya lo cubre TK-01.

| Hallazgo | Cambio |
|---|---|
| 1. `activa` y `__str__` fallaban sin el subtipo | Una Entidad `RESIDENTE` sin su fila no está activa y se muestra como `Entidad <id>`. Con `select_related("residente")`, una sola consulta. Actualicé el punto de integración 11 del readme |
| 2. Un alta fallida dejaba el objeto con un `pk` falso | `_state.adding`; si el alta falla, el Residente recibido queda como estaba y se puede reintentar. Un solo test inyecta la falla con `monkeypatch`, contra PostgreSQL real |
| 3. Mensaje técnico para nombres vacíos | El servicio quita los espacios (error de campo obligatorio) y `ck_residente_nombres` tiene mensaje propio (migración `0004`, que no cambia la base) |
| 4. Un servidor sin `HOGAR_NOMBRE` crearía un Hogar "Demo" definitivo | `config.settings.prod` no arranca sin la variable, y `docker-compose.yml` ya no inventa un valor. No se rechaza el nombre de la demo, porque la demo lo usa. Lo agregué a la primera instalación (readme 2.4) y al `check --deploy` de la guía de HB-04 |
| 5. La guía de HB-06 aconsejaba poner en `.env` un valor con espacios | Corregí la sección 7 y anoté los ajustes en la guía |
| *Nits* 6, 7, 9, 10 y 11 | Nombres normalizados (opcionales vacíos a `NULL`), `nombre_completo` sin espacios de más, comentario sobre el `id = 1`, patrón `ejecutar_sql` y `TODO(TK-01)` para `como_app_user` |

**Comprobaciones:** 75 tests pasan y 1 se omite, con cobertura del 97.38 %. Además, `makemigrations --check` no detecta cambios y la `0004` se revierte y se vuelve a aplicar. Por último, `docker compose config` deja `HOGAR_NOMBRE` vacía y `check --deploy` con la variable no da advertencias. Los anexos de `02` y `06` quedaron sincronizados.

---

## Prompt 15 — Usuario

(Tras una segunda revisión adversarial, sin bloqueantes y con 5 sugerencias y 3 *nits*:) ¿Cuáles son las sugerencias y los *nits*?

(Tras la explicación, con una opinión sobre cada uno:) Ok, atiéndelos.

(Tras el plan, con 3 decisiones:) Apruebo.

---

## Respuesta 15 — Claude

Lo hice como el cambio de OpenSpec `hb-06-ajustes-revision-2`, con `implementar-ticket`. Atendí las 5 sugerencias y los *nits* 6 y 7; el 8 quedó fuera, como recomendé, porque el test de control ya delata esa causa.

| Hallazgo | Cambio |
|---|---|
| 1. El test del reintento usaba `monkeypatch` (ADR-0023) | Ahora provoca una falla real: una restricción temporal `CHECK ... NOT VALID` que PostgreSQL aplica al `INSERT` del Residente. No queda ningún `monkeypatch` |
| 2. Restauración parcial y comprobación de "ya registrado" más débil | `registrar_residente()` rechaza también un Residente con Entidad asignada, y restaura todos los campos, incluidas las fechas que `full_clean` convierte |
| 3. Nada sostenía la restauración de `_state` | Un test con `transaction=True` hace fallar el `COMMIT` con un `UNIQUE ... DEFERRABLE` después de un `save` correcto. Lo comprobé por mutación: sin esa restauración, el test queda en rojo |
| 4. El readme no avisaba de los espacios hasta TK-01 | Readme 2.4 y su anexo |
| 5. El paso 2 de la guía de HB-06 estaba desactualizado | Ahora muestra el código actual de `base.py`, `prod.py` y `docker-compose.yml` |
| *Nit* 6. Largo de `HOGAR_NOMBRE` | Máximo 150 caracteres en todos los entornos, con `ImproperlyConfigured` |
| *Nit* 7. TK-01 borraría el aviso de "obligatoria en producción" | Su paso 1 pide conservarlo |

**Comprobaciones:** 80 tests pasan y 1 se omite, con cobertura del 97.35 %. Además, `makemigrations --check` no detecta cambios y `check --deploy` con la variable no da advertencias. El anexo de `02` quedó sincronizado; la sección 6 del readme no cambió.

---

## Prompt 16 — Usuario

Implementa HB-07.

(Tras el plan:) Apruebo.

(Tras una disputa sobre un test congelado:) Opción recomendada: `"ON public.pauta USING btree"`.

(Tras la revisión adversarial de HB-07 en el PR #2:) ¿Hay hallazgos que arreglar debido a la revisión adversarial? (Tras la respuesta:) Prosigue. (Tras el plan:) Apruebo.

---

## Respuesta 16 — Claude

Hice HB-07 como el cambio de OpenSpec `hb-07-pautas`, con `implementar-ticket`. La app `pautas` tiene `Pauta` con `ck_pauta_dosis`, `ck_pauta_frecuencia`, `ck_pauta_fechas`, `ex_pauta_sin_traslape` (`daterange(fecha_inicio, fecha_fin, '[]')` sobre `btree_gist`), `ix_pauta_vigente`, `ix_pauta_residente_inicio` y `tg_pauta_validar`, sin pantallas ni `/admin/`. Además de los tests de la guía, agregué los de los nombres y definiciones exactos, los tipos, la ausencia de índice propio sobre `residente_id` y una pauta registrada como `app_user`.

Hubo una disputa: un test buscaba `" pauta USING btree"`, pero `pg_get_indexdef` de PostgreSQL 17 devuelve `ON public.pauta USING btree`. Se corrigió solo ese fragmento y se volvió a congelar el archivo.

La revisión adversarial no tuvo bloqueantes, pero sí un hallazgo importante, que comprobé: `full_clean()` de una pauta con fin anterior al inicio lanzaba `DataError`, porque `ExclusionConstraint.validate()` evalúa el `daterange` inválido. En el futuro formulario sería un `500`. Lo atendí en `hb-07-ajustes-revision`:

| Hallazgo | Cambio |
|---|---|
| 1. `DataError` al validar fin anterior al inicio | `Pauta.clean()` avisa en `fecha_fin` y Django ya no evalúa la exclusión. La base no cambia. Comprobado también con un `ModelForm` |
| 2. Los `CHECK` sin mensaje | Mensajes en español, en la migración `0003_mensajes` (`AlterConstraint`, sin SQL) |
| 4. `RangoDeFechas` la importa la migración `0001` | Comentario para que no se renombre ni se mueva |
| 7. Huecos en los tests | La exclusión no rechaza pautas de otro medicamento ni de otro residente, y `app_user` cierra una pauta |

**Comprobaciones:** 107 tests pasan y 1 se omite, con cobertura del 97.37 %. `\d pauta` no cambió, y `migrate pautas zero` y la vuelta funcionan. Los hallazgos 3, 5 y 6 quedaron para la historia de pautas.

---

## Prompt 17 — Usuario

(Tras una segunda revisión adversarial, sin bloqueantes ni importantes y con 6 menores:) ¿Corriste la comprobación? ¿Quedan pendientes para cerrar el HB-07?

(Tras la respuesta, que recomendaba cerrarlo:) No, si quedan documentados como pendientes para después en la historia de las pautas.

(Tras documentarlos en la guía:) Sí, mejor documéntalo en el readme también.

---

## Respuesta 17 — Claude

Sí: reproduje el menor 1 antes de publicarlo en el PR, y `full_clean()` con una fecha de inicio escrita como texto lanza `TypeError` en `Pauta.clean()`. Con un `ModelForm` no ocurre. HB-07 no tenía pendientes obligatorios: los 5 criterios de aceptación se cumplen, `\d pauta` está en el PR y el CI pasa.

Los pendientes quedaron documentados en 2 lugares:

- **Guía de HB-07**, al final de la sección 5: una tabla "Pendientes para la historia de Pautas" con los hallazgos 3, 5 y 6 de la primera revisión y los menores 1 a 5 de la segunda, cada uno con su origen y qué hacer. El menor 6, la huella de los tests fuera del repositorio, es así por diseño de `implementar-ticket`.
- **Readme, sección 5, EP-05:** un punto nuevo, "Pendientes de HB-07 para la historia de pautas", con la lista resumida y un enlace a la guía. El anexo de `05` quedó sincronizado.

---

## Prompt 18 — Usuario

Implementar HB-08.

(Tras el plan, con 4 decisiones:) Apruebo y actualicemos los ADR con las nuevas versiones de Bootstrap y django-axes. Si tienes problemas para verificar con navegador, para y tratemos de resolverlo.

(Tras una disputa sobre un test congelado y el aviso `axes.W006`:) Las 2 opciones recomendadas.

(Durante la verificación:) ¿Cómo puedo conectar a un navegador? ¿Hay que reflejar las versiones fijas en los contenedores? Anótalo en la guía de TK-01. Instalé Claude in Chrome; en la consola de Firefox se ve un error de CSP… en Firefox incógnito no aparece, y con Brave tampoco. Agrégalo a la guía.

---

## Respuesta 18 — Claude

Hice HB-08 como el cambio de OpenSpec `hb-08-login-grupos`, con `implementar-ticket`:

- **Login y plantilla común:** login propio en `/accounts/login/`, cierre de sesión por `POST` y `base.html` con Bootstrap servido desde `static/`.
- **Grupos:** los 2 grupos en una migración de datos (5 y 15 permisos) y `uq_usuario_un_grupo`.
- **Panel:** `UsuarioAdmin` exige un solo grupo, activa `is_staff` y no borra; `GrupoAdmin` no permite crear ni borrar grupos.
- **Fuerza bruta y sesión:** `django-axes` bloquea 15 minutos tras 5 intentos, y la sesión expira a los 30 minutos.

| Decisión | Resultado |
|---|---|
| Versiones | Bootstrap **5.3.9** (la guía decía 5.3.3), copiado de `npm pack`, que comprueba la integridad; `django-axes` **9.1.0**. Quedaron fijadas en ADR-0002, ADR-0022 y el readme |
| Disputa | `groups.add()` inserta con `ON CONFLICT DO NOTHING`, así que la base impide el segundo grupo sin lanzar error. El test inserta directo en la tabla puente |
| `axes.W006` | Silenciado: el bloqueo es por usuario. Detrás de nginx, sin `ipware`, todos llegarían con la IP del proxy y 5 fallos de cualquiera bloquearían a todos |
| Navegador | Sin herramientas de navegador en la sesión, lo revisé con Chrome *headless* por el protocolo DevTools, con emulación de dispositivo. A 390 px no hay desplazamiento horizontal, ni violaciones de CSP en el login ni en `/admin/login/`. Las capturas quedaron en `docs/capturas/HB-08/` y en el PR |
| CSP en Firefox | La causaba una extensión (`sandbox eval code`): no aparece en Chrome, en Brave ni en la ventana privada. Lo anoté en la sección 7 de la guía, para no agregar ese hash a la CSP |
| Contenedores | El `Dockerfile` y `docker-compose.yml` no repiten versiones. En cada equipo hay que reconstruir `web`, migrar y ejecutar `collectstatic`. Lo anoté en el paso 1 de TK-01, con un *target* `make actualizar` |

**Comprobaciones:** 134 tests pasan y 1 se omite, con cobertura del 96.91 %; djLint revisa las 3 plantillas. `accounts` se revierte a `0002` y vuelve. Por nginx, el 5.º intento fallido responde `429` con la CSP.

---

## Prompt 19 — Usuario

(Tras la revisión adversarial de HB-08, sin bloqueantes y con 4 hallazgos importantes y 7 menores:) ¿Queda algún pendiente del HB-08? (Tras la respuesta:) Sí, por favor. (Tras el plan:) Apruebo.

---

## Respuesta 19 — Claude

Lo hice como el cambio de OpenSpec `hb-08-ajustes-revision`. El hallazgo 8, la CSP del panel con sesión, ya es criterio de HB-09.

| Hallazgo | Cambio |
|---|---|
| 1, 2, 3, 7, 10 y 11. Tests que comprobaban la configuración y no el comportamiento | 9 tests de regresión: la barra de `base.html` con sesión, el bloqueo de un usuario que no afecta a otro y termina a los 15 minutos, el 5.º fallo con `429`, la sesión de 1800 segundos, el Administrador sin grupo, `is_staff` al asignar grupo, el `403` para *Solo lectura* y `app_user` en las tablas de `axes` |
| 5. `GrupoAdmin` dejaba cambiar nombre y permisos | Grupos de solo consulta (`has_change_permission = False`) |
| 10. Doble aviso con un grupo inválido | Un solo aviso |
| 6. El Administrador también puede quedar bloqueado | `bloqueado.html` pide esperar 15 minutos. ADR-0022 documenta el bloqueo malicioso y los datos que guarda `axes` |
| 4 y 11. Proceso y guía | Este registro, el paso 2 de la guía con `npm pack` y el *glob* de djLint |

**Comprobaciones:** 147 tests pasan y 1 se omite, con cobertura del 97.27 %. Los 3 tests nuevos en rojo fallaron por el motivo esperado antes de implementar.

---

## Prompt 20 — Usuario

(Tras una segunda revisión adversarial de HB-08, sin bloqueantes y con 1 hallazgo importante y 6 menores:) ¿Hay pendientes para este HB-08? (Tras la respuesta:) Hazlo. (Tras el plan:) Apruebo.

---

## Respuesta 20 — Claude

Antes de responder comprobé por nginx el hallazgo que la revisión dejó sin verificar: **cada intento durante el bloqueo lo reinicia**, porque `axes` renueva la hora del último intento. Lo atendí en el cambio de OpenSpec `hb-08-ajustes-revision-2`:

| Hallazgo | Cambio |
|---|---|
| 1. El test de la sesión de 30 minutos solo comprobaba `settings` | Comprueba la `expire_date` real en la base, su renovación con cada petición y la cookie sin `max-age` ni `expires` |
| 5. El bloqueo se reinicia con cada intento | Tests de los 14 minutos y del reinicio; `bloqueado.html` pide esperar sin volver a intentarlo |
| 2. `DELETE` de `app_user` en las tablas de `axes` | El test comprueba `INSERT`, `UPDATE` y `DELETE` |
| 3. ADR-0022 omitía `axes_accesslog` | Lo nombra, con `axes_reset_logs` y el reinicio del bloqueo |
| 4. "Gestiona grupos" | ADR-0021, el readme y sus anexos: gestiona usuarios y consulta grupos |
| 6 y 7. Detalles | El Scenario cita el mensaje completo; el *Purpose* de la spec de `accounts`; un control positivo de `_save` |

**Comprobaciones:** 150 tests pasan y 1 se omite, con cobertura del 97.27 %. Solo el test del mensaje nació en rojo; los demás fijan el comportamiento comprobado.

---

## Prompt 21 — Usuario

(Tras una tercera revisión adversarial de HB-08, sin bloqueantes ni importantes y con 5 menores:) ¿Hay pendientes para el HB-08? (Tras la respuesta:) Haz 1 y 2 y cerremos.

---

## Respuesta 21 — Claude

Corregí los 2 menores de documentación y cerré HB-08:

- **1. ADR-0022 se contradecía.** Decía "repitiendo 5 fallos cada 15 minutos", pero cada intento durante el bloqueo lo reinicia. Ahora dice que bastan 5 fallos y después un solo intento cada menos de 15 minutos.
- **2. `axes_reset_logs` no vacía el registro de accesos.** Lo comprobé en el paquete instalado: solo borra lo que tiene más de 30 días (`--age N`; con `--age 0`, todo), y nada lo ejecuta de forma automática. Lo corregí en ADR-0022 y en la guía de HB-08.

Los otros 3 menores quedan anotados en la guía, sin cambio: el título de un requisito de la spec de `accounts`, `AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT` con su valor por defecto (lo protege un test) y la numeración de los hallazgos en los comentarios de los tests.

---

## Anexo — Texto final escrito en `readme.md` (sección 6)

## 6. Tickets de Trabajo

> Documenta 3 de los tickets de trabajo principales del desarrollo, uno de backend, uno de frontend, y uno de bases de datos. Da todo el detalle requerido para desarrollar la tarea de inicio a fin teniendo en cuenta las buenas prácticas al respecto. 

Los 3 tickets forman el camino crítico del MVP: el esquema que guarda los saldos, la lógica que los mueve y la pantalla que los muestra. Cada uno se desarrolla en su propia rama y se integra con un *pull request* (sección 7).

Cada ticket tiene además una **guía paso a paso** en [`docs/tickets/`](docs/tickets/), pensada para que un desarrollador junior lo implemente sin bloqueos: tareas en orden, archivos a crear, código de referencia, tests con ejemplos, criterios de calidad, comandos de verificación con su resultado esperado y una tabla de problemas frecuentes.

Antes de los 3, 9 **tickets de habilitación** (HB-01 a HB-09, semanas 1 y 2) dejan listos los contenedores, la conexión con los 2 usuarios de base de datos, los modelos de catálogo, residentes y pautas, el login y los habilitadores del panel `/admin/` (sección 5). Tienen el mismo formato y su propia guía, y su detalle está al final de esta sección.

| Ticket | Tipo | Historia | Puntos | Depende de | Bloquea a |
|---|---|---|---|---|---|
| TK-01 | Base de datos | Base de HU-01, HU-02 y HU-03 | 5 | HB-03 y HB-05 a HB-08 (usuarios de BD, catálogo, residentes, pautas y grupos) | TK-02, TK-03, TK-06 |
| TK-02 | Backend | HU-01 | 5 | TK-01 | TK-04, TK-06 |
| TK-03 | Frontend | HU-02 | 3 | TK-01 (y TK-02 para tener saldos reales) | TK-05 |

**Estimación:** escala Fibonacci (1, 2, 3, 5, 8), relativa a la complejidad, al riesgo y al esfuerzo. TK-01 y los tickets de habilitación son trabajo de base que las estimaciones de las historias no incluían, así que el MVP suma **49 puntos**: 21 de las historias, 5 de TK-01 y 23 de habilitación.

**Backlog del MVP** (tickets restantes, se detallan al planear su sprint):

| Ticket | Tipo | Historia | Puntos | Depende de | Alcance |
|---|---|---|---|---|---|
| TK-04 | Frontend + vistas | HU-01 | 3 | TK-02 | Formularios de entrada, transferencia y baja; historial de movimientos por entidad con el botón "Corregir"; patrón *Post/Redirect/Get* y botón deshabilitado contra el doble envío |
| TK-05 | Backend (API) | HU-02 | 2 | TK-03 | `GET /api/v1/existencias` con DRF sobre el selector de TK-03, manejador de errores Problem Details y tests de contrato contra `openapi.yaml` |
| TK-06 | Backend | HU-03 | 3 | TK-01, TK-02 | Servicio de conteos: iniciar, capturar con foto del saldo, recapturar y cerrar, con sus excepciones (`CONTEO_CERRADO`, `CONTEO_SIN_RENGLONES`) |
| TK-07 | Frontend | HU-03 | 5 | TK-04, TK-06 | Pantallas del conteo: captura en el celular que guarda al salir del campo, diferencias resaltadas, movimientos del período y "Registrar baja/entrada" desde el renglón |

| Historia | Puntos | Tickets |
|---|---|---|
| HU-01 | 8 | TK-02 (5) + TK-04 (3) |
| HU-02 | 5 | TK-03 (3) + TK-05 (2) |
| HU-03 | 8 | TK-06 (3) + TK-07 (5) |
| Base | 5 | TK-01 (5) |
| Habilitación | 23 | HB-01 a HB-09 (tabla siguiente) |
| **Total** | **49** | 13 en los 3 tickets documentados abajo + 13 en el backlog + 23 de habilitación |

Quedan fuera de esta cuenta los endpoints `GET /medicamentos` y `GET /reportes/mensual`, que se estimarán con la historia de reportes.

**Tickets de habilitación** (semanas 1 y 2; detalle al final de esta sección):

| Ticket | Tipo | Alcance | Puntos | Depende de | Bloquea a | Guía |
|---|---|---|---|---|---|---|
| HB-01 | Infraestructura | Servicio `db` (PostgreSQL 17), volumen `pgdata` y los 2 usuarios de BD | 2 | — | HB-02 | [HB-01](docs/tickets/HB-01-postgresql.md) |
| HB-02 | Infraestructura | Proyecto Django, `Dockerfile` y servicio `web` | 3 | HB-01 | HB-03 | [HB-02](docs/tickets/HB-02-imagen-web.md) |
| HB-03 | Infraestructura + BD | Conexión con variables `DB_*`, `web` como `app_user`, `migrate.sh`, modelo `Usuario` y privilegios | 3 | HB-02 | HB-04, HB-05 | [HB-03](docs/tickets/HB-03-conexion-bd.md) |
| HB-04 | Infraestructura | Servicio `nginx` con HTTPS local y cabeceras de seguridad | 2 | HB-03 | HB-08, TK-03 | [HB-04](docs/tickets/HB-04-nginx.md) |
| HB-05 | Base de datos | Catálogo (D2), extensiones, `f_unaccent` e índices trigram | 3 | HB-03 | HB-06 | [HB-05](docs/tickets/HB-05-catalogo.md) |
| HB-06 | Base de datos | Entidades: Hogar y residentes (D3) | 3 | HB-05 | HB-07, HB-08 | [HB-06](docs/tickets/HB-06-entidades.md) |
| HB-07 | Base de datos | Esquema de pautas (D6), sin pantallas | 2 | HB-06 | TK-01 | [HB-07](docs/tickets/HB-07-pautas.md) |
| HB-08 | Backend + frontend | Login, `base.html`, los 2 grupos, usuarios en `/admin/` y `django-axes` | 3 | HB-04, HB-06 | HB-09, TK-01, TK-03 | [HB-08](docs/tickets/HB-08-login-grupos.md) |
| HB-09 | Panel `/admin/` | Catálogo y residentes en el panel, sin borrado y con búsqueda sin acentos | 2 | HB-08 | — | [HB-09](docs/tickets/HB-09-admin-catalogo-residentes.md) |

**Definición de hecho común** (aplica a todos los tickets, TK y HB, además de la propia de cada uno):
- El código pasa `ruff check` y `ruff format --check`, las plantillas pasan `djlint --check` y `djlint --lint`, y no hay `print` ni código comentado. No hay formateador de CSS ni de JS: el proyecto solo usa los de Bootstrap y HTMX, ya minificados en `static/*/vendor/`, que no se reformatean.
- CI en verde: lint, `python manage.py makemigrations --check` y `pytest` contra PostgreSQL 17 (cada *job* se activa cuando existe lo que necesita, sección 7.3).
- Cobertura ≥ 80 % en `apps/` (la exige el CI), más el umbral propio del ticket (sección 2.6).
- *Pull request* revisado y aprobado, con la descripción, cómo probarlo y el enlace al ticket. Se integra a `main` con *squash merge*.
- No hay secretos en el código ni datos personales en los logs (LFPDPPP).
- La documentación afectada del `readme.md` está actualizada.

#### Orden de ejecución

```mermaid
flowchart LR
    subgraph HAB["Semanas 1 y 2 · habilitación"]
        H1["HB-01 · db"] --> H2["HB-02 · web"] --> H3["HB-03 · conexión<br/>y usuarios de BD"]
        H3 --> H4["HB-04 · nginx"]
        H3 --> H5["HB-05 · catálogo"] --> H6["HB-06 · residentes"] --> H7["HB-07 · pautas"]
        H4 --> H8["HB-08 · login y grupos"]
        H6 --> H8
        H8 --> H9["HB-09 · /admin/"]
    end
    H7 --> T1["TK-01 · BD<br/>esquema, permisos y fixtures"]
    H8 --> T1
    T1 --> T2["TK-02 · Backend<br/>services.py"]
    T1 --> T3["TK-03 · Frontend<br/>pantalla de existencias"]
    T2 --> INT{{"Prueba de integración<br/>los 3 en main"}}
    T3 --> INT
    INT --> BL["Backlog<br/>TK-04 a TK-07"]
```

0. **Habilitación primero, en el orden del diagrama.** Cada ticket HB se integra a `main` antes de empezar los que dependen de él. Después de HB-03, HB-04 (nginx) y la cadena HB-05 → HB-07 pueden avanzar en paralelo. HB-09 no bloquea a TK-01: puede integrarse mientras TK-01 avanza.
1. **TK-01 después de HB-07 y HB-08, y sin paralelo entre los TK.** Crea las tablas, los permisos de los grupos y los *fixtures* de prueba que usan los otros 2. Se integra a `main` antes de empezar TK-02 o TK-03.
2. **TK-02 y TK-03 pueden avanzar en paralelo.** TK-03 se desarrolla con los saldos del mock y no necesita el servicio. Con un solo desarrollador, va primero TK-02, porque está en el camino crítico de TK-04 y TK-06.
3. **Orden de integración: TK-01 → TK-02 → TK-03.** El último en integrar hace `git rebase main`, ejecuta la **prueba de integración** (más abajo) en su rama y la deja en el repositorio. Desde ahí corre en CI en cada PR.

**Archivos que tocan varios tickets** (reglas para evitar conflictos):

| Archivo | TK-01 | TK-02 | TK-03 | Regla |
|---|---|---|---|---|
| `app/conftest.py`, `app/pruebas.py` | Agrega los *fixtures* y `saldo` | Solo los usa | Solo los usa | Los crea HB-03 (`conftest.py` vacío y `ejecutar_sql`). Después, solo TK-01 los modifica. Un *fixture* nuevo se pide en el PR de TK-01 o en uno propio |
| `apps/inventario/migrations/` | `0001` a `0004` | — | — | TK-02 y TK-03 no crean migraciones. Si alguno la necesita, se renumera después del *rebase* |
| `config/settings/base.py` | — | — | `django_htmx`, `LOGIN_REDIRECT_URL` | Lo crea HB-02 y lo completan HB-03 a HB-08 (`DATABASES` es de HB-03). Cambios en bloques distintos |
| `requirements.txt` / `requirements-dev.txt` | — | — | `django-htmx` / `pytest-playwright` | Los crea HB-02 (`djlint`, `pytest`, `pytest-django`, `pytest-cov` y `ruff`); TK-05 agrega `jsonschema`. Una dependencia por línea, en orden alfabético |
| `docker-compose.yml`, `.env.example` | Descomenta `HOGAR_NOMBRE` en `.env.example` | — | — | Los crean HB-01 a HB-04 (y HB-06 agrega `HOGAR_NOMBRE`, comentada). Los tickets TK no los modifican, salvo TK-01 en esa línea |

#### Puntos de integración

Son los contratos entre las capas. Si un ticket cambia uno, avisa en su PR a los tickets que lo consumen.

| # | Punto de integración | Lo provee | Lo consume | Contrato | Cómo se verifica |
|---|---|---|---|---|---|
| 1 | Modelos `Existencia`, `Movimiento`, `MotivoBaja` | TK-01 | TK-02, TK-03 | Nombres de campos de la sección 3.2; `Movimiento.Tipo` y `Movimiento.OrigenEntrada`; relaciones `existencias` y `correcciones` | Los tests de TK-02 y TK-03 importan los modelos |
| 2 | Escritura de saldos | TK-02 | TK-03 | Solo `services.py` escribe `existencia.saldo` (≥ 0, 2 decimales) y `actualizado_en` en cada movimiento; TK-03 solo lee | `git grep` de TK-02 y prueba de integración |
| 3 | Restricciones de la base ↔ excepciones de dominio | TK-01 | TK-02 | El servicio valida antes de escribir; la base es la última barrera. `uq_movimiento_corrige` se traduce a `MovimientoYaCorregido` | Tests de esquema (TK-01) y de servicios (TK-02) |
| 4 | Privilegios de `app_user` | HB-03 (todas las tablas) y TK-01 (`movimiento`) | TK-02, TK-03 | La aplicación solo hace `SELECT`/`INSERT` en `movimiento`, sin `FOR UPDATE` sobre esa tabla | Los tests de TK-02 y la prueba de integración corren como `app_user` |
| 5 | Permisos de los grupos | TK-01 (migración `0003`, sobre los grupos de HB-08) | TK-03 (y TK-04) | Los 2 grupos tienen `view_existencia`; *Lectura y escritura* además `add_movimiento` | Tests de vista de TK-03 con `consulta.demo` |
| 6 | Búsqueda sin acentos | HB-05 (`f_unaccent`, índices trigram) | TK-03 | El ORM usa exactamente `f_unaccent(lower(campo))` | Plan de ejecución (TK-03, verificación 4) |
| 7 | *Fixtures* de prueba | TK-01 (`ejecutar_sql` desde HB-03) | TK-02, TK-03 | `datos_demo`, `demo`, `como_app_user`, `ejecutar_sql`, `saldo` | Los 3 tickets los usan sin modificarlos |
| 8 | Vista de conciliación | TK-01 | TK-02, prueba de integración | `v_conciliacion_existencia` vacía = todo cuadra | *Fixture* `autouse` de TK-02 |
| 9 | Selector `buscar_existencias` | TK-03 | TK-05 (API) | Argumentos por nombre, igual que los campos de `FiltroExistenciasForm`; devuelve un `QuerySet[Existencia]` ordenado | Tests de selector de TK-03 |
| 10 | Excepciones con `code` y `campo` | TK-02 | TK-04 (formularios), TK-05/V2 (API) | `code` igual a la sección 4.4; `DatoInvalido.campo` indica qué campo del formulario marcar | Tests de servicios de TK-02 |
| 11 | `Entidad.activa` y `Entidad.__str__` | HB-06 | TK-01, TK-02, TK-03 | `activa`: el Hogar siempre, un residente solo si su estado es `ACTIVO`. `__str__`: nombre del Hogar o nombre completo del residente. Sin su fila en `residente`: no activa y `Entidad <id>`. En listas, con `select_related("residente")` | Requisitos previos de cada guía |
| 12 | Servicio de conteos y sus excepciones | TK-06 | TK-07 | `iniciar_conteo`, `capturar_renglon` y `cerrar_conteo` con argumentos por nombre; `ConteoCerrado` y `ConteoSinRenglones` con `code` de la sección 4.4; el conteo nunca ajusta existencias | Tests de servicio de TK-06 (PR 3, sección 7) |

#### Prueba de integración final

Comprueba que los 3 tickets funcionan juntos: lo que registra el servicio (TK-02), guardado con las reglas de la base (TK-01), aparece en la pantalla (TK-03). La escribe quien integra el último ticket, en `apps/inventario/tests/test_integracion.py`, y desde entonces corre en CI en cada PR. Código, pasos y resultado esperado: [`docs/tickets/integracion.md`](docs/tickets/integracion.md).

| # | Escenario (como `app_user`, con el mock) | Resultado esperado |
|---|---|---|
| 1 | Entrada de 30 Eutirox a Carmen y transferencia de 0.5 Omeprazol del Hogar a Carmen; se consulta la pantalla filtrada por Carmen | Eutirox 63, Exelon 3, Omeprazol "0.5 dosis" y Paracetamol 14 |
| 2 | Baja de 5 Atorvastatina de María (saldo 1) | `ExistenciaInsuficiente`; la pantalla sigue mostrando 1 |
| 3 | Baja de la última Atorvastatina de María | Desaparece de la búsqueda y reaparece como "Agotado" con "Incluir sin saldo" |
| 4 | Corrección de la entrada de Eutirox | La pantalla vuelve a mostrar 33 |
| 5 | Al final de cada escenario | `v_conciliacion_existencia` vacía |

Además, sobre una instalación desde cero (`docker compose down -v`, `migrate.sh` y el mock), se ejecutan la suite completa, los e2e de Playwright y una prueba de humo con curl (ver la guía).

#### Criterios de revisión de código

Quién revisa: el Tech Lead, o, si el autor es el único desarrollador, el propio autor al día siguiente con esta lista más la revisión del subagente `adversarial-reviewer`, registrada en el PR. Se aprueba solo si no queda ningún comentario **bloqueante**.

| Ámbito | El revisor comprueba que… | Severidad si falla |
|---|---|---|
| Alcance | El PR hace solo lo del ticket y cumple todos sus criterios de aceptación | Bloqueante |
| Tamaño | Menos de ~400 líneas sin contar migraciones generadas ni plantillas; si no, se divide | Sugerencia |
| Tests | Cada criterio de aceptación tiene un test; los tests fallan si se quita el código que prueban | Bloqueante |
| Integración | No cambia un punto de integración sin avisar; la prueba de integración pasa | Bloqueante |
| Seguridad | Sin secretos, sin datos personales en logs, permisos validados en el servidor, sin el filtro `safe` ni SQL armado con texto del usuario | Bloqueante |
| Datos | Cantidades en `Decimal`; escrituras de inventario solo por `services.py`, dentro de una transacción | Bloqueante |
| **Infra** (HB-01 a HB-04) | Sin secretos en el repositorio, en la imagen ni en Compose; solo `nginx` publica puertos; `web` corre sin `root` y solo recibe sus variables; imágenes y dependencias con versión fija | Bloqueante |
| **BD** (TK-01, HB-03, HB-05 a HB-07) | Nombres idénticos a las secciones 3.1 y 3.3; toda migración reversible; `sqlmigrate` revisado; sin índices duplicados; privilegios de `app_user` intactos | Bloqueante |
| **Backend** (TK-02, TK-06) | Bloqueo en orden fijo; sin `FOR UPDATE` sobre `movimiento`; cada excepción con su `code`; el servicio valida antes de que actúe un *trigger* (el usuario nunca ve un `500` por una regla de negocio); *docstrings* con ejemplo | Bloqueante |
| **Frontend** (TK-03, HB-08, HB-09) | Sin JavaScript en línea (CSP); `<label>` en cada campo; *responsive* a 390 px; la vista sin lógica de búsqueda; sin N+1 | Bloqueante |
| Legibilidad | Nombres y comentarios en español, como el resto del código; funciones cortas; sin código muerto | Sugerencia |
| Documentación | El readme refleja cualquier cambio de diseño | Bloqueante si cambia un contrato |

Los comentarios se marcan como **[bloqueante]**, **[sugerencia]** o **[nit]** (detalle menor). El autor responde cada uno: lo corrige o explica por qué no.

---

**Ticket 1**

**TK-01 · [BD] Esquema de existencias, movimientos y conteos, con restricciones, *triggers* e índices**

| Campo | Valor |
|---|---|
| Tipo | Base de datos |
| Historias | HU-01 (movimientos), HU-02 (consulta de existencias), HU-03 (conteos) |
| Prioridad | Must, camino crítico |
| Estimación | **5 puntos** |
| Rama | `feature/TK-01-esquema-inventario` |
| Depende de | HB-03 (`Usuario`, los 2 usuarios de BD y los privilegios de `app_user`), HB-05 a HB-07 (`Medicamento`, `Entidad`, `Residente`, `Pauta`, extensiones y `f_unaccent`) y HB-08 (los 2 grupos) |

**Guía paso a paso:** [`docs/tickets/TK-01-esquema-inventario.md`](docs/tickets/TK-01-esquema-inventario.md). Incluye tareas, archivos, código, tests con ejemplos, criterios de calidad y comandos de verificación.

**Contexto.** Las 3 historias dependen de que el saldo sea confiable. Este ticket lleva a migraciones de Django las tablas D4, D5 y de conteos de la sección 3, para que la base de datos sea la **última barrera**: aunque un error de código intente dejar un saldo negativo o editar un movimiento, PostgreSQL lo rechaza.

**Descripción técnica**

**Tecnologías y librerías**

| Tecnología | Versión | Uso en este ticket |
|---|---|---|
| PostgreSQL | 17 (`postgres:17-alpine`) | Tablas, `CHECK`, `UNIQUE`, columna generada, índices parciales, `INCLUDE` y BRIN, *triggers* en PL/pgSQL, vista de conciliación |
| Extensiones `pg_trgm`, `unaccent`, `btree_gist` | Las de PostgreSQL 17 | Ya instaladas en HB-05; este ticket las usa en índices y restricciones |
| Django ORM y migraciones | Django 5.2 LTS | `CheckConstraint(condition=...)`, `UniqueConstraint`, `GeneratedField`, `db_default`, `Index(include=..., condition=...)`, `RunSQL` y `RunPython` |
| `django.contrib.postgres` | Incluido en Django | `BrinIndex` |
| psycopg | 3.x (`psycopg[binary]`) | Controlador de PostgreSQL de Django |
| pytest + pytest-django | Las del proyecto (sección 2.6) | Tests de esquema y de privilegios |

No agrega dependencias nuevas.

1. **Modelos** (`apps/inventario/models.py` y `apps/conteos/models.py`), con los tipos y nombres de la sección 3.2:

   | Modelo | Tabla | Puntos clave |
   |---|---|---|
   | `MotivoBaja` | `motivo_baja` | `clave` única; `activo` |
   | `Existencia` | `existencia` | `saldo` `DecimalField(10, 2)`, `db_default=0`; `actualizado_en` `db_default=Now()` |
   | `Movimiento` | `movimiento` | `tipo` con `TextChoices`; `cantidad` `DecimalField(10, 2)`; `corrige_a` `ForeignKey('self', null=True, on_delete=PROTECT)` con la restricción `uq_movimiento_corrige` (así conserva el nombre del DDL); `fecha_hora` `db_default=Now()` |
   | `ConteoFisico` | `conteo_fisico` | `estado` con `TextChoices`, `db_default='EN_PROCESO'`; `cerrado_en` nullable |
   | `DetalleConteo` | `detalle_conteo` | `diferencia = GeneratedField(expression=F('cantidad_fisica') - F('cantidad_sistema'), output_field=DecimalField(10, 2), db_persist=True)` |

   - Todas las FK con `on_delete=PROTECT` (`ON DELETE RESTRICT`).
   - `db_index=False` en las FK cubiertas por un índice compuesto (tabla "Índices de FK que Django no debe crear", sección 3.3).
   - `Meta.db_table` con el nombre en español de la sección 3. Los modelos no tienen `save()` ni `delete()` personalizados: la lógica vive en `services.py` (TK-02).

2. **Restricciones declarativas** en `Meta.constraints`, con los mismos nombres del DDL para que los errores sean reconocibles:
   - `uq_existencia` y `ck_existencia_saldo`.
   - `ck_movimiento_por_tipo` (con `Q` por tipo, idéntico al DDL de la sección 3.1), `ck_movimiento_cantidad`, `ck_movimiento_entregado` y `ck_movimiento_no_autocorrige`.
   - `ck_conteo_periodo`, `ck_conteo_cierre`, `uq_detalle_conteo`, `ck_detalle_fisica` y `ck_detalle_sistema`.

3. **Índices** en `Meta.indexes`: los de `existencia`, `movimiento`, `conteo_fisico` y `detalle_conteo` de la sección 3.3, incluidos los parciales, el `INCLUDE` y `BrinIndex(fields=['fecha_hora'], name='brin_movimiento_fecha')`.

4. **Migraciones `RunSQL`** (`inventario/migrations/0004_sql.py` y `conteos/migrations/0002_triggers.py`), cada sentencia con su `reverse_sql`:
   - `fn_movimiento_inmutable` + `tg_movimiento_inmutable`.
   - `fn_movimiento_validar_destino` + `tg_movimiento_validar_destino`.
   - `fn_conteo_cerrado` + `tg_conteo_cerrado`, y `fn_detalle_conteo_cerrado` + `tg_detalle_conteo_cerrado`.
   - `fn_medicamento_baja_sin_existencias` + `tg_medicamento_baja` (sección 3.3). Es del catálogo, pero consulta `existencia`, así que nace con esa tabla.
   - `ALTER TABLE existencia SET (fillfactor = 90)`.
   - Vista de conciliación: devuelve las existencias cuyo saldo no coincide con la suma de sus movimientos. Vacía = todo cuadra.

     ```sql
     CREATE VIEW v_conciliacion_existencia AS
     WITH suma AS (
         SELECT entidad_destino_id AS entidad_id, medicamento_id, cantidad FROM movimiento
          WHERE entidad_destino_id IS NOT NULL
         UNION ALL
         SELECT entidad_origen_id, medicamento_id, -cantidad FROM movimiento
          WHERE entidad_origen_id IS NOT NULL
     )
     SELECT coalesce(e.entidad_id, s.entidad_id)         AS entidad_id,
            coalesce(e.medicamento_id, s.medicamento_id) AS medicamento_id,
            coalesce(e.saldo, 0)                         AS saldo,
            coalesce(s.total, 0)                         AS suma_movimientos
     FROM existencia e
     FULL JOIN (SELECT entidad_id, medicamento_id, sum(cantidad) AS total
                FROM suma GROUP BY 1, 2) s
       ON s.entidad_id = e.entidad_id AND s.medicamento_id = e.medicamento_id
     WHERE coalesce(e.saldo, 0) <> coalesce(s.total, 0);
     ```

5. **Dos usuarios de base de datos y privilegios mínimos.** La inmutabilidad solo es real si la aplicación **no** se conecta con el dueño de las tablas: el dueño puede volver a darse permisos (`GRANT`) o desactivar el *trigger* (`ALTER TABLE ... DISABLE TRIGGER`). Por eso hay 2 usuarios, con el **mismo nombre en todos los entornos** (solo cambian las contraseñas). Así las migraciones son deterministas:

   | Usuario | Lo usa | Puede | No puede |
   |---|---|---|---|
   | `app_owner` | `migrate`, la carga del mock y los tests | Crear y modificar tablas; es dueño de la base y del esquema `public` | — |
   | `app_user` | La aplicación (`web`) en tiempo de ejecución | `SELECT`, `INSERT`, `UPDATE` y `DELETE` en las tablas | `UPDATE`, `DELETE` ni `TRUNCATE` en `movimiento`; crear o alterar tablas; desactivar *triggers* |

   Los 2 usuarios y los privilegios generales **ya existen** cuando empieza este ticket:
   - **HB-01**, `db/init/01_roles.sh`: script de inicio del contenedor de PostgreSQL, montado en `/docker-entrypoint-initdb.d/`. Crea los 2 usuarios con las contraseñas de `.env` (`DB_OWNER_PASSWORD`, `DB_APP_PASSWORD`), deja a `app_owner` como dueño de la base y le da a `app_user` solo `CONNECT` y `USAGE` en el esquema. Con `GRANT app_user TO app_owner`, los tests pueden actuar como `app_user` (`SET ROLE`); esto no le da a `app_user` ningún permiso del dueño. Es idempotente. En desarrollo y CI, `app_owner` tiene además `CREATEDB` para que `pytest` cree la base de tests; en producción no lo tiene.
   - **HB-03**, migración `accounts/migrations/0002_privilegios.py` (`RunSQL`, ejecutada por `app_owner`): da a `app_user` `SELECT`, `INSERT`, `UPDATE` y `DELETE` sobre todas las tablas, también las que creen las migraciones siguientes (`ALTER DEFAULT PRIVILEGES`). Va en una migración, y no en el script de inicio, porque los permisos por defecto son de cada base: así también aplican en la base de tests que crea `pytest`.
   - **HB-03**, `scripts/migrate.sh`: ejecuta `migrate` con las credenciales de `app_owner`. El contenedor `web` arranca con `DB_USER=app_user`.

   Este ticket agrega lo propio de `movimiento`: **en su migración**, después de crear la tabla, `REVOKE UPDATE, DELETE, TRUNCATE ON movimiento FROM app_user;` (con su `reverse_sql`, que vuelve a dar esos permisos). Las tablas nuevas dependen de `accounts.0002_privilegios` para nacer con los permisos de `app_user`.

6. **Migración de datos** (`inventario/migrations/0002_motivos_baja.py`) de los 8 motivos de baja (`CONSUMO` … `CORRECCION`), idempotente con `update_or_create` por `clave` y con su función inversa.

7. **Permisos de los grupos** (`inventario/migrations/0003_permisos_grupos.py`): los grupos se crearon en HB-08, antes que estos modelos. La migración les asigna `view_existencia`, `view_movimiento` y `view_motivobaja`, y a *Lectura y escritura* además `add_movimiento`. Nadie recibe `change_movimiento` ni `delete_movimiento`.

8. **Admin:** ninguno de estos modelos se registra en `/admin/` (sección 5, "Controles"). Se agrega un test que lo verifica. Además, el formulario de `MedicamentoAdmin` (HB-09) rechaza desmarcar `activo` si el medicamento tiene existencias, con el mensaje de la sección 5. Esa validación necesita la tabla `existencia`, por eso va aquí.

9. **Fixtures de prueba compartidos** (punto de integración 7): `datos_demo` (carga el mock con `cargar_mock.sql` adaptado), `demo` (accesos a entidades, medicamentos, motivos y usuario), `como_app_user` (el test corre con los permisos de la aplicación; falla si no hay transacción envolvente, para no correr en silencio como `app_owner`) y el helper `saldo`, junto a `ejecutar_sql` (de HB-03). TK-02 y TK-03 los usan sin modificarlos.

10. **`Makefile` de la raíz:** atajos de desarrollo local (`make up`, `make migrate`, `make test`, `make mock`…) sobre los mismos comandos de la guía, con `make help` como punto de entrada. Se crea en este ticket porque es el primero en que todos sus comandos funcionan (`make mock` necesita las tablas de inventario y `make test` los *fixtures*). El CI no lo usa. Como fija cómo se lee `.env`, este ticket también hace que admita valores con espacios sin comillas: `HOGAR_NOMBRE` (HB-06) quedó comentada en `.env.example` porque `. ./.env` (`scripts/migrate.sh` y los atajos `dtest`, `dj` y `dpsql`) la rompe, y así el servidor del hogar puede poner su nombre real.

**Fuera de alcance:** la lógica de negocio (TK-02), las pantallas y la API, los usuarios de base de datos (HB-01 y HB-03) y las tablas de catálogo, entidades y pautas (HB-05 a HB-07).

**Criterios de aceptación**
- [ ] `python manage.py migrate` crea el esquema en una base vacía, y `migrate inventario zero` y `migrate conteos zero` lo revierten sin errores.
- [ ] `makemigrations --check` no detecta cambios pendientes.
- [ ] `make help` lista los 17 comandos, y `make migrate`, `make test` y `make mock` hacen lo mismo que sus comandos directos.
- [ ] Un valor con espacios y sin comillas en `.env`, como `HOGAR_NOMBRE=Hogar Gerontológico Demo`, funciona con `make`, con `scripts/migrate.sh` y los atajos, y con `docker compose`; `.env.example` lo trae sin comentar, y en una base nueva el Hogar queda con ese nombre.
- [ ] `\d movimiento` en `psql` muestra todas las restricciones e índices de las secciones 3.1 y 3.3 con sus nombres exactos.
- [ ] Sin índices duplicados: ninguna FK de la tabla de la sección 3.3 tiene un índice propio además del compuesto.
- [ ] El mock de la sección 3.4 se carga con `cargar_mock.sql` sin errores, y `SELECT count(*) FROM v_conciliacion_existencia` devuelve 0.
- [ ] Cada regla de la base de datos rechaza su caso inválido:

  | Caso | Resultado esperado |
  |---|---|
  | `UPDATE movimiento SET cantidad = 1 WHERE id = 1` | Error del *trigger*: "Los movimientos son inmutables…" |
  | `DELETE FROM movimiento WHERE id = 1` | Error del *trigger* |
  | Entrada sin `entidad_destino_id` | Viola `ck_movimiento_por_tipo` |
  | Baja sin `motivo_baja_id` | Viola `ck_movimiento_por_tipo` |
  | Transferencia con origen = destino | Viola `ck_movimiento_por_tipo` |
  | `cantidad = 0` | Viola `ck_movimiento_cantidad` |
  | Segunda corrección del mismo movimiento | Viola `uq_movimiento_corrige` |
  | `UPDATE existencia SET saldo = -1` | Viola `ck_existencia_saldo` |
  | Entrada a un residente egresado | Error de `tg_movimiento_validar_destino` |
  | Insertar un renglón en el conteo 1 (cerrado) | Error de `tg_detalle_conteo_cerrado` |
  | Desmarcar `activo` de un medicamento con existencias | Error de `tg_medicamento_baja`; en el panel, el mensaje del formulario |
  | `UPDATE detalle_conteo SET diferencia = 0` | Error: columna generada |
  | Como `app_user`: `UPDATE`, `DELETE` o `TRUNCATE` sobre `movimiento` | `permission denied for table movimiento` |
  | Como `app_user`: `ALTER TABLE movimiento DISABLE TRIGGER ALL` | `must be owner of table movimiento` |

- [ ] El dueño de todas las tablas es `app_owner`, y `app_user` conserva `SELECT` e `INSERT` sobre `movimiento` y los 4 permisos sobre las demás tablas.
- [ ] En una instalación nueva (`docker compose down -v` y `up`), los 2 usuarios se crean solos, y `scripts/migrate.sh` deja la base lista para que `web` arranque como `app_user`.

- [ ] Con datos sintéticos de un año (175,000 movimientos), `EXPLAIN (ANALYZE, BUFFERS)` de las consultas 1c y 2 de la sección 3.3 usa sus índices, sin *Seq Scan* sobre `movimiento`.

**Pruebas**
- `apps/inventario/tests/test_esquema.py` y `apps/conteos/tests/test_esquema.py`: un test por fila de la tabla anterior, con `pytest.raises(IntegrityError)` o `InternalError` y verificación del nombre de la restricción en el mensaje.
- Test de migraciones: aplicar y revertir hasta `zero` en CI.
- Test que comprueba que `admin.site` no tiene registrados `Movimiento`, `Existencia`, `ConteoFisico` ni `DetalleConteo`.
- `apps/accounts/tests/test_privilegios.py` (lo crea HB-03 con los tests de dueño y permisos generales): este ticket agrega los de `movimiento`. Consulta `has_table_privilege('app_user', 'movimiento', 'UPDATE' | 'DELETE' | 'TRUNCATE')` (falso) y `'INSERT'` (verdadero), y ejecuta las 2 filas de `app_user` de la tabla anterior con una conexión como `app_user` (`SET ROLE app_user` dentro de la transacción del test).
- CI: el servicio de PostgreSQL ejecuta `db/init/01_roles.sh` antes de los tests, igual que en desarrollo.
- Test de plan de ejecución: `connection.cursor().execute('EXPLAIN …')` y verificación del nombre del índice en el plan (marcado `@pytest.mark.lento`, corre en CI nocturno).

**Definición de hecho**
- [ ] Criterios de aceptación cumplidos y definición de hecho común.
- [ ] Migraciones revisadas línea por línea en el PR: el SQL generado (`sqlmigrate`) coincide con el DDL de las secciones 3.1 y 3.3.
- [ ] El `Makefile` y sus comandos documentados en la sección 1.4.
- [ ] El diagrama ER de la sección 3.1 sigue siendo fiel al esquema; si algo cambió, se actualizó.

**Riesgos**
- `GeneratedField` y `db_default` requieren Django ≥ 5.0: ya cubierto con Django 5.2 LTS.
- Los *triggers* no se ven desde el ORM: se mitigan con los tests de esquema y con la vista de conciliación.

---

**Ticket 2**

**TK-02 · [Backend] Servicio de movimientos de inventario: entradas, transferencias, bajas y correcciones**

| Campo | Valor |
|---|---|
| Tipo | Backend |
| Historia | HU-01 |
| Prioridad | Must, camino crítico |
| Estimación | **5 puntos** |
| Rama | `feature/TK-02-servicio-movimientos` |
| Depende de | TK-01 |

**Guía paso a paso:** [`docs/tickets/TK-02-servicio-movimientos.md`](docs/tickets/TK-02-servicio-movimientos.md).

**Contexto.** HU-01 exige que cada movimiento actualice el saldo de forma atómica, que ningún saldo quede negativo ni con usuarios concurrentes, y que los errores se corrijan con el movimiento inverso. Este ticket construye la capa `services.py`, que es **el único punto del sistema que escribe en `movimiento` y `existencia`**. Las pantallas de HU-01, el conteo de HU-03 y la API V2 la reutilizan.

**Descripción técnica**

**Tecnologías y librerías**

| Tecnología | Versión | Uso en este ticket |
|---|---|---|
| Python | 3.12 | `decimal.Decimal` para cantidades, `logging`, *type hints* |
| Django | 5.2 LTS | `transaction.atomic`, `select_for_update`, `bulk_create(ignore_conflicts=True)`, expresión `Now()` |
| PostgreSQL | 17 | Bloqueo de filas (`SELECT ... FOR UPDATE`), `INSERT ... ON CONFLICT DO NOTHING`, nivel de aislamiento *read committed* |
| pytest + pytest-django | Las del proyecto | `django_db(transaction=True, serialized_rollback=True)` para los tests con hilos |
| `threading` y `concurrent.futures` | Biblioteca estándar | Tests de concurrencia y de *deadlocks* |
| pytest-cov | Última estable, fijada en `requirements-dev.txt` | Cobertura de `services.py` y `exceptions.py` (**dependencia nueva de desarrollo**, si no estaba) |

1. **Excepciones de dominio** (`apps/inventario/exceptions.py`). Cada una lleva un `code` igual al del contrato de la API (sección 4.4) y un mensaje para el usuario:

   | Excepción | `code` | Cuándo |
   |---|---|---|
   | `ErrorInventario` | — | Base de todas |
   | `DatoInvalido` | `VALIDACION` | Falta un dato obligatorio (origen de la entrada, quién entregó) o tiene un valor no permitido (motivo inactivo) |
   | `CantidadInvalida` | `VALIDACION` | Subclase de `DatoInvalido`: cantidad ≤ 0, con más de 2 decimales o fuera de rango |
   | `ExistenciaInsuficiente` | `EXISTENCIA_INSUFICIENTE` | El origen no tiene saldo suficiente. Incluye el disponible |
   | `MismaEntidad` | `MISMA_ENTIDAD` | Transferencia con origen = destino |
   | `EntidadInactiva` | `ENTIDAD_INACTIVA` | Destino egresado o fallecido (salvo correcciones) |
   | `MedicamentoInactivo` | `MEDICAMENTO_INACTIVO` | Medicamento dado de baja (salvo correcciones) |
   | `MotivoReservado` | `MOTIVO_RESERVADO` | Baja manual con el motivo `CORRECCION` |
   | `MovimientoYaCorregido` | `MOVIMIENTO_YA_CORREGIDO` | El movimiento ya tiene corrección |
   | `MovimientoEsCorreccion` | `MOVIMIENTO_ES_CORRECCION` | Se intenta corregir una corrección |

2. **Servicios** (`apps/inventario/services.py`). Funciones con argumentos solo por nombre. Cada una corre en `transaction.atomic()` y devuelve el `Movimiento` creado:

   ```python
   def registrar_entrada(*, usuario, destino, medicamento, cantidad,
                         origen_entrada, entregado_por, nota="") -> Movimiento: ...
   def transferir(*, usuario, origen, destino, medicamento, cantidad, nota="") -> Movimiento: ...
   def dar_de_baja(*, usuario, origen, medicamento, cantidad, motivo, nota="") -> Movimiento: ...
   def corregir(*, usuario, movimiento, nota="") -> Movimiento: ...
   ```

3. **Bloqueo de saldos sin carreras ni *deadlocks*.** Una función privada asegura que la fila de `existencia` exista y la bloquea:

   ```python
   def _bloquear_saldos(medicamento, *entidades) -> dict[int, Existencia]:
       # 1) Crea las filas que falten sin carrera: INSERT ... ON CONFLICT DO NOTHING
       Existencia.objects.bulk_create(
           [Existencia(entidad=e, medicamento=medicamento) for e in entidades],
           ignore_conflicts=True)
       # 2) SELECT ... FOR UPDATE en orden fijo (entidad_id): dos transferencias
       #    cruzadas (Hogar→Carmen y Carmen→Hogar) no se bloquean mutuamente
       filas = (Existencia.objects.select_for_update()
                .filter(medicamento=medicamento, entidad__in=entidades)
                .order_by("entidad_id"))
       return {f.entidad_id: f for f in filas}
   ```

   Después se valida el saldo con la fila ya bloqueada (`ExistenciaInsuficiente` si no alcanza), se actualizan `saldo` y `actualizado_en` con `save(update_fields=[...])` y se inserta el movimiento, todo en la misma transacción.

4. **Reglas por operación:**
   - **Validaciones previas** (antes de tocar la base, para dar mensajes claros): cantidad `Decimal` > 0 con máximo 2 decimales, entidades y medicamento activos, motivo distinto de `CORRECCION`, origen ≠ destino.
   - **Corrección:**

     | Movimiento original | Corrección generada |
     |---|---|
     | `ENTRADA` a X | `BAJA` desde X, motivo `CORRECCION` |
     | `BAJA` desde X | `ENTRADA` a X, sin origen de entrada ni entregado por |
     | `TRANSFERENCIA` X → Y | `TRANSFERENCIA` Y → X |

     La corrección lleva `corrige_a` al original y la misma cantidad y medicamento. Si el saldo ya no alcanza (por ejemplo, la entrada errónea ya se consumió), se lanza `ExistenciaInsuficiente`. Las correcciones quedan exentas de la regla de entidad o medicamento activo.
   - **Carrera en la corrección:** si dos usuarios corrigen el mismo movimiento a la vez, el `IntegrityError` de `uq_movimiento_corrige` se traduce a `MovimientoYaCorregido`. No se usa `select_for_update` sobre `movimiento`: PostgreSQL exige permiso de `UPDATE` para `FOR UPDATE`, y `app_user` no lo tiene.
   - **Los tests corren como `app_user`** (`SET LOCAL ROLE app_user`), igual que en producción, para detectar cualquier operación que necesite un permiso que la aplicación no tiene.

5. **Autorización.** El servicio no decide permisos: las vistas usan `PermissionRequiredMixin` con `inventario.add_movimiento` (sección 2.5). El servicio recibe `usuario` solo para registrar quién hizo el movimiento.

6. **Registro de eventos:** `logger.info("movimiento_registrado", extra={"movimiento_id", "tipo", "usuario_id"})`, sin nombres de residentes (LFPDPPP).

**Fuera de alcance:** formularios, vistas y plantillas de HU-01 (TK-04), la API V2 y la idempotencia por `Idempotency-Key`. En el MVP el doble envío se resuelve en la pantalla (sección 4.1).

**Criterios de aceptación** (con el mock de la sección 3.4)
- [ ] `registrar_entrada` de 30 dosis de Eutirox a Carmen, origen `FAMILIAR`, entregado por "Rosa Torres": el saldo pasa de 33 a 63 y el movimiento guarda usuario, fecha y hora, origen y quien entregó.
- [ ] `transferir` 10 de Paracetamol del Hogar a Carmen: Hogar 80 → 70, Carmen 14 → 24, y se crea 1 solo movimiento.
- [ ] `transferir` a una entidad sin fila previa de `existencia` la crea con el saldo transferido.
- [ ] `dar_de_baja` de 5 Atorvastatina de María (saldo 1) lanza `ExistenciaInsuficiente` con `disponible = 1`, y no se crea nada.
- [ ] `dar_de_baja` con motivo `CORRECCION` lanza `MotivoReservado`.
- [ ] `transferir` del Hogar al Hogar lanza `MismaEntidad`.
- [ ] `corregir` la entrada errónea de 600 de Metformina de María crea una baja `CORRECCION` de 600 que la referencia. Si se intenta de nuevo, lanza `MovimientoYaCorregido`, y corregir esa baja lanza `MovimientoEsCorreccion`.
- [ ] Una cantidad de `0.5` se acepta; `0.555` lanza `CantidadInvalida`.
- [ ] **Concurrencia:** 2 bajas simultáneas de 1 Atorvastatina (saldo 1), en hilos con conexiones separadas: una se aplica, la otra lanza `ExistenciaInsuficiente`, y el saldo final es 0.
- [ ] **Sin *deadlocks*:** 20 transferencias cruzadas simultáneas Hogar ↔ Carmen terminan todas, y los saldos finales cuadran.
- [ ] **Atomicidad:** si falla la inserción del movimiento, después de descontar el origen, el saldo del origen no cambia.
- [ ] Después de cada test, `v_conciliacion_existencia` está vacía.

**Pruebas**
- `apps/inventario/tests/test_services.py`: un test por criterio, sobre el mock con los *fixtures* `demo` y `como_app_user` de TK-01.
- `apps/inventario/tests/test_concurrencia.py`: `@pytest.mark.django_db(transaction=True, serialized_rollback=True)` con `threading` y `connection.close()` en cada hilo.
- Un *fixture* `autouse` que verifica la vista de conciliación al terminar cada test del módulo.

**Definición de hecho**
- [ ] Criterios de aceptación cumplidos y definición de hecho común.
- [ ] Cobertura ≥ 90 % en `services.py` y 100 % de las ramas de `exceptions.py`.
- [ ] Ningún otro módulo escribe en `Movimiento` ni en `Existencia`: verificado con `grep` en el PR (solo `services.py`, los tests y las migraciones).
- [ ] *Docstring* de cada función pública con reglas, excepciones y un ejemplo.
- [ ] Los tests de concurrencia corren en CI contra PostgreSQL real, no contra SQLite.

**Riesgos**
- Los tests de concurrencia pueden ser intermitentes: se usan barreras (`threading.Barrier`) para que los hilos arranquen juntos y un tiempo límite por test.
- `select_for_update` exige estar dentro de una transacción: lo garantiza `transaction.atomic()`, y lo verifica un test que llama al helper fuera de una transacción y espera un error.

---

**Ticket 3**

**TK-03 · [Frontend] Pantalla de consulta de existencias con filtros en vivo y diseño para celular**

| Campo | Valor |
|---|---|
| Tipo | Frontend (plantillas Django + Bootstrap 5 + HTMX) |
| Historia | HU-02 |
| Prioridad | Must |
| Estimación | **3 puntos** |
| Rama | `feature/TK-03-pantalla-existencias` |
| Depende de | TK-01. TK-02 para probar con saldos reales; para desarrollar basta con el mock |

**Guía paso a paso:** [`docs/tickets/TK-03-pantalla-existencias.md`](docs/tickets/TK-03-pantalla-existencias.md).

**Contexto.** Es la pantalla que más se usará: responde "¿cuánto le queda a este residente?". Se consulta desde la computadora de la dirección y desde el celular, a pie de anaquel. Será la **página de inicio** después del login.

**Descripción técnica**

**Tecnologías y librerías**

| Tecnología | Versión | Uso en este ticket |
|---|---|---|
| Django | 5.2 LTS | `ListView`, `LoginRequiredMixin`, `PermissionRequiredMixin`, formularios, filtro de plantilla propio y la etiqueta `{% querystring %}` (Django 5.1+) |
| Bootstrap | 5.3.9 (de `base.html`, HB-08) | Rejilla *responsive*, tabla en escritorio y `list-group` en el celular, `d-md-none` / `d-md-table` |
| HTMX | 2.0.x, servido desde `static/` | `hx-get`, `hx-trigger` con espera, `hx-target`, `hx-push-url`, `hx-swap-oob`, `hx-indicator` |
| django-htmx | Última estable, fijada en `requirements.txt` | `request.htmx` y `HttpResponseClientRedirect` (**dependencia nueva**) |
| pytest-django | La del proyecto | Tests de selector y de vista (`client`, `CaptureQueriesContext`) |
| pytest-playwright + Chromium | Última estable, fijada en `requirements-dev.txt` | Pruebas de extremo a extremo: búsqueda en vivo, celular y teclado (**dependencia nueva de desarrollo**) |
| Lighthouse (Chrome DevTools) | El del navegador | Accesibilidad ≥ 90 |

1. **Consulta reutilizable** (`apps/inventario/selectors.py`): `buscar_existencias(*, entidad=None, medicamento=None, principio_activo=None, q=None, incluir_sin_saldo=False) -> QuerySet[Existencia]`.
   - `select_related("entidad", "entidad__residente", "medicamento", "medicamento__presentacion")`, para evitar N+1.
   - `q` busca en el nombre comercial y en los principios activos, con la expresión `f_unaccent(lower(...))` de la sección 3.3, para que se usen los índices trigram. El endpoint `GET /existencias` reutilizará esta función.
   - Orden: el Hogar primero (`entidad__tipo`: `HOGAR` < `RESIDENTE`), después el residente por apellido y nombre, y después el nombre comercial.

2. **Formulario de filtros** (`apps/inventario/forms.py`, `FiltroExistenciasForm`, por `GET`):

   | Campo | Control | Validación |
   |---|---|---|
   | `entidad` | `select`: "Todos", el Hogar y los residentes. Los egresados o fallecidos aparecen marcados, porque pueden tener sobrantes | Debe existir |
   | `principio_activo` | `select` | Debe existir |
   | `q` | `input type="search"`, `minlength=3`, `maxlength=100` | De 3 a 100 caracteres, recortado |
   | `incluir_sin_saldo` | `checkbox` "Incluir sin saldo" | Booleano |
   | `medicamento` | Oculto. Se llena al tocar el nombre de un medicamento en los resultados | Debe existir |

3. **Vista** (`apps/inventario/views.py`, `ExistenciasView`, `ListView`):
   - `LoginRequiredMixin` + `PermissionRequiredMixin("inventario.view_existencia")`: los 2 grupos pueden consultar.
   - Paginación de 20.
   - Si la petición viene de HTMX (`request.htmx`, de `django-htmx`), responde solo el fragmento `inventario/_resultados.html`. Si no, la página completa `inventario/existencias.html`, así la URL funciona sola, con el botón "Atrás" y al recargar.
   - Si `q` tiene 1 o 2 caracteres, responde la cabecera `HX-Reswap: none`, para que la lista no cambie, y muestra el aviso "Escribe al menos 3 caracteres" con `hx-swap-oob`.

4. **Interacción HTMX** en el formulario:

   ```html
   <form hx-get="{% url 'inventario:existencias' %}" hx-target="#resultados"
         hx-trigger="input changed delay:300ms from:#id_q, change"
         hx-push-url="true" hx-indicator="#cargando">
   ```

   - La búsqueda se lanza 300 ms después de dejar de escribir, y al cambiar un `select` o el *checkbox*.
   - `hx-push-url` mantiene los filtros en la URL, así se puede compartir o guardar.
   - El contenedor `#resultados` tiene `aria-live="polite"`, para que un lector de pantalla anuncie el cambio.
   - Sin JavaScript propio en línea: HTMX se sirve desde `static/`, compatible con la `Content-Security-Policy` de Nginx (sección 2.5).

5. **Diseño *responsive*** (Bootstrap 5):
   - **≥ 768 px:** tabla con Entidad · Medicamento (nombre, presentación y concentración) · Saldo · Último movimiento.
   - **< 768 px:** cada existencia es una tarjeta (`list-group`) con el medicamento en negritas, la entidad debajo y el saldo alineado a la derecha. No hay desplazamiento horizontal.
   - **Formato:** saldo con el filtro propio `dosis` (`10`, `0.5`, `62`, sin ceros sobrantes) y la palabra "dosis"; saldo 0 en gris con la etiqueta "Agotado". Fecha en formato `d/m/Y H:i`, hora de `America/Mexico_City`.
   - **Estado vacío:** "No hay existencias que coincidan con la búsqueda", con el botón "Limpiar filtros".
   - Controles táctiles de al menos 44 × 44 px y etiquetas `<label>` visibles en todos los campos.

6. **Navegación:** la entrada "Existencias" en el menú de `base.html`, y `LOGIN_REDIRECT_URL` apuntando a esta pantalla.

**Fuera de alcance:** el endpoint `GET /api/v1/existencias` (TK-05, que reutiliza el selector), la exportación y los botones de registrar movimientos en cada renglón (llegan con TK-04).

**Criterios de aceptación** (con el mock de la sección 3.4)
- [ ] Como `consulta.demo`, al buscar "losartan" aparecen 3 renglones en este orden: Hogar · Losartán 20, José Luis · Cozaar 32, José Luis · Losartán 10. Hyzaar no aparece.
- [ ] Al filtrar por Carmen Torres Vega aparecen Eutirox 33, Exelon 3 y Paracetamol 14.
- [ ] "paracetamol" con "Incluir sin saldo" muestra Hogar · Paracetamol 80, Hogar · Tempra 0 ("Agotado") y Carmen · Paracetamol 14.
- [ ] "ACIDO" encuentra Aspirina Protect (Hogar 58), sin importar mayúsculas ni acentos.
- [ ] Al escribir "lo" aparece el aviso y la lista anterior no cambia; no se hace la consulta a la base de datos.
- [ ] "ibuprofeno" muestra el estado vacío con "Limpiar filtros".
- [ ] Los resultados se actualizan sin recargar la página, y la URL refleja los filtros. Al abrir esa URL en otra pestaña se ve el mismo resultado.
- [ ] Sin sesión, la pantalla redirige al login y, después de iniciar sesión, vuelve a la consulta.
- [ ] En un viewport de 390 × 844 (celular) no hay desplazamiento horizontal y se ven las tarjetas en lugar de la tabla.
- [ ] Sin N+1: la página hace el mismo número de consultas a la base de datos con 1 resultado que con todas las existencias del mock (13).
- [ ] Con el mock, la respuesta del fragmento tarda menos de 300 ms en el servidor local.

**Pruebas**
- `apps/inventario/tests/test_selectors.py`: los casos de búsqueda anteriores directamente contra `buscar_existencias`.
- `apps/inventario/tests/test_views_existencias.py`:
  - Página completa contra fragmento (cabecera `HX-Request`).
  - `q` corto con `HX-Reswap: none`.
  - Redirección sin sesión.
  - Mismo número de consultas con 1 y con 20 resultados (`django_assert_num_queries`).
- `app/e2e/conftest.py`: el servidor de pruebas (`live_server`) corre como `app_user`.
- `app/e2e/test_existencias.py` (Playwright), sin errores de JavaScript ni violaciones de CSP en la consola:
  - Escribir "losartan" y esperar 3 renglones.
  - Viewport de celular: `document.documentElement.scrollWidth <= window.innerWidth`.
  - Navegación solo con teclado por los filtros.

**Definición de hecho**
- [ ] Criterios de aceptación cumplidos y definición de hecho común.
- [ ] Revisado en Chrome y Firefox de escritorio, y en Chrome de Android (o su emulación) a 390 px.
- [ ] Sin errores en la consola del navegador ni violaciones de la CSP.
- [ ] Lighthouse: Accesibilidad ≥ 90 en la pantalla.
- [ ] Capturas de escritorio y de celular agregadas al PR y a la sección 1.3 del `readme.md`.

**Riesgos**
- Que la búsqueda no use el índice si la expresión del ORM no coincide exactamente con la del índice: se cubre con el test de plan de ejecución de TK-01 aplicado al selector.
- Tablas con nombres largos en el celular: se resuelve con las tarjetas y con `text-break`.

---

#### Tickets de habilitación (HB-01 a HB-09)

Dejan lista la base sobre la que se construyen TK-01 a TK-07: contenedores, conexión segura a la base de datos, modelos de catálogo, residentes y pautas, y los habilitadores del panel `/admin/` (sección 5). Cada ticket tiene una guía paso a paso en [`docs/tickets/`](docs/tickets/) con tareas, archivos, código de referencia, tests con ejemplos, criterios de calidad, comandos de verificación y problemas frecuentes. Aplica además la definición de hecho común.

**Decisiones de diseño de la habilitación:**
- **Los 2 usuarios de base de datos existen desde el primer día** (HB-01 y HB-03), y no desde TK-01. Así la aplicación nunca corre como dueño de las tablas, y el CI, que ya los espera, funciona desde el primer ticket con código.
- **La conexión usa variables separadas** (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) y no una sola `DATABASE_URL`. Los tests y `migrate.sh` cambian solo el usuario y la contraseña para conectarse como `app_owner`, y las contraseñas con caracteres especiales no necesitan codificarse para una URL. Son las mismas variables del CI.
- **Nginx entra en la semana 1** (HB-04), para probar el login y el panel por HTTPS desde el principio, con la CSP real.
- **Las pautas solo tienen esquema** (HB-07): son *Could*, pero el dataset mock inserta pautas y TK-01 lo carga.
- **El CI activa cada *job* cuando existe lo que necesita** (sección 7.3, regla 5): `lint` e `imagen` con `app/manage.py` (HB-02), `tests` con `app/conftest.py` (HB-03) y `e2e` con `app/e2e/` (TK-03).

---

**HB-01 · [Infra] Servicio de PostgreSQL y usuarios de base de datos**

| Campo | Valor |
|---|---|
| Tipo | Infraestructura |
| Prioridad | Must, habilitador (semana 1) |
| Estimación | **2 puntos** |
| Rama | `feature/HB-01-postgresql` |
| Depende de | — |
| Guía | [`docs/tickets/HB-01-postgresql.md`](docs/tickets/HB-01-postgresql.md) |

**Descripción técnica.** Crea `docker-compose.yml` con **solo** el servicio `db` (sección 2.4.1): imagen `postgres:17-alpine`, volumen `pgdata`, red `backend`, *healthcheck* con `pg_isready` y ningún puerto publicado. Monta `db/init/` en `/docker-entrypoint-initdb.d/` (solo lectura), donde `01_roles.sh` crea `app_owner` (dueño de la base y del esquema `public`, con `CREATEDB` solo si `DB_OWNER_CREATEDB=true`) y `app_user` (solo `CONNECT` y `USAGE`), de forma idempotente. Agrega `.env.example` con `POSTGRES_*`, `DB_OWNER_PASSWORD`, `DB_OWNER_CREATEDB` y `DB_APP_PASSWORD`, y un `.gitattributes` que fuerza LF en los `.sh`. Compose falla con un mensaje claro si falta una contraseña (`${VAR:?}`).

**Criterios de aceptación**
- [ ] `docker compose up -d db` deja `db` en `healthy` en menos de 30 s.
- [ ] Con un volumen nuevo, `\du` muestra `app_owner` (`Create DB` en desarrollo) y `app_user` sin atributos.
- [ ] `app_owner` es dueño de la base `hogar` y del esquema `public`.
- [ ] `app_user` se autentica por TCP con la contraseña de `.env` y no puede crear tablas (`permission denied for schema public`).
- [ ] Ejecutar `01_roles.sh` por segunda vez no da error.
- [ ] `docker compose port db 5432` no muestra ningún puerto publicado, y los datos sobreviven a `docker compose restart db`.

**Definición de hecho**
- [ ] `.env` fuera del repositorio; `.env.example` solo con valores de ejemplo.
- [ ] `01_roles.sh` con fin de línea LF y permiso de ejecución en Git.
- [ ] Salida de `\du` y del `CREATE TABLE` rechazado en el PR.

---

**HB-02 · [Infra] Proyecto Django, imagen y servicio `web`**

| Campo | Valor |
|---|---|
| Tipo | Infraestructura |
| Prioridad | Must, habilitador (semana 1) |
| Estimación | **3 puntos** |
| Rama | `feature/HB-02-imagen-web` |
| Depende de | HB-01 |
| Guía | [`docs/tickets/HB-02-imagen-web.md`](docs/tickets/HB-02-imagen-web.md) |

**Descripción técnica.** Crea el proyecto Django 5.2 en `app/`, con la configuración separada en `config/settings/{base,local,prod}.py` (sección 2.3). `SECRET_KEY` (obligatoria), `DEBUG` y `ALLOWED_HOSTS` vienen del entorno, con `es-mx`, `America/Mexico_City` y `USE_TZ = True`. `DATABASES` todavía no se define: Django arranca con el backend `dummy` hasta HB-03. Agrega `requirements.txt` (Django, Gunicorn) y `requirements-dev.txt` (djLint, congelado en 1.50.4; pytest, pytest-django, pytest-cov, ruff) con versiones fijas, y `pyproject.toml` con la configuración de ruff y de djLint (perfil `django`, sin revisar `staticfiles/` ni `static/vendor/`). El `Dockerfile` (`python:3.12-slim`) instala primero las dependencias, solo instala las de desarrollo con `INSTALAR_DEV=true`, corre como el usuario sin privilegios `django` y arranca Gunicorn en el puerto 8000. En Compose, `web` monta `./app` y el volumen `static`, está en las redes `frontend` y `backend`, espera a `db` sana, recibe solo sus variables (sin contraseñas de PostgreSQL) y no publica puertos.

**Criterios de aceptación**
- [ ] `docker compose up -d` deja `db` sana y `web` corriendo; `manage.py check` no reporta problemas.
- [ ] Una petición a `http://localhost:8000/` desde el contenedor responde `404` de Django (Gunicorn atiende).
- [ ] `whoami` en `web` responde `django`, y `web` no publica puertos.
- [ ] `web` alcanza `db:5432` por la red `backend` y no recibe `POSTGRES_PASSWORD` ni `DB_OWNER_PASSWORD`.
- [ ] Sin `SECRET_KEY` en `.env`, Compose se niega a arrancar con un mensaje claro.
- [ ] La imagen construida con `INSTALAR_DEV=false` (la del CI) no contiene pytest.
- [ ] En el PR, el CI corre `lint` y `build de la imagen` en verde, y `tests` y `e2e` aparecen saltados.
- [ ] `djlint . --check` lee `[tool.djlint]` de `pyproject.toml` y, sin plantillas todavía, responde `No files to check!`; el paso de djLint del CI se omite.

**Definición de hecho**
- [ ] Versiones fijadas anotadas en el PR.
- [ ] `ruff check` y `ruff format --check` sin errores.

---

**HB-03 · [Infra/BD] Integración de Django con PostgreSQL**

| Campo | Valor |
|---|---|
| Tipo | Infraestructura y base de datos |
| Prioridad | Must, habilitador (semana 1) |
| Estimación | **3 puntos** |
| Rama | `feature/HB-03-conexion-bd` |
| Depende de | HB-02 |
| Guía | [`docs/tickets/HB-03-conexion-bd.md`](docs/tickets/HB-03-conexion-bd.md) |

**Descripción técnica.** Configura `DATABASES` desde `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`. En Compose, `web` se conecta como `app_user`. Crea `scripts/migrate.sh`, que ejecuta `migrate` como `app_owner`. Agrega `psycopg[binary]` y `Django[argon2]`. Crea la app `accounts` con el modelo `Usuario(AbstractUser)` (tabla `usuario`, sección 3.2, D1) y `AUTH_USER_MODEL = "accounts.Usuario"` **antes del primer `migrate`**. Configura Argon2 como *hasher* principal (PBKDF2 se conserva para el mock) y los validadores de contraseña (mínimo 10 caracteres). Crea la migración `accounts/0002_privilegios.py`: `app_user` recibe `SELECT`, `INSERT`, `UPDATE` y `DELETE` sobre todas las tablas, también las futuras (`ALTER DEFAULT PRIVILEGES`). Configura pytest en `pyproject.toml` (marcadores `lento`, `http`, `integracion`, `infra` y `e2e` con `--strict-markers`) y la cobertura (`[tool.coverage]`: solo `apps/`, con ramas, sin migraciones ni tests), y crea `conftest.py`, que activa el *job* `tests` del CI, y `pruebas.py`, con el helper `ejecutar_sql`.

**Criterios de aceptación**
- [ ] En una base nueva, `./scripts/migrate.sh` aplica `accounts.0001_initial` y `0002_privilegios` sin errores.
- [ ] Desde `web`, `SELECT current_user` devuelve `app_user`; `dj migrate` falla por falta de permisos (las migraciones solo corren con `migrate.sh`).
- [ ] Todas las tablas son de `app_owner`; `app_user` tiene los 4 permisos sobre ellas y no puede crear tablas.
- [ ] Una tabla creada por `app_owner` después de `0002` nace con los permisos de `app_user`.
- [ ] Las contraseñas nuevas se guardan con Argon2, y un *hash* PBKDF2 del mock se valida.
- [ ] `migrate accounts 0001` revierte los privilegios y `migrate` los vuelve a aplicar.
- [ ] El *job* `tests` del CI corre y pasa, con cobertura ≥ 80 % en `apps/`.

**Definición de hecho**
- [ ] Ninguna contraseña en el código: solo `os.environ`.
- [ ] Salida de `showmigrations accounts` y de `current_user` en el PR.

---

**HB-04 · [Infra] Nginx con HTTPS local**

| Campo | Valor |
|---|---|
| Tipo | Infraestructura |
| Prioridad | Must, habilitador (semana 1) |
| Estimación | **2 puntos** |
| Rama | `feature/HB-04-nginx` |
| Depende de | HB-03 |
| Guía | [`docs/tickets/HB-04-nginx.md`](docs/tickets/HB-04-nginx.md) |

**Descripción técnica.** Agrega el servicio `nginx` (`nginx:1.30.7-alpine`, red `frontend`, puertos 80 y 443, el único contenedor que publica puertos) con `nginx/default.conf`. Redirige 80 → 443, termina TLS 1.2+ con el certificado de `mkcert` (`nginx/certs/`, fuera del repositorio), sirve `/static/` desde el volumen `static` y reenvía el resto a `web:8000` con `X-Forwarded-For` y `X-Forwarded-Proto`. Aplica las cabeceras de la sección 2.5: HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options`, `Referrer-Policy` y una `Content-Security-Policy` de solo recursos propios, y oculta las que repite Django. Django envía la misma política CSP (`CONTENT_SECURITY_POLICY` y un *middleware*), para que las pruebas sin nginx la apliquen. En Django: `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS` desde el entorno y *cookies* `Secure`. En `prod.py` se silencian los avisos de HSTS y redirección, porque los hace nginx.

**Criterios de aceptación**
- [ ] `http://localhost/` responde `301` a `https://localhost/`.
- [ ] `https://localhost/admin/login/` responde `200` con las 5 cabeceras de seguridad, y el certificado es de confianza en el equipo de desarrollo.
- [ ] `/static/admin/css/base.css` lo sirve nginx (sin pasar por Django).
- [ ] Solo `nginx` publica puertos, y `nginx` no alcanza a `db`.
- [ ] El Administrador de HB-03 entra al panel por HTTPS sin error de CSRF ni violaciones de CSP en la consola.
- [ ] Django reconoce HTTPS por la cabecera de nginx y rechaza formularios de otro origen (`403`).
- [ ] Django envía la misma política CSP que nginx (un test del CI compara las 2), y por HTTPS llega una sola cabecera CSP.

**Definición de hecho**
- [ ] `nginx -t` sin errores; certificados fuera del repositorio.
- [ ] Cabeceras y tabla de puertos en el PR.

---

**HB-05 · [BD] Catálogo de medicamentos (D2)**

| Campo | Valor |
|---|---|
| Tipo | Base de datos |
| Prioridad | Must, habilitador (semana 2) |
| Estimación | **3 puntos** |
| Rama | `feature/HB-05-catalogo` |
| Depende de | HB-03 |
| Guía | [`docs/tickets/HB-05-catalogo.md`](docs/tickets/HB-05-catalogo.md) |

**Descripción técnica.** Crea la app `catalogo`. Su primera migración instala `btree_gist`, `pg_trgm` y `unaccent`, y crea la función `f_unaccent` (sección 3.1); depende de `accounts.0002_privilegios`. Modelos `Presentacion`, `PrincipioActivo`, `Medicamento` y la tabla puente `MedicamentoPrincipioActivo`, con los nombres de la sección 3.2. Restricciones en `Meta.constraints`, que el panel valida antes de llegar a la base: `uq_medicamento_nombre_pres_conc` y `uq_principio_activo_nombre` (únicos por expresión `f_unaccent(lower(...))`, con mensaje), `ck_medicamento_tipo`, `ck_medicamento_textos`, `ck_principio_activo_nombre`, `ck_presentacion_nombre` y `uq_mpa_medicamento_principio`. Índices `ix_medicamento_nombre_trgm` (GIN parcial, `WHERE activo`), `ix_principio_activo_trgm` e `ix_mpa_principio_medicamento`, sin índices duplicados sobre las FK de la tabla puente. Migración de datos con las 8 presentaciones. Crea `apps/expresiones.py` con `sin_acentos()` (la expresión exacta de los índices) y `no_vacio()`.

**Criterios de aceptación**
- [ ] `\dx` muestra las 3 extensiones, y `f_unaccent(lower('Losartán'))` devuelve `losartan`.
- [ ] `\d medicamento` muestra todas las restricciones e índices con sus nombres exactos.
- [ ] "LOSARTAN 50 MG tableta" se rechaza si existe "Losartán 50 mg tableta"; con `full_clean()` el error es un mensaje, no una excepción de la base.
- [ ] Textos solo con espacios y tipos fuera de `GENERICO`/`ORIGINAL` se rechazan en la base.
- [ ] El plan de ejecución de la búsqueda por nombre desde el ORM usa `ix_medicamento_nombre_trgm` (test `lento`).
- [ ] Existen las 8 presentaciones semilla, y `migrate catalogo zero` revierte todo.

**Definición de hecho**
- [ ] `sqlmigrate` revisado contra las secciones 3.1 y 3.3.
- [ ] Salida de `\d medicamento` y del test `lento` en el PR.

---

**HB-06 · [BD] Entidades: el Hogar y los residentes (D3)**

| Campo | Valor |
|---|---|
| Tipo | Base de datos |
| Prioridad | Must, habilitador (semana 2) |
| Estimación | **3 puntos** |
| Rama | `feature/HB-06-entidades` |
| Depende de | HB-05 |
| Guía | [`docs/tickets/HB-06-entidades.md`](docs/tickets/HB-06-entidades.md) |

**Descripción técnica.** Crea la app `entidades` con `Entidad` (supertipo) y `Residente` (subtipo, con la misma clave). Restricciones `uq_entidad_un_hogar`, `uq_entidad_id_tipo`, `ck_entidad_tipo`, `ck_entidad_nombre`, `ck_entidad_nombre_no_vacio`, `ck_residente_tipo`, `ck_residente_estado`, `ck_residente_baja`, `ck_residente_fechas`, `ck_residente_nombres` y `ck_residente_nacimiento` (secciones 3.1 y 3.3), y el índice `ix_residente_nombre`. La FK compuesta `fk_residente_entidad (entidad_id, tipo) → entidad (id, tipo)` va en una migración `RunSQL`, porque Django no declara FK compuestas. Una migración de datos crea el Hogar con el nombre de `HOGAR_NOMBRE` (por defecto, "Hogar Gerontológico Demo"). Provee el punto de integración 11: `Entidad.activa` y `Entidad.__str__`. El alta pasa por `services.registrar_residente()`, que crea la entidad y el residente en una sola transacción.

**Criterios de aceptación**
- [ ] La migración crea un solo Hogar, con `id = 1` en una base nueva; un segundo Hogar viola `uq_entidad_un_hogar`.
- [ ] Un residente no puede colgar del Hogar (`fk_residente_entidad`).
- [ ] Cada `CHECK` de entidad y residente rechaza su caso inválido (un test por restricción).
- [ ] `activa` es verdadero para el Hogar y para los residentes `ACTIVO`, y falso para `EGRESADO` y `FALLECIDO`; `str()` devuelve el nombre del Hogar o "Carmen Torres Vega", sin los nombres vacíos.
- [ ] `registrar_residente()` con datos inválidos lanza `ValidationError` y no deja una entidad suelta; funciona como `app_user`.
- [ ] `migrate entidades zero` revierte todo.

**Definición de hecho**
- [ ] `sqlmigrate` revisado contra las secciones 3.1 y 3.3.
- [ ] Salida de `\d residente` y de la fila del Hogar en el PR.

---

**HB-07 · [BD] Esquema de pautas (D6)**

| Campo | Valor |
|---|---|
| Tipo | Base de datos |
| Prioridad | Must como esquema (el mock lo necesita); las pantallas de pautas son *Could* |
| Estimación | **2 puntos** |
| Rama | `feature/HB-07-pautas` |
| Depende de | HB-06 |
| Guía | [`docs/tickets/HB-07-pautas.md`](docs/tickets/HB-07-pautas.md) |

**Descripción técnica.** Crea la app `pautas` con el modelo `Pauta` (sección 3.2, D6): `dosis` `numeric(6,2)`, `frecuencia_horas` `smallint` y la vigencia `fecha_inicio`/`fecha_fin`. Restricciones `ck_pauta_dosis`, `ck_pauta_frecuencia`, `ck_pauta_fechas` y la de exclusión `ex_pauta_sin_traslape` (`ExclusionConstraint` con `daterange(..., '[]')`, sobre `btree_gist`). Índices `ix_pauta_vigente` (parcial) e `ix_pauta_residente_inicio`, sin índice propio sobre `residente_id`. Migración `RunSQL` con `fn_pauta_validar` + `tg_pauta_validar` (sección 3.3). Sin pantallas y sin registro en `/admin/`.

**Criterios de aceptación**
- [ ] `\d pauta` muestra las restricciones, los 2 índices y el *trigger* con sus nombres exactos.
- [ ] Dosis 0, frecuencia 0 o 169 y fin anterior al inicio se rechazan.
- [ ] 2 pautas traslapadas del mismo residente y medicamento se rechazan (también si una termina el día en que empieza la otra); cerrar la vigente permite registrar la nueva.
- [ ] No se registran pautas de residentes egresados ni de medicamentos dados de baja.
- [ ] `migrate pautas zero` revierte todo.

**Definición de hecho**
- [ ] Salida de `\d pauta` en el PR.

---

**HB-08 · [Backend/Frontend] Login, grupos y usuarios**

| Campo | Valor |
|---|---|
| Tipo | Backend y frontend |
| Prioridad | Must, habilitador (semana 2) |
| Estimación | **3 puntos** |
| Rama | `feature/HB-08-login-grupos` |
| Depende de | HB-04, HB-06 |
| Guía | [`docs/tickets/HB-08-login-grupos.md`](docs/tickets/HB-08-login-grupos.md) |

**Descripción técnica.** Página de inicio de sesión propia en `/accounts/login/` y cierre de sesión por `POST`, con la plantilla común `base.html` (Bootstrap 5.3.9 servido desde `static/`, sin CDN ni JavaScript en línea, por la CSP), que heredarán todas las pantallas. Migración de datos con los 2 grupos: **Solo lectura** recibe `view_*` y **Lectura y escritura** `view_*`, `add_*` y `change_*`, sobre los modelos del catálogo y de residentes. Nadie recibe `delete_*`. Migración `RunSQL` con `uq_usuario_un_grupo`. En el panel, `UsuarioAdmin` exige exactamente un grupo a quien no es Administrador, le activa `is_staff` y no permite borrar usuarios; los grupos no se crean ni se borran a mano. Seguridad de la sección 2.5: `django-axes` bloquea la cuenta 15 min tras 5 intentos fallidos, y la sesión expira tras 30 min de inactividad y al cerrar el navegador.

**Criterios de aceptación**
- [ ] `/` lleva al login; con credenciales correctas se entra al panel y con incorrectas aparece "Usuario o contraseña incorrectos".
- [ ] Existen exactamente los 2 grupos con sus permisos; ninguno tiene `delete_*` ni permisos sobre usuarios.
- [ ] Un usuario no puede tener 2 grupos (`uq_usuario_un_grupo`), y el formulario del panel avisa si se elige ninguno o más de uno.
- [ ] Solo el Administrador ve "Usuarios" y "Grupos" (`403` para los demás), y nadie borra usuarios.
- [ ] El sexto intento tras 5 contraseñas incorrectas responde `429` con el mensaje de cuenta bloqueada.
- [ ] El login tiene `<label>` en cada campo, se usa bien a 390 px y no tiene violaciones de CSP.
- [ ] Las plantillas (`base.html`, `login.html`, `bloqueado.html`) pasan `djlint --check` y `djlint --lint`; desde este ticket el CI corre djLint.

**Definición de hecho**
- [ ] Capturas del login en escritorio y celular en el PR.
- [ ] Versión de `django-axes` fijada y anotada.

---

**HB-09 · [Panel] Catálogo y residentes en `/admin/`**

| Campo | Valor |
|---|---|
| Tipo | Panel de administración |
| Prioridad | Must, habilitador (semana 2) |
| Estimación | **2 puntos** |
| Rama | `feature/HB-09-admin-catalogo-residentes` |
| Depende de | HB-08 |
| Guía | [`docs/tickets/HB-09-admin-catalogo-residentes.md`](docs/tickets/HB-09-admin-catalogo-residentes.md) |

**Descripción técnica.** Registra en el panel `Presentacion`, `PrincipioActivo`, `Medicamento` (con sus principios activos en línea, al menos uno, con *autocomplete*) y `Residente`, con los "Controles" de la sección 5: sin la acción "Eliminar" (la baja es lógica), búsqueda sin mayúsculas ni acentos con `f_unaccent(lower(...))`, filtros por estado, tipo y presentación, y sin consultas N+1 en las listas. El alta de residentes llama a `registrar_residente()` y no pide el estado; el egreso o la defunción se registran cambiando `estado` y `fecha_baja`. `Entidad` no se registra: el Hogar es fijo. Las reglas comunes viven en `apps/panel.py`.

**Criterios de aceptación**
- [ ] *Solo lectura* consulta el catálogo y los residentes (`200`), pero no da de alta ni cambia nada (`403`).
- [ ] *Lectura y escritura* da de alta un medicamento con su principio activo en la misma pantalla; sin principio activo, el formulario avisa.
- [ ] Un duplicado sin acentos y un egreso sin fecha de baja muestran un mensaje junto al formulario, nunca un `500`.
- [ ] Desmarcar `activo` da de baja un medicamento; nadie puede borrar (`403`, incluido el Administrador).
- [ ] Buscar "losartan" encuentra "Losartán" por nombre y por principio activo; "hernandez" encuentra "Hernández".
- [ ] El alta de un residente crea su entidad `RESIDENTE` y lo deja `ACTIVO`.

**Definición de hecho**
- [ ] Capturas del alta de un medicamento y del mensaje de duplicado en el PR.
- [ ] Sin violaciones de CSP en el panel.

**Documentación proceso para esta seccion:** [06-tickets-trabajo.md](06-tickets-trabajo.md)
