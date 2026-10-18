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

**Prompt 1:**

**Prompt 2:**

**Prompt 3:**

---

### 4. Especificación de la API

**Prompt 1:**

**Prompt 2:**

**Prompt 3:**

---

### 5. Historias de Usuario

**Prompt 1:**

**Prompt 2:**

**Prompt 3:**

---

### 6. Tickets de Trabajo

**Prompt 1:**

**Prompt 2:**

**Prompt 3:**

---

### 7. Pull Requests

**Prompt 1:**

**Prompt 2:**

**Prompt 3:**
