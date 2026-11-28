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
| En el *job* `e2e`, el paso `Crear app_owner y app_user` debe terminar sin `connection refused` | HB-03, "Comprobaciones pendientes" | Revisarlo en el primer PR de TK-03 (guía de HB-03, sección 7.1) |

Las 2 están también en la guía de TK-03, sección 0.4.

## TK-06 · Servicio de conteos (sin guía todavía)

| Pendiente | Origen | Qué hacer |
|---|---|---|
| EXPLAIN de la consulta 2b de la sección 3.3: que el historial de diferencias use `ix_detalle_con_diferencia`. Django lo declara como `NOT diferencia = 0`, y no está comprobado que el planificador lo empareje con `diferencia <> 0` | Revisión de TK-01 (PR #3), hallazgo 8 | Un test `lento` con la consulta del servicio |
| Los permisos de los grupos sobre `conteos` (`view_conteofisico`, `add_conteofisico`…) cambian los conjuntos exactos que fijan `apps/accounts/tests/test_grupos.py` y `test_admin_usuarios.py`, y la spec de `accounts` | Lección de TK-01 (disputa 1) | Sumarlos a esos tests y a la spec en el mismo cambio, como hizo TK-01 con inventario |
| La próxima migración de `conteos` es `0006`: TK-01 tomó de `0003` a `0005`, y el ejemplo de PR de TK-06 (readme, sección 7) ya dice `0006_permisos_grupos.py` | Segunda revisión de TK-01 (PR #3), menor 4 | Crear los permisos de los grupos en `conteos/migrations/0006_permisos_grupos.py`, que depende de `0005_detalle_conteo_bloqueo` |
| El cierre del conteo ya espera a las capturas en curso: `fn_detalle_conteo_cerrado` lee el estado con `FOR SHARE` (`conteos/0005_detalle_conteo_bloqueo`) | Segunda revisión de TK-01 (PR #3), menor 5 | El servicio no necesita bloquear el conteo para eso. Sí valida antes el estado, para que el usuario vea el mensaje y no el error de la base. Quedan 2 riesgos de bloqueo (tercera revisión, menor 2): (a) si una misma transacción captura renglones y después cierra el mismo conteo, 2 sesiones haciéndolo a la vez se interbloquean, porque las 2 tienen el `FOR SHARE` y piden `FOR NO KEY UPDATE`: capturar y cerrar van en transacciones separadas; (b) si `capturar_renglon` bloquea `existencia` (`select_for_update`) y `cerrar_conteo` bloquea el conteo y después `existencia`, el orden debe ser único: primero el conteo, después `existencia` por `entidad_id` (ADR-0014) |

## HB-10 · Despliegue en el hogar

| Pendiente | Origen | Qué hacer |
|---|---|---|
| Los Scenarios del `Makefile` y de `.env` tienen tests solo en parte: `tests/test_makefile.py` cubre ya `make -n` y la contraseña de `app_owner` (que no se vea y que llegue completa a `docker compose`). Falta probar los 18 comandos de `make help`, `HOGAR_NOMBRE` sin comentar en `.env.example` y `scripts/migrate.sh` con valores con espacios | Revisión de TK-01 (PR #3), hallazgo 5; tercera revisión, menor 5 | Sumarlos a `tests/test_makefile.py` (con un `.env` temporal) o junto a `tests/test_candado.py` |
| `scripts/migrate.sh` no quita el `\r` de un `.env` con fin de línea CRLF, y `make format` con `\|\| true` oculta también un fallo real de djLint | Revisión de TK-01 (PR #3), *nits* | Al escribir la lectura de `.env` de los scripts de respaldo y al completar el `Makefile` |
| `make -p` imprime la base de variables de `make`, incluidos los valores de `.env` (contraseñas), porque el `Makefile` hace `-include .env` para el candado | Segunda revisión de TK-01 (PR #3), mayor 1 (límite aceptado) | Decidir al completar el `Makefile` si se filtran, por ejemplo incluyendo solo las variables que necesita |

Están también en la guía de HB-10, sección 0.5, que tiene además los pendientes propios de su ejecución.

## Historia de Pautas (EP-05, sin ticket)

Los 8 pendientes de las 2 revisiones de HB-07 están en la guía de HB-07, en la tabla "Pendientes para la historia de Pautas": índices sobre `medicamento_id` y `registrado_por_id`, `tg_pauta_validar` solo en `INSERT`, `Pauta.__str__`, `Pauta.clean()` y la vía de formulario, entre otros.

## Pantallas de Residentes (sin ticket)

| Pendiente | Origen | Qué hacer |
|---|---|---|
| No hay reglas de transición de estado del Residente (de `FALLECIDO` a `ACTIVO`, `fecha_baja` futura) ni protección contra Residentes duplicados | Primera revisión adversarial de HB-09, hallazgo 5 | Decidirlo en la historia que lleve los Residentes fuera de `/admin/` |
| Los títulos del panel no tienen test, y `accounts` no usa `SinBorrarMixin` | Primera revisión adversarial de HB-09, hallazgo 10 | Al volver a tocar el panel |

## Al tocar el archivo

| Pendiente | Origen | Qué hacer |
|---|---|---|
| "Rojo esperado" queda como texto permanente en los *docstrings* de los tests de TK-01 | Revisión de TK-01 (PR #3), *nit* | Pasarlo a tiempo pasado ("Rojo comprobado") al volver a editar cada archivo |
| `openspec validate --specs --strict` falla en `catalogo`: un requisito pasa de 500 caracteres (aviso que `--strict` vuelve error). Ya fallaba antes de TK-01 | Cierre de la segunda revisión de TK-01 (PR #3) | Al volver a tocar la spec de `catalogo`, partir ese requisito o pasar sus ejemplos a escenarios |
