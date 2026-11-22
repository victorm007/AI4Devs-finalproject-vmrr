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
- **AND** la conexión `default` usa PostgreSQL (desde HB-03; antes, el backend `dummy`)

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

### Requirement: Conexión a PostgreSQL desde el entorno

Django DEBE (MUST) conectarse a PostgreSQL 17 con `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`. La aplicación DEBE (MUST) conectarse como `app_user`, y los tests como `app_owner`.

#### Scenario: La base es PostgreSQL 17 (HB-03, descripción técnica)

- **GIVEN** la conexión de los tests
- **WHEN** se consulta su motor y su versión
- **THEN** el motor es `postgresql` y la versión es 17 o mayor

#### Scenario: La aplicación corre como app_user (HB-03, criterio 2)

- **GIVEN** el servicio `web` corriendo
- **WHEN** Django ejecuta `SELECT current_user`
- **THEN** el resultado es `app_user`

#### Scenario: Los tests corren como app_owner (HB-03, descripción técnica)

- **GIVEN** la conexión de los tests
- **WHEN** se ejecuta `SELECT current_user`
- **THEN** el resultado es `app_owner`

#### Scenario: Los tests pueden actuar como app_user (HB-03, descripción técnica)

- **GIVEN** la conexión de los tests
- **WHEN** se ejecuta `SELECT current_user` con `SET LOCAL ROLE app_user`
- **THEN** el resultado es `app_user`

#### Scenario: app_user sin atributos especiales (HB-03, descripción técnica)

- **GIVEN** el rol `app_user`
- **WHEN** se consultan sus atributos
- **THEN** no es superusuario, no crea bases y no crea roles

### Requirement: Migraciones como app_owner

Las migraciones DEBEN (MUST) ejecutarse con `scripts/migrate.sh`, como `app_owner`. Con migraciones pendientes, `migrate` como `app_user` DEBE (MUST) fallar por falta de permisos.

#### Scenario: Instalación desde cero (HB-03, criterio 1)

- **GIVEN** una base nueva
- **WHEN** se ejecuta `./scripts/migrate.sh`
- **THEN** se aplican `accounts.0001_initial` y `accounts.0002_privilegios` sin errores

#### Scenario: migrate como app_user (HB-03, criterio 2)

- **GIVEN** una base nueva
- **WHEN** se ejecuta `python manage.py migrate` en `web`, como `app_user`
- **THEN** falla con `permission denied for schema public`

### Requirement: Privilegios de app_user sobre las tablas

Todas las tablas DEBEN (MUST) pertenecer a `app_owner`. `app_user` DEBE (MUST) tener `SELECT`, `INSERT`, `UPDATE` y `DELETE` sobre todas, también las que creen migraciones futuras, y NO DEBE (MUST NOT) poder crear tablas.

#### Scenario: Dueño de todas las tablas (HB-03, criterio 3)

- **GIVEN** la base migrada
- **WHEN** se buscan tablas de `public` cuyo dueño no sea `app_owner`
- **THEN** no hay ninguna

#### Scenario: Los 4 permisos de app_user (HB-03, criterio 3)

- **GIVEN** la base migrada
- **WHEN** se revisan los permisos de `app_user` en cada tabla de `public`
- **THEN** tiene `SELECT`, `INSERT`, `UPDATE` y `DELETE` en todas

#### Scenario: app_user no crea tablas (HB-03, criterio 3)

- **GIVEN** una sesión que actúa como `app_user`
- **WHEN** ejecuta `CREATE TABLE`
- **THEN** PostgreSQL responde `permission denied for schema public`

#### Scenario: Las tablas nuevas heredan los permisos (HB-03, criterio 4)

- **GIVEN** la base con `accounts.0002_privilegios` aplicada
- **WHEN** `app_owner` crea una tabla nueva
- **THEN** `app_user` tiene `INSERT` sobre ella

#### Scenario: La migración de privilegios se revierte (HB-03, criterio 6)

- **GIVEN** la base migrada
- **WHEN** se ejecuta `./scripts/migrate.sh accounts 0001`
- **THEN** `app_user` recibe `permission denied for table usuario` al leer `usuario`
- **AND** `./scripts/migrate.sh` vuelve a darle acceso

### Requirement: Contraseñas fuera del código

El código NO DEBE (MUST NOT) contener contraseñas: solo las lee del entorno.

#### Scenario: Ninguna contraseña en la configuración (HB-03, definición de hecho)

- **GIVEN** el código de `app/config`
- **WHEN** se buscan las menciones de `password`
- **THEN** cada una lee su valor con `os.environ`

### Requirement: Pruebas en el CI

El *job* `tests` del CI DEBE (MUST) correr desde este ticket contra PostgreSQL 17 y exigir cobertura de al menos 80 % en `apps/`.

#### Scenario: Suite local igual que el CI (HB-03, criterio 7)

- **GIVEN** la base de pruebas de PostgreSQL
- **WHEN** se ejecuta `pytest -m "not e2e and not lento" --cov=apps --cov-fail-under=80` como `app_owner`
- **THEN** todos los tests pasan y la cobertura alcanza el 80 %

#### Scenario: Job tests en el pull request (HB-03, criterio 7)

- **GIVEN** el pull request que incluye este ticket
- **WHEN** termina el CI
- **THEN** el *job* `tests` corre y pasa

### Requirement: Proxy inverso como único punto de entrada

El servicio `nginx` (`nginx:1.30.7-alpine`, versión fija; red `frontend`) DEBE (MUST) ser el único contenedor que publica puertos (80 y 443), redirigir HTTP a HTTPS y reenviar a `web:8000` lo que no sea estático. NO DEBE (MUST NOT) tener ruta a `db`.

#### Scenario: Redirección de HTTP a HTTPS (HB-04, criterio 1)

- **GIVEN** el servicio `nginx` corriendo
- **WHEN** se pide `http://localhost/`
- **THEN** la respuesta es `301` con `Location: https://localhost/`

#### Scenario: Solo nginx publica puertos (HB-04, criterio 4)

- **GIVEN** los servicios `db`, `web` y `nginx` corriendo
- **WHEN** se listan sus puertos con `docker compose ps`
- **THEN** `nginx` publica 80 y 443
- **AND** `web` y `db` no publican ninguno

#### Scenario: nginx no alcanza a db (HB-04, criterio 4)

- **GIVEN** el servicio `nginx` corriendo
- **WHEN** intenta abrir una conexión a `db:5432`
- **THEN** no hay ruta a `db`

#### Scenario: Configuración válida (HB-04, definición de hecho)

- **GIVEN** `nginx/default.conf` montado en el contenedor
- **WHEN** se ejecuta `nginx -t`
- **THEN** la sintaxis es correcta y la prueba termina con éxito

### Requirement: HTTPS con certificado local de confianza

`nginx` DEBE (MUST) terminar TLS 1.2 o superior con el certificado de `mkcert`. Los certificados NO DEBEN (MUST NOT) versionarse.

#### Scenario: Certificado de confianza en desarrollo (HB-04, criterio 2)

- **GIVEN** la CA de `mkcert` instalada en el equipo de desarrollo
- **WHEN** se pide `https://localhost/admin/login/` validando el certificado
- **THEN** la respuesta es `200` sin error de certificado

#### Scenario: Certificados fuera del repositorio (HB-04, definición de hecho)

- **GIVEN** los certificados en `nginx/certs/`
- **WHEN** se ejecuta `git status`
- **THEN** no aparece ningún archivo `*.pem`
- **AND** solo se versiona `nginx/certs/.gitkeep`

### Requirement: Cabeceras de seguridad

Toda respuesta HTTPS DEBE (MUST) llevar `Strict-Transport-Security`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` y `Content-Security-Policy`, también en las respuestas de error. Cada una DEBE (MUST) llegar una sola vez.

#### Scenario: Las 5 cabeceras en el panel (HB-04, criterio 2)

- **GIVEN** el servicio `nginx` corriendo
- **WHEN** se pide `https://localhost/admin/login/`
- **THEN** la respuesta es `200`
- **AND** incluye `Strict-Transport-Security`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` y `Content-Security-Policy`

#### Scenario: Una sola cabecera CSP (HB-04, criterio 7)

- **GIVEN** que Django y nginx envían la política CSP
- **WHEN** se pide `https://localhost/admin/login/`
- **THEN** la respuesta trae exactamente una cabecera `Content-Security-Policy`

#### Scenario: Cabeceras también en errores (HB-04, guía, criterios de calidad)

- **GIVEN** el servicio `nginx` corriendo
- **WHEN** se pide una ruta que no existe por HTTPS
- **THEN** la respuesta `404` incluye `Strict-Transport-Security` y `Content-Security-Policy`
- **AND** la cabecera `Server` dice `nginx`, sin versión

### Requirement: Estáticos servidos por nginx

`nginx` DEBE (MUST) servir `/static/` desde el volumen `static`, sin pasar por Django.

#### Scenario: CSS del panel servido por nginx (HB-04, criterio 3)

- **GIVEN** `collectstatic` ejecutado en `web`
- **WHEN** se pide `https://localhost/static/admin/css/base.css`
- **THEN** la respuesta es `200` y trae la cabecera `Expires` que agrega nginx

### Requirement: Django detrás del proxy

Django DEBE (MUST) reconocer HTTPS por `X-Forwarded-Proto`, enviar sus *cookies* solo por HTTPS y aceptar formularios solo desde los orígenes de `CSRF_TRUSTED_ORIGINS`, que se leen del entorno.

#### Scenario: HTTPS por la cabecera de nginx (HB-04, criterio 6)

- **GIVEN** una petición con `X-Forwarded-Proto: https`
- **WHEN** Django evalúa si es segura
- **THEN** la considera HTTPS

#### Scenario: Sin la cabecera no es HTTPS (HB-04, criterio 6)

- **GIVEN** una petición sin `X-Forwarded-Proto`
- **WHEN** Django evalúa si es segura
- **THEN** no la considera HTTPS

#### Scenario: Cookies solo por HTTPS (HB-04, descripción técnica)

- **GIVEN** la configuración de Django
- **WHEN** se consultan las *cookies* de sesión y de CSRF
- **THEN** ambas están marcadas `Secure`

#### Scenario: Formulario desde el origen de nginx (HB-04, criterio 5)

- **GIVEN** el formulario de `/admin/login/` pedido por HTTPS
- **WHEN** se envía con `Origin: https://localhost` y un token CSRF válido
- **THEN** Django no responde `403`

#### Scenario: Formulario desde otro origen (HB-04, criterio 6)

- **GIVEN** el formulario de `/admin/login/` pedido por HTTPS
- **WHEN** se envía con `Origin: https://sitio-malicioso.example`
- **THEN** Django responde `403`

#### Scenario: El Administrador entra al panel por HTTPS (HB-04, criterio 5)

- **GIVEN** el Administrador creado con `createsuperuser` y la CA de `mkcert` instalada
- **WHEN** entra a `https://localhost/admin/` desde el navegador
- **THEN** inicia sesión sin error de CSRF
- **AND** la consola del navegador no muestra violaciones de CSP

### Requirement: Política CSP compartida por Django y nginx

Django DEBE (MUST) enviar en sus respuestas la misma política CSP que nginx, para que las pruebas que no pasan por nginx la apliquen.

#### Scenario: Django envía la política CSP (HB-04, criterio 7)

- **GIVEN** la configuración de Django
- **WHEN** se pide `/admin/login/` sin pasar por nginx
- **THEN** la respuesta trae `Content-Security-Policy` con el valor de `CONTENT_SECURITY_POLICY`

#### Scenario: La misma política en Django y en nginx (HB-04, criterio 7)

- **GIVEN** `nginx/default.conf` y la configuración de Django
- **WHEN** se compara la política de `add_header Content-Security-Policy` con `CONTENT_SECURITY_POLICY`
- **THEN** son idénticas

### Requirement: Producción detrás de nginx

La configuración `config.settings.prod` NO DEBE (MUST NOT) repetir la redirección a HTTPS ni HSTS, que hace nginx, y DEBE (MUST) pasar `check --deploy` sin advertencias de seguridad.

#### Scenario: check --deploy en producción (HB-04, descripción técnica)

- **GIVEN** la configuración `config.settings.prod` con una `SECRET_KEY` larga y `HOGAR_NOMBRE` definida
- **WHEN** se ejecuta `python manage.py check --deploy`
- **THEN** no hay advertencias
- **AND** `security.W004` y `security.W008` aparecen silenciados

### Requirement: Nombre del Hogar obligatorio en producción

La configuración `config.settings.prod` NO DEBE (MUST NOT) cargarse si `HOGAR_NOMBRE` falta o está vacía, para que el servidor del hogar nunca cree un Hogar con un nombre que no eligió. `docker-compose.yml` DEBE (MUST) pasar a `web` el valor de `.env` sin agregar uno por defecto. En desarrollo, en el CI y en los tests, sin la variable, el Hogar DEBE (MUST) seguir llamándose "Hogar Gerontológico Demo".

#### Scenario: Producción sin HOGAR_NOMBRE (revisión de HB-06, sugerencia 4)

- **GIVEN** un proceso de Django con `config.settings.prod` y sin `HOGAR_NOMBRE`, o con la variable vacía
- **WHEN** se carga la configuración
- **THEN** falla con un error de configuración que pide definir `HOGAR_NOMBRE` en `.env`

#### Scenario: Producción con HOGAR_NOMBRE (revisión de HB-06, sugerencia 4)

- **GIVEN** un proceso de Django con `config.settings.prod` y `HOGAR_NOMBRE` definida
- **WHEN** se carga la configuración
- **THEN** el nombre del Hogar es el de la variable

#### Scenario: Desarrollo sin HOGAR_NOMBRE (revisión de HB-06, sugerencia 4)

- **GIVEN** un proceso de Django con `config.settings.local` y `HOGAR_NOMBRE` vacía o ausente
- **WHEN** se carga la configuración
- **THEN** el nombre del Hogar es "Hogar Gerontológico Demo"

#### Scenario: Compose no inventa el nombre del Hogar (revisión de HB-06, sugerencia 4)

- **GIVEN** un `.env` sin `HOGAR_NOMBRE`
- **WHEN** se ejecuta `docker compose config`
- **THEN** `HOGAR_NOMBRE` del servicio `web` está vacía, no "Hogar Gerontológico Demo"
