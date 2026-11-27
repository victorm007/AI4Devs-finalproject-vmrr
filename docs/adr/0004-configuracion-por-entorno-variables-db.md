# ADR-0004 · Configuración por entorno y conexión con variables `DB_*`

- **Estado:** Aceptado. Supersedido en parte por [ADR-0026](0026-despliegue-servidor-del-hogar-y-demo-local.md): en la operación, el superusuario también crea la base de ensayo, recrea la de la aplicación en una vuelta atrás y repone sus permisos
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes`, `api`
- **Fuentes:** `readme.md` §2.3, §2.4, §2.5 y §6 (decisiones de diseño de la habilitación, HB-02, HB-03 y criterios de revisión de infraestructura)

## Contexto

El mismo código corre en desarrollo, en CI, en el servidor del hogar y en el VPS. Los secretos no pueden quedar en el repositorio ni en la imagen. Además, los tests y `scripts/migrate.sh` necesitan conectarse con otro usuario de base de datos (`app_owner`) que la aplicación (`app_user`), ver [ADR-0006](0006-dos-usuarios-de-base-de-datos.md).

## Decisión

- La configuración de Django está **separada por entorno** (`config/settings/base.py`, `local.py` y `prod.py`) y se controla con **variables de entorno**, siguiendo la metodología *12-factor*.
- `SECRET_KEY` y las credenciales de la base de datos viven en `.env`, que no se versiona; el repositorio solo tiene `.env.example`. En producción, `DEBUG=False` y `ALLOWED_HOSTS` restringido.
- La conexión a PostgreSQL usa **variables separadas**: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`. Son las mismas variables del CI.
- Hay 3 contraseñas de PostgreSQL: `POSTGRES_PASSWORD` (superusuario, solo para la inicialización), `DB_OWNER_PASSWORD` (`app_owner`) y `DB_APP_PASSWORD` (`app_user`).
- El contenedor `web` recibe solo sus variables. No ve las contraseñas de PostgreSQL que no usa.

## Alternativas consideradas

- **Una sola variable `DATABASE_URL`:** se descartó. Con variables separadas, los tests y `migrate.sh` cambian solo el usuario y la contraseña para conectarse como `app_owner`, y las contraseñas con caracteres especiales no necesitan codificarse para una URL (§6).

## Consecuencias

**Positivas:**
- No hay cambios de código entre entornos; migrar al VPS solo cambia variables de entorno (§2.4).
- Cambiar de usuario de base de datos es cambiar 2 variables.

**Negativas:**
- Hay que mantener `.env.example` al día con cada variable nueva. Los tickets HB-01 a HB-04 lo crean, y HB-06 agrega `HOGAR_NOMBRE` (§6).
