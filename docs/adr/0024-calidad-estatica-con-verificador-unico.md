# ADR-0024 · Calidad estática con ruff, djLint y un verificador único

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes`, `api`
- **Fuentes:** `readme.md` §2.3, §2.4 y §6 (definición de hecho común, decisiones de diseño de la habilitación y ficha de HB-02); `CLAUDE.md` ("Stack tecnológico estricto", "Documentación del proceso", "Comandos" y "Formato y verificación del código")

## Contexto

El código Python y las plantillas de Django necesitan un formato y un lint uniformes. El CI y el desarrollo local deben aplicar exactamente las mismas comprobaciones, y el CI no debe fallar por algo que todavía no existe.

## Decisión

- **ruff** para el lint y el formato de Python, y **djLint** para las plantillas de Django (perfil `django`), congelado en la versión **1.50.4**. Las versiones se fijan en `requirements-dev.txt`, que nunca entra en la imagen de producción.
- **No hay formateador de CSS ni de JS:** el proyecto solo usa los de Bootstrap y HTMX, ya minificados en `static/*/vendor/`, que no se reformatean.
- **Un solo verificador, `scripts/verificar.py`**, ejecuta `ruff check`, `ruff format --check` y, si hay plantillas, `djlint --check` y `djlint --lint`. Lo usan:
  - el *job* `lint` del CI (`--modo local`);
  - el hook de Claude Code que corre antes de cada commit con código de `app/`;
  - el hook que formatea cada `.py` o `.html` de `app/` al escribirlo (`--corregir <archivo>`).
- **Cada *job* del CI se activa cuando existe lo que necesita:** `lint` e `imagen` con `app/manage.py` (HB-02), `tests` con `app/conftest.py` (HB-03) y `e2e` con `app/e2e/` (TK-03). Un *job* saltado cuenta como aprobado.
- Pasar `ruff` y djLint es parte de la definición de hecho común de todos los tickets.

## Alternativas consideradas

- **Un formateador de CSS y JS:** no se usa, porque el proyecto solo tiene los archivos de Bootstrap y HTMX, ya minificados, que no se reformatean (definición de hecho común, §6).

## Consecuencias

**Positivas:**
- El CI y el commit local ejecutan exactamente lo mismo, y la regla de saltar djLint mientras no haya plantillas vive en un solo lugar.
- Los PR de solo documentación y los primeros tickets de habilitación no fallan por algo que todavía no existe (§6).

**Negativas:**
- Subir la versión de djLint cambia el formato esperado: se hace en un PR propio que reformatee todas las plantillas.
- El hook de commits niega el commit si no encuentra ruff ni djLint (falla cerrada): hay que levantar el contenedor `web` o instalarlos en el equipo.
