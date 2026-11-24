# Tasks

## 1. Documentación

- [x] 1.1 Guía de HB-09: el *import* dentro del test (3.1), el test del Hogar en 3.2, la sección 3.3, los pasos 1 y 3b, el bloque de `validadores.py` vuelto a copiar y las notas de los hallazgos 4 y 6. Verificado: los 5 bloques de código coinciden con los archivos, y los tests base de 3.1, 3.2 y 3.3 pasan con el código actual (16 de 16).
- [x] 1.2 Una sola capa para la regla en la V2: la nota del readme, `04-api.md`, `openapi.yaml` y el *docstring* de `validadores.py`. Verificado con `npx @redocly/cli lint docs/api/openapi.yaml` (0 errores) y `python scripts/verificar.py`.
- [x] 1.3 El escenario de la spec (delta de `catalogo`), `CLAUDE.md` con `panel.E003` y `Prompt 27`/`Respuesta 27`; verificar con `openspec validate hb-09-ajustes-revision-5 --strict` y la suite completa (`dtest -q --cov=apps --cov-fail-under=80`).

## Workflow follow-up

- Commit y push solo cuando el usuario los pida.
- `/openspec-archive-change hb-09-ajustes-revision-5`, sincronizando las specs.
