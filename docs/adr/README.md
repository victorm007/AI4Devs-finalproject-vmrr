# Registro de decisiones de arquitectura (ADR)

Esta carpeta formaliza las decisiones de arquitectura significativas que ya están tomadas en el diseño del proyecto, antes de inicializar OpenSpec.

**Origen:** cada decisión sale de `readme.md` (secciones 2 a 6) y de `CLAUDE.md`. Ningún ADR agrega requisitos nuevos. Si un ADR y el readme no coinciden, es un error de documentación que se corrige antes de seguir; para cambiar una decisión se sigue la supersedencia de más abajo. Cada ADR indica en **Fuentes** las secciones de donde sale, y en **Alternativas consideradas** solo menciona las que el propio diseño descarta; cuando el diseño no documenta ninguna, lo dice.

**Formato:** MADR ligero, con estado, fecha, *capabilities* afectadas, fuentes, contexto, decisión, alternativas consideradas y consecuencias.

## Índice

| ID | Título | Estado | Fecha | *Capabilities* futuras afectadas |
|---|---|---|---|---|
| [ADR-0001](0001-monolito-modular-mvt-django.md) | Monolito modular MVT con Django 5.2 LTS | Aceptado | 2026-11-16 | Todas |
| [ADR-0002](0002-renderizado-en-servidor-con-htmx.md) | Renderizado en el servidor con plantillas, Bootstrap 5 y HTMX | Aceptado | 2026-11-16 | `accounts`, `inventario`, `conteos`, `reportes` |
| [ADR-0003](0003-despliegue-docker-compose-tres-contenedores.md) | Despliegue con Docker Compose: `nginx`, `web` y `db` | Aceptado | 2026-11-16 | Todas |
| [ADR-0004](0004-configuracion-por-entorno-variables-db.md) | Configuración por entorno y conexión con variables `DB_*` | Aceptado | 2026-11-16 | Todas |
| [ADR-0005](0005-postgresql-ultima-barrera-de-integridad.md) | PostgreSQL 17 como última barrera de integridad | Aceptado | 2026-11-16 | `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos` |
| [ADR-0006](0006-dos-usuarios-de-base-de-datos.md) | Dos usuarios de base de datos con privilegios mínimos | Aceptado | 2026-11-16 | `accounts`, `inventario`, `conteos` |
| [ADR-0007](0007-nomenclatura-de-objetos-de-base-de-datos.md) | Nombres explícitos y con prefijo para los objetos de la base de datos | Aceptado | 2026-11-16 | `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos` |
| [ADR-0008](0008-supertipo-entidad-subtipo-residente.md) | Entidad como supertipo del Hogar y de cada Residente | Aceptado | 2026-11-16 | `entidades`, `inventario`, `conteos`, `pautas` |
| [ADR-0009](0009-bajas-logicas-y-on-delete-restrict.md) | Bajas lógicas y `ON DELETE RESTRICT` en todas las claves foráneas | Aceptado | 2026-11-16 | `accounts`, `catalogo`, `entidades`, `inventario` |
| [ADR-0010](0010-cantidades-en-dosis-y-tipos-de-fecha.md) | Cantidades en dosis con `numeric` y fechas con zona horaria | Aceptado | 2026-11-16 | `inventario`, `conteos`, `pautas`, `reportes`, `api` |
| [ADR-0011](0011-capa-de-servicios-unica-via-de-escritura.md) | La capa de servicios es la única vía de escritura del inventario | Aceptado | 2026-11-16 | `inventario`, `conteos`, `reportes`, `api` |
| [ADR-0012](0012-movimientos-inmutables-y-correccion.md) | Movimientos inmutables, corregidos con el Movimiento inverso | Aceptado | 2026-11-16 | `inventario`, `reportes`, `api` |
| [ADR-0013](0013-existencia-materializada-y-conciliable.md) | La Existencia es un saldo materializado y conciliable | Aceptado | 2026-11-16 | `inventario`, `conteos`, `reportes`, `api` |
| [ADR-0014](0014-concurrencia-bloqueo-de-existencias.md) | Concurrencia: transacciones y bloqueo de Existencias en orden fijo | Aceptado | 2026-11-16 | `inventario`, `conteos` |
| [ADR-0015](0015-conteo-fisico-no-ajusta-existencias.md) | El conteo físico no ajusta las Existencias | Aceptado | 2026-11-16 | `conteos`, `inventario`, `reportes` |
| [ADR-0016](0016-pautas-informativas-con-vigencia.md) | Pautas informativas, con vigencia y sin traslapes | Aceptado | 2026-11-16 | `pautas`, `entidades`, `catalogo` |
| [ADR-0017](0017-busqueda-sin-acentos-con-trigram.md) | Búsqueda sin mayúsculas ni acentos con `f_unaccent` e índices trigram | Aceptado | 2026-11-16 | `catalogo`, `entidades`, `inventario`, `api` |
| [ADR-0018](0018-indices-guiados-por-consultas.md) | Índices guiados por las consultas frecuentes | Aceptado | 2026-11-16 | `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes` |
| [ADR-0019](0019-api-rest-solo-lectura-openapi-design-first.md) | API REST de solo lectura en el MVP, con contrato OpenAPI 3.2 *design-first* | Aceptado | 2026-11-16 | `api`, `inventario`, `catalogo`, `reportes` |
| [ADR-0020](0020-habilitadores-en-panel-admin.md) | Catálogo, Residentes y usuarios desde el panel `/admin/` en el MVP | Aceptado | 2026-11-16 | `catalogo`, `entidades`, `accounts` |
| [ADR-0021](0021-autorizacion-por-grupos-en-el-servidor.md) | Autorización por 2 grupos de Django, validada en el servidor | Aceptado | 2026-11-16 | Todas |
| [ADR-0022](0022-autenticacion-sesion-argon2-axes.md) | Autenticación: usuario propio, Argon2, sesiones con expiración y django-axes | Aceptado | 2026-11-16 | `accounts`, `api` |
| [ADR-0023](0023-pruebas-contra-postgresql-real.md) | Pruebas contra PostgreSQL real, con el dataset mock y los permisos de la aplicación | Aceptado | 2026-11-16 | Todas |
| [ADR-0024](0024-calidad-estatica-con-verificador-unico.md) | Calidad estática con ruff, djLint y un verificador único | Aceptado | 2026-11-16 | Todas |

**Todas** = `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes` y `api`: las 8 *capabilities* previstas, una por app de Django (§2.2).

## Cómo agregar un ADR

1. Copia la estructura de un ADR existente con el siguiente número libre: `NNNN-titulo-en-kebab-case.md`.
2. Escríbelo en español y con el vocabulario de dominio de `CLAUDE.md`: Residente, Entidad, Medicamento, Existencia, Movimiento, Pauta y Baja.
3. Agrega su fila a la tabla de este índice.
4. Un ADR aceptado no se reescribe.

## Cumplimiento y supersedencia

Las reglas están en `CLAUDE.md` ("Decisiones de Arquitectura (ADRs)"):
- Ninguna propuesta de OpenSpec, ticket ni cambio de código puede contradecir un ADR en estado `Aceptado`.
- Para cambiar una decisión aceptada, primero se crea un ADR nuevo, el anterior pasa a estado `Supersedido por ADR-NNNN` (en su ficha y en este índice), y se actualiza `readme.md`. Solo después se modifican el código o las specs.
- El subagente `adversarial-reviewer` valida cada PR contra los ADR que apliquen.
