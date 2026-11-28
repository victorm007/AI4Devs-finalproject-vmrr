# Pendientes por ticket

Hallazgos de las revisiones y comprobaciones que un ticket dejó para otro. Ninguno contradice al readme. Se agrupan por el ticket o la historia que los retoma.

**Cómo se usa** (skill `implementar-ticket`):
- **Al explorar un ticket,** lee su sección de este archivo. Cada pendiente entra en el plan: se atiende, o se explica por qué sigue esperando.
- **Al cerrarlo,** quita los pendientes que atendió y agrega los que deja, con su destino. Si el destino tiene guía, copia también ahí la nota.
- **Si un pendiente no tiene destino claro,** va en "Al tocar el archivo".

## TK-02 · Servicio de movimientos

| Pendiente | Origen | Qué hacer |
|---|---|---|
| `corregir` debe generar el inverso exacto del original: mismo medicamento, misma cantidad y entidades intercambiadas. `tg_movimiento_validar_destino` exime a cualquier Movimiento con `corrige_a` sin comprobarlo | Revisión de TK-01 (PR #3), hallazgo 9 | Un test en `test_services.py`. Ya está en la guía de TK-02, paso 6 |

## TK-03 · Pantalla de existencias

| Pendiente | Origen | Qué hacer |
|---|---|---|
| EXPLAIN de la consulta 1 de la sección 3.3: que la búsqueda por medicamento use `ix_existencia_med_entidad`, además de los índices trigram | Revisión de TK-01 (PR #3), hallazgo 8 | Un test `lento` con el selector `buscar_existencias` |
| El criterio 11 de TK-01 (readme, sección 6) habla de "las consultas 1c y 2", pero la consulta 1c no existe | Revisión de TK-01 (PR #3), hallazgo 8 | Corregir la errata en el readme y en el anexo de `06` |
| En el *job* `e2e`, el paso `Crear app_owner y app_user` debe terminar sin `connection refused` | HB-03, "Comprobaciones pendientes" | Revisarlo en el primer PR de TK-03 (guía de HB-03, sección 7.1) |

Las 3 están también en la guía de TK-03, sección 0.4.

## TK-06 · Servicio de conteos (sin guía todavía)

| Pendiente | Origen | Qué hacer |
|---|---|---|
| EXPLAIN de la consulta 2b de la sección 3.3: que el historial de diferencias use `ix_detalle_con_diferencia`. Django lo declara como `NOT diferencia = 0`, y no está comprobado que el planificador lo empareje con `diferencia <> 0` | Revisión de TK-01 (PR #3), hallazgo 8 | Un test `lento` con la consulta del servicio |
| Los permisos de los grupos sobre `conteos` (`view_conteofisico`, `add_conteofisico`…) cambian los conjuntos exactos que fijan `apps/accounts/tests/test_grupos.py` y `test_admin_usuarios.py`, y la spec de `accounts` | Lección de TK-01 (disputa 1) | Sumarlos a esos tests y a la spec en el mismo cambio, como hizo TK-01 con inventario |

## HB-10 · Despliegue en el hogar

| Pendiente | Origen | Qué hacer |
|---|---|---|
| Los Scenarios del `Makefile` y de `.env` (18 comandos, `HOGAR_NOMBRE` sin comentar, valores con espacios) solo se comprueban a mano | Revisión de TK-01 (PR #3), hallazgo 5 | Un test en `tests/` con un `.env` temporal, junto a `tests/test_candado.py` |
| `scripts/migrate.sh` no quita el `\r` de un `.env` con fin de línea CRLF, y `make format` con `\|\| true` oculta también un fallo real de djLint | Revisión de TK-01 (PR #3), *nits* | Al escribir la lectura de `.env` de los scripts de respaldo y al completar el `Makefile` |

Están también en la guía de HB-10, sección 0.5, que tiene además los pendientes propios de su ejecución.

## Historia de reportes (EP-04, sin ticket)

| Pendiente | Origen | Qué hacer |
|---|---|---|
| Django crea índices sobre `movimiento.motivo_baja_id`, `movimiento.usuario_id` y `conteo_fisico.usuario_id` que ninguna consulta de la sección 3.3 usa (ADR-0018) | Revisión de TK-01 (PR #3), hallazgo 6 | Con las consultas del reporte mensual, decidir en el readme si se quedan o pasan a `db_index=False` |

## Historia de Pautas (EP-05, sin ticket)

Los 8 pendientes de las 2 revisiones de HB-07 están en la guía de HB-07, en la tabla "Pendientes para la historia de Pautas": índices sobre `medicamento_id` y `registrado_por_id`, `tg_pauta_validar` solo en `INSERT`, `Pauta.__str__`, `Pauta.clean()` y la vía de formulario, entre otros.

## Pantallas de Residentes (sin ticket)

| Pendiente | Origen | Qué hacer |
|---|---|---|
| No hay reglas de transición de estado del Residente (de `FALLECIDO` a `ACTIVO`, `fecha_baja` futura) ni protección contra Residentes duplicados | Revisión de HB-09, hallazgo 5 | Decidirlo en la historia que lleve los Residentes fuera de `/admin/` |
| Los títulos del panel no tienen test, y `accounts` no usa `SinBorrarMixin` | Revisión de HB-09, hallazgo 10 | Al volver a tocar el panel |

## Al tocar el archivo

| Pendiente | Origen | Qué hacer |
|---|---|---|
| "Rojo esperado" queda como texto permanente en los *docstrings* de los tests de TK-01 | Revisión de TK-01 (PR #3), *nit* | Pasarlo a tiempo pasado ("Rojo comprobado") al volver a editar cada archivo |
