# Design

## Context

HB-01 ya dejó `docker-compose.yml` con el servicio `db`, `.env.example` y el `.env` local. `app/` solo contiene `fixtures/mock/`. La motivación y el alcance están en `proposal.md`, y el comportamiento exigido, en `specs/infraestructura/spec.md`.

El código de la guía se ensayó en un contenedor desechable con las versiones de este diseño: la imagen se construye, Gunicorn responde `404`, `manage.py check` no reporta problemas y ruff no encuentra errores.

## Goals / Non-Goals

**Goals:**

- Construir y levantar `web` con un solo comando, sin que Django toque la base de datos.
- Comprobar cada criterio con un comando que falle cuando el criterio no se cumple.

**Non-Goals:**

- Conectar Django a PostgreSQL, crear el modelo de usuario o configurar pytest: son de HB-03.
- Servir HTTPS o estáticos: es de HB-04.

## Decisions

### 1. Versiones fijadas

Se usan las últimas estables consultadas en PyPI el 2026-11-18: Django 5.2.19 (última de la serie LTS), gunicorn 27.0.1, pytest 9.2.0, pytest-cov 7.1.0, pytest-django 4.14.0 y ruff 0.17.5. djLint se queda en 1.50.4 por decisión del proyecto ([ADR-0024](../../../docs/adr/0024-calidad-estatica-con-verificador-unico.md)).

### 2. `SECRET_KEY` solo con letras y números

La guía genera la clave con `get_random_secret_key()` y pide evitar `$` y `#`. Esa función también produce `&`, `(`, `)` y `*`, y `. ./.env` falla con un error de sintaxis ante `&` o paréntesis. En un ensayo, las 200 claves generadas traían algún carácter fuera de letras, números, `_`, `=`, `+` y `-`. La clave se genera con `secrets` y solo letras y números, 64 caracteres.

*Alternativa descartada:* poner la clave entre comillas en `.env`. El proyecto prohíbe comillas en sus valores porque `make` (TK-01) las lee de forma distinta.

### 3. La prueba de caché cambia contenido real

La guía usa `touch app/config/urls.py`, pero Docker calcula la caché por contenido, no por fecha: con `touch` también sale de la caché el paso que copia el código, así que la prueba no demuestra nada. Además, en salida no interactiva `CACHED` aparece en una línea aparte. La verificación copia `app/` a un directorio temporal, cambia un `.py` y comprueba por número de paso que `pip install` sale de la caché y que `COPY` se ejecuta.

### 4. `:0` cuenta como puerto sin publicar

Docker Compose 5.6.1 imprime `:0` en `docker compose port` cuando el puerto no está publicado, en lugar de no imprimir nada como dice la guía. La verificación acepta `:0` y exige además que `docker inspect` no tenga puertos enlazados.

### 5. La lectura de `[tool.djlint]` se prueba por su efecto

Sin plantillas, `No files to check!` aparece con o sin configuración. La verificación pasa un HTML por la entrada estándar: con `pyproject.toml` no se reporta `H030`, y sin él sí. Se comprobó en el ensayo.

### 6. Las verificaciones viven fuera del repositorio

HB-02 no tiene pytest. `verificacion.sh` se guarda en el directorio temporal de la sesión, imprime `PASS` o `FAIL` por prueba y queda congelado por su huella antes de implementar.

## Risks / Trade-offs

- [El resultado del CI solo se conoce en el pull request] → El cambio queda sin archivar hasta comprobar ese Scenario en el PR.
- [El hook de commits necesita ruff y djLint] → Viven en `web`: el contenedor debe estar corriendo al hacer commit de código de `app/`.
- [`./app:/app` oculta el código copiado en la imagen] → Es lo esperado en desarrollo; la imagen de producción se prueba por separado.
- [`--reload` solo sirve en desarrollo] → `GUNICORN_CMD_ARGS` viene de `.env` y queda vacío por defecto.
