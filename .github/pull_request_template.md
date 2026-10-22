<!--
Plantilla de pull request (readme, sección 7).
Título: <tipo>(<módulo>): <qué hace> (TK-NN)   ej.: feat(inventario): servicio de movimientos (TK-02)
Tipos: feat, fix, refactor, test, docs, chore. Borra los comentarios y las secciones que no apliquen.
-->

## Ticket e historia

- **Ticket:** TK-NN (readme, sección 6) · **Historia:** HU-NN · **Guía:** `docs/tickets/TK-NN-....md`
- **Depende de:** #PR / ninguno · **Bloquea a:** TK-NN / ninguno

## Qué cambia y por qué

<!-- 3 a 6 líneas: el problema, la solución y la decisión técnica más importante. -->

## Cómo probarlo

```bash
# Comandos exactos y resultado esperado (copiados de la sección 5 de la guía del ticket)
```

## Archivos modificados

| Capa | Archivo | Cambio |
|---|---|---|
| BD / Backend / Frontend / Tests / Infra | `ruta/archivo.py` | Nuevo · Modificado · Eliminado: qué y por qué |

## Puntos de integración afectados

<!-- Números de la tabla "Puntos de integración" de la sección 6. Si cambias uno que provees, avisa aquí a quien lo consume. -->
- Provee: … · Consume: … · ¿Cambia algún contrato? No / Sí: …

## Checklist del autor

**Definición de hecho común**
- [ ] `ruff check` y `ruff format --check` sin errores; sin `print` ni código comentado.
- [ ] CI en verde: lint, `makemigrations --check`, `pytest` (incluida la prueba de integración) contra PostgreSQL 17.
- [ ] Cobertura ≥ 80 % en servicios y permisos, y no baja respecto de `main`.
- [ ] Sin secretos en el código ni datos personales en los logs (LFPDPPP).
- [ ] La documentación afectada del `readme.md` está actualizada.

**Ticket**
- [ ] Todos los criterios de aceptación del ticket se cumplen (cada uno con su test).
- [ ] La definición de hecho propia del ticket se cumple.
- [ ] La lista de la sección 6 de la guía del ticket está completa.
- [ ] La rama está al día con `main` (`git rebase main`) y sin conflictos.

**Según el tipo de cambio** (marca los que apliquen)
- [ ] BD: migraciones reversibles (`migrate <app> zero`), `sqlmigrate` revisado, nombres iguales a las secciones 3.1 y 3.3.
- [ ] Backend: escrituras de inventario solo por `services.py`, en una transacción; cantidades en `Decimal`.
- [ ] Frontend: sin JavaScript en línea, `<label>` en cada campo, revisado a 390 px; capturas abajo.

## Capturas (solo frontend)

| Escritorio | Celular (390 px) |
|---|---|
| | |

## Métricas de impacto (si aplican)

| Métrica | Antes (`main`) | Después | Objetivo |
|---|---|---|---|
| Tests | | | |
| Cobertura de los módulos tocados | | | |
| Consultas a la BD por operación / página | | | |
| Tiempo de respuesta | | | |

## Riesgos y cómo revertir

<!-- Qué podría fallar en producción y cómo se revierte (revert del squash, migrate a la migración anterior). -->

## Revisión

<!-- Lo completa el revisor. Comentarios en el código marcados como [bloqueante], [sugerencia] o [nit]. -->
- **Revisor:** @… · **Revisión asistida por IA:** sí / no
- **Resumen:** N bloqueantes (resueltos: N) · N sugerencias · N nits

| # | Severidad | Archivo | Comentario | Resolución |
|---|---|---|---|---|
| 1 | | | | |

## Lecciones aprendidas

<!-- Qué haríamos distinto, qué conviene reutilizar y qué hay que documentar en el readme o en las guías. -->
