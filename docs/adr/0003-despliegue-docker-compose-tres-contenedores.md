# ADR-0003 · Despliegue con Docker Compose: `nginx`, `web` y `db`

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes`, `api`
- **Fuentes:** `readme.md` §2.1, §2.2, §2.4, §2.4.1, §2.5 y §6 (HB-01 a HB-04, decisiones de diseño de la habilitación)

## Contexto

Hoy la producción corre en un servidor Ubuntu dentro de la red del hogar. En el futuro correrá en un VPS (HostGator), que también sirve como entorno de demo con datos ficticios. El mismo despliegue debe funcionar en los dos lugares sin cambiar código, y lo opera una sola persona.

## Decisión

- Todo se empaqueta con **Docker Compose** en 3 contenedores:

  | Contenedor | Imagen | Responsabilidad | Puertos | Redes |
  |---|---|---|---|---|
  | `nginx` | `nginx:stable-alpine` | Único punto de entrada: termina HTTPS, redirige 80 → 443, sirve `/static/` y aplica cabeceras de seguridad (HSTS, CSP, `X-Frame-Options: DENY`) | 80 y 443 publicados | `frontend` |
  | `web` | Imagen propia: Python 3.12, Django 5.2 y Gunicorn | App web, API REST y panel `/admin/` | 8000, solo interno | `frontend` y `backend` |
  | `db` | `postgres:17-alpine` | Persistencia, transacciones y bloqueo de filas | 5432, solo interno | `backend` |

- **La app y la API viven en el mismo contenedor `web`:** las ejecuta el mismo proceso Django.
- **Certificados:** `mkcert` en la red local y Let's Encrypt en el VPS.
- **Orden de arranque:** `db` declara un *healthcheck* (`pg_isready`), `web` espera con `depends_on: condition: service_healthy` y `nginx` arranca después de `web`.
- **Despliegue manual por SSH**, suficiente para un solo mantenedor: `git pull`, `docker compose up -d --build`, `./scripts/migrate.sh` y `collectstatic`.
- **Respaldos:** un cron diario ejecuta `pg_dump` comprimido y cifrado (GPG), con retención de 14 días y copia a un disco externo. Una vez al mes se prueba la restauración.
- **Nginx entra en la semana 1** (HB-04), para probar el login y el panel por HTTPS desde el principio, con la CSP real.

## Alternativas consideradas

El diseño no documenta alternativas a Docker Compose.

## Consecuencias

**Positivas:**
- El mismo despliegue corre en el servidor local y en el VPS. Migrar al VPS solo cambia variables de entorno (§2.4).
- PostgreSQL no expone puertos: solo `web` llega a `db`, y `nginx` no tiene ruta hacia la base (§2.5).
- Al tener la app y la API en el mismo contenedor, aplican la misma lógica y los mismos permisos, con un contenedor menos que operar (§2.4.1).

**Negativas:**
- El servidor local es un punto único de falla. Se mitiga con respaldos diarios y un procedimiento de restauración documentado (§2.1).
- Mientras solo se despliegue en la red local, no hay acceso desde fuera del hogar (§2.1).
