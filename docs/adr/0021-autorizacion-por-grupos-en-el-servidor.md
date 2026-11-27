# ADR-0021 · Autorización por 2 grupos de Django, validada en el servidor

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Actualización:** 2026-11-23, HB-08: los grupos son de solo consulta en el panel, sin cambiar la decisión
- **Capabilities afectadas:** `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes`, `api`
- **Fuentes:** `readme.md` §2.2, §2.5, §2.6, §3.1, §3.2 (D1), §4.2, §5 y §6 (HB-08, TK-01 punto 7 y punto de integración 5); `CLAUDE.md` ("Frontend y vistas: autorización")

## Contexto

Hay 3 niveles de acceso globales: el Administrador, quien solo consulta y quien además registra. Ocultar botones en la interfaz no basta: un usuario de solo lectura podría enviar un `POST` a mano.

## Decisión

- Hay **exactamente 2 grupos** de Django, creados por una migración de datos:
  - **Solo lectura:** permisos `view_*`.
  - **Lectura y escritura:** permisos `view_*`, `add_*` y `change_*` de los módulos de negocio.
- **El Administrador es el superusuario** (`is_superuser`) y es el único que gestiona usuarios y consulta los grupos. Los grupos son de solo consulta en el panel: su nombre y sus permisos solo los cambia una migración (HB-08).
- **Ningún grupo recibe permisos `delete_*`**, ni permisos sobre usuarios. Sobre `movimiento`, nadie recibe `change_movimiento` ni `delete_movimiento`.
- **Un usuario que no es superusuario tiene exactamente un grupo:** el "a lo sumo uno" lo garantiza la base de datos (`uq_usuario_un_grupo`) y el "al menos uno", el formulario del panel.
- **La autorización se valida siempre en el servidor:**
  - **Pantallas:** `LoginRequiredMixin` y `PermissionRequiredMixin` (por ejemplo, `inventario.add_movimiento`).
  - **API del MVP:** `IsAuthenticated`, porque sus 3 endpoints son de solo lectura ([ADR-0019](0019-api-rest-solo-lectura-openapi-design-first.md)).
  - **`/admin/`:** los permisos de modelo asignados a cada grupo ([ADR-0020](0020-habilitadores-en-panel-admin.md)).
- Los permisos de los modelos de inventario se asignan a los grupos en una migración de TK-01, porque los grupos se crean antes (HB-08).
- La interfaz oculta los botones según el nivel, pero eso es solo comodidad: un usuario de solo lectura que envía un `POST` para registrar una Baja recibe `403` y no se crea el Movimiento.

## Alternativas consideradas

El diseño no documenta alternativas.

## Consecuencias

**Positivas:**
- Los permisos de Django por grupo sirven igual en las pantallas, en el panel y, en V2, en la API (cada operación declara su nivel en `x-nivel-acceso`, §4.2).

**Negativas:**
- Cada modelo nuevo necesita asignar sus permisos a los 2 grupos en una migración.
