# Ajustes de HB-06 tras la revisión adversarial

**Historia:** — (habilitador de EP-01) · **Ticket:** HB-06 · **Épica:** EP-01

## Why

La revisión adversarial del PR #2 no encontró bloqueantes en HB-06, pero sí 5 sugerencias y 6 *nits*. Afectan al punto de integración 11, que consumen TK-01, TK-02 y TK-03, y a la creación del Hogar en producción. Conviene resolverlas antes de que esos tickets dependan del comportamiento actual. Son ajustes del mismo ticket: no agregan nada fuera de la ficha de HB-06 ni del punto 11.

## What Changes

- **`Entidad.activa` y `Entidad.__str__`** (sugerencia 1, punto de integración 11):
  - Una Entidad `RESIDENTE` sin su fila en `residente` ya no lanza una excepción: no está activa y se muestra como `Entidad <id>`.
  - Con `select_related("residente")`, recorrer Entidades no hace consultas extra. El docstring lo indica a TK-02 y TK-03.
- **`registrar_residente()`** (sugerencia 2 y *nits* 6 y 7):
  - Decide si el Residente ya está registrado con `_state.adding`, no con `pk`.
  - Si la validación o la escritura fallan, deja el objeto recibido como estaba: estado, fecha de baja y sin Entidad. Así se puede reintentar.
  - Quita los espacios de los extremos de los 4 nombres, y guarda como `NULL` el segundo nombre o el segundo apellido vacíos.
  - `Residente.nombre_completo` no deja espacios de más.
- **Mensaje de `ck_residente_nombres`** (sugerencia 3): `violation_error_message` claro. Llega en una migración `0004` que no cambia la base.
- **`HOGAR_NOMBRE` obligatorio en producción** (sugerencia 4):
  - `config.settings.prod` no arranca sin `HOGAR_NOMBRE`.
  - `docker-compose.yml` deja de inyectar un valor por defecto. Así, un servidor sin la variable no crea un Hogar "Demo" definitivo, que después no se podría renombrar desde la aplicación.
  - Desarrollo, CI y tests siguen con "Hogar Gerontológico Demo" por defecto.
- **Documentación** (sugerencia 5):
  - La sección 7 de la guía de HB-06 ya no aconseja poner en `.env` un valor con espacios antes de TK-01.
  - La guía de HB-04 pasa `HOGAR_NOMBRE` a `check --deploy`.
  - `.env.example` y el readme (2.4, primera instalación) dicen que es obligatoria en producción.
- **Tests** (*nits* 9, 10 y 11):
  - un comentario sobre por qué el Hogar tiene `id = 1`;
  - el mismo patrón `ejecutar_sql` en el test del segundo Hogar;
  - un `TODO(TK-01)` para pasar a `como_app_user`.

**Fuera de alcance:**
- renombrar el Hogar después de la primera migración: va en el despliegue en el servidor del hogar, que aún no tiene ticket;
- leer `.env` con valores con espacios (TK-01);
- el *nit* 8, que ya cubre TK-01.

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `entidades`: Entidad sin subtipo y sin consultas extra; alta con nombres normalizados, objeto restaurado si falla, y mensaje claro para nombres vacíos.
- `infraestructura`: `config.settings.prod` exige `HOGAR_NOMBRE`; `check --deploy` en producción se ejecuta con la variable definida.

## Impact

- **Código:**
  - `app/apps/entidades/models.py`, `services.py` y una migración `0004` (solo cambia el mensaje de `ck_residente_nombres`);
  - `app/config/settings/base.py` y `prod.py`;
  - `docker-compose.yml` y `.env.example`.
- **Tests:**
  - `app/apps/entidades/tests/test_modelos.py` y `test_services.py`;
  - un archivo nuevo, `app/config/tests/test_configuracion.py`, con el marcador `infra`.
- **Documentación:** guías de HB-04 y HB-06, `readme.md` (2.4 y el punto de integración 11 de la sección 6), con su anexo en los transcripts `02` y `06`.
- **Puntos de integración:**
  - amplía el punto 11 (`Entidad.activa` y `Entidad.__str__`) sin romperlo: el contrato para el Hogar y los Residentes no cambia, y se agrega el caso sin subtipo y el uso de `select_related`;
  - consume el punto 6 (`no_vacio()`).
- **ADR aplicables:**
  - [ADR-0004](../../../docs/adr/0004-configuracion-por-entorno-variables-db.md): configuración por entorno;
  - [ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md): mensajes claros antes de la última barrera;
  - [ADR-0008](../../../docs/adr/0008-supertipo-entidad-subtipo-residente.md): supertipo y subtipo;
  - [ADR-0011](../../../docs/adr/0011-capa-de-servicios-unica-via-de-escritura.md): la escritura pasa por `services.py`;
  - [ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md): pruebas contra PostgreSQL real.
