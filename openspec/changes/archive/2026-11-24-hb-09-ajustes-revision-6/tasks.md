# Tasks

## 1. Documentación

- [x] 1.1 Guía de HB-09: `test_formularios.py` aparte en el paso 1 y en la tabla del rojo, y la sección 3.4. Verificado: el bloque de la sección 3.4, copiado a un archivo temporal, pasa con el código actual (4 de 4), y `ruff check` y `ruff format --check` no marcan nada.
- [x] 1.2 La nota de la V2 en el readme (sección 4) y en `04-api.md`. Verificado: la línea es idéntica en los 2 archivos.
- [x] 1.3 La descripción del requisito en la spec (delta de `catalogo`). Verificar con `openspec validate hb-09-ajustes-revision-6 --strict`.
- [x] 1.4 La tabla de estos ajustes en la sección 5 de la guía, y `Prompt 29`/`Respuesta 29` en `06-tickets-trabajo.md`. Verificar con `python scripts/verificar.py` y la suite completa (`dtest -q --cov=apps --cov-fail-under=80`).

## Workflow follow-up

- Commit y push solo cuando el usuario los pida.
- `/openspec-archive-change hb-09-ajustes-revision-6`, sincronizando las specs.
