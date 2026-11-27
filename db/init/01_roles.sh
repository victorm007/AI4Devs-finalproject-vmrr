#!/bin/sh
# Crea los usuarios de la aplicación (readme, sección 6, HB-01).
# PostgreSQL ejecuta este script solo al crear el volumen pgdata por primera vez.
# El CI lo ejecuta antes de los tests, igual que en desarrollo.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v owner_pw="$DB_OWNER_PASSWORD" -v app_pw="$DB_APP_PASSWORD" \
     -v createdb="${DB_OWNER_CREATEDB:-false}" <<'SQL'
-- Idempotente: solo crea los usuarios si no existen
SELECT format('CREATE ROLE app_owner LOGIN PASSWORD %L', :'owner_pw')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_owner') \gexec
SELECT format('CREATE ROLE app_user LOGIN PASSWORD %L', :'app_pw')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') \gexec
SELECT 'ALTER ROLE app_owner CREATEDB' WHERE :'createdb' = 'true' \gexec

-- Los tests pueden actuar como app_user (SET ROLE); app_user no gana nada del dueño
GRANT app_user TO app_owner;

-- app_owner es dueño de la base y del esquema; app_user solo se conecta y lo usa
SELECT format('ALTER DATABASE %I OWNER TO app_owner', current_database()) \gexec
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database()) \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO app_user', current_database()) \gexec
ALTER SCHEMA public OWNER TO app_owner;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO app_user;
SQL
