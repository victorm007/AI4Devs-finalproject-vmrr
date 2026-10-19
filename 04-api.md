# 04 - Especificación de la API (sesión con Claude)

> Transcripción de la sesión de diseño de la API REST con Claude, que actúa como arquitecto de software especialista en diseño e implementación de APIs REST.

---

## Prompt 1 — Usuario

Definamos la API REST. Como arquitecto de software especialista en el diseño e implementación de APIs REST, diseña la API REST y todos los endpoints necesarios para el sistema de Gestión de Medicamentos del Hogar Gerontológico.

Considera estos requisitos:
- **Endpoints** para las operaciones detalladas en los requisitos funcionales:

| # | Funcionalidad |
|---|---|
| 1 | Inicio de sesión y 2 niveles de acceso |
| 2 | Catálogo de medicamentos (alta, baja y cambio), con principio activo, presentación y búsqueda sin acentos |
| 3 | Residentes (alta, baja y cambio), con el Hogar como entidad fija |
| 4 | Movimientos: entrada (con quién entregó), transferencia, baja con motivo y corrección |
| 5 | Consulta de existencias filtrada por paciente, medicamento o principio activo |
| 6 | Conteo físico simple: capturar lo que hay físicamente, ver la diferencia contra lo registrado y cerrar el conteo |
| 7 | Reporte mensual en pantalla: movimientos y saldos por mes |

- Especificación OpenAPI 3.2.0.
- Validaciones de petición y respuesta.
- Códigos de error detallados.
- Ejemplos realistas para tests.

Esto es enfocado a un MVP.

---

## Respuesta 1 — Claude

Diseñé la API completa del MVP. El contrato está en `docs/api/openapi.yaml` y la sección 4 del `readme.md` lo documenta.

**Contrato (`docs/api/openapi.yaml`, OpenAPI 3.2.0):**
- **27 rutas, 34 operaciones, 57 esquemas y 21 parámetros**, organizados en 9 *tags*.
- Validado con **Redocly CLI**: 0 errores y 2 advertencias intencionales (un ejemplo inválido a propósito para provocar el `400`, y `GET /auth/csrf` sin respuestas 4XX).
- Usa lo propio de 3.2: `summary` en los *tags* y `dataValue` en los ejemplos. Los esquemas son JSON Schema 2020-12, con tipos `[string, 'null']`.
- Cada operación declara su nivel en `x-nivel-acceso`.

**Sección 4 del readme:**
- **4.1 Convenciones:**
  - URL `/api/v1`, campos en español y cantidades decimales en dosis.
  - Paginación `pagina` / `por_pagina` y búsqueda `q` sin acentos.
  - Peticiones estrictas (`additionalProperties: false`).
  - Baja lógica con acciones explícitas y movimientos inmutables (`405`).
  - `Idempotency-Key` contra el doble envío, y respuestas de movimientos con los saldos resultantes.
- **4.2 Autenticación:** sesión de Django más CSRF, y la tabla de niveles de acceso.
- **4.3** Tabla de todos los endpoints por funcionalidad y nivel.
- **4.4 Errores:**
  - Problem Details (RFC 9457) con `code` estable y `errores[]` por campo.
  - Catálogo de 24 códigos con su HTTP y el criterio 409 contra 422.
- **4.5** Los 3 endpoints principales en formato OpenAPI, con petición y respuesta: transferencia, consulta de existencias y captura del conteo.
- **4.6** **24 casos de prueba** sobre el dataset mock, con resultado esperado.
- **4.7 Implementación:**
  - Django REST Framework sobre `services.py`.
  - Un manejador de excepciones que produce Problem Details.
  - Tests de contrato con `jsonschema`.
  - Una nota sobre el soporte de OpenAPI 3.2 en las herramientas.

**Decisiones de diseño (a validar):**
1. **La API pasa de "3 endpoints de solo lectura" a una API completa de lectura y escritura**, como pide este prompt. Esto contradice lo documentado en la sección 2 (2.1, 2.2, 2.4.1, 2.5 y 2.6), que habrá que actualizar.
2. **`Idempotency-Key`** en los `POST` de movimientos. Requiere una tabla pequeña (`clave_idempotencia`) que no está en el modelo de datos de la sección 3.
3. **La corrección la calcula el servidor:** `POST /movimientos/{id}/correccion` genera el inverso. Un movimiento se corrige una sola vez y una corrección no se corrige.
4. **Criterio 409 contra 422:** `409` cuando hay un choque con el estado del recurso, `422` cuando se viola una regla de negocio.
5. **Autenticación por sesión de Django más CSRF**, en lugar de tokens o JWT: es coherente con la arquitectura y no hay clientes externos.
6. **La gestión de usuarios queda en `/admin/`**, fuera de la API del MVP.
7. **El conteo se captura con `PUT` idempotente por medicamento**, y la foto de `cantidad_sistema` se toma en cada captura.

---

## Prompt 2 — Usuario

¿Es viable hacer un MVP con solo 3 endpoints?

---

## Respuesta 2 — Claude

Sí, es viable. Con la arquitectura que ya definimos, es incluso lo más natural.

**Por qué funciona:** en la sección 2 decidimos que la aplicación **genera las páginas en el servidor** con Django y HTMX. Las 7 funcionalidades del MVP se hacen desde **pantallas web con formularios**, que llaman directamente a `services.py`, sin pasar por la API. En el MVP la API sirve para dos cosas:
- **La entrega del curso:** la sección 4 pide "máximo 3 endpoints".
- **Integraciones futuras**, por ejemplo una app móvil o un tablero.

**Los 3 endpoints que propongo (solo lectura):**

| Endpoint | Funcionalidad | Por qué este |
|---|---|---|
| `GET /existencias` | 5. Existencias por paciente, medicamento o principio activo | Es la consulta más valiosa del sistema |
| `GET /medicamentos?q=` | 2. Búsqueda sin acentos por nombre o principio activo | Muestra la búsqueda optimizada de la sección 3.3 |
| `GET /reportes/mensual` | 7. Movimientos y saldos del mes | Es la salida que pide la dirección |

Coinciden con lo que ya dice la sección 2: "3 endpoints JSON de solo lectura".

**Qué ganas y qué pierdes:**

| Con 3 endpoints de solo lectura | Con la API completa (34 operaciones) |
|---|---|
| ✅ La sección 2 no cambia: no hay contradicción | ❌ Hay que actualizar 5 apartados de la sección 2 |
| ✅ Sin escrituras por API: no hace falta CSRF en la API ni la tabla de idempotencia | ❌ Más superficie de seguridad y una tabla nueva |
| ✅ Menos código y menos tests: 3 vistas de DRF | ❌ 34 operaciones que implementar, probar y mantener |
| ✅ Las reglas viven solo en `services.py`, que usan las pantallas | ✅ También las comparte, pero hay más puntos de entrada |
| ❌ Una app móvil o un sistema externo no podría registrar movimientos | ✅ Lista para cualquier cliente |

**El doble envío desde el celular** sigue siendo un riesgo en los formularios web. Se resuelve sin tabla nueva: se redirige después de guardar (patrón *Post/Redirect/Get*) y el botón se desactiva al enviar.

**Qué haría con lo que ya está diseñado:** no lo tiraría. El contrato completo es trabajo útil para la versión 2. Propongo:
1. **Marcar el alcance en `openapi.yaml`** con una extensión `x-alcance` en cada operación.
2. **Cambiar la sección 4.5** para que muestre los 3 endpoints de solo lectura.
3. **Reducir la tabla de casos de prueba (4.6)** a los de esos 3 endpoints.
4. **La sección 2 se queda como está.**

---

## Prompt 3 — Usuario

Excelente respuesta. Sí, deja los 3 endpoints en el MVP y el resto marcado para después, la V2. Entonces registra el prompt anterior con tus respuestas, y ejecuta las acciones que propones para este MVP de 3 endpoints:
1. Marcar el alcance en `openapi.yaml`.
2. Cambiar la sección 4.5.
3. Reducir la tabla de casos de prueba.

Además, reformula las 7 preguntas anteriores, solo las que apliquen.

---

## Respuesta 3 — Claude

**Acciones realizadas:**
1. **`openapi.yaml`:**
   - Cada operación tiene ahora la extensión **`x-alcance`**: `MVP` en las 3 de solo lectura (`listarExistencias`, `listarMedicamentos`, `obtenerReporteMensual`) y `V2` en las otras 31.
   - La descripción general explica el alcance.
   - Sigue validando con Redocly: 0 errores, y las 2 advertencias intencionales quedan en operaciones `V2`.
2. **Sección 4 del readme**, reescrita según el alcance:
   - La introducción explica por qué 3 endpoints.
   - **4.1** tiene una columna de alcance por convención y aclara cómo se resuelve el doble envío en la web.
   - **4.2** explica que el MVP usa la sesión del login web, sin endpoints de autenticación.
   - **4.3** tiene una columna de alcance.
   - **4.4** lista los errores que pueden dar los endpoints del MVP (400, 401, 404, 405 y 500) y resume los de `V2`.
   - **4.5** ahora muestra `GET /existencias`, `GET /medicamentos` y `GET /reportes/mensual`, con su OpenAPI, petición y respuesta. El reporte de octubre de María muestra la corrección del 600.
   - **4.7** describe la implementación del MVP con 3 `ListAPIView`.
3. **Casos de prueba (4.6):** quedaron **16 casos** de los 3 endpoints. Las reglas de escritura se prueban desde `services.py` y las pantallas web.
4. **Ajuste de coherencia en la sección 2.6:** el caso de prueba de la API ahora usa `GET /api/v1/existencias?entidad_id=<id>` y espera `401` sin sesión, como define el contrato. También lo actualicé en el anexo de `02-arquitectura.md`.

**Preguntas reformuladas.** Solo quedan las que aplican al MVP de 3 endpoints. Se descartan:
- La contradicción con la sección 2: ya no existe.
- La gestión de usuarios en `/admin/`: ya estaba decidida en la sección 2.
- El criterio 409 contra 422: solo aplica a `V2`.

1. **Autenticación de la API del MVP:** la API usa la misma sesión del login web (cookie `sessionid`), sin endpoints `/auth` ni tokens. Cualquier usuario autenticado, de cualquier nivel, puede consultar los 3 endpoints. Los clientes externos con login propio quedan para `V2`. ¿De acuerdo?
2. **Doble envío en las pantallas web:** se resuelve con *Post/Redirect/Get* y desactivando el botón al enviar, **sin la tabla `clave_idempotencia`**. Así el modelo de datos de la sección 3 no cambia. ¿De acuerdo?
3. **Corrección desde la pantalla web:** el usuario elige el movimiento a corregir y escribe el motivo; `services.py` calcula y registra el movimiento inverso. Cada movimiento se corrige una sola vez y una corrección no se corrige. ¿De acuerdo?
4. **Conteo desde la pantalla web:** la foto del saldo registrado (`cantidad_sistema`) se toma al capturar cada renglón, no al crear el conteo. Si se vuelve a capturar un renglón, la foto se actualiza. ¿De acuerdo?

---

## Prompt 4 — Usuario

De acuerdo en todas las preguntas. Haz commit.

---

## Respuesta 4 — Claude

Quedan confirmadas las 4 decisiones:
1. La API del MVP usa la sesión del login web, para cualquier nivel de acceso.
2. El doble envío se evita con *Post/Redirect/Get* y desactivando el botón, sin la tabla `clave_idempotencia`.
3. La corrección la calcula `services.py`: una sola vez por movimiento, y una corrección no se corrige.
4. La foto del saldo del conteo se toma al capturar cada renglón.

El texto del `readme.md` ya las presentaba como definitivas, así que no cambia. Hice el commit con el contrato OpenAPI, la sección 4 y esta transcripción.

---

## Anexo — Texto final escrito en `readme.md` (sección 4)

## 4. Especificación de la API

> Si tu backend se comunica a través de API, describe los endpoints principales (máximo 3) en formato OpenAPI. Opcionalmente puedes añadir un ejemplo de petición y de respuesta para mayor claridad

**Alcance del MVP: 3 endpoints de solo lectura.** La aplicación genera sus páginas en el servidor (sección 2), así que las 7 funcionalidades del MVP se operan desde **pantallas web**, que llaman directamente a `services.py`. En el MVP la API REST expone solo las 3 consultas de mayor valor, para integraciones y para documentar el contrato:

| Endpoint | Funcionalidad | Por qué este |
|---|---|---|
| `GET /existencias` | 5. Existencias por paciente, medicamento o principio activo | Es la consulta más valiosa del sistema |
| `GET /medicamentos?q=` | 2. Búsqueda sin acentos por nombre o principio activo | Usa la búsqueda optimizada de la sección 3.3 |
| `GET /reportes/mensual` | 7. Movimientos y saldos del mes | Es la salida que pide la dirección |

**Contrato completo:** [`docs/api/openapi.yaml`](docs/api/openapi.yaml), escrito en **OpenAPI 3.2.0** con un enfoque *design-first*. Tiene 27 rutas y 34 operaciones, y cada operación declara su alcance en la extensión **`x-alcance`**:
- **`MVP`**: los 3 endpoints anteriores.
- **`V2`**: las otras 31, que quedan **diseñadas para una versión posterior** con clientes externos, por ejemplo una app móvil. Incluyen autenticación, altas, movimientos y conteos por API.

Se validó con **Redocly CLI** (`npx @redocly/cli lint docs/api/openapi.yaml`): **0 errores**. Quedan 2 advertencias intencionales, las dos en operaciones `V2`:
- Un ejemplo de petición inválido a propósito, para provocar el error `400`.
- `GET /auth/csrf` no tiene respuestas 4XX.

#### 4.1. Convenciones

| Aspecto | Decisión | Alcance |
|---|---|---|
| URL base | `https://{host}/api/v1`. La versión va en la ruta | MVP |
| Formato | JSON UTF-8, campos en `snake_case` y en español (iguales al modelo de datos) | MVP |
| Cantidades | En **dosis**, `number` con hasta 2 decimales (`multipleOf: 0.01`), por ejemplo 0.5 tableta | MVP |
| Fechas | `YYYY-MM-DD`. Fecha y hora en ISO 8601 con zona: `2026-10-01T10:00:00-06:00` | MVP |
| Paginación | `?pagina=1&por_pagina=20` (máximo 100). Respuesta `{ total, pagina, por_pagina, resultados[] }` | MVP |
| Búsqueda | `q` con un mínimo de 3 caracteres, parcial, sin mayúsculas ni acentos: usa los índices trigram de la sección 3.3 | MVP |
| Solo lectura | Los endpoints del MVP solo aceptan `GET`; cualquier otro método responde `405` | MVP |
| Peticiones estrictas | `additionalProperties: false`: un campo desconocido responde `400` con `CAMPO_DESCONOCIDO` | V2 |
| Baja lógica | Acciones explícitas (`POST .../baja`, `POST .../egreso`), no `DELETE` | V2 |
| Inmutabilidad | Los movimientos no tienen `PUT`, `PATCH` ni `DELETE` (`405`). Se corrigen con `POST /movimientos/{id}/correccion` | V2 |
| Doble envío | Cabecera `Idempotency-Key` en los `POST` de movimientos (requiere la tabla `clave_idempotencia`) | V2 |
| Respuesta de movimientos | `201` con el movimiento y los saldos resultantes de las entidades afectadas | V2 |

> **Doble envío en el MVP:** las pantallas web lo resuelven sin tabla nueva. Después de guardar se redirige (patrón *Post/Redirect/Get*) y el botón de enviar se desactiva al pulsarlo.

#### 4.2. Autenticación y niveles de acceso

**MVP:** la API usa la **misma sesión de Django** que la aplicación web. El usuario inicia sesión en la pantalla de login y el navegador envía la cookie `sessionid` (30 min de inactividad). No hay endpoints de login ni tokens.
- Los 3 endpoints son de lectura, así que **cualquier usuario autenticado** puede usarlos: `Solo lectura`, `Lectura y escritura` o Administrador.
- Al ser `GET`, no requieren la cabecera CSRF.
- Sin sesión responden `401`.

**V2:** se agregan `GET /auth/csrf`, `POST /auth/login`, `POST /auth/logout` y `GET /auth/me`, y las operaciones de escritura, que exigen la cabecera `X-CSRFToken`. Cada operación declara su nivel en `x-nivel-acceso`:

| Nivel | Puede |
|---|---|
| `SOLO_LECTURA` | Todos los `GET` |
| `LECTURA_ESCRITURA` | Todo lo anterior y las operaciones de escritura |
| `ADMINISTRADOR` | Igual que lectura y escritura, y además el panel `/admin/` |

La gestión de usuarios se hace en `/admin/` y no forma parte de la API.

#### 4.3. Endpoints

| Funcionalidad | Método y ruta | Nivel | Alcance |
|---|---|---|---|
| 2. Medicamentos | `GET /medicamentos` (filtros `q`, `principio_activo_id`, `tipo`, `presentacion_id`, `activo`) | Lectura | **MVP** |
| 5. Existencias | `GET /existencias` (filtros `entidad_id`, `medicamento_id`, `principio_activo_id`, `q`, `incluir_sin_saldo`) | Lectura | **MVP** |
| 7. Reporte mensual | `GET /reportes/mensual?anio=&mes=&entidad_id=` | Lectura | **MVP** |
| 1. Sesión | `GET /auth/csrf` · `POST /auth/login` · `POST /auth/logout` · `GET /auth/me` | Público / autenticado | V2 |
| Catálogos | `GET /presentaciones` · `GET /motivos-baja` · `GET /principios-activos` · `POST /principios-activos` | Lectura / escritura | V2 |
| 2. Medicamentos | `GET /medicamentos/{id}` · `POST /medicamentos` · `PATCH /medicamentos/{id}` · `POST /medicamentos/{id}/baja` · `POST /medicamentos/{id}/reactivacion` | Lectura / escritura | V2 |
| 3. Entidades y residentes | `GET /entidades` · `GET /residentes` · `GET /residentes/{id}` · `POST /residentes` · `PATCH /residentes/{id}` · `POST /residentes/{id}/egreso` | Lectura / escritura | V2 |
| 4. Movimientos | `GET /movimientos` · `GET /movimientos/{id}` · `POST /movimientos/entradas` · `POST /movimientos/transferencias` · `POST /movimientos/bajas` · `POST /movimientos/{id}/correccion` | Lectura / escritura | V2 |
| 6. Conteo físico | `GET /conteos` · `GET /conteos/{id}` · `POST /conteos` · `PUT /conteos/{id}/detalles/{medicamento_id}` · `DELETE /conteos/{id}/detalles/{medicamento_id}` · `POST /conteos/{id}/cierre` | Lectura / escritura | V2 |

#### 4.4. Errores

Todos los errores usan **Problem Details (RFC 9457)**, con el tipo `application/problem+json`. Además del estándar llevan un `code` estable que la aplicación puede usar en sus condiciones, y `errores[]` con el detalle por campo:

```json
{
  "type": "https://hogar.example/errores/validacion",
  "title": "Datos inválidos",
  "status": 400,
  "code": "VALIDACION",
  "detail": "La petición tiene 1 error de validación.",
  "instance": "/api/v1/medicamentos",
  "errores": [
    { "campo": "q", "codigo": "LONGITUD_INVALIDA", "mensaje": "La búsqueda requiere al menos 3 caracteres." }
  ]
}
```

**Errores que pueden devolver los endpoints del MVP:**

| HTTP | `code` | Cuándo ocurre |
|---|---|---|
| 400 | `VALIDACION` | Un parámetro no es válido. `errores[].codigo`: `LONGITUD_INVALIDA` (`q` con menos de 3 caracteres), `TIPO_INVALIDO` (`entidad_id=abc`), `VALOR_FUERA_DE_RANGO` (`mes=13`, `por_pagina=500`), `OPCION_INVALIDA` (`tipo=OTRO`) |
| 401 | `NO_AUTENTICADO` | No hay sesión o la sesión expiró |
| 404 | `NO_ENCONTRADO` | `entidad_id` inexistente en el reporte mensual |
| 405 | `METODO_NO_PERMITIDO` | Cualquier método distinto de `GET` |
| 500 | `ERROR_INTERNO` | Error inesperado; el detalle no expone información interna |

El contrato define además los códigos de las operaciones `V2`: `CREDENCIALES_INVALIDAS`, `SIN_PERMISO`, `CSRF_INVALIDO`, `ESTADO_INVALIDO`, `MEDICAMENTO_DUPLICADO`, `PRINCIPIO_ACTIVO_DUPLICADO`, `MEDICAMENTO_CON_EXISTENCIAS`, `MOVIMIENTO_YA_CORREGIDO`, `MOVIMIENTO_ES_CORRECCION`, `CONTEO_CERRADO`, `IDEMPOTENCIA_CONFLICTO`, `EXISTENCIA_INSUFICIENTE`, `ENTIDAD_INACTIVA`, `MEDICAMENTO_INACTIVO`, `MISMA_ENTIDAD`, `MOTIVO_RESERVADO`, `REFERENCIA_INVALIDA`, `CONTEO_SIN_RENGLONES` y `DEMASIADOS_INTENTOS`. El criterio es `409` cuando la operación choca con el estado del recurso y `422` cuando viola una regla de negocio.

En el MVP, esas mismas reglas de negocio las valida `services.py` y las pantallas web las muestran como mensajes en el formulario.

#### 4.5. Endpoints principales (MVP)

**1. `GET /existencias`: consultar existencias por paciente, medicamento o principio activo**

```yaml
/existencias:
  get:
    tags: [Existencias]
    operationId: listarExistencias
    summary: Consultar existencias
    description: Filtros combinables. Por defecto solo devuelve saldos mayores a 0.
    x-alcance: MVP
    x-nivel-acceso: SOLO_LECTURA
    parameters:
      - { name: entidad_id,          in: query, description: Paciente o el Hogar, schema: { type: integer, format: int64, minimum: 1 } }
      - { name: medicamento_id,      in: query, schema: { type: integer, format: int64, minimum: 1 } }
      - { name: principio_activo_id, in: query, schema: { type: integer, format: int64, minimum: 1 } }
      - { name: q,                   in: query, schema: { type: string, minLength: 3, maxLength: 100 } }
      - { name: incluir_sin_saldo,   in: query, schema: { type: boolean, default: false } }
      - $ref: '#/components/parameters/Pagina'
      - $ref: '#/components/parameters/PorPagina'
    responses:
      '200':
        description: Página de existencias, ordenada por entidad (Hogar primero) y nombre comercial.
        content:
          application/json:
            schema: { $ref: '#/components/schemas/PaginaExistencias' }   # entidad, medicamento, saldo, actualizado_en
      '400': { $ref: '#/components/responses/Validacion' }
      '401': { $ref: '#/components/responses/NoAutenticado' }
```

```http
GET /api/v1/existencias?principio_activo_id=2
Cookie: sessionid=<sesión>
```

```json
200 OK
{
  "total": 3, "pagina": 1, "por_pagina": 20,
  "resultados": [
    { "entidad": { "id": 1, "tipo": "HOGAR", "nombre": "Hogar Gerontológico Demo", "activa": true },
      "medicamento": { "id": 2, "nombre_comercial": "Losartán", "presentacion": "tableta", "concentracion": "50 mg" },
      "saldo": 20, "actualizado_en": "2026-10-02T09:00:00-06:00" },
    { "entidad": { "id": 102, "tipo": "RESIDENTE", "nombre": "José Luis Ramírez Ortega", "activa": true },
      "medicamento": { "id": 3, "nombre_comercial": "Cozaar", "presentacion": "tableta", "concentracion": "50 mg" },
      "saldo": 32, "actualizado_en": "2026-10-03T11:00:00-06:00" },
    { "entidad": { "id": 102, "tipo": "RESIDENTE", "nombre": "José Luis Ramírez Ortega", "activa": true },
      "medicamento": { "id": 2, "nombre_comercial": "Losartán", "presentacion": "tableta", "concentracion": "50 mg" },
      "saldo": 10, "actualizado_en": "2026-10-02T09:00:00-06:00" }
  ]
}
```

**2. `GET /medicamentos`: buscar medicamentos por nombre o principio activo, sin acentos**

```yaml
/medicamentos:
  get:
    tags: [Medicamentos]
    operationId: listarMedicamentos
    summary: Buscar medicamentos
    description: q busca en el nombre comercial o en cualquiera de sus principios activos, sin mayúsculas ni acentos.
    x-alcance: MVP
    x-nivel-acceso: SOLO_LECTURA
    parameters:
      - { name: q,                   in: query, schema: { type: string, minLength: 3, maxLength: 100 } }
      - { name: principio_activo_id, in: query, schema: { type: integer, format: int64, minimum: 1 } }
      - { name: tipo,                in: query, schema: { type: string, enum: [GENERICO, ORIGINAL] } }
      - { name: presentacion_id,     in: query, schema: { type: integer, format: int64, minimum: 1 } }
      - { name: activo,              in: query, schema: { type: boolean, default: true } }
      - { name: orden,               in: query, schema: { type: string, enum: [nombre_comercial, -nombre_comercial, creado_en, -creado_en], default: nombre_comercial } }
      - $ref: '#/components/parameters/Pagina'
      - $ref: '#/components/parameters/PorPagina'
    responses:
      '200':
        description: Página de medicamentos con su presentación y principios activos.
        content:
          application/json:
            schema: { $ref: '#/components/schemas/PaginaMedicamentos' }
      '400': { $ref: '#/components/responses/Validacion' }
      '401': { $ref: '#/components/responses/NoAutenticado' }
```

```http
GET /api/v1/medicamentos?q=paracetamol
Cookie: sessionid=<sesión>
```

```json
200 OK
{
  "total": 2, "pagina": 1, "por_pagina": 20,
  "resultados": [
    { "id": 6, "nombre_comercial": "Paracetamol", "tipo": "GENERICO",
      "presentacion": { "id": 1, "nombre": "tableta" }, "concentracion": "500 mg",
      "principios_activos": [ { "id": 5, "nombre": "Paracetamol" } ],
      "activo": true, "creado_en": "2026-09-01T08:00:00-06:00", "actualizado_en": "2026-09-01T08:00:00-06:00" },
    { "id": 7, "nombre_comercial": "Tempra", "tipo": "ORIGINAL",
      "presentacion": { "id": 3, "nombre": "jarabe" }, "concentracion": "160 mg / 5 ml",
      "principios_activos": [ { "id": 5, "nombre": "Paracetamol" } ],
      "activo": true, "creado_en": "2026-09-01T08:00:00-06:00", "actualizado_en": "2026-09-01T08:00:00-06:00" }
  ]
}
```

Tempra aparece aunque su nombre no coincida, porque su principio activo es paracetamol.

**3. `GET /reportes/mensual`: movimientos y saldos de un mes**

```yaml
/reportes/mensual:
  get:
    tags: [Reportes]
    operationId: obtenerReporteMensual
    summary: Movimientos y saldos de un mes
    description: Se calcula al momento a partir de movimiento; un mes en curso muestra el saldo a la fecha.
    x-alcance: MVP
    x-nivel-acceso: SOLO_LECTURA
    parameters:
      - { name: anio,       in: query, required: true, schema: { type: integer, minimum: 2020, maximum: 2100 } }
      - { name: mes,        in: query, required: true, schema: { type: integer, minimum: 1, maximum: 12 } }
      - { name: entidad_id, in: query, description: Si se omite incluye todas las entidades, schema: { type: integer, format: int64, minimum: 1 } }
    responses:
      '200':
        description: Por entidad y medicamento, saldo_inicial, entradas, transferencias, bajas (total y por motivo) y saldo_final.
        content:
          application/json:
            schema: { $ref: '#/components/schemas/ReporteMensual' }
      '400': { $ref: '#/components/responses/Validacion' }
      '401': { $ref: '#/components/responses/NoAutenticado' }
      '404': { $ref: '#/components/responses/NoEncontrado' }
```

```http
GET /api/v1/reportes/mensual?anio=2026&mes=10&entidad_id=101
Cookie: sessionid=<sesión>
```

```json
200 OK
{
  "anio": 2026, "mes": 10, "desde": "2026-10-01", "hasta": "2026-10-31",
  "generado_en": "2026-10-19T09:00:00-06:00",
  "entidades": [
    { "entidad": { "id": 101, "tipo": "RESIDENTE", "nombre": "María Guadalupe Hernández López", "activa": true },
      "medicamentos": [
        { "medicamento": { "id": 9, "nombre_comercial": "Atorvastatina", "presentacion": "tableta", "concentracion": "20 mg" },
          "saldo_inicial": 1, "entradas": 0, "transferencias_recibidas": 0, "transferencias_enviadas": 0,
          "bajas": 0, "bajas_por_motivo": {}, "saldo_final": 1 },
        { "medicamento": { "id": 1, "nombre_comercial": "Metformina", "presentacion": "tableta", "concentracion": "850 mg" },
          "saldo_inicial": 2, "entradas": 660, "transferencias_recibidas": 0, "transferencias_enviadas": 0,
          "bajas": 600, "bajas_por_motivo": { "CORRECCION": 600 }, "saldo_final": 62 }
      ] }
  ]
}
```

El reporte de octubre de María muestra la corrección: 660 de entradas (600 capturadas por error y 60 correctas) y 600 de baja `CORRECCION`. El saldo final cuadra: 2 + 660 − 600 = 62.

#### 4.6. Casos de prueba de la API del MVP (sobre el dataset mock)

Con el mock de la sección 3.4 recién cargado. La sesión es la de `operador.demo` salvo que se indique otra cosa.

| # | Petición | Esperado |
|---|---|---|
| 1 | `GET /existencias` sin sesión | `401 NO_AUTENTICADO` |
| 2 | Con la sesión de `consulta.demo` (solo lectura): `GET /existencias` | `200`: el nivel de solo lectura puede consultar la API |
| 3 | `GET /existencias?principio_activo_id=2` | `200`, `total: 3`: Hogar Losartán 20, José Luis Cozaar 32, José Luis Losartán 10 |
| 4 | `GET /existencias?entidad_id=103` | `200`: Eutirox 33, Exelon 3, Paracetamol 14 |
| 5 | `GET /existencias?entidad_id=1&incluir_sin_saldo=true` | `200`, `total: 5`, incluye Tempra con saldo 0 |
| 6 | `GET /existencias?q=lo` | `400 VALIDACION`, `errores[0].codigo: LONGITUD_INVALIDA` |
| 7 | `GET /medicamentos?q=losartan` | `200`, `total: 3`: Cozaar, Hyzaar y Losartán |
| 8 | `GET /medicamentos?q=paracetamol` | `200`, `total: 2`: Paracetamol y Tempra (por principio activo) |
| 9 | `GET /medicamentos?q=ACIDO` | `200`: Aspirina Protect, por "Ácido acetilsalicílico" (sin mayúsculas ni acentos) |
| 10 | `GET /medicamentos?tipo=ORIGINAL` | `200`, `total: 7` |
| 11 | `GET /medicamentos?por_pagina=500` | `400 VALIDACION`, `VALOR_FUERA_DE_RANGO` |
| 12 | `GET /reportes/mensual?anio=2026&mes=9&entidad_id=101` | Metformina 0 + 60 − 58 = 2; Atorvastatina 0 + 30 − 29 = 1 |
| 13 | `GET /reportes/mensual?anio=2026&mes=10&entidad_id=101` | Metformina 2 + 660 − 600 = 62, `bajas_por_motivo: { CORRECCION: 600 }` |
| 14 | `GET /reportes/mensual?anio=2026&mes=13` | `400 VALIDACION`, `VALOR_FUERA_DE_RANGO` |
| 15 | `GET /reportes/mensual?anio=2026&mes=9&entidad_id=999` | `404 NO_ENCONTRADO` |
| 16 | `POST /existencias` | `405 METODO_NO_PERMITIDO` |

Las reglas de escritura (saldo insuficiente, duplicados, conteo cerrado, corrección, permisos de solo lectura) se prueban en el MVP desde los tests de `services.py` y de las pantallas web (sección 2.6). Los casos de la API `V2` están en los ejemplos de `openapi.yaml`.

#### 4.7. Implementación

- **MVP:** 3 vistas de Django REST Framework de solo lectura (`ListAPIView`), con `SessionAuthentication` y el permiso `IsAuthenticated`. Las consultas son las de la sección 3.3 y reusan los mismos índices.
- **Un `EXCEPTION_HANDLER` propio** traduce las excepciones a Problem Details: `ValidationError` → `400 VALIDACION`, `NotAuthenticated` → `401`, `NotFound` → `404`, `MethodNotAllowed` → `405`.
- **Tests de contrato:** las pruebas de `pytest` validan cada respuesta de los 3 endpoints contra los esquemas de `openapi.yaml` con un validador de JSON Schema 2020-12 (`jsonschema`). Los 16 casos de la tabla anterior son la base de esos tests.
- **V2:** las operaciones marcadas `V2` se implementan sobre la misma capa `services.py`. Las vistas de la API serán delgadas y aplicarán las mismas reglas que las pantallas web.
- **Herramientas y OpenAPI 3.2:** drf-spectacular genera un esquema 3.0/3.1 para la documentación interactiva (Swagger UI en `/api/v1/docs/`). El archivo 3.2 es el contrato de diseño y la fuente de verdad. Si alguna herramienta todavía no soporta 3.2, el contrato se baja a 3.1 cambiando `dataValue` por `value` y quitando el campo `summary` de los tags.
