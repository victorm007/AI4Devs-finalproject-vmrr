# Spec Delta

## ADDED Requirements

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

- **GIVEN** la configuración `config.settings.prod` con una `SECRET_KEY` larga
- **WHEN** se ejecuta `python manage.py check --deploy`
- **THEN** no hay advertencias
- **AND** `security.W004` y `security.W008` aparecen silenciados
