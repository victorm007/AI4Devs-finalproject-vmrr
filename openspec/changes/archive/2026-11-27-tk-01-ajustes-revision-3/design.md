# Design

## Context

Ver `proposal.md`. El PR #3 queda abierto mientras se suman los tickets siguientes, por decisión del usuario.

## Decisions

1. **La contraseña va por el entorno de `docker compose`, no por sus argumentos.**
   - Las recetas `test`, `test-ci` y `e2e` empiezan con `DB_PASSWORD="$(CLAVE_OWNER)" $(DC) exec -e DB_USER=app_owner -e DB_PASSWORD web …`. `-e VAR` sin valor hace que `docker compose exec` copie el valor del entorno del proceso.
   - `CLAVE_OWNER := $${DB_OWNER_PASSWORD-$$(sed -n 's/^DB_OWNER_PASSWORD=//p' .env | head -n 1 | tr -d '\r')}`. Si el shell tiene la variable, manda el entorno, como en HB-10. Si no, se toma la primera línea de `.env`.
   - `make` no exporta lo que incluye de `.env` (sección "Sin export" del `Makefile`). Así, el shell solo ve `DB_OWNER_PASSWORD` si venía del entorno.
   - `make -n` sigue mostrando la expresión y no el valor.
   - Se descartó un archivo temporal con la contraseña: tendría que borrarse aunque la receta falle.
2. **Test con un `docker` falso** en `tests/test_makefile.py`.
   - Es un *script* de shell en `tmp_path` que escribe sus argumentos y `$DB_PASSWORD` en un archivo. El test lo pone al principio del `PATH` y corre `make -C <tmp> -f <repo>/Makefile test`, sin `-n`.
   - Se omite si no hay `make` o si `make` no encuentra `/bin/bash`, el `SHELL` del `Makefile`.
3. **El test de migraciones revierte en 2 pasos.** Primero a `0004_fk_sin_indice`: la función debe ser la de `0003`, con `OLD.CONTEO_ID` y `NEW.CONTEO_ID`, sin `FOR SHARE` ni `V_CONTEO`. Después a `0002_triggers`. Al volver a migrar exige `count("FOR SHARE") == 2`.
4. **Rama `OLD`:** un tercer test de concurrencia, el borrado de un renglón mientras se cierra el conteo. Usa las 2 conexiones de los otros 2 tests. Nace en verde, porque `0005` ya bloquea las 2 lecturas. Lo protege también el `count("FOR SHARE") == 2`.
5. **Ubicación de los tests de concurrencia.** Siguen en `conteos/tests/test_esquema.py`, porque prueban un *trigger* y no un servicio. Usan 2 conexiones en lugar de hilos, porque así son deterministas sin `sleep`. `test_concurrencia.py` queda para los servicios, desde TK-02. Se anota en la guía de TK-01.

## Risks / Trade-offs

- [En Windows, GNU Make 3.81 corre las recetas con el `bash` de Git, que convierte el `PATH`] → si el `docker` falso no se encuentra, el test se omite con un motivo claro. El CI (Ubuntu) lo corre siempre.
- [Una variable `DB_OWNER_PASSWORD` vacía en el entorno gana sobre `.env`] → es la semántica de `${VAR-…}`, la misma de HB-10: el entorno manda si está definido.
