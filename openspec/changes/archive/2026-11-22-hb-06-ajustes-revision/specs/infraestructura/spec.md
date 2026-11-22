# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Producción detrás de nginx

La configuración `config.settings.prod` NO DEBE (MUST NOT) repetir la redirección a HTTPS ni HSTS, que hace nginx, y DEBE (MUST) pasar `check --deploy` sin advertencias de seguridad.

#### Scenario: check --deploy en producción (HB-04, descripción técnica)

- **GIVEN** la configuración `config.settings.prod` con una `SECRET_KEY` larga y `HOGAR_NOMBRE` definida
- **WHEN** se ejecuta `python manage.py check --deploy`
- **THEN** no hay advertencias
- **AND** `security.W004` y `security.W008` aparecen silenciados
