# ADR-0020 · Catálogo, Residentes y usuarios desde el panel `/admin/` en el MVP

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `catalogo`, `entidades`, `accounts`
- **Fuentes:** `readme.md` §2.2, §5 ("Habilitadores en el panel `/admin/` de Django") y §6 (HB-08, HB-09 y TK-01 punto 8); `CLAUDE.md` ("Las pantallas son la aplicación; la API no" y "Frontend y vistas")

## Contexto

El catálogo de Medicamentos y los Residentes se capturan al arrancar y después cambian poco. Hacerles pantallas propias costaría cerca de una semana de las 6 del plan, y ese tiempo rinde más en HU-01, HU-02 y HU-03, que son las que dan valor diario.

## Decisión

- En el MVP, los **habilitadores** se operan desde el panel de administración de Django (`django.contrib.admin`, ruta `/admin/`):

  | Habilitador | Qué se hace en `/admin/` | Quién |
  |---|---|---|
  | Usuarios y niveles de acceso | Alta de usuarios, asignación del grupo y desactivación | Administrador |
  | Catálogo de Medicamentos | Alta, cambio y Baja lógica de Medicamentos, principios activos y presentaciones | *Lectura y escritura* edita; *Solo lectura* consulta |
  | Residentes | Alta, cambio de datos y cambio de estado (activo, egresado, fallecido) | *Lectura y escritura* edita; *Solo lectura* consulta |

- **Controles para que el panel respete las reglas del proyecto:**
  - **Sin borrado** (`has_delete_permission = False`): la Baja es lógica ([ADR-0009](0009-bajas-logicas-y-on-delete-restrict.md)).
  - **Existencias, Movimientos y conteos no se registran en el panel**, así nadie puede editar un saldo ni un Movimiento a mano.
  - Los principios activos se agregan en la misma pantalla del Medicamento (*inline* de la tabla puente).
  - Los usuarios de los 2 grupos tienen `is_staff = True` para entrar, y **solo el Administrador** ve las secciones de usuarios y grupos.
  - Los formularios validan antes de guardar las reglas que viven en *triggers*, para mostrar un mensaje en lugar de un `500`. Por ejemplo, rechazan dar de Baja un Medicamento con Existencias.
- El Hogar no se da de alta: lo crean las migraciones.

## Alternativas consideradas

- **Pantallas propias con Bootstrap y HTMX:** se postergaron a la V2 porque costarían cerca de una semana del plan (§5).

## Consecuencias

**Positivas** (§5):
- Poco código: unas 20 a 30 líneas de `admin.py` por modelo.
- Ya incluye las validaciones del modelo y de `Meta.constraints`, los permisos por grupo validados en el servidor, la búsqueda, los filtros, la paginación y el historial de cambios (`LogEntry`).
- Lo mantiene Django 5.2 LTS.
- Es desechable sin costo: al llegar las pantallas propias se quitan los modelos del panel, porque las reglas viven en los modelos, en la base de datos y en `services.py`.

**Negativas** (§5, limitaciones aceptadas):
- La interfaz es genérica, sin el estilo de la aplicación, y menos cómoda en el celular. No afecta el uso diario, porque estas tareas se hacen pocas veces y desde la computadora.
