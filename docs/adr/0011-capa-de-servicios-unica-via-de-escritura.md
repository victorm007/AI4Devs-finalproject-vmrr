# ADR-0011 · La capa de servicios es la única vía de escritura del inventario

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `inventario`, `conteos`, `reportes`, `api`
- **Fuentes:** `readme.md` §2.1, §2.3, §3.2 (D4), §4.4, §4.7, §5 (controles del panel) y §6 (TK-01, TK-02, puntos de integración 2, 9, 10 y 12, criterios de revisión de datos); `CLAUDE.md` ("Lógica de negocio aislada" y "Una sola vía de escritura")

## Contexto

Las reglas de las Entradas, Transferencias y Bajas son el núcleo del sistema. La web y la API deben aplicar exactamente las mismas, y deben poder probarse de forma aislada.

## Decisión

- Las reglas de inventario viven **exclusivamente** en `apps/inventario/services.py`: `registrar_entrada`, `transferir`, `dar_de_baja` y `corregir`, con argumentos por nombre.
- **Solo `services.py` escribe en `movimiento` y `existencia`**, siempre dentro de `transaction.atomic()` ([ADR-0014](0014-concurrencia-bloqueo-de-existencias.md)).
- Las **lecturas reutilizables** van en `selectors.py` (por ejemplo, `buscar_existencias`, que comparten la pantalla y la API).
- **Las vistas no contienen lógica**, y los modelos no sobrescriben `save()` ni `delete()`.
- Los errores de negocio son excepciones de `exceptions.py` con un `code` igual al de la §4.4 (por ejemplo, `ExistenciaInsuficiente` y `MovimientoYaCorregido`), y `DatoInvalido.campo` indica qué campo del formulario marcar.
- **El servicio no decide permisos:** las vistas usan `PermissionRequiredMixin` (por ejemplo, `inventario.add_movimiento`), y el servicio recibe `usuario` solo para registrar quién hizo el Movimiento.
- Los conteos físicos tienen su propio servicio, con `iniciar_conteo`, `capturar_renglon` y `cerrar_conteo` (TK-06).
- Existencias, Movimientos y conteos **no se registran en `/admin/`**: solo se operan desde las pantallas de HU-01 y HU-03.

## Alternativas consideradas

El diseño no documenta alternativas.

## Consecuencias

**Positivas:**
- La web y la API comparten la misma lógica, y las operaciones V2 de la API se implementarán sobre la misma capa, con vistas delgadas (§4.7).
- Las reglas se prueban de forma aislada (§2.1).
- Nadie puede editar un saldo ni un Movimiento a mano desde el panel (§5).

**Negativas:**
- Escribir en el inventario fuera de `services.py` es un defecto bloqueante en la revisión de código (§6).
