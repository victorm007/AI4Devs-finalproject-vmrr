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

### Requirement: Servicio web disponible

El servicio `web` DEBE (MUST) arrancar después de que `db` esté sana y atender peticiones con Gunicorn en el puerto 8000.

#### Scenario: Arranque de los servicios (HB-02, criterio 1)

- **GIVEN** un archivo `.env` con las variables requeridas
- **WHEN** se ejecuta `docker compose up -d`
- **THEN** `db` queda `healthy`
- **AND** `web` queda corriendo sin reinicios

#### Scenario: Configuración de Django válida (HB-02, criterio 1)

- **GIVEN** el servicio `web` corriendo
- **WHEN** se ejecuta `python manage.py check` en `web`
- **THEN** la salida es `System check identified no issues (0 silenced).`

#### Scenario: Gunicorn atiende peticiones (HB-02, criterio 2)

- **GIVEN** el servicio `web` corriendo
- **WHEN** se hace una petición a `http://localhost:8000/` desde el contenedor
- **THEN** la respuesta es `404`
- **AND** la cabecera `Server` indica `gunicorn`

#### Scenario: Definición del servicio web (HB-02, descripción técnica)

- **GIVEN** el servicio `web` corriendo
- **WHEN** se inspecciona su configuración
- **THEN** está en las redes `frontend` y `backend`
- **AND** monta `./app` en `/app` y el volumen `static` en `/app/staticfiles`
- **AND** espera a que `db` esté `healthy`

### Requirement: Proceso web sin privilegios

El proceso del servicio `web` DEBE (MUST) correr con el usuario sin privilegios `django`.

#### Scenario: Usuario del proceso (HB-02, criterio 3)

- **GIVEN** el servicio `web` corriendo
- **WHEN** se ejecuta `whoami` en `web` y se revisa el usuario del proceso principal
- **THEN** `whoami` responde `django`
- **AND** el proceso principal no corre como `root`

### Requirement: Servicio web sin puertos publicados

El servicio `web` NO DEBE (MUST NOT) publicar ningún puerto al host.

#### Scenario: Puerto 8000 sin publicar (HB-02, criterio 3)

- **GIVEN** el servicio `web` corriendo
- **WHEN** se ejecuta `docker compose port web 8000`
- **THEN** no se muestra ningún puerto publicado

### Requirement: Acceso de web a la base de datos

El servicio `web` DEBE (MUST) alcanzar `db` por la red `backend` y NO DEBE (MUST NOT) recibir las contraseñas de PostgreSQL.

#### Scenario: web alcanza db (HB-02, criterio 4)

- **GIVEN** los servicios `web` y `db` corriendo
- **WHEN** `web` abre una conexión a `db:5432`
- **THEN** la conexión se establece

#### Scenario: web no recibe contraseñas de PostgreSQL (HB-02, criterio 4)

- **GIVEN** el servicio `web` corriendo
- **WHEN** se revisan los nombres de sus variables de entorno
- **THEN** no existen `POSTGRES_PASSWORD`, `DB_OWNER_PASSWORD` ni `DB_APP_PASSWORD`

### Requirement: Clave secreta obligatoria

La aplicación NO DEBE (MUST NOT) arrancar sin `SECRET_KEY`.

#### Scenario: Compose sin SECRET_KEY (HB-02, criterio 5)

- **GIVEN** una configuración sin `SECRET_KEY`
- **WHEN** se ejecuta `docker compose config`
- **THEN** el comando falla con el mensaje `Falta SECRET_KEY en .env`

#### Scenario: Django sin SECRET_KEY (HB-02, descripción técnica)

- **GIVEN** un proceso de Django sin la variable `SECRET_KEY`
- **WHEN** se ejecuta `python manage.py check`
- **THEN** el comando falla con `KeyError: 'SECRET_KEY'`

### Requirement: Configuración de Django por entorno

La configuración de Django DEBE (MUST) separarse en `base`, `local` y `prod`, y tomar del entorno los valores que cambian entre entornos.

#### Scenario: Valores comunes (HB-02, descripción técnica)

- **GIVEN** la configuración activa de Django
- **WHEN** se consultan sus valores
- **THEN** `LANGUAGE_CODE` es `es-mx`, `TIME_ZONE` es `America/Mexico_City` y `USE_TZ` es verdadero
- **AND** la conexión `default` usa el backend `dummy`

#### Scenario: DEBUG y ALLOWED_HOSTS desde el entorno (HB-02, descripción técnica)

- **GIVEN** las variables `DEBUG=True` y `ALLOWED_HOSTS=a.example,b.example`
- **WHEN** se carga la configuración `config.settings.local`
- **THEN** `DEBUG` es verdadero
- **AND** `ALLOWED_HOSTS` contiene `a.example` y `b.example`

#### Scenario: Producción sin DEBUG (readme 2.5)

- **GIVEN** la variable `DEBUG=True`
- **WHEN** se carga la configuración `config.settings.prod`
- **THEN** `DEBUG` es falso

### Requirement: Imagen de producción

La imagen construida con `INSTALAR_DEV=false` NO DEBE (MUST NOT) contener las herramientas de desarrollo, y un cambio de código NO DEBE (MUST NOT) reinstalar las dependencias.

#### Scenario: Imagen sin herramientas de desarrollo (HB-02, criterio 6)

- **GIVEN** la imagen construida con `INSTALAR_DEV=false`
- **WHEN** se buscan `pytest`, `ruff` y `djlint` en la imagen
- **THEN** ninguno está instalado
- **AND** la imagen corre con el usuario `django`

#### Scenario: Cambiar código no reinstala dependencias (HB-02, descripción técnica)

- **GIVEN** una imagen ya construida
- **WHEN** se reconstruye después de cambiar el contenido de un archivo `.py`
- **THEN** el paso que instala las dependencias sale de la caché
- **AND** el paso que copia el código se vuelve a ejecutar

### Requirement: Dependencias con versión fija

Todas las dependencias DEBEN (MUST) fijarse con `==`, con Django en la serie 5.2 y djLint en 1.50.4.

#### Scenario: Versiones fijas (HB-02, descripción técnica)

- **GIVEN** los archivos `requirements.txt` y `requirements-dev.txt`
- **WHEN** se revisan sus dependencias
- **THEN** cada una usa `==`
- **AND** Django pertenece a la serie 5.2 y djLint es 1.50.4

### Requirement: Calidad estática del proyecto

El código DEBE (MUST) pasar ruff, y djLint DEBE (MUST) leer su configuración de `pyproject.toml`.

#### Scenario: ruff sin errores (HB-02, definición de hecho)

- **GIVEN** el código de `app/`
- **WHEN** se ejecutan `ruff check .` y `ruff format --check .` en `web`
- **THEN** ninguno reporta errores

#### Scenario: djLint lee su configuración (HB-02, criterio 8)

- **GIVEN** `app/` sin plantillas
- **WHEN** se ejecuta `djlint . --check` en `web`
- **THEN** responde `No files to check!`
- **AND** las reglas ignoradas en `[tool.djlint]` no se reportan

#### Scenario: El verificador omite djLint sin plantillas (HB-02, criterio 8)

- **GIVEN** `app/` sin plantillas y el servicio `web` corriendo
- **WHEN** se ejecuta `python scripts/verificar.py`
- **THEN** termina sin errores
- **AND** informa que omite djLint

### Requirement: Variables de entorno de la aplicación

`.env.example` DEBE (MUST) documentar las variables del servicio `web`, y el `.env` local DEBE (MUST) poder cargarse en el shell.

#### Scenario: Archivos de entorno del servicio web (HB-02, descripción técnica)

- **GIVEN** los archivos `.env.example` y `.env`
- **WHEN** se revisan sus variables
- **THEN** `.env.example` define `SECRET_KEY` con un valor de ejemplo, `DEBUG`, `ALLOWED_HOSTS`, `DJANGO_SETTINGS_MODULE`, `INSTALAR_DEV` y `GUNICORN_CMD_ARGS`
- **AND** `.env` se carga con `. ./.env` sin errores

### Requirement: Activación de los jobs del CI

El CI DEBE (MUST) correr `lint` y `build de la imagen` desde este ticket, y mantener saltados `tests` y `e2e` hasta que exista lo que necesitan.

#### Scenario: Condiciones de activación (HB-02, criterio 7)

- **GIVEN** el repositorio con los archivos del ticket
- **WHEN** se revisan las rutas que activan cada *job*
- **THEN** existe `app/manage.py`
- **AND** no existen `app/conftest.py` ni `app/e2e/`

#### Scenario: Resultado en el pull request (HB-02, criterio 7)

- **GIVEN** el pull request que incluye este ticket
- **WHEN** termina el CI
- **THEN** `lint` y `build de la imagen` están en verde
- **AND** `tests` y `e2e` aparecen saltados
