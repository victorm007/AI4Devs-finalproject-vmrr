# infraestructura Specification

## Purpose

Define los contenedores, la red, la configuración por entorno y los roles de base de datos sobre los que corre la aplicación, en cualquier entorno.

## Requirements

### Requirement: Servicio de base de datos disponible

El servicio `db` DEBE (MUST) correr PostgreSQL 17 con la imagen `postgres:17-alpine`, en la red `backend`, y reportarse sano solo cuando ya acepta conexiones por TCP.

#### Scenario: Arranque sano en menos de 30 segundos (HB-01, criterio 1)

- **GIVEN** un archivo `.env` con las variables requeridas
- **WHEN** se ejecuta `docker compose up -d db`
- **THEN** el servicio `db` queda en estado `healthy` en menos de 30 segundos

#### Scenario: Sano significa que ya responde por TCP (readme 2.4.1, orden de arranque)

- **GIVEN** un volumen `pgdata` nuevo
- **WHEN** el servicio `db` se reporta `healthy`
- **THEN** `app_user` se conecta por TCP de inmediato

#### Scenario: Definición del servicio (HB-01, descripción técnica)

- **GIVEN** el servicio `db` en ejecución
- **WHEN** se inspecciona el contenedor
- **THEN** usa la imagen `postgres:17-alpine`
- **AND** guarda sus datos en el volumen `pgdata`
- **AND** está conectado a la red `backend`
- **AND** monta `db/init/` en `/docker-entrypoint-initdb.d/` en solo lectura

### Requirement: Usuarios de base de datos

Al crear el volumen `pgdata`, el servicio `db` DEBE (MUST) crear los usuarios `app_owner` y `app_user`. `app_owner` DEBE (MUST) tener `CREATEDB` solo si `DB_OWNER_CREATEDB=true`.

#### Scenario: Usuarios en desarrollo (HB-01, criterio 2)

- **GIVEN** un volumen nuevo y `DB_OWNER_CREATEDB=true`
- **WHEN** se consultan los usuarios con `\du`
- **THEN** `app_owner` aparece con `Create DB`
- **AND** `app_user` aparece sin atributos

#### Scenario: Sin CREATEDB fuera de desarrollo (HB-01, descripción técnica)

- **GIVEN** un volumen nuevo y `DB_OWNER_CREATEDB=false`
- **WHEN** se consultan los atributos de `app_owner`
- **THEN** `app_owner` no tiene `CREATEDB`

### Requirement: Dueño de la base y del esquema

`app_owner` DEBE (MUST) ser dueño de la base `hogar` y del esquema `public`.

#### Scenario: Dueños de la base y del esquema (HB-01, criterio 3)

- **GIVEN** el servicio `db` recién inicializado
- **WHEN** se consultan los dueños de la base `hogar` y del esquema `public`
- **THEN** el dueño de los 2 es `app_owner`

### Requirement: Autenticación de la aplicación por contraseña

`app_user` DEBE (MUST) autenticarse por TCP con la contraseña definida en `.env`, y una contraseña distinta DEBE (MUST) ser rechazada.

#### Scenario: Contraseña correcta por TCP (HB-01, criterio 4)

- **GIVEN** el servicio `db` sano
- **WHEN** `app_user` se conecta por TCP desde una dirección que no es de loopback, con la contraseña de `.env`
- **THEN** `SELECT current_user` devuelve `app_user`

#### Scenario: Contraseña incorrecta por TCP (HB-01, criterio 4)

- **GIVEN** el servicio `db` sano
- **WHEN** `app_user` se conecta por TCP desde una dirección que no es de loopback, con otra contraseña
- **THEN** la conexión se rechaza con `password authentication failed`

### Requirement: La aplicación no crea tablas

`app_user` NO DEBE (MUST NOT) poder crear tablas en el esquema `public`.

#### Scenario: Creación de tabla rechazada (HB-01, criterio 4)

- **GIVEN** una sesión conectada como `app_user`
- **WHEN** ejecuta `CREATE TABLE prueba (id int)`
- **THEN** PostgreSQL responde `permission denied for schema public`

### Requirement: Inicialización idempotente

El script `01_roles.sh` DEBE (MUST) poder ejecutarse de nuevo sobre una base ya inicializada sin dar error.

#### Scenario: Segunda ejecución del script (HB-01, criterio 5)

- **GIVEN** una base donde `01_roles.sh` ya se ejecutó
- **WHEN** se ejecuta `01_roles.sh` por segunda vez
- **THEN** termina sin error

### Requirement: PostgreSQL sin puertos publicados

El servicio `db` NO DEBE (MUST NOT) publicar ningún puerto al host.

#### Scenario: Puerto 5432 sin publicar (HB-01, criterio 6)

- **GIVEN** el servicio `db` en ejecución
- **WHEN** se ejecuta `docker compose port db 5432`
- **THEN** no se muestra ningún puerto publicado

### Requirement: Persistencia de los datos

Los datos DEBEN (MUST) conservarse cuando el servicio `db` se reinicia.

#### Scenario: Datos después de un reinicio (HB-01, criterio 6)

- **GIVEN** una tabla creada por `app_owner`
- **WHEN** se ejecuta `docker compose restart db`
- **AND** el servicio vuelve a estar `healthy`
- **THEN** la tabla sigue existiendo

### Requirement: Contraseñas obligatorias

Docker Compose DEBE (MUST) detenerse con un mensaje claro si falta una contraseña, en lugar de arrancar con una contraseña vacía.

#### Scenario: Falta una contraseña (HB-01, descripción técnica)

- **GIVEN** una configuración sin `POSTGRES_PASSWORD`, sin `DB_OWNER_PASSWORD` o sin `DB_APP_PASSWORD`
- **WHEN** se ejecuta `docker compose config`
- **THEN** el comando falla
- **AND** el mensaje nombra la variable que falta

### Requirement: Secretos fuera del repositorio

El archivo `.env` NO DEBE (MUST NOT) versionarse, y `.env.example` DEBE (MUST) contener solo valores de ejemplo.

#### Scenario: Archivos de entorno (HB-01, definición de hecho)

- **GIVEN** el repositorio con los archivos del ticket
- **WHEN** se revisan `.env` y `.env.example`
- **THEN** Git ignora `.env`
- **AND** las 3 contraseñas de `.env.example` son valores de ejemplo `cambia-esto`

### Requirement: Script de inicio ejecutable en Linux

`db/init/01_roles.sh` DEBE (MUST) versionarse con fin de línea LF y permiso de ejecución.

#### Scenario: Fin de línea LF (HB-01, definición de hecho)

- **GIVEN** el archivo `db/init/01_roles.sh`
- **WHEN** se revisa su contenido y `.gitattributes`
- **THEN** el archivo no contiene CRLF
- **AND** `.gitattributes` fuerza LF en los `.sh`

#### Scenario: Permiso de ejecución en Git (HB-01, definición de hecho)

- **GIVEN** `db/init/01_roles.sh` agregado al índice de Git
- **WHEN** se ejecuta `git ls-files -s db/init/01_roles.sh`
- **THEN** el modo del archivo es `100755`
