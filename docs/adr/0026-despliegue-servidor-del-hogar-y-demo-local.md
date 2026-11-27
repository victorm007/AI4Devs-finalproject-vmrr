# ADR-0026 · Despliegue solo en el servidor del hogar, con demo en una máquina local

- **Estado:** Aceptado
- **Fecha:** 2026-11-26
- **Supersede a:** [ADR-0025](0025-despliegue-docker-compose-nginx-version-fija.md), y en parte a:
  - [ADR-0022](0022-autenticacion-sesion-argon2-axes.md): quién hace la redirección a HTTPS y HSTS;
  - [ADR-0004](0004-configuracion-por-entorno-variables-db.md) y [ADR-0006](0006-dos-usuarios-de-base-de-datos.md): qué usuarios de PostgreSQL usa la operación del servidor.
- **Capabilities afectadas:** `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`, `reportes`, `api`
- **Fuentes:** `readme.md` §2.1, §2.2, §2.4, §2.4.1, §2.5, §3.4, §5 (plan de 6 semanas) y §6 (HB-10)

## Contexto

ADR-0025 (y antes ADR-0003) preveía 2 lugares de despliegue: el servidor del hogar para producción y un VPS de HostGator para la demo con datos ficticios, que además sería la producción futura, con Let's Encrypt.

No hay fondos para el VPS. La demo tiene que correr en una máquina local, y la producción, solo en el servidor del hogar. Además, el despliegue no tenía ticket ni guía: el plan lo daba por hecho en la semana 6. Al detallarlo en HB-10 aparecieron 3 puntos que los ADR anteriores no resolvían, o resolvían distinto de lo implementado:

- **HTTPS.** ADR-0022 dice "En producción: `SECURE_SSL_REDIRECT=True`, HSTS…", pero desde HB-04 la redirección y HSTS las hace nginx, y `config.settings.prod` pone `SECURE_SSL_REDIRECT = False`, como exige la spec de `infraestructura` ("Producción detrás de nginx"). ADR-0025 ya decía que nginx redirige y envía HSTS; el conflicto era con ADR-0022.
- **Usuarios de PostgreSQL en la operación.** ADR-0006 asigna `app_owner` a `migrate`, la carga del mock y los tests, y ADR-0004 reserva el superusuario para la inicialización. Los respaldos y su ensayo necesitan otros usos.
- **La CA de `mkcert`.** Se instala como raíz de confianza en las PC y los celulares del hogar, y no tiene restricción de nombres: quien tenga su llave privada puede emitir certificados válidos para cualquier sitio en esos dispositivos.

Los contextos de ADR-0001, ADR-0003, ADR-0004 y ADR-0010 siguen mencionando el VPS: son historia, y se leen con este ADR.

## Decisión

- **Contenedores** (las mismas decisiones de ADR-0025, que este ADR reemplaza):
  - Docker Compose con `nginx`, `web` (imagen propia: Python 3.12, Django 5.2 y Gunicorn) y `db` (`postgres:17-alpine`).
  - La app y la API viven en el mismo contenedor `web`: las ejecuta el mismo proceso Django.
  - `nginx` es el único con puertos publicados (80 y 443) y está solo en la red `frontend`, sin ruta a `db`. `web` está en `frontend` y `backend`, y `db` solo en `backend`, sin puertos publicados.
  - La imagen de `nginx` se fija en una versión de parche de la rama estable y se actualiza a mano, con un commit. La etiqueta vive en `docker-compose.yml` y en el readme (§2.4.1); este ADR no la repite.
  - `db` declara un *healthcheck* (`pg_isready`), `web` espera con `depends_on: condition: service_healthy` y `nginx` arranca después de `web`.
- **3 entornos, sin VPS:**

  | Entorno | Dónde | Acceso | Certificado | Datos |
  |---|---|---|---|---|
  | Desarrollo | Equipo del desarrollador | `localhost` | `mkcert` (`localhost`) | Semillas y mock |
  | Producción | Servidor Ubuntu con Docker en el hogar | Solo la red del hogar, por su IP fija | `mkcert`, con la IP del servidor, de una CA propia del hogar | Reales |
  | Demo | Una máquina local (laptop o el equipo de desarrollo) | `localhost` | `mkcert` (`localhost`) | Mock (§3.4), ficticio |

- **Certificados:**
  - Solo `mkcert`. No hay Let's Encrypt ni dominio público.
  - La CA del hogar se crea en la PC del Administrador, en una carpeta propia (`CAROOT`), distinta de la CA de desarrollo, y su llave privada nunca va al servidor.
  - El servidor recibe solo el certificado y su llave, y en los dispositivos se instala solo `rootCA.pem`.
  - La carpeta de la CA se resguarda en las 2 memorias USB, cifrada con su propia frase. Después de emitir un certificado, `rootCA-key.pem` se borra de la PC del Administrador: para renovar, se recupera del resguardo.
- **HTTPS lo resuelve nginx** (supersede ese punto de ADR-0022): nginx redirige 80 → 443 y envía HSTS. `config.settings.prod` no los repite (`SECURE_SSL_REDIRECT = False`) y sí exige las *cookies* `Secure` (`SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE`). El resto de ADR-0022 sigue vigente.
- **Usuarios de PostgreSQL en la operación** (amplía ADR-0006 y ADR-0004):
  - **`app_owner`** hace el respaldo (`pg_dump`) y la restauración (`pg_restore`), porque es el dueño de todas las tablas.
  - **El superusuario** solo crea y borra la base de ensayo `hogar_ensayo`, recrea vacía la base de la aplicación en una vuelta atrás (guía de HB-10, sección 8.2) y repone los permisos de base que `pg_dump` no respalda (`REVOKE ALL ... FROM PUBLIC` y `GRANT CONNECT ... TO app_user`, los de `db/init/01_roles.sh`). Lo hace por el *socket* del contenedor `db`, sin contraseña. `POSTGRES_PASSWORD` sigue siendo solo para la inicialización.
  - `web` sigue usando solo `app_user`.
- **Cifrado en reposo:** el disco del servidor del hogar se cifra con LUKS al instalar Ubuntu (LVM cifrado), con una frase que se escribe en cada arranque. Protege los datos personales y de salud de los Residentes (LFPDPPP) si roban el equipo o se desecha el disco. La frase la guarda el Administrador, aparte del servidor y de la memoria USB, y las memorias guardan una copia de la cabecera de LUKS. Los respaldos ya van cifrados con GPG, así que los discos externos no necesitan LUKS.
- **La demo usa la configuración de producción** (`config.settings.prod`, imagen sin herramientas de desarrollo) con el nombre de Hogar de la demo y el mock.
- **`make` no borra la base ni carga el mock en el servidor del hogar:** `make reset` y `make mock` se niegan si ven una señal del servidor: un `HOGAR_NOMBRE` distinto del de la demo (o vacío con `config.settings.prod`), `RESPALDO_DESTINATARIO` definida o `/etc/cron.d/hogar` (HB-10). No se fían solo del nombre, porque `.env.example` trae el de la demo y alguien puede olvidar cambiarlo. El candado es de `make`: `docker compose down -v` o cargar `cargar_mock.sql` a mano siguen siendo posibles, y la guía de HB-10 lo advierte. `cargar_mock.sql` se niega además si la base ya tiene datos de negocio.
- **Despliegue manual por SSH**, en el servidor del hogar: un respaldo manual, `git pull`, `make actualizar` (imagen, `migrate.sh` y `collectstatic`, TK-01) y una prueba de humo.
- **Respaldos:**
  - Un cron diario guarda un `pg_dump` cifrado con la llave pública GPG del Administrador, con retención de 14 días y copia a un disco externo conectado. La llave privada está solo en la PC del Administrador y, exportada con su frase y con su certificado de revocación, en 2 memorias USB de resguardo: una en el hogar y otra fuera. La frase se guarda aparte.
  - **El respaldo no lleva los datos de `axes` ni de `django_session`** (`--exclude-table-data`), solo su esquema. Así se cumple ADR-0022: esos datos (IP, *user-agent* y, por error, una contraseña escrita en el campo de usuario) no salen del servidor. En el servidor, un cron semanal borra los registros de acceso y de fallos de más de 30 días (`axes_reset_logs` y `axes_reset_failure_logs`) y todos los intentos fallidos (`axes_reset`), que ADR-0022 deja sin purga automática. Tras una restauración, esas tablas quedan vacías y cada usuario vuelve a iniciar sesión.
  - Una vez al mes, el Administrador copia el último respaldo a un segundo disco que se guarda **fuera del hogar**. Así hay una copia que sobrevive a un incendio, un robo o un *ransomware* en el servidor.
  - La prueba de restauración también es mensual: restaura en `hogar_ensayo`, sin detener la aplicación, y compara las tablas de negocio.
  - Cada respaldo completo deja una marca de tiempo, y el mensaje de entrada por SSH avisa si el último tiene más de 26 horas.
  - Lo concretan `scripts/backup_db.sh` y `scripts/restore_db.sh` (HB-10).
- **El despliegue tiene su ticket:** HB-10 (semana 6), con guía paso a paso en `docs/tickets/HB-10-despliegue-hogar.md`.

## Alternativas consideradas

- **Demo en un VPS (ADR-0025):** se descarta por falta de fondos. Si los hay, un ADR nuevo decide el proveedor, el dominio y Let's Encrypt (`certbot` y renovación), y supersede a este.
- **Demo solo con un video grabado:** se descarta como única opción, porque la demo en vivo muestra la aplicación real, HTTPS y CSP incluidos. El video queda como respaldo para quien evalúe a distancia.
- **Certificado autofirmado sin CA:** cada navegador mostraría la advertencia de sitio no seguro. Con la CA de `mkcert` instalada, el candado es válido en los dispositivos del hogar.
- **CA de `mkcert` en el servidor:** es más simple, pero quien comprometa el servidor podría emitir certificados que los dispositivos del personal aceptarían para cualquier sitio. Se descarta.
- **Cifrado simétrico de los respaldos, con la frase en el servidor:** el ensayo mensual no necesitaría al Administrador, pero quien tenga el servidor y el disco podría leer los respaldos. Se descarta.
- **Disco externo como única copia:** protege contra la falla del disco del servidor, pero no contra un incendio, un robo o un *ransomware*, porque está en el mismo lugar y montado. Se descarta.
- **Servidor sin cifrar el disco:** quien se llevara el equipo leería la base completa. Se descarta.
- **Desbloqueo automático de LUKS con TPM:** evita escribir la frase en cada arranque, pero quien se lleve el equipo completo lo arrancaría y la base se abriría sola. Se descarta. Sí se admite, como opción, el desbloqueo por SSH con `dropbear-initramfs` (guía de HB-10, paso 7.1).
- **Avisos por correo de un respaldo fallido:** necesitan un servidor de correo que el hogar no tiene. Queda el aviso al entrar por SSH, más la revisión mensual.

## Consecuencias

**Positivas:**
- Sin costo de hosting: todo corre en equipos que ya existen.
- La demo es la misma aplicación que producción, con la misma configuración y la misma imagen, solo con otros datos.
- La portabilidad se conserva: Docker Compose y la configuración por variables ([ADR-0004](0004-configuracion-por-entorno-variables-db.md)) permiten moverla a un hosting sin cambiar la arquitectura.
- Ni el servidor ni el disco externo, por sí solos, permiten leer los respaldos ni emitir certificados de confianza.
- Si roban el servidor o se desecha su disco, la base no se lee sin la frase de LUKS.

**Negativas:**
- El servidor no arranca solo: tras un corte de luz o un reinicio, alguien escribe la frase de LUKS, en su teclado o por SSH. Hasta entonces el sistema no está disponible. Se recomienda un no-break (UPS).
- Si se pierden la frase de LUKS o la cabecera, el disco del servidor no se recupera: queda restaurar el último respaldo (guía de HB-10, sección 8.4).
- Sin acceso desde fuera del hogar, y sin demo pública: quien evalúe a distancia ve el video o el repositorio.
- El servidor del hogar es un punto único de falla. Se mitiga con respaldos diarios, la copia mensual fuera del hogar y la restauración probada cada mes.
- Entre 2 copias mensuales fuera del hogar se pueden perder hasta 30 días si se pierden a la vez el servidor y el disco conectado.
- El ensayo mensual, la vuelta atrás y la restauración tras una falla necesitan al Administrador, con la llave privada GPG.
- Un respaldo fallido solo se ve al entrar por SSH o en la revisión mensual: no hay aviso automático fuera del servidor.
- Hay que instalar la CA de `mkcert` en cada dispositivo nuevo, y renovar el certificado antes de que venza (`mkcert` lo emite por 2 años y 3 meses), desde la PC del Administrador.
- Las correcciones de seguridad de `nginx` siguen sin llegar solas, como en ADR-0025: hay que revisar las versiones estables y actualizar la etiqueta.
