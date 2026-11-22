# Spec Delta

## MODIFIED Requirements

### Requirement: Nombre del Hogar obligatorio en producción

`config.settings.prod` NO DEBE (MUST NOT) cargarse si `HOGAR_NOMBRE` falta o está vacía, y ninguna configuración NO DEBE (MUST NOT) cargarse con más de 150 caracteres, el largo de `entidad.nombre`. `docker-compose.yml` DEBE (MUST) pasar el valor de `.env` sin agregar uno por defecto. En desarrollo, en el CI y en los tests, sin la variable, el Hogar DEBE (MUST) llamarse "Hogar Gerontológico Demo".

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

#### Scenario: HOGAR_NOMBRE demasiado largo (segunda revisión de HB-06, nit 6)

- **GIVEN** un proceso de Django con `config.settings.local` o `config.settings.prod` y un `HOGAR_NOMBRE` de 151 caracteres
- **WHEN** se carga la configuración
- **THEN** falla con un error de configuración que menciona `HOGAR_NOMBRE` y el máximo de 150 caracteres

#### Scenario: HOGAR_NOMBRE de 150 caracteres (segunda revisión de HB-06, nit 6)

- **GIVEN** un proceso de Django con `config.settings.prod` y un `HOGAR_NOMBRE` de exactamente 150 caracteres
- **WHEN** se carga la configuración
- **THEN** el nombre del Hogar es el de la variable
