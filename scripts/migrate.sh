#!/bin/sh
# Ejecuta las migraciones como app_owner, el dueño de las tablas (readme, sección 2.4).
# La aplicación (contenedor web) se conecta como app_user, que no puede crear tablas.
# Uso: ./scripts/migrate.sh                 (todas)
#      ./scripts/migrate.sh accounts 0001   (hasta una migración concreta)
set -eu
set -a; . ./.env; set +a
docker compose run --rm -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" \
    web python manage.py migrate "$@"
