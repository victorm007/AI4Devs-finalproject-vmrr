# Spec Delta

## ADDED Requirements

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
