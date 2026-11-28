# Segundos ajustes de la revisión adversarial de TK-01 (PR #3)

**Historia:** HU-01, HU-02, HU-03 · **Ticket:** TK-01 · **Épica:** EP-02

## Why

La revisión adversarial de `c67f733` encontró 1 bloqueante, 2 mayores, 6 menores y 3 *nits*. Lo bloqueante: Django crea 3 índices de FK que ninguna consulta usa, contra ADR-0018. Lo mayor: `make -n test` todavía muestra la contraseña de `app_owner`, y los tests de borrado con historial pasarían aunque faltaran las FK del historial. Se corrigen antes de integrar TK-01, porque TK-02 y TK-03 parten de este esquema.

## What Changes

- **B1 (ADR-0018):** `db_index=False` en `movimiento.motivo_baja_id`, `movimiento.usuario_id` y `conteo_fisico.usuario_id`. Las migraciones `inventario/0005_fk_sin_indice` y `conteos/0004_fk_sin_indice` quitan los índices y son reversibles. La sección 3.3 del readme suma una tabla "FK sin índice porque ninguna consulta las usa".
- **M1:** el `Makefile` ya no expande la contraseña de `app_owner`: la lee el shell de `.env` al ejecutar la receta. Así no aparece ni con `make -n` ni con `--trace`, y desaparecen el `@` y el `echo` con `***` (también el *nit* 1). Lo comprueba un test nuevo en `tests/` con un `.env` temporal.
- **M2:** los tests de borrado con historial demuestran que la causa es el historial, y cubren Medicamento, Entidad, usuario y motivo de baja, como dice el requisito.
- **m1:** el test de migraciones protege con su `try` también `migrate conteos zero`, y comprueba el cuerpo de `fn_detalle_conteo_cerrado` en la ida y en la vuelta.
- **m5:** `fn_detalle_conteo_cerrado` lee el estado del conteo con `FOR SHARE` (migración `conteos/0005_detalle_conteo_bloqueo`). Así, un renglón capturado y el cierre del conteo, en paralelo, ya no dejan un renglón en un conteo cerrado.
- **Documentación:** m2 (ficha y guía de TK-01 con las migraciones y restricciones nuevas), m3 (`PROTECT` en lugar de `RESTRICT` en 3.3), m4 (`0006_permisos_grupos` en el ejemplo de PR de TK-06), m6 (errata "1c" del criterio 11, que queda marcado como parcial), n2 (referencias de `pendientes.md`) y n3 (rol sensible a mayúsculas en `ejecutar_sql` y `session_user` en su test).

**Fuera de alcance:**
- `make -p` sigue mostrando los valores de `.env`, porque el `Makefile` lo incluye para HB-10. Queda anotado como límite aceptado.
- Los EXPLAIN de las consultas 1 (TK-03) y 2b (TK-06) siguen pendientes.
- Los índices de `pauta` siguen en los pendientes de la historia de Pautas.
- El resto de los tests del `Makefile` y de `.env` (pendiente 5) sigue para HB-10.

## Capabilities

### New Capabilities

<!-- Ninguna. -->

### Modified Capabilities

- `inventario`: sin índices propios sobre las FK que ninguna consulta usa, y borrado con historial probado para cada dueño del historial.
- `conteos`: sin índice sobre `conteo_fisico.usuario_id`, y el cierre de un conteo no deja pasar un renglón capturado en paralelo.
- `infraestructura`: el `Makefile` no muestra la contraseña ni con `make -n`.

## Impact

- **Archivos:**
  - Modelos: `app/apps/inventario/models.py` y `app/apps/conteos/models.py`.
  - Migraciones nuevas: `inventario/0005_fk_sin_indice`, `conteos/0004_fk_sin_indice` y `conteos/0005_detalle_conteo_bloqueo`.
  - Herramientas: `Makefile` y `tests/test_makefile.py` (nuevo).
  - Tests: `test_esquema.py` de `inventario` y `conteos`, y `app/pruebas.py` (solo el *docstring*).
  - Documentación: `readme.md` (3.3, ficha de TK-01, ejemplo de PR de TK-06), anexos de `03`, `06` y `07`, guía de TK-01 y `docs/tickets/pendientes.md`.
- **Puntos de integración:** 7 (*fixtures*). `ejecutar_sql` solo documenta el rol sensible a mayúsculas, y su firma no cambia. Los puntos 1, 3, 4, 5 y 8 no cambian.
- **ADR aplicables:** ADR-0018 (se cumple), ADR-0027, ADR-0005, ADR-0015 y ADR-0023.
