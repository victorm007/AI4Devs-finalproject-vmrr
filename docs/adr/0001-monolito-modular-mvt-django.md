# ADR-0001 · Monolito modular MVT con Django 5.2 LTS

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes`, `api`
- **Fuentes:** `readme.md` §2.1, §2.2 y §2.3; `CLAUDE.md` ("Stack tecnológico estricto" y "Reglas de arquitectura")

## Contexto

El sistema atiende un solo hogar: 1 sede, unos 20 residentes y de 1 a 3 usuarios. Lo mantiene una sola persona, con perfil de infraestructura y backend. Se usa desde la computadora y desde el celular, debe poder moverse del servidor local del hogar a un VPS sin cambiar código, y necesita transacciones y bloqueo de filas para que las Existencias nunca queden negativas.

## Decisión

- La aplicación es un **monolito modular** sobre el patrón **MVT (Modelo–Vista–Template)** de Django, con Python 3.12 y Django 5.2 LTS.
- Cada módulo de negocio es una *app* de Django en `app/apps/`: `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes` y `api`.
- Las dependencias entre módulos son las del diagrama de la §2.2:
  - `pautas` usa `catalogo` y `entidades`.
  - `inventario` usa `catalogo`, `entidades` y `accounts`.
  - `conteos` usa `inventario`.
  - `reportes` usa `inventario` y `conteos`.
  - `api` usa `catalogo`, `inventario` y `reportes`.
- La estructura de ficheros se organiza **por dominio**: cada app contiene sus modelos, servicios, vistas, plantillas y tests. La infraestructura (`nginx/`, `scripts/`, `docker-compose.yml`) queda fuera del código de la aplicación.
- La web y la API viven en el mismo proceso Django y comparten la capa de servicios y los modelos (ver [ADR-0011](0011-capa-de-servicios-unica-via-de-escritura.md)).

## Alternativas consideradas

- **Microservicios, una SPA o colas de mensajes:** se descartaron porque, con esta escala y una carga mínima, solo añadirían complejidad (§2.1).

## Consecuencias

**Positivas** (§2.1):
- Desarrollo rápido y pocas dependencias: Django trae ORM, migraciones, autenticación, sesiones, permisos por grupos, CSRF, formularios con validación y panel de administración.
- Despliegue sencillo, de 3 contenedores.
- Seguridad sólida por defecto.
- Las reglas de negocio se prueban con facilidad.
- Los módulos bien delimitados permitirían extraer servicios en el futuro si hiciera falta.

**Negativas** (§2.1):
- Escalado solo vertical (un servidor más grande), suficiente para este volumen.
- Acoplamiento a Django: cambiar de framework implicaría reescribir.
- Interactividad limitada frente a una SPA (ver [ADR-0002](0002-renderizado-en-servidor-con-htmx.md)).
