> Detalla en esta sección los prompts principales utilizados durante la creación del proyecto, que justifiquen el uso de asistentes de código en todas las fases del ciclo de vida del desarrollo. Esperamos un máximo de 3 por sección, principalmente los de creación inicial o  los de corrección o adición de funcionalidades que consideres más relevantes.
Puedes añadir adicionalmente la conversación completa como link o archivo adjunto si así lo consideras


## Índice

1. [Descripción general del producto](#1-descripción-general-del-producto)
2. [Arquitectura del sistema](#2-arquitectura-del-sistema)
3. [Modelo de datos](#3-modelo-de-datos)
4. [Especificación de la API](#4-especificación-de-la-api)
5. [Historias de usuario](#5-historias-de-usuario)
6. [Tickets de trabajo](#6-tickets-de-trabajo)
7. [Pull requests](#7-pull-requests)

---

## 1. Descripción general del producto
### Modelo: Opus 5.5
### Esfuerzo: High
### Herramienta: Claude Code / plugin IntelliJ


```
Como Product Owner (PO o PDO) especialista en sector Salud -  Hogar Gerontologico, crea una breve descripcion para este nuevo proyecto.

Software de gestion de hogar gerontologico - Inventario material de medicamento para un hogar gerontologico.

Descripcion de funcionalidad:
Inventario medicamentos
1. Manejo e inventario de medicamentos, poder hacer a/b/c (alta, baja, cambios) medicamentos y filtrado para facilitar esta operacion.
   2.ABC de existencias por entidad(persona o el mismo negocio), cada paciente tiene su existencia de medicamentos y asimismo el asilo cuenta como entidad.
   3 Filtrar medicamentos por paciente y por nombre de medicamento o principio activo
4. Inventariar por paciente, a demanda (fecha inicio y fin) -Existencia vs registrados -, reporte de medicamentos mensual
5. Establecer niveles de acceso: Solo lectura, lectura y escritura. Definen que puede hacer el usuario en las acciones anteriores.

Descripcion no funcional:
Es un proyecto para una empresa pequeña, que pueda ser accesible desde cualquier lugar me diante cliente web, debe ser seguro porque maneja datos personales (nombre, fecha nacimiento) y medicamentos que consume.

Antes de empezar, como product owner, pregúntame qué más necesitas saber para definir el proyecto
```
**Respuesta clave de Claude Code Opus 5.5 High:**
> "Gestión de Medicamentos – Hogar Gerontológico es una aplicación web responsive (computadora y celular) que controla el inventario de medicamentos de un hogar de adultos mayores. Lleva las existencias por entidad: cada residente tiene su propio inventario y el hogar cuenta como una entidad más. Registra entradas (con quién entregó el medicamento), transferencias entre entidades y bajas por motivo. Permite filtrar por paciente, nombre comercial o principio activo, y hacer conteos físicos que se comparan contra lo registrado. Corre en un servidor local, tiene acceso por usuario con dos niveles (solo lectura / lectura y escritura) y protege los datos personales y de salud de los residentes según la LFPDPPP de México."

**Impacto en el proyecto:**
Establecio una colaboracion 1:1 como PO conmigo, creo la base conceptual del proyecto que revise y aprobe. Sin embargo propuso irse directo a las historias 3 y luego al 5, que no hice. Segui con arquitectura.
---

## 2. Arquitectura del Sistema
### Modelo: Opus 5.5
### Esfuerzo: High
### Herramienta: Claude Code / plugin IntelliJ

### **2.1. Diagrama de arquitectura:**

**Prompt 1: Diseño de arquitectura**
```
Vamos al punto 2 referente a Arquitectura. Como arquitecto de software experto en aplicaciones web, propón la arquitectura de este proyecto, preferentemente simple y escalable.

Antes de comenzar pregunta qué necesitas saber y qué vas a considerar para diseñar esta arquitectura. Explícame paso por paso qué vas a seguir.

Con estas preguntas analiza y explica qué vas a hacer para diseñar este diagrama y la arquitectura del proyecto.
```
**Respuesta clave de Claude Code Opus 5.5 High:**
> "Leyendo los requisitos funcionales y no funcionales del proyecto propuso una arquitectura inicial, el alcance, pregunto todo lo pertinente para el diseño."

**Impacto en el proyecto:**
> "Propuso una arquitectura inicial del proyecto, acotado al scope del proyecto, y luego hizo preguntas referentes al stack, para acotar a las necesidades."

**Prompt 2: Seleccion del Stack:**
> 1. Stack: Prefiero un stack con todo incluido como Django, si es viable. Necesito que sea sencillo de montar en un hosting y que sea soportado por HostGator o Hostinger con VPS.
> 2. Frontend: Soy ingeniero de infraestructura y backend. No quiero SPA porque son lentas para cargar; queda cubierto con la respuesta 1.
> 3. Base de datos: PostgreSQL.
> 4. Mantenimiento: Yo.

**Respuesta clave de Claude Code Opus 5.5 High:**
> "Definio el stack para esta aplicacion y basado en mis respuestas y necesidades"
**Impacto en el proyecto:**
> Propuso opciones para el stack tecnologico y despues de alguans clarificaciones propuso opciones con menor friccion para despliege e implementacion. Con esto definio todos los puntos del apartado 2.

**Prompt 3: Definicion infrastructura**
>Servidor local: Por defecto (Linux Ubuntu con Docker).
> Acceso: Por ahora la máquina solo es accesible desde la red del hogar; el despliegue futuro será en HostGator/VPS una vez que se fondee.
> URL para evaluadores: Sí.
> Sección 4 (API): Tomemos la opción a).

### **2.2. Descripción de componentes principales:**

**Prompt 1:**

**Prompt 2:**

**Prompt 3:**

### **2.3. Descripción de alto nivel del proyecto y estructura de ficheros**

**Prompt 1:**

**Prompt 2:**

**Prompt 3:**

### **2.4. Infraestructura y despliegue**

**Prompt 1:**

**Prompt 2:**

**Prompt 3:**

### **2.5. Seguridad**

**Prompt 1:**

**Prompt 2:**

**Prompt 3:**

### **2.6. Tests**

**Prompt 1:**

**Prompt 2:**

**Prompt 3:**

---

### 3. Modelo de Datos
### Modelo: Opus 5.5
### Esfuerzo: High
### Herramienta: Claude Code / plugin IntelliJ

**Prompt 1:Diseño del modelo relacional**
```
Como Arquitecto de diseño diseña un modelo de datos completo para este sistema  Gestion Medicamentos Hogar Gerontologico.
Para cubrir los requisitos funcionales ya detallados en la seccion 1.2 del readme.md:
- Base de datos normalizada (3NF)
- Pon atencion especial a los antipatrones en el diseño de la DBs
- Soporte para los almacenes de datos que definiste en la seccion 2.1.1 del readme.md,parte de las 6 tablas de datos del diagrama de flujo: usuarios y grupos, medicamentos, entidades, existencias, movimientos y pautas:
  Id	Almacén	Contenido
  D1	Usuarios y grupos	Usuarios, contraseña (hash), estado activo y grupo (Solo lectura / Lectura y escritura)
  D2	Medicamentos	Catálogo: nombre comercial, principio activo, genérico/original, presentación, concentración, activo
  D3	Entidades	El hogar y los residentes (nombre, fecha de nacimiento, estado)
  D4	Existencias	Saldo en dosis por entidad y medicamento
  D5	Movimientos	Entradas, transferencias y bajas, con usuario y fecha/hora (inmutables)
  D6	Pautas	Dosis y frecuencia por residente y medicamento, con vigencia

- Considera, las reglas confirmadas:
* La baja de un medicamento es lógica.
* No se repite la combinación de nombre comercial, presentación y concentración.
* El Hogar es una entidad fija.
* Cada usuario tiene un solo grupo.
* Las pautas guardan vigencia.
* Los movimientos no se modifican y son la trazabilidad mínima.
* Los conteos físicos, que hacen falta para comparar existencia contra registrado.

Crea los diagramas entidad relacion usando mermaid e inclue todos sus detalles, primary keys, foreign keys, data types, constraints.
```

**Respuesta clave de Claude Code Opus 5.5 High:**
> "Ya está la sección 3 (modelo de datos) en el readme.md. También creé 03-modelo-datos.md con tu prompt, mi respuesta y un anexo con el texto final del readme, copiado de forma automática para que sea idéntico.."

**Impacto en el proyecto:**
> "Creo el diseño de datos para soportar la funcionalidad, evito antipatrones, creo el ERD en mermaid, y pidio confirmar unas decisiones logicas del diseño de datos."


**Prompt 2:**
```Ahora optimízalo para performance:
- Indices para busquedas frecuentes
- Constraints para la integridad de datos

Las consultas frecuentes son:
- Busqueda por medicamento y/o principio activo y existencias.
- Busqueda por medicamento y detalles en conteo fisico.
- Busqueda de pautas por residentes.
```
**Respuesta clave de Claude Code Opus 5.5 High:**
> "Agregué la sección 3.3. Optimización para rendimiento: índices y restricciones de integridad al readme.md. En 03-modelo-datos.md registré la conversación como Prompt 3 y Respuesta 3, y regeneré el anexo.
> "Punto de partida: según la estimación, la tabla que crece es movimiento, con 60,000 a 175,000 filas al año si se registra el consumo diario. El catálogo y las entidades son pequeños. Por eso cada índice responde a una consulta concreta, y quité los índices que Django crearía de más para no frenar las escrituras."

**Impacto en el proyecto:**
> "Estimo las consultas por crecimiento estimado y creo indices segun fuera necesario.Ajusto las constrains para ignorar acentos"


**Prompt 3:**
```
Excelente, ahora creación de mock dataset completo para demo y desarrollo:
Necesitamos datos mock completo para esta aplicacion para los demos:
- 2 Usuarios, uno read only y otr read write
- 3 Residentes
- 1 pauta por residente
- 15 Medicamentos con principios activos, presentacion, existencias 
- 1 o 2 Conteos fisicos
- Movimientos 
- Datos en JSON para inyectarlos en la DB, para demo y mocks de desarrollo, PostgresSQL soporta inyeccion de datos con JSON

Lo suficientemente realista para hacer el demo y que sea sencillo de entender.
```

**Respuesta clave de Claude Code Opus 5.5 High:**
> "Ya está el dataset mock para la demo y el desarrollo, y lo probé contra un PostgreSQL 17 real: la carga terminó sin errores y las validaciones funcionan."


**Impacto en el proyecto:**
> "Genero un conjunto de datos en JSON, el cual valido contra una imagen de postgres real en un contenedor docker que ella misma levanto. Luego añadio instrucciones de como importar los datos. Facilito enormemente (en teoria) el demo y pruebas."



---

### 4. Especificación de la API

**Prompt 1:**
```
Definamos la API REST: Como Software Architect, especialista en el diseño e implementacion de API REST diseña la API REST y todos los endpoints necesarios para el sistema de Gestion Medicamentos Hogar Gerontologico.

Considera estos requisitos:
- Endpoints: Para las operaciones detalladas en los requisitos funcionales
#	Funcionalidad
1	Inicio de sesión y 2 niveles de acceso.
2	Catálogo de medicamentos (alta, baja y cambio), con principio activo, presentación y búsqueda sin acentos	
3	Residentes (alta, baja y cambio), con el Hogar como entidad fija
4	Movimientos: entrada (con quién entregó), transferencia, baja con motivo y corrección
5	Consulta de existencias filtrada por paciente, medicamento o principio activo
6	Conteo físico simple: capturar lo que hay físicamente, ver la diferencia contra lo registrado y cerrar el conteo
7	Reporte mensual en pantalla: movimientos y saldos por mes

- Especificacion OpenAPI 3.2.0
- Validaciones de request/response
- Codigo de errores detallados
- Ejemplos realistas para tests

```
**Respuesta clave de Claude Code Opus 5.5 High:**
> "Diseñé la API completa del MVP. El contrato está en `docs/api/openapi.yaml` y la sección 4 del `readme.md` lo documenta.

**Contrato (`docs/api/openapi.yaml`, OpenAPI 3.2.0):**
- **27 rutas, 34 operaciones, 57 esquemas y 21 parámetros**, organizados en 9 *tags*.
- Validado con **Redocly CLI**: 0 errores y 2 advertencias intencionales (un ejemplo inválido a propósito para provocar el `400`, y `GET /auth/csrf` sin respuestas 4XX).
- Usa lo propio de 3.2: `summary` en los *tags* y `dataValue` en los ejemplos. Los esquemas son JSON Schema 2020-12, con tipos `[string, 'null']`.
- Cada operación declara su nivel en `x-nivel-acceso`."


**Impacto en el proyecto:**
> "Creo increiblemente rapido la API Rest solicitada para el MVP facilitando enormemente el desarrollo, con todo y validaciones, y lleno toda la seccion 4.Luego pidio unas validaciones que este promp contradice en el diseño"



**Prompt 2:Confirmar como reducir a 3 endpoints para el MVP (v1)**
```Este prompt no lo registres, es viable hacer un MVP con solo 3 endpoints?
```
**Respuesta clave de Claude Code Opus 5.5 High:**
> "Sí, es viable. Con la arquitectura que ya definimos, es incluso lo más natural."

**Impacto en el proyecto:**
> "Redujo racionalmente el MVP de 27 rutas a solo 3. Lo que facilita enormemente la salida del MVP y de este proyecto."

**Prompt 3:Definir si puede haber MVP con solo 3 Endpoints**
```Si 3 endpoints en el MVP y el resto marcado para despues la V2., entonces registra el prompt anterior, con tus respuestas, y ejecuta las acciones que propones para este MVP de 3 endpoints: 1. Marcar el alcance openapi.yaml, 2. Cambiarla seccion 4.5, 3. Reducir la tabla de casos de prueba. Ademas reformula las 7 preguntas anteriores, solo las que apliquen.
```
**Respuesta clave de Claude Code Opus 5.5 High:**
> "Hice las 3 acciones para el MVP de 3 endpoints y registré los dos intercambios en 04-api.md.."

**Impacto en el proyecto:**
> "Redujo efectivamente el MVP a 3 endpoints, redujo dramaticamente el cogido por generar y las pruebas y su mantenimiento, actualizo las seccion 4, simplifico enormemente la primera entrega"

**Prompt 4: Generar ejemplos**
```
Agrega solo en el 04-api.md una seccion al final con ejemplos de uso de los endpoints con CURL para testing.
```
**Respuesta clave de Claude Code Opus 5.5 High:**
> "Agregué al final de este archivo la sección **Ejemplos de uso con curl para testing**, sin tocar el `readme.md`. Incluye:
> -" Cómo obtener la sesión con curl desde el login web."
> "- Un ejemplo por cada caso de prueba de la sección 4.6, con su resultado esperado."
> "- Un script de humo que ejecuta los 16 casos y compara los códigos HTTP."
> "- Ejemplos de referencia para la `V2`."

**Impacto en el proyecto:**
> "Genero ejemplos con curl para referencia de pruebas que sirven como documentacion practica de que esperar facilitando el desarrollo y pruebas." 
---



### 5. Historias de Usuario

**Prompt 1:Definir Historias de Usario (Use Cases) principales para MVP viable**
Trabajemos con las historias de usuario. Como Product Owner experimentado, crea historias de usuario, limitándote a las 3 más críticas o importantes para lograr el MVP y el máximo impacto en el proyecto. Toma en cuenta lo que hemos documentado, con especial foco en los requisitos funcionales:

- Creación de valor inmediata.
- Viabilidad técnica para el MVP en 6 semanas.
- ROI desde el primer día.

Enfócate en las funcionalidades más importantes para lograr un MVP efectivo.

**Respuesta clave de Claude Code Opus 5.5 High:**
> "Escribí la sección 5 del `readme.md` con las 3 historias que resuelven el problema central del hogar: **cuánto medicamento hay, de quién es y si coincide con el anaquel**."
>
**Impacto en el proyecto:**
>  Definio 3 historias para poder realizar un MVP entregando valor inmediatamente, con plan semanal de implementacion. Señalo las ventajas del panel /admin/ de DJango para disparar los habilitadores, como crear  login, catálogo y residentes,
>  tambien el orden, las dependencias, los story points y con criterios de aceptacion Gherkin basados  en el dataset del mock previamente definido, de cada historia de usuario.

**Prompt 2:**

**Prompt 3:**

---

### 6. Tickets de Trabajo

**Prompt 1:**
```
Excelente especificacion de Historias de Usuario. Ahora trabajemos en la seccion 6 de Tickets de Trabajo.
Como Tech Lead Experimentado, a partir de las historias de usuario que justo creaste, crea 3 tickets de trabajo principales para el desarrollo, uno de backend, uno de frontend, y uno de bases de datos.
Da todo el detalle requerido para desarrollar la tarea de inicio a fin teniendo en cuenta las buenas prácticas al respecto. 
Incluye en cada ticket:
- Descripcion tecnica
- Criterios de aceptacion
- Definicion de hecho (definition of done)
- Estimacion en story points
```

**Respuesta clave de Claude Code Opus 5.5 High:**
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

**Impacto en el proyecto:**
> Creo los 3 tickets por capa como se le pidio, el orden recomendado, historias con las que se relaciona, cual ticket bloquea a cual, story points. 
> Un hallazgo importante es que los tickets son secuenciales por su naturaleza.Definio otros tickets que le siguen y que se van al backlog no sin confirmar para que la suma de story points fuera correcta. 

**Prompt 2:**
```
Para que un desarrollador junior pueda hacer el ticket sin bloqueos, detalla cada ticket con:
- Tareas especificas paso a paso
- Archivos y estructura de codigo a crear
- Test requeridos con ejemplos
- Criterios de calidad
- Comandos/pasos especificos para la verificacion
```

**Respuesta clave de Claude Code Opus 5.5 High:**

> Creé una guía paso a paso por ticket en `docs/tickets/` y la enlacé desde cada ticket de la sección 6. Las puse en archivos aparte porque cada una tiene entre 800 y 1,100 líneas, y así el readme sigue siendo legible.

| Guía | Contenido principal |
|---|---|
| [`TK-01-esquema-inventario.md`](docs/tickets/TK-01-esquema-inventario.md) | Usuarios `app_owner`/`app_user`, modelos completos, 5 migraciones, fixture que carga el mock en pytest, tests de cada restricción y de privilegios |
| [`TK-02-servicio-movimientos.md`](docs/tickets/TK-02-servicio-movimientos.md) | Excepciones y `services.py` completos, conceptos de bloqueo explicados, tests de reglas y de concurrencia con hilos |
| [`TK-03-pantalla-existencias.md`](docs/tickets/TK-03-pantalla-existencias.md) | Selector, formulario, vista, plantillas HTMX y *responsive*, filtro `dosis`, tests de vista y Playwright |


**Impacto en el proyecto:**
> Genero los pasos detallados para el desarrolo  de cda tickety esbozo el codigo, especifico los tests con ejemplos y su verificacion. Haciendo mas facile el desarrollo tanto para un agente como para un humano.
> 
**Prompt 3:**
```
Ahora define(si no lo esta ya):
- Tecnologias y librerias a utilizar en el apartado de Descripcion Tecnica
- Dependencias entre tickets y orden de ejecución
- Puntos de integración entre frontend/backend/database
- Criterios de revisión de código
Asegúrate de que los 3 tickets se integren perfectamente al final.
```
**Respuesta clave de Claude Code Opus 5.5 High:**

**Impacto en el proyecto:**
---

### 7. Pull Requests

**Prompt 1:**

**Prompt 2:**

**Prompt 3:**
