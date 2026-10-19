## Índice

0. [Ficha del proyecto](#0-ficha-del-proyecto)
1. [Descripción general del producto](#1-descripción-general-del-producto)
2. [Arquitectura del sistema](#2-arquitectura-del-sistema)
3. [Modelo de datos](#3-modelo-de-datos)
4. [Especificación de la API](#4-especificación-de-la-api)
5. [Historias de usuario](#5-historias-de-usuario)
6. [Tickets de trabajo](#6-tickets-de-trabajo)
7. [Pull requests](#7-pull-requests)

---

## 0. Ficha del proyecto

### **0.1. Tu nombre completo:**
Victor Manuel Ramirez Ruvalcaba
### **0.2. Nombre del proyecto:**
Gestion Medicamentos Hogar Gerontologico
### **0.3. Descripción breve del proyecto:**
**Gestión de Medicamentos – Hogar Gerontológico** es una aplicación web responsive (computadora y celular) para controlar el inventario de medicamentos de un hogar de adultos mayores. Gestiona las existencias **por entidad** (cada residente tiene su propio inventario y el hogar es una entidad más), registra entradas indicando quién entregó el medicamento, transferencias entre entidades y bajas por motivo. Permite filtrar por paciente, nombre comercial o principio activo, y realizar conteos físicos comparados contra lo registrado. Se despliega inicialmente en un servidor local (con posibilidad de migrar a un servicio de hosting), con acceso por usuario en dos niveles (solo lectura / lectura y escritura) y protección de los datos personales y de salud de los residentes conforme a la LFPDPPP (México).

### **0.4. URL del proyecto:**

>https://github.com/victorm007/AI4Devs-finalproject-vmrr

### 0.5. URL o archivo comprimido del repositorio

> Puedes tenerlo alojado en público o en privado, en cuyo caso deberás compartir los accesos de manera segura. Puedes enviarlos a [alvaro@lidr.co](mailto:alvaro@lidr.co) usando algún servicio como [onetimesecret](https://onetimesecret.com/). También puedes compartir por correo un archivo zip con el contenido
---

## 1. Descripción general del producto

> Describe en detalle los siguientes aspectos del producto:

### **1.1. Objetivo:**

> Propósito del producto. Qué valor aporta, qué soluciona, y para quién.

En un hogar gerontológico el control manual de medicamentos genera incertidumbre: no se sabe con certeza cuánto medicamento hay de cada residente, quién lo entregó, qué ocurrió con el sobrante de un residente que egresó o falleció, ni si lo que hay físicamente coincide con lo registrado.

El producto ofrece a la **administración / dirección** del hogar un inventario confiable y consultable desde cualquier dispositivo, que separa claramente qué medicamento pertenece a cada residente y cuál al hogar, y facilita el **corte mensual** de existencias.

**Contexto de uso:** una sola sede, aproximadamente 20 residentes y de 1 a 3 usuarios del sistema.

### **1.2. Características y funcionalidades principales:**

> Enumera y describe las características y funcionalidades específicas que tiene el producto para satisfacer las necesidades identificadas.

**Funcionales**

1. **Catálogo de medicamentos (alta / baja / cambio):** nombre comercial, principio activo, tipo (genérico u original), presentación y concentración. Búsqueda y filtrado por nombre o principio activo. No se controla por lote.
2. **Gestión de entidades:** alta, baja y cambio de residentes (nombre, fecha de nacimiento, estado: activo / egresado / fallecido). El hogar existe como entidad propia.
3. **Existencias por entidad (controladas en dosis):**
   - **Entradas:** registro de quién entregó el medicamento (familiar, el hogar, otro).
   - **Transferencias** entre entidades (hogar → residente, residente → hogar, residente → residente), por ejemplo para reasignar sobrantes tras un egreso o defunción.
   - **Bajas por motivo:** consumo / administración, caducidad, merma, rotura, devolución a la familia, defunción y egreso. La baja por caducidad se registra manualmente al detectar el medicamento vencido.
4. **Pauta del residente:** registro de dosis y frecuencia de cada medicamento por paciente (informativo; no incluye registro de administración por turno).
5. **Filtros combinados** por paciente, nombre de medicamento y principio activo.
6. **Inventario físico y reportes (en pantalla):**
   - Conteo físico a demanda por paciente y por rango de fechas (inicio y fin), comparando existencia física contra lo registrado y resaltando diferencias.
   - Reporte mensual de movimientos y existencias para la dirección.
7. **Usuarios y niveles de acceso globales:** el Administrador da de alta a los usuarios y les asigna su nivel.
   - *Solo lectura:* consulta y reportes.
   - *Lectura y escritura:* todas las operaciones anteriores.
8. **Trazabilidad mínima:** cada movimiento de inventario guarda el usuario que lo registró y la fecha/hora.

**No funcionales**

- **Accesibilidad:** cliente web responsive, utilizable desde computadora y celular.
- **Despliegue:** servidor local en el hogar; la solución debe poder migrarse a un servicio de hosting sin cambios de arquitectura.
- **Seguridad:** autenticación con contraseñas cifradas (hash), sesiones con expiración, comunicación por HTTPS, autorización por nivel de acceso validada en el backend y respaldos periódicos de la base de datos.
- **Privacidad:** tratamiento de datos personales y de salud (nombre, fecha de nacimiento, medicamentos) conforme a la LFPDPPP, con aviso de privacidad.
- **Escala:** dimensionado para una pequeña empresa (1 sede, ~20 residentes, 1 a 3 usuarios).

**Fuera de alcance (MVP)**

Registro de administración por turno (MAR), alertas de stock mínimo o caducidad, control por lote, insumos distintos a medicamentos, multisede, exportación a PDF/Excel, bitácora de auditoría completa e integraciones con sistemas externos.

### **1.3. Diseño y experiencia de usuario:**

> Proporciona imágenes y/o videotutorial mostrando la experiencia del usuario desde que aterriza en la aplicación, pasando por todas las funcionalidades principales.

### **1.4. Instrucciones de instalación:**
> Documenta de manera precisa las instrucciones para instalar y poner en marcha el proyecto en local (librerías, backend, frontend, servidor, base de datos, migraciones y semillas de datos, etc.)

---

## 2. Arquitectura del Sistema

### **2.1. Diagrama de arquitectura:**
> Usa el formato que consideres más adecuado para representar los componentes principales de la aplicación y las tecnologías utilizadas. Explica si sigue algún patrón predefinido, justifica por qué se ha elegido esta arquitectura, y destaca los beneficios principales que aportan al proyecto y justifican su uso, así como sacrificios o déficits que implica.

```mermaid
flowchart LR
    U["Usuario<br/>Administrador / Lectura y escritura / Solo lectura<br/>(navegador en PC o celular)"]
    subgraph SRV["Servidor: local en la red del hogar (hoy) / VPS (futuro)"]
        direction LR
        NG["Nginx<br/>HTTPS, archivos estáticos,<br/>cabeceras de seguridad"]
        subgraph APP["Aplicación Django (Gunicorn)"]
            direction TB
            WEB["Vistas + plantillas<br/>Bootstrap 5 + HTMX"]
            API["API REST solo lectura<br/>Django REST Framework + OpenAPI"]
            SVC["Capa de servicios<br/>reglas de inventario"]
            MOD["Modelos / ORM"]
            WEB --> SVC
            SVC --> MOD
            API --> MOD
        end
        DB[("PostgreSQL")]
        BK["Respaldos<br/>pg_dump diario (cron)"]
    end
    U -- "HTTPS 443" --> NG
    NG -- "HTTP interno" --> WEB
    NG -- "HTTP interno" --> API
    MOD -- "SQL (red interna Docker)" --> DB
    DB -. "dump" .-> BK
```

**Patrón:** **monolito modular** sobre el patrón **MVT (Modelo–Vista–Template) de Django**, con páginas **renderizadas en el servidor**. Cada módulo de negocio es una *app* de Django independiente. Las reglas de inventario (entradas, transferencias y bajas) viven en una **capa de servicios** (`services.py`), separada de las vistas, para que la web y la API compartan la misma lógica y se pueda probar de forma aislada.

**Por qué esta arquitectura:**
- **Escala del problema:** 1 sede, ~20 residentes y 1 a 3 usuarios. La carga es mínima, y microservicios, una SPA o colas de mensajes solo añadirían complejidad.
- **Un solo mantenedor (perfil infra/backend):** Django trae ORM, migraciones, autenticación, sesiones, permisos por grupos, CSRF, formularios con validación y panel de administración. Hay menos piezas que integrar y mantener.
- **Rendimiento en celular:** el HTML llega listo desde el servidor, sin descargar ni compilar un *bundle* de JavaScript. HTMX permite filtrar y paginar sin recargar la página completa.
- **Portabilidad:** todo se empaqueta con **Docker Compose**, de modo que el mismo despliegue corre en el servidor local y en un VPS de HostGator sin cambiar código.
- **Integridad de datos:** PostgreSQL ofrece transacciones y bloqueo de filas, necesarios para que una transferencia descuente y abone en un solo paso y para que nunca haya existencias negativas.

**Beneficios:**
- Desarrollo rápido.
- Pocas dependencias.
- Despliegue sencillo, de 3 contenedores.
- Seguridad sólida por defecto.
- Facilidad para probar las reglas de negocio.
- Los módulos bien delimitados permiten extraer servicios en el futuro si fuera necesario.

**Sacrificios / déficits:**
- **Escalado solo vertical** (servidor más grande), suficiente para este volumen.
- **Acoplamiento a Django**: cambiar de framework implicaría reescribir.
- **Interactividad limitada** frente a una SPA: no hay edición en tiempo real ni funcionamiento sin conexión.
- **El servidor local es un punto único de falla**, que se mitiga con respaldos diarios y un procedimiento de restauración documentado.
- **Sin acceso desde fuera del hogar** mientras se despliegue solo en la red local.

#### **2.1.1. Diagrama de flujo de datos (DFD)**

**Notación:** rectángulo = entidad externa · círculo = proceso · cilindro = almacén de datos · flecha continua = flujo de datos · flecha punteada = respuesta de error o flujo físico (fuera del sistema).

**Almacenes de datos** (el detalle de cada uno está en la [sección 3](#3-modelo-de-datos)):

| Id | Almacén | Contenido |
|---|---|---|
| D1 | Usuarios y grupos | Usuarios, contraseña (hash), estado activo y grupo (`Solo lectura` / `Lectura y escritura`) |
| D2 | Medicamentos | Catálogo: nombre comercial, principio activo, genérico/original, presentación, concentración, activo |
| D3 | Entidades | El hogar y los residentes (nombre, fecha de nacimiento, estado) |
| D4 | Existencias | Saldo en dosis por entidad y medicamento |
| D5 | Movimientos | Entradas, transferencias y bajas, con usuario y fecha/hora (inmutables) |
| D6 | Pautas | Dosis y frecuencia por residente y medicamento, con vigencia |

##### Nivel 0 — Contexto

```mermaid
flowchart LR
    ADM["Administrador"]
    RW["Usuario<br/>Lectura y escritura"]
    RO["Usuario<br/>Solo lectura"]
    FAM["Familiar / quien entrega"]
    S(("Sistema de gestión<br/>de medicamentos"))
    ADM -- "usuarios y niveles de acceso" --> S
    RW -- "medicamentos, residentes,<br/>movimientos y pautas" --> S
    S -- "catálogo, existencias,<br/>historial y pautas" --> RW
    RO -- "filtros de búsqueda" --> S
    S -- "consultas y reportes" --> RO
    FAM -. "medicamento físico<br/>(lo registra el usuario)" .-> RW
```

##### Nivel 1 — Procesos principales

```mermaid
flowchart LR
    ADM["Administrador"]
    RW["Usuario<br/>Lectura y escritura"]
    RO["Usuario<br/>Solo lectura"]

    P1(("1. Gestionar<br/>catálogo"))
    P2(("2. Gestionar<br/>entidades"))
    P3(("3. Registrar<br/>movimientos"))
    P4(("4. Registrar<br/>pautas"))
    P5(("5. Gestionar usuarios<br/>y accesos"))

    D1[("D1 Usuarios y grupos")]
    D2[("D2 Medicamentos")]
    D3[("D3 Entidades")]
    D4[("D4 Existencias")]
    D5[("D5 Movimientos")]
    D6[("D6 Pautas")]

    ADM -- "datos de usuario + nivel" --> P5
    P5 -- "usuario, hash, grupo" --> D1

    RW -- "datos del medicamento" --> P1
    P1 -- "medicamento" --> D2

    RW -- "datos del residente / estado" --> P2
    P2 -- "entidad" --> D3

    RW -- "entrada / transferencia / baja" --> P3
    D2 -- "medicamento" --> P3
    D3 -- "entidad origen / destino" --> P3
    D4 -- "saldo actual" --> P3
    P3 -- "saldo actualizado" --> D4
    P3 -- "movimiento + usuario + fecha" --> D5

    RW -- "dosis y frecuencia" --> P4
    D2 -- "medicamento" --> P4
    D3 -- "residente" --> P4
    P4 -- "pauta" --> D6

    P1 -- "listado filtrado" --> RO
    P2 -- "listado de entidades" --> RO
    P3 -- "existencias e historial" --> RO
    P4 -- "pautas por residente" --> RO
```

> Todos los procesos validan la sesión y los permisos contra **D1** antes de leer o escribir (proceso 5.4 y 5.5). Un usuario `Solo lectura` solo recibe flujos de salida (consultas); cualquier escritura que intente devuelve `403`.

##### Flujo 1 — Catálogo de medicamentos (alta / baja / cambio)

```mermaid
flowchart LR
    RW["Usuario<br/>Lectura y escritura"]
    US["Cualquier usuario<br/>autenticado"]
    P11(("1.1 Validar<br/>permiso y datos"))
    P12(("1.2 Alta"))
    P13(("1.3 Cambio"))
    P14(("1.4 Baja lógica"))
    P15(("1.5 Buscar<br/>y filtrar"))
    D1[("D1 Usuarios y grupos")]
    D2[("D2 Medicamentos")]
    D4[("D4 Existencias")]

    RW -- "nombre comercial, principio activo,<br/>tipo, presentación, concentración" --> P11
    D1 -- "permisos catalogo.*" --> P11
    D2 -- "¿duplicado?" --> P11
    P11 -- "nuevo" --> P12
    P11 -- "modificado" --> P13
    P11 -- "baja" --> P14
    P12 -- "medicamento activo" --> D2
    P13 -- "datos actualizados" --> D2
    D4 -- "¿existencia > 0?" --> P14
    P14 -- "activo = falso" --> D2
    P11 -. "403 / datos inválidos / duplicado" .-> RW
    P14 -. "rechazo: tiene existencias" .-> RW
    US -- "nombre o principio activo" --> P15
    D2 -- "coincidencias" --> P15
    P15 -- "listado filtrado" --> US
```

- La **baja es lógica** (`activo = falso`) para conservar el historial de movimientos. Se rechaza si alguna entidad todavía tiene existencias de ese medicamento.
- No se permite duplicar la combinación nombre comercial + presentación + concentración.

##### Flujo 2 — Gestión de entidades (alta / baja / cambio)

```mermaid
flowchart LR
    RW["Usuario<br/>Lectura y escritura"]
    P21(("2.1 Validar<br/>permiso y datos"))
    P22(("2.2 Alta de<br/>residente"))
    P23(("2.3 Cambio<br/>de datos"))
    P24(("2.4 Cambio de estado<br/>egreso / defunción"))
    D1[("D1 Usuarios y grupos")]
    D3[("D3 Entidades")]
    D4[("D4 Existencias")]
    F3(("3. Registrar<br/>movimientos"))

    RW -- "nombre, fecha de nacimiento,<br/>estado" --> P21
    D1 -- "permisos entidades.*" --> P21
    P21 -- "nuevo" --> P22
    P21 -- "modificado" --> P23
    P21 -- "egreso / defunción" --> P24
    P22 -- "entidad tipo RESIDENTE, activo" --> D3
    P23 -- "datos actualizados" --> D3
    P24 -- "estado + fecha" --> D3
    D4 -- "existencias pendientes" --> P24
    P24 -- "lista de existencias a resolver" --> RW
    RW -- "transferir al hogar o<br/>baja por devolución / defunción / egreso" --> F3
    P21 -. "403 / datos inválidos" .-> RW
```

- La entidad **Hogar** se crea en la instalación (semilla) y no se puede dar de baja.
- Los residentes **no se borran**: el egreso o la defunción cambian su estado. El sistema muestra las existencias pendientes del residente para que el usuario las resuelva con el flujo 3.

##### Flujo 3 — Existencias por entidad (entradas, transferencias y bajas)

```mermaid
flowchart TB
    RW["Usuario<br/>Lectura y escritura"]
    P31(("3.1 Validar<br/>permiso y datos"))
    P32(("3.2 Registrar<br/>entrada"))
    P33(("3.3 Transferir"))
    P34(("3.4 Dar de baja"))
    D1[("D1 Usuarios y grupos")]
    D2[("D2 Medicamentos")]
    D3[("D3 Entidades")]
    D4[("D4 Existencias")]
    D5[("D5 Movimientos")]

    RW -- "tipo, entidad(es), medicamento, dosis,<br/>quién entregó / motivo de baja" --> P31
    D1 -- "permiso inventario.add_movimiento" --> P31
    D2 -- "medicamento activo" --> P31
    D3 -- "entidades activas" --> P31
    P31 -- "entrada" --> P32
    P31 -- "transferencia" --> P33
    P31 -- "baja" --> P34
    D4 -- "saldo origen (bloqueado)" --> P33
    D4 -- "saldo (bloqueado)" --> P34
    P32 -- "+ dosis a la entidad" --> D4
    P33 -- "− origen / + destino" --> D4
    P34 -- "− dosis" --> D4
    P32 -- "ENTRADA + quién entregó + usuario + fecha" --> D5
    P33 -- "TRANSFERENCIA + usuario + fecha" --> D5
    P34 -- "BAJA + motivo + usuario + fecha" --> D5
    P31 -. "403 / datos inválidos" .-> RW
    P33 -. "saldo insuficiente" .-> RW
    P34 -. "saldo insuficiente" .-> RW
```

- Cada operación corre en una sola transacción (`transaction.atomic()`): se escribe el movimiento en **D5** y se actualiza el saldo en **D4**, o no se hace nada.
- Transferencias y bajas **bloquean el saldo** (`select_for_update()`) y lo validan antes de descontar, para que nunca quede negativo.
- Motivos de baja: consumo / administración, caducidad, merma, rotura, devolución a la familia, defunción y egreso.
- Los movimientos no se editan ni se borran: un error se corrige con el movimiento inverso.

##### Flujo 4 — Pauta del residente (dosis y frecuencia)

```mermaid
flowchart LR
    RW["Usuario<br/>Lectura y escritura"]
    US["Cualquier usuario<br/>autenticado"]
    P41(("4.1 Validar<br/>permiso y datos"))
    P42(("4.2 Registrar<br/>pauta"))
    P43(("4.3 Modificar<br/>pauta"))
    P44(("4.4 Consultar<br/>pautas"))
    D1[("D1 Usuarios y grupos")]
    D2[("D2 Medicamentos")]
    D3[("D3 Entidades")]
    D6[("D6 Pautas")]

    RW -- "residente, medicamento, dosis,<br/>frecuencia, fecha de inicio" --> P41
    D1 -- "permisos pautas.*" --> P41
    D2 -- "medicamento activo" --> P41
    D3 -- "residente activo" --> P41
    P41 -- "nueva" --> P42
    P41 -- "cambio de dosis o frecuencia" --> P43
    P42 -- "pauta vigente" --> D6
    D6 -- "pauta vigente" --> P43
    P43 -- "cierra la vigente (fecha fin)<br/>y crea una nueva" --> D6
    P41 -. "403 / datos inválidos" .-> RW
    US -- "residente" --> P44
    D6 -- "pautas vigentes e historial" --> P44
    P44 -- "pautas del residente" --> US
```

- La pauta es **informativa**: no mueve existencias ni registra la administración.
- Un cambio de dosis o frecuencia cierra la pauta vigente y crea una nueva, así queda el historial.

##### Flujo 5 — Alta de usuarios y nivel de acceso global

```mermaid
flowchart LR
    ADM["Administrador"]
    US["Usuario"]
    P51(("5.1 Alta de<br/>usuario"))
    P52(("5.2 Asignar<br/>nivel de acceso"))
    P53(("5.3 Desactivar<br/>usuario"))
    P54(("5.4 Autenticar"))
    P55(("5.5 Autorizar<br/>petición"))
    D1[("D1 Usuarios y grupos")]
    PR(("Procesos 1 a 4"))

    ADM -- "usuario, nombre,<br/>contraseña inicial" --> P51
    P51 -- "usuario + hash Argon2" --> D1
    ADM -- "Solo lectura o<br/>Lectura y escritura" --> P52
    P52 -- "grupo único" --> D1
    ADM -- "baja de usuario" --> P53
    P53 -- "activo = falso" --> D1
    US -- "usuario y contraseña" --> P54
    D1 -- "hash, activo, intentos fallidos" --> P54
    P54 -- "sesión (30 min de inactividad)" --> US
    P54 -. "credenciales inválidas /<br/>bloqueo tras 5 intentos" .-> US
    US -- "petición con sesión" --> P55
    D1 -- "permisos del grupo" --> P55
    P55 -- "petición permitida" --> PR
    P55 -. "403 sin permiso" .-> US
```

- Solo el **Administrador** (superusuario) da de alta usuarios, desde el panel de administración de Django.
- Cada usuario pertenece a **un solo grupo**, que define su nivel global: `Solo lectura` (consulta y reportes) o `Lectura y escritura` (todas las operaciones de los flujos 1 a 4).
- Los usuarios **se desactivan en lugar de borrarse**, porque sus movimientos deben seguir mostrando quién los registró.

### **2.2. Descripción de componentes principales:**

> Describe los componentes más importantes, incluyendo la tecnología utilizada

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| **Proxy inverso** | Nginx | Termina HTTPS (certificado `mkcert` en la red local, Let's Encrypt en el VPS), sirve `static/`, aplica cabeceras de seguridad y reenvía el resto a Gunicorn. |
| **Servidor de aplicación** | Gunicorn | Ejecuta la aplicación Django (WSGI) con varios *workers*. |
| **Backend / web** | Python 3.12 + Django 5.2 LTS | Vistas, formularios, autenticación, autorización por grupos y lógica de negocio. |
| **Frontend** | Plantillas Django + Bootstrap 5 + HTMX | Interfaz responsive renderizada en el servidor. HTMX actualiza fragmentos de página (filtros, búsquedas) sin una SPA. |
| **API REST** | Django REST Framework + drf-spectacular | 3 endpoints JSON **de solo lectura** (existencias por entidad, búsqueda de medicamentos, reporte mensual) documentados en OpenAPI. Ver [sección 4](#4-especificación-de-la-api). |
| **Base de datos** | PostgreSQL 17 | Persistencia relacional, transacciones y búsqueda por nombre / principio activo. |
| **Respaldos** | `pg_dump` + cron | Respaldo diario comprimido, con retención de 14 días y copia a disco externo. |

**Módulos (apps de Django) y sus dependencias:**

```mermaid
flowchart TB
    accounts["accounts<br/>usuarios y niveles de acceso"]
    catalogo["catalogo<br/>medicamentos"]
    entidades["entidades<br/>hogar y residentes"]
    pautas["pautas<br/>dosis y frecuencia"]
    inventario["inventario<br/>existencias y movimientos"]
    conteos["conteos<br/>inventario físico"]
    reportes["reportes<br/>reporte mensual"]
    api["api<br/>endpoints solo lectura"]
    pautas --> catalogo
    pautas --> entidades
    inventario --> catalogo
    inventario --> entidades
    inventario --> accounts
    conteos --> inventario
    reportes --> inventario
    reportes --> conteos
    api --> catalogo
    api --> inventario
    api --> reportes
```

- **accounts:** inicio y cierre de sesión. Grupos `Solo lectura` y `Lectura y escritura`. El Administrador (superusuario) gestiona los usuarios desde el panel de administración de Django.
- **catalogo:** alta, baja y cambio de medicamentos (nombre comercial, principio activo, genérico u original, presentación, concentración) y búsqueda.
- **entidades:** el hogar y los residentes (nombre, fecha de nacimiento, estado). Cada uno es una *entidad* dueña de existencias.
- **pautas:** dosis y frecuencia de cada medicamento por residente (informativo).
- **inventario:** existencias por entidad y medicamento (en dosis) y registro de **movimientos** (entrada, transferencia, baja con motivo). Incluye `services.py` con las reglas de negocio.
- **conteos:** conteo físico a demanda por entidad y rango de fechas, y comparación contra lo registrado.
- **reportes:** reporte mensual en pantalla de existencias y movimientos.
- **api:** *serializers* y vistas de solo lectura de DRF, además del esquema OpenAPI.

### **2.3. Descripción de alto nivel del proyecto y estructura de ficheros**

> Representa la estructura del proyecto y explica brevemente el propósito de las carpetas principales, así como si obedece a algún patrón o arquitectura específica.

```
AI4Devs-finalproject-vmrr/
├── readme.md                  # documentación del proyecto
├── prompts.md                 # prompts utilizados con IA
├── docs/                      # documentación de apoyo y diagramas
├── docker-compose.yml         # servicios: nginx, web, db
├── .env.example               # variables de entorno de ejemplo (el .env real no se versiona)
├── .github/workflows/ci.yml   # integración continua: lint + tests
├── nginx/
│   ├── default.conf           # proxy inverso, HTTPS, cabeceras de seguridad
│   └── certs/                 # certificados locales (no versionados)
├── scripts/
│   ├── backup_db.sh           # respaldo con pg_dump
│   └── restore_db.sh          # restauración de un respaldo
└── app/                       # proyecto Django
    ├── Dockerfile
    ├── requirements.txt
    ├── manage.py
    ├── config/                # configuración global
    │   ├── settings/          # base.py, local.py, prod.py
    │   ├── urls.py
    │   └── wsgi.py
    ├── apps/                  # un módulo de negocio por app
    │   ├── accounts/
    │   ├── catalogo/
    │   ├── entidades/
    │   ├── pautas/
    │   ├── inventario/
    │   │   ├── models.py      # Existencia, Movimiento
    │   │   ├── services.py    # reglas: registrar_entrada, transferir, dar_de_baja
    │   │   ├── forms.py
    │   │   ├── views.py
    │   │   ├── urls.py
    │   │   ├── templates/inventario/
    │   │   └── tests/
    │   ├── conteos/
    │   ├── reportes/
    │   └── api/               # serializers.py, views.py, urls.py
    ├── templates/             # base.html y layout común (Bootstrap)
    ├── static/                # css, js (htmx), imágenes
    └── fixtures/              # datos de ejemplo y grupos de permisos
```

**Patrón:** estructura estándar de Django organizada **por dominio**: cada app contiene sus modelos, servicios, vistas, plantillas y tests. La configuración está separada por entorno (`local` / `prod`) y se controla con variables de entorno, siguiendo la metodología *12-factor*. La infraestructura (`nginx/`, `scripts/`, `docker-compose.yml`) queda fuera del código de la aplicación.

### **2.4. Infraestructura y despliegue**

> Detalla la infraestructura del proyecto, incluyendo un diagrama en el formato que creas conveniente, y explica el proceso de despliegue que se sigue

```mermaid
flowchart TB
    subgraph DEV["Desarrollo"]
        GH["GitHub<br/>repositorio"]
        CI["GitHub Actions<br/>ruff + pytest + build de imagen"]
        GH --> CI
    end
    subgraph LAN["Red del hogar (producción actual)"]
        PC["PC / celular<br/>wifi del hogar"]
        subgraph HOST["Servidor local: Ubuntu + Docker"]
            N1["nginx<br/>certificado mkcert"] --> W1["web<br/>Django + Gunicorn"] --> D1[("db<br/>PostgreSQL<br/>volumen pgdata")]
        end
        EXT["Disco externo<br/>respaldos"]
        PC -- "HTTPS (IP fija o nombre local)" --> N1
        D1 -. "pg_dump diario" .-> EXT
    end
    subgraph VPS["VPS: entorno demo hoy / producción futura (HostGator)"]
        N2["nginx<br/>Let's Encrypt"] --> W2["web<br/>Django + Gunicorn"] --> D2[("db<br/>PostgreSQL<br/>datos ficticios")]
    end
    EV["Evaluadores / usuarios remotos"] -- "HTTPS dominio público" --> N2
    GH -. "git pull + docker compose up" .-> W1
    GH -. "git pull + docker compose up (SSH)" .-> W2
```

**Entornos:**

| Entorno | Ubicación | Acceso | Certificado | Datos |
|---|---|---|---|---|
| **Desarrollo** | Equipo del desarrollador | `localhost` | — | Semillas de ejemplo |
| **Producción local** | Servidor Ubuntu con Docker en el hogar | Solo red del hogar | `mkcert` (CA local instalada en los dispositivos) | Reales |
| **Demo** | VPS HostGator (alternativa: video grabado en el equipo de desarrollo si aún no hay VPS) | Internet | Let's Encrypt | Ficticios |
| **Producción futura** | VPS, cuando haya presupuesto | Internet | Let's Encrypt | Reales (migrados con `pg_dump` / `pg_restore`) |

#### **2.4.1. Diagrama de contenedores (C4 – Nivel 2)**

```mermaid
C4Container
    title Contenedores (C4 nivel 2) - Gestión de Medicamentos Hogar Gerontológico

    Person(admin, "Administrador", "Gestiona usuarios y niveles de acceso")
    Person(rw, "Usuario Lectura y escritura", "Registra medicamentos, residentes, movimientos y pautas")
    Person(ro, "Usuario Solo lectura", "Consulta existencias y reportes")

    System_Boundary(sys, "Sistema de Gestión de Medicamentos (Docker Compose)") {
        Container(nginx, "nginx", "Nginx", "Proxy inverso: termina HTTPS, sirve archivos estáticos y aplica cabeceras de seguridad")
        Container(web, "web", "Python 3.12, Django 5.2, Gunicorn, DRF", "App web (HTML con Bootstrap + HTMX) y API REST de solo lectura; reglas de negocio y permisos")
        ContainerDb(db, "db", "PostgreSQL 17", "Usuarios, medicamentos, entidades, existencias, movimientos y pautas")
    }

    System_Ext(backup, "Respaldos", "cron + pg_dump en el host; copia cifrada a disco externo")

    Rel(admin, nginx, "Administra usuarios", "HTTPS 443")
    Rel(rw, nginx, "Opera el inventario", "HTTPS 443")
    Rel(ro, nginx, "Consulta", "HTTPS 443")
    Rel(nginx, web, "Reenvía peticiones", "HTTP 8000, red frontend")
    Rel(web, db, "Lee y escribe con transacciones", "TCP 5432, red backend")
    Rel(backup, db, "Respaldo diario", "pg_dump")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

<!-- NOTA: la sintaxis C4Container de Mermaid es experimental. Si el diagrama no se renderiza correctamente en GitHub (etiquetas encimadas o error de render), se puede convertir a un diagrama de flujo (flowchart) con estilo C4, con los mismos elementos y relaciones, como los diagramas de las secciones 2.1 y 2.1.1. -->

> El **app** y la **API backend** viven en el mismo contenedor `web`: los ejecuta el mismo proceso Django y comparten la capa de servicios y los modelos. Así cumplen la misma lógica y los mismos permisos, con un contenedor menos que operar. Su separación interna (vistas HTML, API, servicios, ORM) se ve en el diagrama de la sección 2.1.

**Qué hace cada contenedor:**

| Contenedor | Imagen / tecnología | Responsabilidad | Puertos | Volúmenes | Redes |
|---|---|---|---|---|---|
| **`nginx`** — proxy inverso | `nginx:stable-alpine` | Único punto de entrada. Termina **HTTPS** (`mkcert` en la red local, Let's Encrypt en el VPS) y redirige 80 → 443. Sirve `/static/` sin pasar por Django. Aplica cabeceras de seguridad (HSTS, CSP, `X-Frame-Options`) y límites de tamaño de petición. Reenvía el resto a `web`. | **80 y 443 publicados** al host | `static` (solo lectura), `nginx/certs` | `frontend` |
| **`web`** — app + API backend | Imagen propia: Python 3.12 + Django 5.2 + Gunicorn | **App web:** renderiza las páginas HTML (Bootstrap + HTMX) de catálogo, entidades, movimientos, pautas, conteos y reportes. **API REST** (DRF): 3 endpoints JSON de solo lectura bajo `/api/`, con esquema OpenAPI. **Backend:** autenticación, sesiones, permisos por grupo, reglas de inventario (`services.py`) y panel `/admin/` para gestionar usuarios. | 8000 (solo interno, no publicado) | `static` (escribe con `collectstatic`) | `frontend` y `backend` |
| **`db`** — base de datos | `postgres:17-alpine` | Persistencia relacional de los almacenes D1 a D6. Garantiza transacciones atómicas y bloqueo de filas (`SELECT ... FOR UPDATE`) para que las existencias nunca queden negativas. | 5432 (solo interno, no publicado) | `pgdata` (datos persistentes) | `backend` |

**Flujos de comunicación entre contenedores:**

| # | Origen → destino | Protocolo / puerto | Contenido | Seguridad |
|---|---|---|---|---|
| 1 | Navegador → `nginx` | **HTTPS (TLS 1.2+) / 443** (80 solo redirige) | Peticiones de páginas, formularios (POST), fragmentos HTMX y llamadas `GET /api/...` | Certificado TLS, HSTS, cookie de sesión `Secure` + `HttpOnly` |
| 2 | `nginx` → navegador | HTTPS / 443 | HTML completo o fragmentos HTMX, JSON de la API, archivos estáticos (CSS, JS, imágenes) | Cabeceras CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options` |
| 3 | `nginx` → `web` | **HTTP / 8000** (proxy inverso, red interna `frontend`) | La misma petición, con cabeceras `X-Forwarded-For` y `X-Forwarded-Proto` | No sale del host; Django confía en `X-Forwarded-Proto` solo desde `nginx` |
| 4 | `web` → `db` | **Protocolo PostgreSQL sobre TCP / 5432** (red interna `backend`) | Consultas SQL parametrizadas del ORM y transacciones de inventario | Usuario de base de datos con privilegios mínimos; credenciales en `.env`; `nginx` no tiene ruta a `db` |
| 5 | Host (cron) → `db` | `docker compose exec db pg_dump` | Respaldo diario comprimido y cifrado (GPG) | Se guarda fuera del contenedor, con retención de 14 días |

**Orden de arranque:** `db` declara un *healthcheck* (`pg_isready`). `web` arranca con `depends_on: condition: service_healthy` y `nginx` arranca después de `web`. Así `web` nunca intenta conectarse a una base de datos que todavía no responde.

**Proceso de despliegue:**
1. **Integración continua:** en cada *push* o *pull request* a `main`, GitHub Actions ejecuta `ruff` (lint), `pytest` contra un servicio PostgreSQL y el *build* de la imagen. Solo se integra a `main` con el pipeline en verde.
2. **Despliegue (local o VPS):** se hace manualmente por SSH, lo cual es suficiente para un solo mantenedor:
   ```bash
   git pull origin main
   docker compose up -d --build
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py collectstatic --noinput
   ```
3. **Primera instalación:** se copia `.env.example` a `.env` y se configuran los secretos, se generan los certificados (`mkcert` en local, `certbot` en el VPS), se crea el superusuario con `createsuperuser` y se cargan los grupos de permisos con `loaddata grupos`.
4. **Respaldos:** un cron diario ejecuta `scripts/backup_db.sh`, que genera un `pg_dump` comprimido y cifrado, con retención de 14 días y copia a un disco externo. Una vez al mes se prueba la restauración con `scripts/restore_db.sh`.
5. **Migración a hosting:** se aprovisiona el VPS con Ubuntu y Docker, se clona el repositorio, se restaura el último respaldo y se apunta el dominio. No hay cambios de código, solo variables de entorno.

### **2.5. Seguridad**

> Enumera y describe las prácticas de seguridad principales que se han implementado en el proyecto, añadiendo ejemplos si procede

| Práctica | Implementación |
|---|---|
| **Cifrado en tránsito** | HTTPS en todos los entornos. En producción: `SECURE_SSL_REDIRECT=True`, HSTS, `SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE`. |
| **Contraseñas** | Hash **Argon2** (`django[argon2]`) y validadores de longitud y complejidad de Django. |
| **Sesiones** | Expiran tras 30 min de inactividad (`SESSION_COOKIE_AGE=1800`, `SESSION_SAVE_EVERY_REQUEST=True`) y al cerrar el navegador. Cookies `HttpOnly` y `SameSite=Lax`. |
| **Fuerza bruta** | `django-axes`: bloquea temporalmente la cuenta tras 5 intentos fallidos. |
| **Autorización** | Grupos `Solo lectura` / `Lectura y escritura` con permisos de Django, validados **en el backend** (`PermissionRequiredMixin` en vistas y `DjangoModelPermissions` en la API). La interfaz oculta botones según el nivel, pero la autorización real ocurre en el servidor. Ejemplo: un usuario de solo lectura que envía un `POST` a `/inventario/bajas/` recibe `403`. |
| **API** | Solo lectura (`GET`), requiere sesión autenticada y no expone métodos de escritura. |
| **Vulnerabilidades web** | CSRF por defecto en formularios y peticiones HTMX. Protección contra XSS por el *autoescape* de plantillas. Protección contra inyección SQL al usar el ORM con consultas parametrizadas. `X-Frame-Options: DENY` y `Content-Security-Policy` en Nginx. |
| **Secretos y configuración** | `SECRET_KEY` y credenciales de base de datos en `.env` (no versionado). `DEBUG=False` y `ALLOWED_HOSTS` restringido en producción. |
| **Aislamiento de red** | PostgreSQL sin puertos expuestos, accesible solo desde el contenedor `web`. El usuario de base de datos de la aplicación tiene privilegios mínimos. |
| **Integridad y trazabilidad** | Cada movimiento guarda usuario y fecha/hora. Los movimientos **no se editan ni se borran**: los errores se corrigen con un movimiento inverso. Las operaciones de inventario corren en `transaction.atomic()` con `select_for_update()` para evitar saldos negativos. |
| **Privacidad (LFPDPPP)** | Minimización de datos (solo nombre y fecha de nacimiento del residente), aviso de privacidad visible y residentes egresados o fallecidos marcados como inactivos en lugar de borrados, para conservar el historial. |
| **Respaldos** | Diarios y cifrados (GPG), con retención limitada y prueba de restauración mensual. |
| **Dependencias** | Versiones fijadas en `requirements.txt` y revisión periódica con `pip-audit`. |

### **2.6. Tests**

> Describe brevemente algunos de los tests realizados

**Herramientas:** `pytest` + `pytest-django` + `factory_boy`, ejecutados en CI contra PostgreSQL real. Playwright (Python) para el flujo de extremo a extremo.

| Tipo | Caso | Resultado esperado |
|---|---|---|
| **Unitario (servicios)** | Registrar una entrada de 30 dosis para un residente | La existencia del residente aumenta en 30 y se crea un movimiento con usuario, fecha y quién entregó. |
| **Unitario (servicios)** | Dar de baja más dosis de las disponibles | Se lanza `ExistenciaInsuficiente` y el saldo no cambia. |
| **Unitario (servicios)** | Transferir del hogar a un residente cuando falla el abono al destino | La transacción se revierte y el saldo del hogar queda igual (atomicidad). |
| **Concurrencia** | Dos bajas simultáneas que juntas superan la existencia (`TransactionTestCase`) | Solo una se aplica y el saldo nunca es negativo. |
| **Unitario (conteos)** | Conteo físico de 18 dosis cuando el sistema registra 20 | La diferencia reportada es −2. |
| **Permisos** | Usuario `Solo lectura` envía un `POST` para registrar una baja | Responde `403` y no se crea el movimiento. |
| **Permisos** | Usuario sin sesión accede a cualquier pantalla | Redirige al login. |
| **API** | `GET /api/v1/existencias?entidad_id=<id>` sin autenticación / autenticado | `401` / `200` con solo las existencias de esa entidad (casos completos en la sección 4.6). |
| **Extremo a extremo** | Login → alta de medicamento → entrada a residente → consulta filtrada por principio activo | El medicamento aparece con la existencia correcta. |

**Criterio:** cobertura ≥ 80 % en las capas de servicios y permisos, que concentran las reglas críticas del negocio.

---

## 3. Modelo de Datos

### **3.1. Diagrama del modelo de datos:**

> Recomendamos usar mermaid para el modelo de datos, y utilizar todos los parámetros que permite la sintaxis para dar el máximo detalle, por ejemplo las claves primarias y foráneas.

**Motor:** PostgreSQL 17. **Convenciones:**
- Claves primarias sustitutas `bigint GENERATED BY DEFAULT AS IDENTITY` (las tablas de catálogo pequeñas usan `smallint`).
- Las claves naturales se protegen con `UNIQUE`.
- Las fechas con hora son `timestamptz`.
- Las cantidades son `numeric(10,2)`, para admitir media tableta sin errores de redondeo.
- **Todas las claves foráneas son `ON DELETE RESTRICT`** (`PROTECT` en Django): no se puede borrar físicamente ningún registro con historial.

```mermaid
erDiagram
    usuario {
        bigint id PK "IDENTITY"
        varchar username UK "150, NOT NULL"
        varchar password "128, NOT NULL, hash Argon2"
        varchar first_name "150, NOT NULL, DEFAULT vacio"
        varchar last_name "150, NOT NULL, DEFAULT vacio"
        varchar email "254, NOT NULL, DEFAULT vacio"
        boolean is_active "NOT NULL, DEFAULT true, baja logica"
        boolean is_superuser "NOT NULL, DEFAULT false, Administrador"
        boolean is_staff "NOT NULL, DEFAULT false, acceso a /admin"
        timestamptz last_login "NULL"
        timestamptz date_joined "NOT NULL, DEFAULT now()"
    }
    auth_group {
        int id PK "IDENTITY"
        varchar name UK "150, NOT NULL: Solo lectura / Lectura y escritura"
    }
    usuario_groups {
        bigint id PK "IDENTITY"
        bigint usuario_id FK, UK "NOT NULL, UNIQUE: un solo grupo por usuario"
        int group_id FK "NOT NULL"
    }
    auth_permission {
        int id PK "IDENTITY"
        varchar codename "100, NOT NULL, ej. add_movimiento"
        varchar name "255, NOT NULL"
        int content_type_id "FK a django_content_type (no mostrado)"
    }
    auth_group_permissions {
        bigint id PK "IDENTITY"
        int group_id FK "NOT NULL, UK compuesto con permission_id"
        int permission_id FK "NOT NULL"
    }
    presentacion {
        smallint id PK "IDENTITY"
        varchar nombre UK "60, NOT NULL: tableta, capsula, jarabe..."
        boolean activo "NOT NULL, DEFAULT true"
    }
    principio_activo {
        bigint id PK "IDENTITY"
        varchar nombre UK "150, NOT NULL, unico sin distinguir mayusculas"
        timestamptz creado_en "NOT NULL, DEFAULT now()"
    }
    medicamento {
        bigint id PK "IDENTITY"
        varchar nombre_comercial "150, NOT NULL"
        varchar tipo "10, NOT NULL, CHECK GENERICO u ORIGINAL"
        smallint presentacion_id FK "NOT NULL"
        varchar concentracion "60, NOT NULL, ej. 500 mg"
        boolean activo "NOT NULL, DEFAULT true, baja logica"
        timestamptz creado_en "NOT NULL, DEFAULT now()"
        timestamptz actualizado_en "NOT NULL, DEFAULT now()"
    }
    medicamento_principio_activo {
        bigint id PK "IDENTITY"
        bigint medicamento_id FK "NOT NULL, UK compuesto con principio_activo_id"
        bigint principio_activo_id FK "NOT NULL"
    }
    entidad {
        bigint id PK "IDENTITY, UK compuesto (id, tipo)"
        varchar tipo "10, NOT NULL, CHECK HOGAR o RESIDENTE"
        varchar nombre "150, obligatorio solo si HOGAR; NULL si RESIDENTE"
        timestamptz creado_en "NOT NULL, DEFAULT now()"
        timestamptz actualizado_en "NOT NULL, DEFAULT now()"
    }
    residente {
        bigint entidad_id PK, FK "FK compuesta (entidad_id, tipo) a entidad"
        varchar tipo "10, NOT NULL, CHECK = RESIDENTE"
        varchar primer_nombre "60, NOT NULL"
        varchar segundo_nombre "60, NULL"
        varchar primer_apellido "60, NOT NULL"
        varchar segundo_apellido "60, NULL"
        date fecha_nacimiento "NOT NULL"
        date fecha_ingreso "NOT NULL"
        varchar estado "10, NOT NULL, DEFAULT ACTIVO, CHECK ACTIVO, EGRESADO, FALLECIDO"
        date fecha_baja "NULL si ACTIVO, obligatoria en otro caso"
    }
    existencia {
        bigint id PK "IDENTITY"
        bigint entidad_id FK "NOT NULL, UK compuesto con medicamento_id"
        bigint medicamento_id FK "NOT NULL"
        numeric saldo "10,2, NOT NULL, DEFAULT 0, CHECK mayor o igual a 0"
        timestamptz actualizado_en "NOT NULL, DEFAULT now()"
    }
    motivo_baja {
        smallint id PK "IDENTITY"
        varchar clave UK "30, NOT NULL, ej. CADUCIDAD"
        varchar descripcion "100, NOT NULL"
        boolean activo "NOT NULL, DEFAULT true"
    }
    movimiento {
        bigint id PK "IDENTITY"
        varchar tipo "15, NOT NULL, CHECK ENTRADA, TRANSFERENCIA, BAJA"
        bigint medicamento_id FK "NOT NULL"
        numeric cantidad "10,2, NOT NULL, CHECK mayor a 0, en dosis"
        bigint entidad_origen_id FK "NULL en ENTRADA"
        bigint entidad_destino_id FK "NULL en BAJA"
        smallint motivo_baja_id FK "obligatorio solo en BAJA"
        varchar origen_entrada "10, CHECK FAMILIAR, HOGAR, OTRO; solo ENTRADA"
        varchar entregado_por "150, quien entrego; solo ENTRADA"
        bigint corrige_a_id FK, UK "NULL, movimiento que corrige"
        text nota "NULL"
        bigint usuario_id FK "NOT NULL, quien registro"
        timestamptz fecha_hora "NOT NULL, DEFAULT now()"
    }
    pauta {
        bigint id PK "IDENTITY"
        bigint residente_id FK "NOT NULL, a residente.entidad_id"
        bigint medicamento_id FK "NOT NULL"
        numeric dosis "6,2, NOT NULL, CHECK mayor a 0, dosis por toma"
        smallint frecuencia_horas "NOT NULL, CHECK 1 a 168, cada N horas"
        boolean si_necesario "NOT NULL, DEFAULT false, PRN"
        text indicaciones "NULL"
        date fecha_inicio "NOT NULL"
        date fecha_fin "NULL = vigente, CHECK mayor o igual a fecha_inicio"
        bigint registrado_por_id FK "NOT NULL, a usuario"
        timestamptz creado_en "NOT NULL, DEFAULT now()"
    }
    conteo_fisico {
        bigint id PK "IDENTITY"
        bigint entidad_id FK "NOT NULL"
        date periodo_inicio "NOT NULL"
        date periodo_fin "NOT NULL, CHECK mayor o igual a periodo_inicio"
        varchar estado "10, NOT NULL, DEFAULT EN_PROCESO, CHECK EN_PROCESO o CERRADO"
        bigint usuario_id FK "NOT NULL, quien realiza el conteo"
        timestamptz creado_en "NOT NULL, DEFAULT now()"
        timestamptz cerrado_en "NULL, obligatoria si CERRADO"
        text nota "NULL"
    }
    detalle_conteo {
        bigint id PK "IDENTITY"
        bigint conteo_id FK "NOT NULL, UK compuesto con medicamento_id"
        bigint medicamento_id FK "NOT NULL"
        numeric cantidad_fisica "10,2, NOT NULL, CHECK mayor o igual a 0"
        numeric cantidad_sistema "10,2, NOT NULL, foto del saldo al contar"
        numeric diferencia "10,2, GENERATED: fisica menos sistema, STORED"
    }

    usuario ||--o| usuario_groups : "tiene a lo sumo uno"
    auth_group ||--o{ usuario_groups : "agrupa"
    auth_group ||--o{ auth_group_permissions : "otorga"
    auth_permission ||--o{ auth_group_permissions : "incluido en"
    presentacion ||--o{ medicamento : "clasifica"
    medicamento ||--|{ medicamento_principio_activo : "contiene"
    principio_activo ||--o{ medicamento_principio_activo : "forma parte de"
    entidad ||--o| residente : "subtipo"
    entidad ||--o{ existencia : "posee"
    medicamento ||--o{ existencia : "se almacena como"
    medicamento ||--o{ movimiento : "se mueve en"
    entidad |o--o{ movimiento : "origen"
    entidad |o--o{ movimiento : "destino"
    motivo_baja |o--o{ movimiento : "justifica"
    usuario ||--o{ movimiento : "registra"
    movimiento |o--o| movimiento : "corrige a"
    residente ||--o{ pauta : "tiene"
    medicamento ||--o{ pauta : "se prescribe en"
    usuario ||--o{ pauta : "registra"
    entidad ||--o{ conteo_fisico : "se cuenta en"
    usuario ||--o{ conteo_fisico : "realiza"
    conteo_fisico ||--|{ detalle_conteo : "incluye"
    medicamento ||--o{ detalle_conteo : "se cuenta en"
```

**Correspondencia con los almacenes del DFD (sección 2.1.1):**

| Almacén | Tablas |
|---|---|
| D1 Usuarios y grupos | `usuario`, `auth_group`, `usuario_groups`, `auth_permission`, `auth_group_permissions` |
| D2 Medicamentos | `medicamento`, `presentacion`, `principio_activo`, `medicamento_principio_activo` |
| D3 Entidades | `entidad` (supertipo), `residente` (subtipo) |
| D4 Existencias | `existencia` |
| D5 Movimientos | `movimiento`, `motivo_baja` |
| D6 Pautas | `pauta` |
| Conteos físicos | `conteo_fisico`, `detalle_conteo` |

**Restricciones avanzadas (DDL PostgreSQL).** Django genera la mayoría con `UniqueConstraint`, `CheckConstraint`, `ExclusionConstraint` y `GeneratedField`. Las demás se agregan en migraciones con `RunSQL`.

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;  -- para la restricción de exclusión de pautas
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- búsqueda por nombre / principio activo (ver 3.3)
CREATE EXTENSION IF NOT EXISTS unaccent;    -- comparar sin acentos: "Losartán" = "losartan"

-- Envoltura IMMUTABLE de unaccent, necesaria para usarla en índices
CREATE FUNCTION f_unaccent(text) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    RETURN public.unaccent('public.unaccent'::regdictionary, $1);

-- D1: cada usuario pertenece a un solo grupo
ALTER TABLE usuario_groups ADD CONSTRAINT uq_usuario_un_grupo UNIQUE (usuario_id);

-- D2: sin duplicados de nombre comercial + presentación + concentración
--     (sin distinguir mayúsculas ni acentos)
CREATE UNIQUE INDEX uq_medicamento_nombre_pres_conc
    ON medicamento (f_unaccent(lower(nombre_comercial)), presentacion_id, f_unaccent(lower(concentracion)));
CREATE UNIQUE INDEX uq_principio_activo_nombre ON principio_activo (f_unaccent(lower(nombre)));

-- D3: un solo Hogar y subtipo coherente con el supertipo
CREATE UNIQUE INDEX uq_entidad_un_hogar ON entidad (tipo) WHERE tipo = 'HOGAR';
ALTER TABLE entidad
    ADD CONSTRAINT uq_entidad_id_tipo UNIQUE (id, tipo),
    ADD CONSTRAINT ck_entidad_nombre  CHECK ((tipo = 'HOGAR') = (nombre IS NOT NULL));
ALTER TABLE residente
    ADD CONSTRAINT ck_residente_tipo  CHECK (tipo = 'RESIDENTE'),
    ADD CONSTRAINT fk_residente_entidad FOREIGN KEY (entidad_id, tipo)
        REFERENCES entidad (id, tipo) ON DELETE RESTRICT,
    ADD CONSTRAINT ck_residente_baja  CHECK ((estado = 'ACTIVO') = (fecha_baja IS NULL)),
    ADD CONSTRAINT ck_residente_fechas CHECK (fecha_baja IS NULL OR fecha_baja >= fecha_ingreso);

-- D4: un saldo por entidad y medicamento, nunca negativo
ALTER TABLE existencia
    ADD CONSTRAINT uq_existencia UNIQUE (entidad_id, medicamento_id),
    ADD CONSTRAINT ck_existencia_saldo CHECK (saldo >= 0);

-- D5: columnas obligatorias y prohibidas según el tipo de movimiento
ALTER TABLE movimiento ADD CONSTRAINT ck_movimiento_por_tipo CHECK (
    (tipo = 'ENTRADA'
        AND entidad_origen_id IS NULL AND entidad_destino_id IS NOT NULL
        AND motivo_baja_id IS NULL
        AND (corrige_a_id IS NOT NULL OR (origen_entrada IS NOT NULL AND entregado_por IS NOT NULL)))
 OR (tipo = 'TRANSFERENCIA'
        AND entidad_origen_id IS NOT NULL AND entidad_destino_id IS NOT NULL
        AND entidad_origen_id <> entidad_destino_id
        AND motivo_baja_id IS NULL AND origen_entrada IS NULL AND entregado_por IS NULL)
 OR (tipo = 'BAJA'
        AND entidad_origen_id IS NOT NULL AND entidad_destino_id IS NULL
        AND motivo_baja_id IS NOT NULL AND origen_entrada IS NULL AND entregado_por IS NULL)
);
ALTER TABLE movimiento
    ADD CONSTRAINT ck_movimiento_cantidad CHECK (cantidad > 0),
    ADD CONSTRAINT uq_movimiento_corrige UNIQUE (corrige_a_id),
    ADD CONSTRAINT ck_movimiento_no_autocorrige CHECK (corrige_a_id <> id);

-- D5: inmutabilidad (doble barrera: privilegios + trigger)
REVOKE UPDATE, DELETE ON movimiento FROM app_user;
CREATE FUNCTION fn_movimiento_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Los movimientos son inmutables: registre un movimiento de corrección';
END $$;
CREATE TRIGGER tg_movimiento_inmutable BEFORE UPDATE OR DELETE ON movimiento
    FOR EACH ROW EXECUTE FUNCTION fn_movimiento_inmutable();

-- D6: sin pautas con vigencias traslapadas para el mismo residente y medicamento
ALTER TABLE pauta
    ADD CONSTRAINT ck_pauta_dosis      CHECK (dosis > 0),
    ADD CONSTRAINT ck_pauta_frecuencia CHECK (frecuencia_horas BETWEEN 1 AND 168),
    ADD CONSTRAINT ck_pauta_fechas     CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio),
    ADD CONSTRAINT ex_pauta_sin_traslape EXCLUDE USING gist (
        residente_id WITH =, medicamento_id WITH =,
        daterange(fecha_inicio, fecha_fin, '[]') WITH &&);

-- Conteos: un renglón por medicamento y diferencia calculada por la base de datos
ALTER TABLE conteo_fisico
    ADD CONSTRAINT ck_conteo_periodo CHECK (periodo_fin >= periodo_inicio),
    ADD CONSTRAINT ck_conteo_cierre  CHECK ((estado = 'CERRADO') = (cerrado_en IS NOT NULL));
ALTER TABLE detalle_conteo
    ADD CONSTRAINT uq_detalle_conteo UNIQUE (conteo_id, medicamento_id),
    ADD CONSTRAINT ck_detalle_fisica CHECK (cantidad_fisica >= 0);
-- diferencia: numeric(10,2) GENERATED ALWAYS AS (cantidad_fisica - cantidad_sistema) STORED

-- Índices de rendimiento y restricciones de integridad adicionales: ver sección 3.3
```

**Datos semilla (migración de datos):**
- La entidad `HOGAR`.
- Los grupos `Solo lectura` y `Lectura y escritura` con sus permisos.
- Los motivos de baja: `CONSUMO`, `CADUCIDAD`, `MERMA`, `ROTURA`, `DEVOLUCION_FAMILIA`, `DEFUNCION`, `EGRESO` y `CORRECCION`.
- Las presentaciones más comunes: tableta, cápsula, jarabe, gotas, ampolleta, parche, crema, inhalador.

### **3.2. Descripción de entidades principales:**

> Recuerda incluir el máximo detalle de cada entidad, como el nombre y tipo de cada atributo, descripción breve si procede, claves primarias y foráneas, relaciones y tipo de relación, restricciones (unique, not null…), etc.

#### D1 — Usuarios y grupos

**`usuario`**: modelo de usuario propio de Django (`AbstractUser`), definido desde el inicio del proyecto como recomienda Django. Representa a quienes usan el sistema.

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | bigint | PK, identity | Identificador |
| `username` | varchar(150) | NOT NULL, UNIQUE | Nombre de inicio de sesión |
| `password` | varchar(128) | NOT NULL | Hash Argon2; nunca la contraseña en claro |
| `first_name` / `last_name` | varchar(150) | NOT NULL, DEFAULT `''` | Nombre para mostrar |
| `email` | varchar(254) | NOT NULL, DEFAULT `''` | Opcional |
| `is_active` | boolean | NOT NULL, DEFAULT true | `false` = usuario dado de baja (no se borra) |
| `is_superuser` | boolean | NOT NULL, DEFAULT false | `true` = **Administrador** |
| `is_staff` | boolean | NOT NULL, DEFAULT false | Acceso al panel `/admin/` (solo el Administrador) |
| `last_login` | timestamptz | NULL | Último inicio de sesión |
| `date_joined` | timestamptz | NOT NULL, DEFAULT now() | Fecha de alta |

**Relaciones:**
- `usuario` 1 — 0..1 `usuario_groups` (**un solo grupo**, por el `UNIQUE (usuario_id)`).
- 1 — N con `movimiento`, `pauta` y `conteo_fisico` (quién registró).

**`auth_group` / `usuario_groups` / `auth_permission` / `auth_group_permissions`**: tablas del sistema de permisos de Django.
- `auth_group` contiene exactamente 2 filas: **Solo lectura** (permisos `view_*`) y **Lectura y escritura** (permisos `view_*`, `add_*` y `change_*` de los módulos de negocio).
- `usuario_groups` es la tabla puente usuario ↔ grupo. Django la define como N:M; el `UNIQUE (usuario_id)` la reduce a **N:1**.
- Un usuario que no es superusuario debe tener exactamente un grupo. El "a lo sumo uno" lo garantiza la base de datos y el "al menos uno" lo valida el formulario del panel de administración.

#### D2 — Medicamentos

**`presentacion`**: catálogo de formas farmacéuticas.

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | smallint | PK, identity | Identificador |
| `nombre` | varchar(60) | NOT NULL, UNIQUE | Tableta, cápsula, jarabe, gotas… |
| `activo` | boolean | NOT NULL, DEFAULT true | Permite retirar opciones sin borrarlas |

**`principio_activo`**: sustancia activa (ej. *paracetamol*, *losartán*).

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | bigint | PK, identity | Identificador |
| `nombre` | varchar(150) | NOT NULL, UNIQUE sin distinguir mayúsculas ni acentos | Nombre de la sustancia; índice trigram para búsqueda (3.3) |
| `creado_en` | timestamptz | NOT NULL, DEFAULT now() | Fecha de alta |

**`medicamento`**: producto del catálogo.

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | bigint | PK, identity | Identificador |
| `nombre_comercial` | varchar(150) | NOT NULL | Nombre del producto; índice trigram para búsqueda (3.3) |
| `tipo` | varchar(10) | NOT NULL, CHECK (`GENERICO`, `ORIGINAL`) | Genérico u original |
| `presentacion_id` | smallint | FK → `presentacion.id`, NOT NULL | Forma farmacéutica |
| `concentracion` | varchar(60) | NOT NULL | Texto libre normalizado, ej. `500 mg`, `50 mg / 12.5 mg` |
| `activo` | boolean | NOT NULL, DEFAULT true | **Baja lógica**; se rechaza si existe saldo > 0 en alguna entidad |
| `creado_en` / `actualizado_en` | timestamptz | NOT NULL, DEFAULT now() | Control de cambios |

- **UNIQUE** (nombre comercial, `presentacion_id`, concentración), sin distinguir mayúsculas ni acentos (`f_unaccent(lower(...))`). La unicidad aplica también a los inactivos: en lugar de duplicar, se reactiva.
- **Relaciones:**
  - N:1 con `presentacion`.
  - N:M con `principio_activo`, a través de `medicamento_principio_activo`.
  - 1:N con `existencia`, `movimiento`, `pauta` y `detalle_conteo`.

**`medicamento_principio_activo`**: tabla puente. Un medicamento tiene **uno o más** principios activos (por ejemplo, una combinación) y un principio activo aparece en muchos medicamentos.

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | bigint | PK, identity | Identificador |
| `medicamento_id` | bigint | FK → `medicamento.id`, NOT NULL | Medicamento |
| `principio_activo_id` | bigint | FK → `principio_activo.id`, NOT NULL | Principio activo |

- UNIQUE (`medicamento_id`, `principio_activo_id`). El "al menos uno" se valida en el formulario.

#### D3 — Entidades

**`entidad`**: **supertipo** de todo lo que puede poseer existencias: el Hogar y cada residente. Gracias a él, `existencia`, `movimiento` y `conteo_fisico` tienen una sola FK real hacia "la entidad".

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | bigint | PK, identity; UNIQUE (`id`, `tipo`) | Identificador |
| `tipo` | varchar(10) | NOT NULL, CHECK (`HOGAR`, `RESIDENTE`) | Discriminador del subtipo |
| `nombre` | varchar(150) | NULL; CHECK: obligatorio si y solo si `tipo = 'HOGAR'` | Nombre del Hogar. En los residentes queda nulo, porque su nombre vive desglosado en `residente` (sin duplicarlo) |
| `creado_en` / `actualizado_en` | timestamptz | NOT NULL, DEFAULT now() | Control de cambios |

- **Un solo Hogar:** índice único parcial `(tipo) WHERE tipo = 'HOGAR'`. Se crea con la semilla y la aplicación no permite modificar su tipo ni darlo de baja.

**`residente`**: **subtipo** de `entidad`, con los datos propios del residente (relación 1:0..1).

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `entidad_id` | bigint | PK; FK compuesta (`entidad_id`, `tipo`) → `entidad (id, tipo)` | Misma clave que su entidad |
| `tipo` | varchar(10) | NOT NULL, CHECK = `RESIDENTE` | Garantiza que solo una entidad `RESIDENTE` tenga fila aquí |
| `primer_nombre` | varchar(60) | NOT NULL | Primer nombre (dato personal, LFPDPPP) |
| `segundo_nombre` | varchar(60) | NULL | Segundo nombre, si lo tiene |
| `primer_apellido` | varchar(60) | NOT NULL | Primer apellido |
| `segundo_apellido` | varchar(60) | NULL | Segundo apellido, si lo tiene |
| `fecha_nacimiento` | date | NOT NULL | Dato personal (LFPDPPP) |
| `fecha_ingreso` | date | NOT NULL | Ingreso al hogar |
| `estado` | varchar(10) | NOT NULL, DEFAULT `ACTIVO`, CHECK (`ACTIVO`, `EGRESADO`, `FALLECIDO`) | La baja es **lógica** |
| `fecha_baja` | date | NULL; CHECK: nula si y solo si `ACTIVO`, y ≥ `fecha_ingreso` | Fecha de egreso o defunción |

- **Nombre para mostrar:** se compone al vuelo (`primer_nombre segundo_nombre primer_apellido segundo_apellido`, omitiendo los nulos) y no se guarda. El índice `ix_residente_nombre` (3.3) acelera la búsqueda y el orden por paciente.
- **Relaciones:** 1:N con `pauta`. Las existencias, movimientos y conteos del residente cuelgan de su `entidad`.

#### D4 — Existencias

**`existencia`**: saldo actual, en dosis, de un medicamento en una entidad.

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | bigint | PK, identity | Identificador |
| `entidad_id` | bigint | FK → `entidad.id`, NOT NULL | Dueño del saldo |
| `medicamento_id` | bigint | FK → `medicamento.id`, NOT NULL | Medicamento |
| `saldo` | numeric(10,2) | NOT NULL, DEFAULT 0, CHECK ≥ 0 | Dosis disponibles (admite 0.5) |
| `actualizado_en` | timestamptz | NOT NULL, DEFAULT now() | Último movimiento aplicado |

- UNIQUE (`entidad_id`, `medicamento_id`).
- **Dato derivado controlado:** el saldo es la suma de los movimientos de esa entidad y ese medicamento. Se guarda materializado porque el DFD lo exige como almacén (D4) y para no sumar todo el historial en cada consulta. Solo lo modifica `inventario/services.py`, dentro de la **misma transacción** que inserta el movimiento y con `SELECT ... FOR UPDATE`. Una consulta de conciliación verifica que `saldo` coincida con la suma de los movimientos; se ejecuta en los tests y como verificación periódica.

#### D5 — Movimientos

**`motivo_baja`**: catálogo de motivos de baja.

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | smallint | PK, identity | Identificador |
| `clave` | varchar(30) | NOT NULL, UNIQUE | `CONSUMO`, `CADUCIDAD`, `MERMA`, `ROTURA`, `DEVOLUCION_FAMILIA`, `DEFUNCION`, `EGRESO`, `CORRECCION` |
| `descripcion` | varchar(100) | NOT NULL | Texto para mostrar |
| `activo` | boolean | NOT NULL, DEFAULT true | Permite retirar motivos sin borrarlos |

**`movimiento`**: registro **inmutable** de cada entrada, transferencia o baja. Es la trazabilidad mínima del sistema.

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | bigint | PK, identity | Identificador |
| `tipo` | varchar(15) | NOT NULL, CHECK (`ENTRADA`, `TRANSFERENCIA`, `BAJA`) | Tipo de operación |
| `medicamento_id` | bigint | FK → `medicamento.id`, NOT NULL | Medicamento movido |
| `cantidad` | numeric(10,2) | NOT NULL, CHECK > 0 | Dosis; siempre positiva (el sentido lo dan origen y destino) |
| `entidad_origen_id` | bigint | FK → `entidad.id`, NULL | De dónde sale (transferencia y baja) |
| `entidad_destino_id` | bigint | FK → `entidad.id`, NULL | A dónde entra (entrada y transferencia) |
| `motivo_baja_id` | smallint | FK → `motivo_baja.id`, NULL | Obligatorio solo en `BAJA` |
| `origen_entrada` | varchar(10) | NULL, CHECK (`FAMILIAR`, `HOGAR`, `OTRO`) | Quién aporta, solo en `ENTRADA` |
| `entregado_por` | varchar(150) | NULL | Nombre de quien entregó, solo en `ENTRADA` |
| `corrige_a_id` | bigint | FK → `movimiento.id`, NULL, UNIQUE | Movimiento que este corrige (cada movimiento se corrige una sola vez) |
| `nota` | text | NULL | Observaciones |
| `usuario_id` | bigint | FK → `usuario.id`, NOT NULL | Quién registró |
| `fecha_hora` | timestamptz | NOT NULL, DEFAULT now() | Cuándo se registró |

**Reglas por tipo** (CHECK `ck_movimiento_por_tipo`):

| Tipo | Origen | Destino | Motivo | Origen de entrada / entregado por | Efecto en `existencia` |
|---|---|---|---|---|---|
| `ENTRADA` | NULL | obligatorio | NULL | obligatorios (salvo en una corrección) | + destino |
| `TRANSFERENCIA` | obligatorio | obligatorio, ≠ origen | NULL | NULL | − origen / + destino |
| `BAJA` | obligatorio | NULL | obligatorio | NULL | − origen |

- **Inmutabilidad:** el usuario de base de datos de la aplicación no tiene privilegios `UPDATE` ni `DELETE` sobre la tabla, y un *trigger* rechaza cualquier intento de modificación.
- **Corrección de errores:** se registra el movimiento inverso con `corrige_a_id`:
  - Una entrada se corrige con una baja de motivo `CORRECCION`.
  - Una baja se corrige con una entrada.
  - Una transferencia se corrige con la transferencia en sentido contrario.
- **Relaciones:**
  - N:1 con `medicamento`, `usuario` y `motivo_baja` (opcional).
  - N:0..1 con `entidad`, dos veces (origen y destino).
  - 0..1:0..1 consigo misma (corrección).

#### D6 — Pautas

**`pauta`**: dosis y frecuencia de un medicamento para un residente, con vigencia. Es informativa: no mueve existencias.

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | bigint | PK, identity | Identificador |
| `residente_id` | bigint | FK → `residente.entidad_id`, NOT NULL | Solo residentes, nunca el Hogar |
| `medicamento_id` | bigint | FK → `medicamento.id`, NOT NULL | Medicamento pautado |
| `dosis` | numeric(6,2) | NOT NULL, CHECK > 0 | Dosis por toma (ej. 0.5, 1, 2) |
| `frecuencia_horas` | smallint | NOT NULL, CHECK 1–168 | Cada cuántas horas (8, 12, 24; semanal = 168) |
| `si_necesario` | boolean | NOT NULL, DEFAULT false | Pauta "en caso necesario" (PRN); la frecuencia es el intervalo mínimo |
| `indicaciones` | text | NULL | Ej. "en ayunas", "con alimentos" |
| `fecha_inicio` | date | NOT NULL | Inicio de vigencia |
| `fecha_fin` | date | NULL, CHECK ≥ `fecha_inicio` | NULL = vigente |
| `registrado_por_id` | bigint | FK → `usuario.id`, NOT NULL | Quién registró |
| `creado_en` | timestamptz | NOT NULL, DEFAULT now() | Fecha de registro |

- **Vigencia sin traslapes:** una restricción de exclusión (`EXCLUDE USING gist`) impide dos pautas con vigencias superpuestas para el mismo residente y medicamento.
- **Cambio de pauta:** se cierra la vigente (`fecha_fin`) y se crea una nueva, así se conserva el historial.

#### Conteos físicos

**`conteo_fisico`**: encabezado de un inventario físico de una entidad para un período.

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | bigint | PK, identity | Identificador |
| `entidad_id` | bigint | FK → `entidad.id`, NOT NULL | Entidad inventariada (residente u Hogar) |
| `periodo_inicio` / `periodo_fin` | date | NOT NULL, CHECK fin ≥ inicio | Rango de fechas a demanda |
| `estado` | varchar(10) | NOT NULL, DEFAULT `EN_PROCESO`, CHECK (`EN_PROCESO`, `CERRADO`) | Permite contar en varias sesiones |
| `usuario_id` | bigint | FK → `usuario.id`, NOT NULL | Quién realiza el conteo |
| `creado_en` | timestamptz | NOT NULL, DEFAULT now() | Inicio del conteo |
| `cerrado_en` | timestamptz | NULL; CHECK: obligatoria si y solo si `CERRADO` | Cierre del conteo |
| `nota` | text | NULL | Observaciones |

**`detalle_conteo`**: un renglón por medicamento contado.

| Atributo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | bigint | PK, identity | Identificador |
| `conteo_id` | bigint | FK → `conteo_fisico.id`, NOT NULL | Conteo al que pertenece |
| `medicamento_id` | bigint | FK → `medicamento.id`, NOT NULL | Medicamento contado |
| `cantidad_fisica` | numeric(10,2) | NOT NULL, CHECK ≥ 0 | Dosis contadas físicamente |
| `cantidad_sistema` | numeric(10,2) | NOT NULL | **Foto** del saldo registrado al momento de contar |
| `diferencia` | numeric(10,2) | GENERATED ALWAYS AS (`cantidad_fisica − cantidad_sistema`) STORED | Calculada por la base de datos; nunca se escribe a mano |

- UNIQUE (`conteo_id`, `medicamento_id`).
- `cantidad_sistema` no es redundante: es un hecho histórico (el saldo de ese momento), que cambia después con nuevos movimientos.
- El conteo **no ajusta existencias automáticamente**. Si hay diferencias, el usuario registra los movimientos que correspondan (por ejemplo, una baja por merma).

#### Normalización (3FN)

- **1FN:** todos los atributos son atómicos. No hay listas ni grupos repetidos: los principios activos de un medicamento van en una tabla puente, no en una columna separada por comas.
- **2FN:** todas las tablas usan una clave primaria sustituta de una sola columna, así que no hay dependencias parciales. En las tablas puente y de detalle, los atributos dependen de la combinación completa.
- **3FN:** ningún atributo no clave depende de otro atributo no clave:
  - La forma farmacéutica vive en `presentacion` y el motivo de baja en `motivo_baja`, en lugar de repetirse como texto.
  - Los datos del residente están en `residente` y no se repiten en `movimiento` ni en `pauta`.
  - El nombre del residente se guarda una sola vez, desglosado en 4 campos atómicos. `entidad.nombre` solo se usa para el Hogar, así el nombre completo no se repite en dos tablas.
  - El estado activo de una entidad no se duplica: se deriva de `residente.estado` (el Hogar siempre está activo).
- **Excepciones documentadas y controladas:**
  - `existencia.saldo`: dato derivado materializado, mantenido en la misma transacción que el movimiento y conciliable.
  - `detalle_conteo.cantidad_sistema`: foto histórica, no redundancia.
  - `detalle_conteo.diferencia`: columna generada por la base de datos.
  - El **reporte mensual no tiene tabla**: se calcula con consultas sobre `movimiento` y `existencia`.

#### Antipatrones evitados

| Antipatrón | Riesgo | Cómo se evita en este modelo |
|---|---|---|
| **Asociación polimórfica** (`entidad_tipo` + `entidad_id` sin FK) | Referencias huérfanas: la base de datos no puede validar la FK | Supertipo `entidad` con subtipo `residente`. Todas las FK son reales y la FK compuesta (`entidad_id`, `tipo`) impide subtipos incoherentes |
| **Listas separadas por comas** (*jaywalking*) en principio activo | No se puede filtrar ni indexar bien, y hay duplicados ocultos | Tabla puente `medicamento_principio_activo` |
| **EAV** (entidad-atributo-valor) | Sin tipos ni restricciones; consultas complejas | Columnas explícitas y tipadas en cada tabla |
| **ENUM/CHECK para listas que cambian** | Requiere migraciones para agregar valores | `presentacion` y `motivo_baja` son tablas de catálogo. CHECK solo para dominios fijos ligados a la lógica (`tipo` de movimiento, `estado`) |
| **Restricciones solo en la aplicación** | Un error o un acceso directo a la base de datos rompe las reglas | `UNIQUE`, `CHECK`, `EXCLUDE` y FK en PostgreSQL. La aplicación valida primero para dar mensajes claros |
| **Borrado físico de historial** | Se pierde la trazabilidad y quedan FK rotas | Baja lógica (`activo`, `estado`, `is_active`), `ON DELETE RESTRICT` y movimientos inmutables |
| **`FLOAT` para cantidades** | Errores de redondeo en saldos | `numeric(10,2)` |
| **Claves naturales mutables como PK** | Cambiar un nombre rompe las referencias | PK sustitutas e índices `UNIQUE` sobre las claves naturales |
| **Datos derivados sin control** | Saldos que no cuadran | Saldo actualizado solo en la transacción del movimiento, con `CHECK ≥ 0`, conciliación y diferencia generada por la base de datos |
| **Fechas sin zona horaria** | Horas ambiguas al migrar a un VPS | `timestamptz` para fecha y hora; `date` para fechas de calendario |
| **Columnas repetidas** (`dosis1`, `dosis2`…) | Esquema rígido | Una fila por pauta, con vigencia |
| **Contraseñas legibles** | Exposición de credenciales | Solo el hash Argon2 en `usuario.password` |

### **3.3. Optimización para rendimiento: índices y restricciones de integridad**

**Volumen esperado.** El catálogo y las entidades son pequeños: unos 300 medicamentos y 21 entidades (20 residentes y el Hogar). La tabla que crece es **`movimiento`**: si se registran las bajas por consumo, son unas 20 personas × 8 medicamentos × 1 a 3 registros al día, es decir, **60,000 a 175,000 filas por año**. Le siguen `detalle_conteo` y `pauta`. Por eso los índices se concentran en las 3 consultas frecuentes y en `movimiento`. En las tablas de catálogo el beneficio principal es la **búsqueda parcial sin acentos**, que sin índice no escala.

**Principios aplicados:**
- Cada índice atiende una consulta concreta. No se indexa "por si acaso", porque cada índice encarece las escrituras.
- **Sin índices redundantes:** Django crea un índice por cada `ForeignKey`. Cuando un índice compuesto ya empieza por esa columna, se declara `db_index=False` para no duplicarlo. Las FK siguen protegidas por `RESTRICT`, porque el índice compuesto también sirve para esas comprobaciones.
- **Orden de columnas:** primero la de igualdad (`=`), luego la de rango u orden (`fecha`).
- **Índices parciales e `INCLUDE`** donde reducen tamaño o permiten *index-only scans*, sin indexar columnas que se actualizan en cada movimiento (`existencia.saldo`).

#### Consulta 1 — Búsqueda por medicamento y/o principio activo, con existencias

```sql
-- Búsqueda parcial, sin acentos ni mayúsculas (mínimo 3 caracteres, como exige trigram).
-- UNION en lugar de OR, para que cada rama use su propio índice.
WITH coincidencias AS (
    SELECT m.id
    FROM medicamento m
    WHERE m.activo
      AND f_unaccent(lower(m.nombre_comercial)) LIKE '%' || f_unaccent(lower(:q)) || '%'
    UNION
    SELECT mpa.medicamento_id
    FROM principio_activo pa
    JOIN medicamento_principio_activo mpa ON mpa.principio_activo_id = pa.id
    WHERE f_unaccent(lower(pa.nombre)) LIKE '%' || f_unaccent(lower(:q)) || '%'
)
SELECT m.id, m.nombre_comercial, p.nombre AS presentacion, m.concentracion,
       e.entidad_id, e.saldo
FROM coincidencias c
JOIN medicamento m       ON m.id = c.id AND m.activo
JOIN presentacion p      ON p.id = m.presentacion_id
LEFT JOIN existencia e   ON e.medicamento_id = m.id AND e.saldo > 0
                        AND (:entidad_id IS NULL OR e.entidad_id = :entidad_id)
ORDER BY m.nombre_comercial;
```

| Índice | Tabla | Definición | Para qué |
|---|---|---|---|
| `ix_medicamento_nombre_trgm` | `medicamento` | `GIN (f_unaccent(lower(nombre_comercial)) gin_trgm_ops) WHERE activo` | Búsqueda parcial por nombre, solo en el catálogo vigente |
| `ix_principio_activo_nombre_trgm` | `principio_activo` | `GIN (f_unaccent(lower(nombre)) gin_trgm_ops)` | Búsqueda parcial por principio activo |
| `ix_mpa_principio_medicamento` | `medicamento_principio_activo` | `(principio_activo_id, medicamento_id)` | Principio activo → medicamentos (el `UNIQUE (medicamento_id, principio_activo_id)` cubre el sentido inverso) |
| `ix_existencia_medicamento_entidad` | `existencia` | `(medicamento_id, entidad_id)` | Medicamento → existencias en todas las entidades. El `UNIQUE (entidad_id, medicamento_id)` cubre entidad → medicamentos |

> **Por qué `existencia.saldo` no va en el índice:** el saldo cambia en cada movimiento. Si estuviera indexado (incluso en `INCLUDE`), PostgreSQL no podría hacer actualizaciones *HOT* y tendría que reescribir los índices cada vez. Además, la tabla se declara con `fillfactor = 90` para dejar espacio a esas actualizaciones en la misma página.

#### Consulta 2 — Búsqueda por medicamento y detalles del conteo físico

```sql
-- a) Detalle de un conteo (pantalla del conteo)
SELECT d.medicamento_id, m.nombre_comercial, d.cantidad_fisica, d.cantidad_sistema, d.diferencia
FROM detalle_conteo d JOIN medicamento m ON m.id = d.medicamento_id
WHERE d.conteo_id = :conteo_id;

-- b) Historial de conteos de un medicamento (¿en qué conteos hubo diferencias?)
SELECT c.id, c.entidad_id, c.periodo_inicio, c.periodo_fin, d.cantidad_fisica, d.cantidad_sistema, d.diferencia
FROM detalle_conteo d JOIN conteo_fisico c ON c.id = d.conteo_id
WHERE d.medicamento_id = :medicamento_id AND d.diferencia <> 0
ORDER BY c.periodo_fin DESC;

-- c) Existencia vs registrados: movimientos de una entidad y un medicamento en el período del conteo
SELECT tipo, cantidad, fecha_hora
FROM movimiento
WHERE (entidad_origen_id = :entidad_id OR entidad_destino_id = :entidad_id)
  AND medicamento_id = :medicamento_id
  AND fecha_hora >= :periodo_inicio AND fecha_hora < :periodo_fin + 1;
```

| Índice | Tabla | Definición | Para qué |
|---|---|---|---|
| `uq_detalle_conteo` (ya existente) | `detalle_conteo` | `UNIQUE (conteo_id, medicamento_id)` | Consulta a: renglones de un conteo |
| `ix_detalle_medicamento_conteo` | `detalle_conteo` | `(medicamento_id, conteo_id) INCLUDE (cantidad_fisica, cantidad_sistema, diferencia)` | Consulta b: historial por medicamento con *index-only scan* (el detalle casi no se actualiza) |
| `ix_detalle_con_diferencia` | `detalle_conteo` | `(medicamento_id) WHERE diferencia <> 0` | Consulta b: solo los renglones con diferencias; índice muy pequeño |
| `ix_conteo_entidad_periodo` | `conteo_fisico` | `(entidad_id, periodo_fin DESC)` | Conteos de un residente o del Hogar, del más reciente al más antiguo |
| `ix_movimiento_origen_med_fecha` | `movimiento` | `(entidad_origen_id, medicamento_id, fecha_hora) WHERE entidad_origen_id IS NOT NULL` | Consulta c (salidas). Parcial: excluye las entradas, que no tienen origen |
| `ix_movimiento_destino_med_fecha` | `movimiento` | `(entidad_destino_id, medicamento_id, fecha_hora) WHERE entidad_destino_id IS NOT NULL` | Consulta c (entradas). El planificador puede combinar ambos índices con un *BitmapOr*, o usar `ix_movimiento_medicamento_fecha` y filtrar por entidad, según las estadísticas de la tabla |
| `ix_movimiento_medicamento_fecha` | `movimiento` | `(medicamento_id, fecha_hora)` | Historial (kárdex) de un medicamento en todas las entidades |
| `brin_movimiento_fecha` | `movimiento` | `BRIN (fecha_hora)` | Reporte mensual por rango de fechas. `movimiento` solo recibe inserciones en orden cronológico, el caso ideal para BRIN: el índice ocupa unos KB |

#### Consulta 3 — Pautas por residente

```sql
-- a) Pautas vigentes de un residente (la consulta más frecuente)
SELECT p.*, m.nombre_comercial
FROM pauta p JOIN medicamento m ON m.id = p.medicamento_id
WHERE p.residente_id = :residente_id
  AND p.fecha_inicio <= current_date
  AND (p.fecha_fin IS NULL OR p.fecha_fin >= current_date);

-- b) Historial de pautas del residente
SELECT * FROM pauta WHERE residente_id = :residente_id ORDER BY fecha_inicio DESC;
```

| Índice | Tabla | Definición | Para qué |
|---|---|---|---|
| `ix_pauta_vigente` | `pauta` | `(residente_id, medicamento_id) WHERE fecha_fin IS NULL` | Consulta a: las pautas abiertas, que son casi todas las vigentes. Índice parcial y pequeño |
| `ix_pauta_residente_inicio` | `pauta` | `(residente_id, fecha_inicio DESC)` | Consulta b, y las pautas vigentes con fecha de fin futura |
| `ex_pauta_sin_traslape` (ya existente) | `pauta` | `GiST (residente_id, medicamento_id, daterange)` | Integridad de la vigencia; también sirve para buscar la pauta vigente de un medicamento específico |
| `ix_residente_nombre` | `residente` | `(f_unaccent(lower(primer_apellido)), f_unaccent(lower(primer_nombre)))` | Buscar y ordenar residentes por apellido y nombre, sin acentos |

#### DDL de índices

```sql
-- Consulta 1
CREATE INDEX ix_medicamento_nombre_trgm ON medicamento
    USING gin (f_unaccent(lower(nombre_comercial)) gin_trgm_ops) WHERE activo;
CREATE INDEX ix_principio_activo_nombre_trgm ON principio_activo
    USING gin (f_unaccent(lower(nombre)) gin_trgm_ops);
CREATE INDEX ix_mpa_principio_medicamento ON medicamento_principio_activo (principio_activo_id, medicamento_id);
CREATE INDEX ix_existencia_medicamento_entidad ON existencia (medicamento_id, entidad_id);
ALTER TABLE existencia SET (fillfactor = 90);

-- Consulta 2
CREATE INDEX ix_detalle_medicamento_conteo ON detalle_conteo (medicamento_id, conteo_id)
    INCLUDE (cantidad_fisica, cantidad_sistema, diferencia);
CREATE INDEX ix_detalle_con_diferencia ON detalle_conteo (medicamento_id) WHERE diferencia <> 0;
CREATE INDEX ix_conteo_entidad_periodo ON conteo_fisico (entidad_id, periodo_fin DESC);
CREATE INDEX ix_movimiento_origen_med_fecha ON movimiento (entidad_origen_id, medicamento_id, fecha_hora)
    WHERE entidad_origen_id IS NOT NULL;
CREATE INDEX ix_movimiento_destino_med_fecha ON movimiento (entidad_destino_id, medicamento_id, fecha_hora)
    WHERE entidad_destino_id IS NOT NULL;
CREATE INDEX ix_movimiento_medicamento_fecha ON movimiento (medicamento_id, fecha_hora);
CREATE INDEX brin_movimiento_fecha ON movimiento USING brin (fecha_hora);

-- Consulta 3
CREATE INDEX ix_pauta_vigente ON pauta (residente_id, medicamento_id) WHERE fecha_fin IS NULL;
CREATE INDEX ix_pauta_residente_inicio ON pauta (residente_id, fecha_inicio DESC);
CREATE INDEX ix_residente_nombre ON residente (f_unaccent(lower(primer_apellido)), f_unaccent(lower(primer_nombre)));
```

**Índices de FK que Django no debe crear** (`db_index=False`), porque ya los cubre un índice compuesto:

| FK | Cubierta por |
|---|---|
| `medicamento_principio_activo.medicamento_id` | `UNIQUE (medicamento_id, principio_activo_id)` |
| `medicamento_principio_activo.principio_activo_id` | `ix_mpa_principio_medicamento` |
| `existencia.entidad_id` | `uq_existencia (entidad_id, medicamento_id)` |
| `existencia.medicamento_id` | `ix_existencia_medicamento_entidad` |
| `movimiento.entidad_origen_id` / `entidad_destino_id` | `ix_movimiento_origen_med_fecha` / `ix_movimiento_destino_med_fecha` |
| `movimiento.medicamento_id` | `ix_movimiento_medicamento_fecha` |
| `detalle_conteo.conteo_id` / `medicamento_id` | `uq_detalle_conteo` / `ix_detalle_medicamento_conteo` |
| `conteo_fisico.entidad_id` | `ix_conteo_entidad_periodo` |
| `pauta.residente_id` | `ix_pauta_residente_inicio` |

#### Restricciones de integridad adicionales

Complementan las de la sección 3.1. Llevan a la base de datos las reglas de negocio que antes solo validaba la aplicación, para que ni un error de código ni un acceso directo puedan romperlas.

| Regla | Mecanismo | Tabla |
|---|---|---|
| No se da de baja un medicamento con existencias | *Trigger* `BEFORE UPDATE OF activo` | `medicamento` |
| No entran existencias a un medicamento inactivo ni a un residente egresado o fallecido (salvo correcciones) | *Trigger* `BEFORE INSERT` | `movimiento` |
| Solo se registran pautas para residentes activos y medicamentos activos | *Trigger* `BEFORE INSERT` | `pauta` |
| Un conteo cerrado no se modifica, ni su encabezado ni sus renglones | *Triggers* `BEFORE UPDATE OR DELETE` / `INSERT OR UPDATE OR DELETE` | `conteo_fisico`, `detalle_conteo` |
| Los textos obligatorios no pueden ser solo espacios | `CHECK (btrim(col) <> '')` | `medicamento`, `principio_activo`, `presentacion`, `entidad`, `residente`, `movimiento` |
| Fechas del residente coherentes | `CHECK` | `residente` |
| La foto del saldo en el conteo no es negativa | `CHECK` | `detalle_conteo` |

```sql
-- Textos obligatorios no vacíos y fechas coherentes
ALTER TABLE medicamento      ADD CONSTRAINT ck_medicamento_textos
    CHECK (btrim(nombre_comercial) <> '' AND btrim(concentracion) <> '');
ALTER TABLE principio_activo ADD CONSTRAINT ck_principio_activo_nombre CHECK (btrim(nombre) <> '');
ALTER TABLE presentacion     ADD CONSTRAINT ck_presentacion_nombre     CHECK (btrim(nombre) <> '');
ALTER TABLE entidad          ADD CONSTRAINT ck_entidad_nombre_no_vacio CHECK (nombre IS NULL OR btrim(nombre) <> '');
ALTER TABLE residente
    ADD CONSTRAINT ck_residente_nombres
        CHECK (btrim(primer_nombre) <> '' AND btrim(primer_apellido) <> ''),
    ADD CONSTRAINT ck_residente_nacimiento
        CHECK (fecha_nacimiento >= DATE '1900-01-01' AND fecha_ingreso >= fecha_nacimiento);
ALTER TABLE movimiento       ADD CONSTRAINT ck_movimiento_entregado
    CHECK (entregado_por IS NULL OR btrim(entregado_por) <> '');
ALTER TABLE detalle_conteo   ADD CONSTRAINT ck_detalle_sistema CHECK (cantidad_sistema >= 0);

-- Medicamento: la baja lógica se rechaza si hay existencias
CREATE FUNCTION fn_medicamento_baja_sin_existencias() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.activo AND NOT NEW.activo AND EXISTS (
        SELECT 1 FROM existencia WHERE medicamento_id = NEW.id AND saldo > 0) THEN
        RAISE EXCEPTION 'No se puede dar de baja el medicamento %: tiene existencias', NEW.id;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_medicamento_baja BEFORE UPDATE OF activo ON medicamento
    FOR EACH ROW EXECUTE FUNCTION fn_medicamento_baja_sin_existencias();

-- Movimiento: el destino debe estar activo (las correcciones quedan exentas)
CREATE FUNCTION fn_movimiento_validar_destino() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.entidad_destino_id IS NOT NULL AND NEW.corrige_a_id IS NULL THEN
        IF NOT (SELECT activo FROM medicamento WHERE id = NEW.medicamento_id) THEN
            RAISE EXCEPTION 'El medicamento % está dado de baja', NEW.medicamento_id;
        END IF;
        IF EXISTS (SELECT 1 FROM residente
                   WHERE entidad_id = NEW.entidad_destino_id AND estado <> 'ACTIVO') THEN
            RAISE EXCEPTION 'La entidad destino % no está activa', NEW.entidad_destino_id;
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_movimiento_validar_destino BEFORE INSERT ON movimiento
    FOR EACH ROW EXECUTE FUNCTION fn_movimiento_validar_destino();

-- Pauta: solo residentes y medicamentos activos
CREATE FUNCTION fn_pauta_validar() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM residente
                   WHERE entidad_id = NEW.residente_id AND estado = 'ACTIVO') THEN
        RAISE EXCEPTION 'El residente % no está activo', NEW.residente_id;
    END IF;
    IF NOT (SELECT activo FROM medicamento WHERE id = NEW.medicamento_id) THEN
        RAISE EXCEPTION 'El medicamento % está dado de baja', NEW.medicamento_id;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_pauta_validar BEFORE INSERT ON pauta
    FOR EACH ROW EXECUTE FUNCTION fn_pauta_validar();

-- Conteo cerrado: inmutable
CREATE FUNCTION fn_conteo_cerrado() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.estado = 'CERRADO' THEN
        RAISE EXCEPTION 'El conteo % está cerrado y no se puede modificar', OLD.id;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_conteo_cerrado BEFORE UPDATE OR DELETE ON conteo_fisico
    FOR EACH ROW EXECUTE FUNCTION fn_conteo_cerrado();

CREATE FUNCTION fn_detalle_conteo_cerrado() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_conteo bigint;
BEGIN
    IF TG_OP = 'DELETE' THEN v_conteo := OLD.conteo_id; ELSE v_conteo := NEW.conteo_id; END IF;
    IF (SELECT estado FROM conteo_fisico WHERE id = v_conteo) = 'CERRADO' THEN
        RAISE EXCEPTION 'El conteo % está cerrado', v_conteo;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_detalle_conteo_cerrado BEFORE INSERT OR UPDATE OR DELETE ON detalle_conteo
    FOR EACH ROW EXECUTE FUNCTION fn_detalle_conteo_cerrado();
```

> Las reglas siguen validándose también en la aplicación (formularios y `services.py`), para dar mensajes claros al usuario. La base de datos es la **última barrera**, no la única.

#### Implementación en Django y verificación

- **Índices:** se declaran en `Meta.indexes` de cada modelo.
  - Índices por expresión, con `GinIndex(OpClass(Func(Lower('nombre_comercial'), function='f_unaccent'), name='gin_trgm_ops'), condition=Q(activo=True))`.
  - Índices compuestos y parciales, con `Index(fields=[...], condition=Q(...), include=[...])`.
  - El índice de fechas de movimiento, con `BrinIndex(fields=['fecha_hora'])`.
- **Extensiones, función, *triggers* y `fillfactor`:** se agregan en migraciones con `RunSQL`, cada una con su `reverse_sql` para poder revertirla.
- **Búsquedas desde el ORM:** se usa una expresión anotada, `annotate(n=Func(Lower('nombre_comercial'), function='f_unaccent')).filter(n__contains=...)`. Así coincide exactamente con la expresión del índice.
- **Verificación:**
  - Se cargan datos sintéticos de un año (unos 175,000 movimientos) y se revisa con `EXPLAIN (ANALYZE, BUFFERS)` que cada consulta frecuente use su índice.
  - Un test de integración lo comprueba con `assertNumQueries` y el plan de ejecución de las consultas clave.
  - En producción, `pg_stat_statements` identifica consultas lentas, y `pg_stat_user_indexes` detecta índices que no se usan para eliminarlos.

### **3.4. Datos de prueba (mock) para demo y desarrollo**

| Archivo | Contenido |
|---|---|
| [`app/fixtures/mock/demo.json`](app/fixtures/mock/demo.json) | Dataset completo en JSON |
| [`app/fixtures/mock/cargar_mock.sql`](app/fixtures/mock/cargar_mock.sql) | Script que lo inserta con las funciones JSON de PostgreSQL (`jsonb_to_recordset`, `jsonb_array_elements_text`) en una sola transacción |

> ⚠️ **Datos 100 % ficticios y contraseñas públicas.** Solo para los entornos de desarrollo y demo; nunca en producción.

**Escenario:** septiembre y la primera quincena de octubre de 2026 en un hogar con 3 residentes. El consumo se registra al corte de cada mes. Las horas están en `America/Mexico_City` (UTC−06:00).

**Usuarios** (el Administrador se crea aparte con `createsuperuser`):

| Usuario | Nombre | Grupo | Contraseña demo |
|---|---|---|---|
| `consulta.demo` | Laura Méndez Castro | Solo lectura | `DemoLectura2026!` |
| `operador.demo` | Jorge Salinas Pérez | Lectura y escritura | `DemoEscritura2026!` |

Las contraseñas vienen como hash **PBKDF2** con el formato de Django (`pbkdf2_sha256$1000000$...`), porque PostgreSQL no puede calcular Argon2. Django las acepta mientras `PBKDF2PasswordHasher` siga en `PASSWORD_HASHERS` después de Argon2, y en el primer inicio de sesión **las rehace automáticamente con Argon2**.

**Residentes:**

| Id | Nombre | Nacimiento | Ingreso | Pauta |
|---|---|---|---|---|
| 101 | María Guadalupe Hernández López | 1938-04-12 | 2023-02-01 | Metformina 850 mg: 1 dosis cada 12 h, con el desayuno y la cena |
| 102 | José Luis Ramírez Ortega | 1941-11-03 | 2024-06-15 | Cozaar 50 mg: 1 dosis cada 24 h, por la mañana |
| 103 | Carmen Torres Vega (sin segundo nombre) | 1935-07-22 | 2025-01-10 | Paracetamol 500 mg: 1 dosis cada 8 h **en caso necesario** (PRN) |

**Medicamentos (15) y existencias finales** (13 principios activos):

| Id | Nombre comercial | Tipo | Presentación | Concentración | Principio(s) activo(s) | Existencias |
|---|---|---|---|---|---|---|
| 1 | Metformina | Genérico | tableta | 850 mg | Metformina | María 62 |
| 2 | Losartán | Genérico | tableta | 50 mg | Losartán | Hogar 20 · José Luis 10 |
| 3 | Cozaar | Original | tableta | 50 mg | Losartán | José Luis 32 |
| 4 | Hyzaar | Original | tableta | 50 mg / 12.5 mg | Losartán + Hidroclorotiazida | — |
| 5 | Omeprazol | Genérico | cápsula | 20 mg | Omeprazol | Hogar 59 |
| 6 | Paracetamol | Genérico | tableta | 500 mg | Paracetamol | Hogar 80 · Carmen 14 |
| 7 | Tempra | Original | jarabe | 160 mg / 5 ml | Paracetamol | Hogar 0 (caducado) |
| 8 | Eutirox | Original | tableta | 100 mcg | Levotiroxina | Carmen 33 |
| 9 | Atorvastatina | Genérico | tableta | 20 mg | Atorvastatina | María 1 |
| 10 | Aspirina Protect | Original | tableta | 100 mg | Ácido acetilsalicílico | Hogar 58 |
| 11 | Donepezilo | Genérico | tableta | 10 mg | Donepezilo | José Luis 2 |
| 12 | Quetiapina | Genérico | tableta | 25 mg | Quetiapina | — |
| 13 | Ventolin | Original | inhalador | 100 mcg / dosis | Salbutamol | — |
| 14 | Exelon | Original | parche | 4.6 mg / 24 h | Rivastigmina | Carmen 3 |
| 15 | Hipromelosa | Genérico | gotas | 0.5 % | Hipromelosa | — |

**Movimientos (28):**
- **15 entradas.** Incluyen compras del hogar, entregas de familiares y una donación (`OTRO`).
- **2 transferencias:**
  - Del Hogar a Carmen, paracetamol para su pauta PRN.
  - **Préstamo** de losartán genérico del Hogar a José Luis mientras su familia trae Cozaar.
- **11 bajas:**
  - Consumo mensual.
  - Merma (blíster húmedo), caducidad (frasco de Tempra) y rotura (cápsula).
  - Una **corrección**: el 1 de octubre se capturó una entrada de 600 en lugar de 60. Se corrigió con una baja `CORRECCION` que la referencia (`corrige_a_id`) y se registró la entrada correcta. El historial conserva los tres movimientos.

**Conteos físicos (2):**

| Id | Entidad | Período | Estado | Resultado |
|---|---|---|---|---|
| 1 | María | 2026-09-01 a 2026-09-30 | `CERRADO` | Metformina cuadra (2 = 2). **Falta 1 tableta de atorvastatina** (0 contra 1) |
| 2 | Hogar | 2026-10-01 a 2026-10-15 | `EN_PROCESO` | Paracetamol y aspirina cuadran. **Falta 1 cápsula de omeprazol** (58 contra 59). Quedan por contar Losartán y Tempra |

**Cómo cargarlo** (en una base recién migrada, con los datos semilla):

```bash
docker compose cp app/fixtures/mock/. db:/tmp/mock/
docker compose exec db psql -U <usuario> -d <base> -v ON_ERROR_STOP=1 -f /tmp/mock/cargar_mock.sql
```

Para volver a empezar: `docker compose down -v`, `docker compose up -d`, `migrate` y cargar de nuevo.

**Validaciones del script** (si algo falla, la transacción completa se revierte):
- Exige que existan el Hogar y las semillas, y **rechaza la carga si la base ya tiene datos** de negocio.
- Las referencias del JSON (grupo, presentación, motivo, usuario, entidad) se resuelven con `LEFT JOIN`. Una referencia inexistente aborta la carga por `NOT NULL` o `CHECK`, en lugar de omitir la fila en silencio.
- **Las existencias no se escriben a mano:** se calculan sumando los movimientos y se comparan contra `existencias_esperadas` del JSON.
- Verifica que **ningún saldo sea negativo en ningún momento** de la historia (suma acumulada con función de ventana).
- Verifica que la foto `cantidad_sistema` de cada conteo sea el saldo real a la hora del conteo.
- Los conteos se insertan `EN_PROCESO` y después se cierran, porque el *trigger* impide agregar renglones a un conteo cerrado.
- Reajusta las secuencias de identidad tras insertar ids explícitos.
- Todos los `CHECK` y *triggers* de las secciones 3.1 y 3.3 siguen activos durante la carga.

**Guion sugerido para la demo:**

| # | Acción | Qué demuestra |
|---|---|---|
| 1 | Buscar "losartan" (sin acento) | Encuentra Losartán y Cozaar por nombre y principio activo, y Hyzaar por su combinación. Muestra existencias por entidad |
| 2 | Buscar "paracetamol" | Aparece Tempra (jarabe) por su principio activo, aunque el nombre no coincida |
| 3 | Entrar como `consulta.demo` e intentar registrar una baja | Solo lectura: responde `403` |
| 4 | Ver el historial de María | La entrada errónea de 600, su corrección y la entrada correcta: los movimientos son inmutables |
| 5 | Ver las existencias de José Luis | El préstamo de losartán genérico del Hogar |
| 6 | Abrir el conteo 2 del Hogar y terminarlo | Conteo en proceso, diferencia calculada y cierre |
| 7 | Dar de baja Tempra (saldo 0) y luego Paracetamol (saldo > 0) | La primera se permite (baja lógica); la segunda se rechaza |
| 8 | Ver las pautas de Carmen | Pauta "en caso necesario" (PRN) |

**Verificación realizada:** el dataset se cargó en un contenedor `postgres:17` sobre las tablas y el DDL de las secciones 3.1 y 3.3, tal como están documentados. Resultado:
- La carga terminó sin errores: 2 usuarios, 13 principios activos, 15 medicamentos, 3 residentes, 3 pautas, 28 movimientos, 13 existencias, 2 conteos y 5 renglones de conteo.
- Las consultas de la sección 3.3 devuelven lo esperado, y los planes de ejecución usan los índices de búsqueda, de pautas, de conteos y de movimientos.
- Las reglas de integridad rechazaron:
  - Modificar un movimiento.
  - Dar de baja un medicamento con existencias.
  - Agregar un renglón a un conteo cerrado.
  - Duplicar "LOSARTAN 50 MG".
  - Una pauta traslapada.
  - Una baja sin motivo.
  - Una segunda carga del mock.

---

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

---

## 5. Historias de Usuario

> Documenta 3 de las historias de usuario principales utilizadas durante el desarrollo, teniendo en cuenta las buenas prácticas de producto al respecto.

**Historia de Usuario 1**

**Historia de Usuario 2**

**Historia de Usuario 3**

---

## 6. Tickets de Trabajo

> Documenta 3 de los tickets de trabajo principales del desarrollo, uno de backend, uno de frontend, y uno de bases de datos. Da todo el detalle requerido para desarrollar la tarea de inicio a fin teniendo en cuenta las buenas prácticas al respecto. 

**Ticket 1**

**Ticket 2**

**Ticket 3**

---

## 7. Pull Requests

> Documenta 3 de las Pull Requests realizadas durante la ejecución del proyecto

**Pull Request 1**

**Pull Request 2**

**Pull Request 3**

