# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
