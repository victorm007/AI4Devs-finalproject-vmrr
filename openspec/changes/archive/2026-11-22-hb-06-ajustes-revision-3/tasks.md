# Tasks

## 1. Spec

- [x] 1.1 Acotar el requisito "Alta atómica de Residentes" y el GIVEN del Scenario "Un fallo al confirmar permite reintentar"; verificar con `openspec validate hb-06-ajustes-revision-3 --strict`.

## 2. Coherencia con el código

- [x] 2.1 Aclarar el comentario junto al `try` de `registrar_residente()` (savepoint dentro de un `atomic` externo) y comprobar que el docstring de `registrar_residente()` dice lo mismo y que `dtest apps/entidades -q` sigue en verde, sin cambios de comportamiento.

## Workflow follow-up

- Archivar con `/openspec-archive-change hb-06-ajustes-revision-3`, sincronizando la spec `entidades`.
