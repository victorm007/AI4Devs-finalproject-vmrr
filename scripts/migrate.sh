#!/bin/sh
# Ejecuta las migraciones como app_owner, el dueño de las tablas (readme, sección 2.4).
# La aplicación (contenedor web) se conecta como app_user, que no puede crear tablas.
# Uso: ./scripts/migrate.sh                 (todas)
#      ./scripts/migrate.sh accounts 0001   (hasta una migración concreta)
set -eu
# Lee .env línea por línea y exporta cada CLAVE=valor tal cual, sin pasar por el shell:
# con ". ./.env", un valor con espacios y sin comillas (HOGAR_NOMBRE=Hogar Gerontológico Demo)
# se leería como una asignación seguida de un comando. Salta las líneas vacías y los
# comentarios. El .env debe estar en LF: con CRLF, cada valor arrastra un \r (TK-01).
while IFS= read -r linea || [ -n "$linea" ]; do
    case $linea in ''|'#'*) ;; *) export "$linea" ;; esac
done < .env
docker compose run --rm -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" \
    web python manage.py migrate "$@"
