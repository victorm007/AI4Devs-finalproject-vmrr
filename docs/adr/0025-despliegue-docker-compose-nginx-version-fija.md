# ADR-0025 · Despliegue con Docker Compose: `nginx`, `web` y `db`, con `nginx` en versión fija

- **Estado:** Supersedido por [ADR-0026](0026-despliegue-servidor-del-hogar-y-demo-local.md)
- **Fecha:** 2026-11-20
- **Supersede a:** [ADR-0003](0003-despliegue-docker-compose-tres-contenedores.md)
- **Capabilities afectadas:** `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes`, `api`
- **Fuentes:** `readme.md` §2.1, §2.2, §2.4, §2.4.1, §2.5 y §6 (HB-01 a HB-04, criterios de revisión de la habilitación)

## Contexto

ADR-0003 decidió el despliegue en 3 contenedores, con la imagen `nginx:stable-alpine`. Esa etiqueta es un canal: cambia de versión, incluso de versión mayor, sin que cambie el repositorio. Contradice el criterio de revisión de la habilitación de la sección 6 ("imágenes y dependencias con versión fija", bloqueante).

Al implementar HB-04 se decidió fijar la versión de `nginx`, por 3 razones:

- **Estabilidad:** una nueva versión no cambia el comportamiento del proxy sin una revisión.
- **Recreabilidad:** el mismo commit levanta siempre la misma imagen.
- **Seguridad:** cada actualización de la imagen es un cambio visible y revisado.

Este ADR repite la decisión de ADR-0003 y solo cambia la imagen de `nginx`.

## Decisión

- Todo se empaqueta con **Docker Compose** en 3 contenedores:

  | Contenedor | Imagen | Responsabilidad | Puertos | Redes |
  |---|---|---|---|---|
  | `nginx` | `nginx:1.30.7-alpine` | Único punto de entrada: termina HTTPS, redirige 80 → 443, sirve `/static/` y aplica cabeceras de seguridad (HSTS, CSP, `X-Frame-Options: DENY`) | 80 y 443 publicados | `frontend` |
  | `web` | Imagen propia: Python 3.12, Django 5.2 y Gunicorn | App web, API REST y panel `/admin/` | 8000, solo interno | `frontend` y `backend` |
  | `db` | `postgres:17-alpine` | Persistencia, transacciones y bloqueo de filas | 5432, solo interno | `backend` |

- **La imagen de `nginx` se fija en una versión de parche** de la rama estable (1.30.7, la de `stable-alpine` el 2026-11-20). Se actualiza a mano, con un commit que cambia la etiqueta en `docker-compose.yml`, `readme.md` §2.4.1 y este ADR.
- **La app y la API viven en el mismo contenedor `web`:** las ejecuta el mismo proceso Django.
- **Certificados:** `mkcert` en la red local y Let's Encrypt en el VPS.
- **Orden de arranque:** `db` declara un *healthcheck* (`pg_isready`), `web` espera con `depends_on: condition: service_healthy` y `nginx` arranca después de `web`.
- **Despliegue manual por SSH**, suficiente para un solo mantenedor: `git pull`, `docker compose up -d --build`, `./scripts/migrate.sh` y `collectstatic`.
- **Respaldos:** un cron diario ejecuta `pg_dump` comprimido y cifrado (GPG), con retención de 14 días y copia a un disco externo. Una vez al mes se prueba la restauración.
- **Nginx entra en la semana 1** (HB-04), para probar el login y el panel por HTTPS desde el principio, con la CSP real.

## Alternativas consideradas

- **`nginx:stable-alpine`** (ADR-0003): recibe las correcciones sin intervención, pero la imagen puede cambiar entre 2 despliegues del mismo commit. Se descarta por el criterio de versión fija.
- **Fijar por *digest* (`nginx@sha256:...`):** es aún más reproducible, porque la etiqueta `1.30.7-alpine` se reconstruye cuando Alpine publica parches. Se descarta porque no se lee qué versión es, y la etiqueta de parche basta para el criterio de revisión.

## Consecuencias

**Positivas:**
- Las mismas que ADR-0003: el mismo despliegue en el servidor local y en el VPS (§2.4); PostgreSQL sin puertos expuestos y `nginx` sin ruta hacia la base (§2.5); la app y la API con la misma lógica y los mismos permisos (§2.4.1).
- La versión de `nginx` solo cambia con un commit revisado.

**Negativas:**
- Las mismas que ADR-0003: el servidor local es un punto único de falla, mitigado con respaldos diarios y una restauración documentada (§2.1), y sin acceso desde fuera del hogar mientras solo se despliegue en la red local (§2.1).
- Las correcciones de seguridad de `nginx` no llegan solas: hay que revisar las versiones estables y actualizar la etiqueta.
