# HB-10 · Guía paso a paso: despliegue en el servidor del hogar, respaldos y demo local

> **Ticket:** [readme, sección 6, HB-10](../../readme.md#tickets-de-habilitación-hb-01-a-hb-10) · **Tipo:** infraestructura y operación · **Estimación:** 5 puntos · **Rama:** `feature/HB-10-despliegue-hogar`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket, en las secciones 2.4 y 2.5 del readme y en [ADR-0026](../adr/0026-despliegue-servidor-del-hogar-y-demo-local.md). Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.

**Resultado al terminar:**
- El sistema corre en el servidor del hogar y se usa por HTTPS, con candado válido, desde las PC y los celulares de la red del hogar.
- Cada noche se guarda un respaldo cifrado en el servidor y en un disco externo, y cada mes una copia va a un segundo disco que se guarda fuera del hogar.
- La restauración está probada: el ensayo restaura un respaldo en una base aparte y las tablas de negocio cuadran.
- Una máquina local queda lista para la demo con el dataset mock.
- La sección 8 deja escrito cómo actualizar, volver atrás y restaurar.

**Las 3 partes del ticket:**

| Parte | Dónde | Cuándo | Pasos |
|---|---|---|---|
| **A. Repositorio** | Tu equipo de desarrollo | En cuanto TK-01 está en `main`: conviene adelantarla, porque la semana 6 es la última | 1 a 6 |
| **B. Servidor del hogar** | El servidor, por SSH, y la PC del Administrador | Semana 6, con el MVP integrado (TK-01 a TK-07, prueba de integración y e2e en verde). Necesita una noche para comprobar el cron | 7 a 14 |
| **C. Demo local** | La máquina de la demo | Después de la parte A | 15 |

> **Estado de esta guía.** Las partes B y C se siguen tal cual. Los scripts de la parte A (pasos 2 a 4) son una **versión de referencia**: se escriben y se prueban al ejecutar el ticket, después de TK-01, cuando estén cerradas las decisiones abiertas de la sección 0.4. Sus tests (sección 3) fijan lo que deben cumplir. Si al ejecutarlos cambia algo del código de referencia, actualiza esta guía en el mismo PR.
>
> **Verificado el 2026-11-26.** Se copió el código de esta guía a archivos temporales en Windows (Git Bash), con PostgreSQL 17 en Docker. El resultado está en la sección 3.4, y lo que no se pudo probar, en la sección 0.5.

---

## 0. Antes de empezar

### 0.1 Lee primero (30 min)

| Qué | Dónde | Para qué |
|---|---|---|
| Entornos y proceso de despliegue | readme, sección 2.4 | Qué corre dónde, y los 6 puntos del proceso |
| Seguridad | readme, sección 2.5 | HTTPS, secretos, aislamiento de red y respaldos |
| Decisión de despliegue | [ADR-0026](../adr/0026-despliegue-servidor-del-hogar-y-demo-local.md) | Sin VPS, la CA fuera del servidor, la copia fuera del hogar, y qué usuarios de PostgreSQL usa la operación |
| Usuarios de base de datos | [ADR-0006](../adr/0006-dos-usuarios-de-base-de-datos.md), ampliado por ADR-0026 | Por qué `app_owner` respalda y restaura, y `web` sigue siendo solo `app_user` |
| Retención de los datos de `axes` | [ADR-0022](../adr/0022-autenticacion-sesion-argon2-axes.md) | Por qué hay un cron semanal que limpia `axes_accesslog`, `axes_accessfailurelog` y `axes_accessattempt` |
| `Makefile` y lectura de `.env` | Guía de TK-01, paso 1 | `make actualizar`, `make reset`, `make mock` y la lectura línea por línea |
| Instalación desde cero | [`integracion.md`](integracion.md), sección 3 | El ensayo que simula el servidor del hogar |
| Dataset mock y guion de la demo | readme, sección 3.4 | Qué muestra la demo |

### 0.2 Requisitos previos

**Para la parte A (tu equipo):**
- TK-01 integrado en `main`: existe el `Makefile` (con `actualizar`, `reset` y `mock`), `scripts/migrate.sh` lee `.env` línea por línea, así que `HOGAR_NOMBRE` puede llevar espacios, y existe la vista `v_conciliacion_existencia`.
- `gpg` y `make`. Git Bash trae `gpg` (`gpg --version`); `make` se instala aparte (readme, sección 1.4). En Linux, los paquetes `gnupg` y `make`.
- Python con pytest para los tests de `tests/` (`python -m pytest --version`), con las versiones de `app/requirements-dev.txt`.
- Los contenedores de desarrollo levantados (`make up`) con la base migrada.

**Para la parte B (el servidor del hogar):**
- El MVP integrado en `main`: TK-01 a TK-07, con la prueba de integración y los e2e en verde.
- Un equipo para el servidor. Como mínimo: 2 núcleos, 4 GB de RAM, 64 GB de SSD y conexión por cable al router. Con ~20 residentes y 3 usuarios, la carga es mínima.
- **2 discos externos USB:** uno siempre conectado al servidor, y otro que se guarda fuera del hogar (ADR-0026).
- Acceso al panel del router, para reservar la IP del servidor.
- Un monitor y un teclado conectados al servidor, o el desbloqueo por SSH del paso 7.1: con el disco cifrado (LUKS), hay que escribir su frase en cada arranque.
- Recomendado: un no-break (UPS). Cada corte de luz obliga a escribir de nuevo la frase de LUKS.
- **2 memorias USB de resguardo**, con el mismo contenido: la llave privada GPG exportada y su certificado de revocación, la carpeta de la CA de `mkcert` del hogar, cada una cifrada con su propia frase (pasos 9 y 12), y la copia de la cabecera de LUKS (paso 7.1). Una se queda en el hogar, en un lugar seguro, y la otra fuera, con el disco de fuera del hogar. La llave GPG y la CA van cifradas con su frase, que se guarda aparte. La cabecera de LUKS no abre el disco sin la frase de LUKS, y el certificado de revocación no descifra nada, pero permite anular la llave: guárdalos igual de bien.
- La PC del Administrador, con Git Bash (o Linux), `ssh`, `gpg`, `openssl` y `mkcert` (Windows: `winget install FiloSottile.mkcert`). Git Bash trae `ssh`, `gpg` y `openssl`.

**Para la parte C (la demo):** una laptop con Docker Desktop, Git Bash, `make` y `mkcert`, igual que un equipo de desarrollo (readme, sección 1.4). También puede ser tu propio equipo.

### 0.3 Crea la rama

```bash
git switch main && git pull
git switch -c feature/HB-10-despliegue-hogar
make up && make migrate
```

Como todo ticket HB, se ejecuta con la skill `implementar-ticket` (`CLAUDE.md`), con el perfil **Operación**:
- la parte A, con plan, tests en rojo con `test-writer`, tests congelados e implementación con `implementer`;
- las partes B y C, con los comandos con resultado esperado de la sección 5.

### 0.4 Decisiones

Las decisiones 1 a 3 y la 6 ya están tomadas en ADR-0026. La 4 y la 5 tienen una propuesta: el plan de `implementar-ticket` la confirma o la cambia, y la respuesta se anota aquí antes de escribir los scripts.

| # | Decisión | Estado | Qué se hace | Alternativa |
|---|---|---|---|---|
| 1 | Custodia de la llave privada GPG | Decidida (ADR-0026) | Solo en la PC del Administrador, más una copia en la memoria USB de resguardo. El servidor tiene solo la llave pública | Cifrado simétrico con la frase en el servidor: descartada, porque quien tenga el servidor y el disco podría leer los respaldos |
| 2 | Discos externos | Decidida (ADR-0026) | Uno siempre conectado y montado en `/mnt/respaldos`, y una copia mensual a un segundo disco que se guarda fuera del hogar | Solo el disco conectado: descartada, porque no sobrevive a un incendio, un robo ni un *ransomware* |
| 3 | Dirección del servidor | Decidida (ADR-0026) | IP fija reservada en el router (en esta guía, `192.168.1.50`). El certificado la incluye | Un nombre local, si el router tiene DNS propio. Android no resuelve bien los nombres `.local` |
| 4 | Hora del respaldo | Abierta | 02:30, cuando nadie usa el sistema | Otra hora sin uso |
| 5 | Retención | Abierta | 14 días en el servidor y en el disco conectado, y 12 copias mensuales en el disco de fuera | Más días en el disco conectado |
| 6 | Cifrado del disco del servidor (LUKS) | Decidida (ADR-0026) | Cifrado con LUKS al instalar Ubuntu, con una frase que se escribe en cada arranque (paso 7.1). Protege los datos de salud de los Residentes (LFPDPPP) si roban el equipo o se desecha el disco | Sin cifrar: descartada. Desbloqueo automático con TPM: descartado, porque quien se lleve el equipo completo lo arrancaría |

### 0.5 Pendientes para la ejecución

Esta guía pasó 5 revisiones adversariales en papel; la última terminó sin bloqueantes. La revisión del PR que la agregó dejó 1 hallazgo mayor y 5 menores, sobre el hook de secretos y esta guía, y también están atendidos. Lo que sigue no se pudo probar al escribirla: necesita el esquema de TK-01, GitHub Actions o el servidor real. El plan de `implementar-ticket` parte de esta lista, y cada punto se cierra con su evidencia en el PR.

| Pendiente | Por qué espera | Cómo se cierra |
|---|---|---|
| Los 2 tests del ensayo y `test_la_restauracion_conserva_la_inmutabilidad_de_movimiento` | Necesitan `v_conciliacion_existencia` y `movimiento`, de TK-01 | Los 13 de `tests/test_respaldos.py` en verde (paso 3) |
| El *job* `respaldos` en un *runner* real, con `tests/test_candado.py` y GNU Make 4.3 | Solo existe en GitHub Actions | El *job* en verde en el PR (paso 4) |
| La rama de `RESPALDOS_EXIGIR=1` que hace fallar la recolección | Solo se alcanza cuando falta `db`, `gpg` o `bash`, y en el *job* nunca faltan | Con `db` detenido, `RESPALDOS_EXIGIR=1 python -m pytest tests/test_respaldos.py` falla con `RESPALDOS_EXIGIR=1, pero no pueden correr: ...`, sin ningún test omitido. La salida va en el PR |
| El ensayo completo del paso 6 con el `Makefile` real | El `Makefile` (`reset`, `mock`, `candado`) nace en TK-01 y se completa en el paso 4; los pasos se simularon sin él | Los 5 puntos del paso 6 en tu equipo, con su resultado esperado. La salida va en el PR |
| La vuelta atrás completa de la sección 8.2 (`DROP DATABASE ... WITH (FORCE)`, `CREATE DATABASE` y la restauración por la entrada estándar) | Borra la base: no se ejecutó al escribir la guía | El punto 4 del paso 6 en tu equipo: `restore_db.sh -` restaura, `make restore-ensayo` dice `ensayo: cuadra.` y el login responde `200`. La parte de la 8.2 que necesita una actualización real (el `diff` de `showmigrations --plan` y el respaldo del estado actual) se prueba en la primera actualización del servidor |
| Publicar los puertos de la demo solo en `127.0.0.1` | Cambia `docker-compose.yml` (configuración: va con `implementar-ticket`), y el servidor sí necesita los puertos en la red local | En el plan: o se queda la nota del paso 15, o los puertos de nginx toman la IP de una variable que solo la demo define (`NGINX_IP=127.0.0.1` en su `.env`, paso 15). Sin la variable, la publicación debe quedar como hoy, en IPv4 y en IPv6, para no cambiar las salidas esperadas de HB-04 y del paso 10: `"${NGINX_IP:+${NGINX_IP}:}443:443"`, no `"${NGINX_IP:-0.0.0.0}:443:443"`, que deja fuera IPv6. Se comprueba con `docker compose config` y `docker compose ps`, con la variable y sin ella |
| ShellCheck dentro de `scripts/verificar.py --herramientas`, con su test | Es una tarea de este ticket (paso 4) | `verificar.py --herramientas` lo corre, también en el CI |
| La señal `/etc/cron.d/hogar` del candado | Necesita `root` en Linux | `sudo touch /etc/cron.d/hogar && make candado` se niega en una máquina de prueba (y después `sudo rm` del archivo) |
| La instalación con LUKS, la copia de su cabecera y el desbloqueo por SSH con `dropbear-initramfs` | Necesitan el servidor real | Paso 7.1, con un reinicio de prueba |
| Las decisiones 4 y 5 de la sección 0.4 (hora del respaldo y retención) | Se cierran en el plan del ticket | Anotadas en la sección 0.4 |
| Quitar el VPS de `prod.py`, `.env.example`, `docker-compose.yml` y las guías de HB-02 y HB-04 | Es código y configuración de este ticket | Paso 5, con su `git grep` |

---

## 1. Archivos que vas a crear o modificar

Solo la parte A cambia el repositorio. Las partes B y C configuran equipos y no se versionan, salvo lo que se anota en el PR.

```
AI4Devs-finalproject-vmrr/
├── .env.example                     # MODIFICAR: comentarios sin VPS y con los usos de ADR-0026; RESPALDO_* comentadas
├── Makefile                         # MODIFICAR: backup, restore, restore-ensayo y el candado de reset y mock
├── .github/workflows/ci.yml         # MODIFICAR: el job respaldos, no obligatorio (paso 4)
├── docker-compose.yml               # MODIFICAR: solo el comentario de nginx (ADR-0025 -> ADR-0026)
├── scripts/
│   ├── verificar.py                 # MODIFICAR: ShellCheck en --herramientas (paso 4)
│   ├── leer_env.sh                  # NUEVO: lee .env sin pisar lo que ya trae el entorno
│   ├── backup_db.sh                 # NUEVO: pg_dump cifrado con GPG, retención, disco externo y marca de éxito
│   ├── restore_db.sh                # NUEVO: restauración en base vacía y ensayo en base aparte
│   └── hogar.cron                   # NUEVO: respaldo y clearsessions diarios, axes_reset_logs semanal
├── tests/
│   ├── test_respaldos.py            # NUEVO: los 13 tests de los 2 scripts (sección 3.1)
│   ├── test_candado.py              # NUEVO: el candado de make, sin ejecutar reset ni mock (sección 3.2)
│   └── test_verificar.py            # MODIFICAR: el caso de ShellCheck (paso 4)
├── app/config/settings/prod.py      # MODIFICAR: docstring sin VPS
└── docs/tickets/
    ├── HB-02-imagen-web.md          # MODIFICAR: las copias de prod.py y .env.example
    ├── HB-04-nginx.md               # MODIFICAR: la copia del comentario de CSRF_TRUSTED_ORIGINS
    └── HB-10-despliegue-hogar.md    # MODIFICAR: esta guía, si el código de referencia cambia
```

`tests/` es la carpeta de las herramientas del repositorio (readme, sección 2.3): sus tests corren en tu equipo con `python -m pytest tests`, fuera del contenedor `web`, porque los scripts corren en el *host* y hablan con `docker compose`.

**Ya está hecho** (en la revisión del diseño de este ticket, no lo repitas):
- `.gitattributes` fuerza LF en `*.cron`, `Makefile` y `.env.example`: cron y `leer_env` no toleran CRLF.
- `.gitignore` ignora `*.asc`, `*.gpg`, `*.dump`, `*.dump.*`, `rootCA*.pem` y `.respaldos-ensayo/`.
- El hook de secretos reconoce la llave privada que exporta GPG (`PRIVATE KEY BLOCK`).

---

## 2. Tareas paso a paso

### Parte A · En el repositorio

#### Paso 1. Tests en rojo (≈ 45 min)

Escribe `tests/test_respaldos.py` (sección 3.1) y ejecútalo **antes** de crear los scripts:

```bash
python -m pytest tests/test_respaldos.py -v -p no:cacheprovider
```

Resultado esperado: **13 failed**. Todos fallan porque `scripts/backup_db.sh` y `scripts/restore_db.sh` no existen, y bash responde `No such file or directory`. Ninguno pasa por accidente: los que esperan un error comprueban además su mensaje.

Si ves `13 skipped`, falta algo para correrlos: el contenedor `db` (`make up`), el `gpg` y el `bash` de Git Bash (en Windows) o un `.env` de desarrollo. Los tests no corren si `HOGAR_NOMBRE` no es el de la demo, para no tocar nunca el clúster del servidor del hogar. La razón aparece con `-rs`.

Así avanza el rojo con cada paso:

| Al terminar | Comando | Resultado esperado |
|---|---|---|
| Paso 2 (respaldo) | `python -m pytest tests/test_respaldos.py -v -k "not ensayo and not restaura"` | Pasan los 8 del respaldo |
| Paso 3 (restauración) | `python -m pytest tests/test_respaldos.py -v` | 13 passed |
| Paso 4 (candado) | `python -m pytest tests/test_candado.py -v` | 6 passed |

#### Paso 2. El respaldo: `leer_env.sh` y `backup_db.sh` (≈ 1 h)

**`scripts/leer_env.sh`.** Usa la lectura línea por línea de TK-01, pero no pisa una variable que el entorno ya trae. Así el cron y los tests pueden cambiar, por ejemplo, la carpeta de respaldos sin tocar `.env`:

```sh
# Exporta las variables de .env que el entorno no trae ya (HB-10). Lectura línea por línea, como
# migrate.sh (TK-01): los valores pueden llevar espacios y no llevan comillas. .env debe estar en LF.
# Uso, desde la raíz del repositorio: . scripts/leer_env.sh && leer_env
# shellcheck shell=sh
leer_env() {
    while IFS= read -r linea || [ -n "$linea" ]; do
        case $linea in '' | '#'*) continue ;; esac
        clave=${linea%%=*}
        case $clave in '' | *[!A-Za-z0-9_]*) continue ;; esac
        # ${linea?}: se exporta la asignación CLAVE=valor que contiene la variable (ShellCheck SC2163)
        printenv "$clave" >/dev/null || export "${linea?}"   # el entorno manda
    done < .env
}
```

> `migrate.sh` (TK-01) lee `.env` con la misma lectura, pero **pisa** lo que trae el entorno. Aquí manda el entorno, para que el cron y los tests puedan cambiar un valor sin editar `.env`. Si después quieres una sola lectura, `migrate.sh` puede usar `leer_env`, porque el resultado es el mismo cuando el entorno no trae esas variables. Eso queda fuera de este ticket.

**`scripts/backup_db.sh`.** Usa bash, no `sh`, porque necesita `pipefail`: sin él, si `pg_dump` falla a la mitad, `gpg` cifra un respaldo incompleto y el script termina "bien".

```bash
#!/usr/bin/env bash
# Respaldo cifrado de la base (readme, sección 2.4, punto 4; HB-10).
# Lo ejecutan el cron cada noche (scripts/hogar.cron) y "make backup" antes de cada actualización.
# Variables, del entorno o de .env (el entorno manda):
#   RESPALDO_DESTINATARIO  correo o huella de la llave pública GPG del Administrador (obligatoria)
#   RESPALDO_DIR           carpeta local de respaldos (por defecto /var/backups/hogar)
#   RESPALDO_DISCO         punto de montaje del disco externo (por defecto, y si está vacía, /mnt/respaldos)
#   RESPALDO_SIN_DISCO     1 = sin copia al disco: solo en desarrollo y en los tests, nunca en el servidor
#   RESPALDO_DIAS          días que se conservan (por defecto 14)
# Al terminar bien, deja la hora en $RESPALDO_DIR/.ultimo-ok: el aviso de SSH la revisa (paso 12).
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/leer_env.sh
. scripts/leer_env.sh
leer_env

: "${RESPALDO_DESTINATARIO:?Falta RESPALDO_DESTINATARIO: la llave pública GPG del Administrador}"
dir=${RESPALDO_DIR:-/var/backups/hogar}
disco=${RESPALDO_DISCO:-/mnt/respaldos}   # vacía no salta la copia: un .env mal editado no la apaga
if [ "${RESPALDO_SIN_DISCO:-}" = "1" ]; then disco=""; fi
dias=${RESPALDO_DIAS:-14}

# Nunca un respaldo sin cifrar: sin la llave pública, no se respalda
if ! gpg --batch --list-keys "$RESPALDO_DESTINATARIO" >/dev/null 2>&1; then
    echo "backup_db: no está la llave pública '$RESPALDO_DESTINATARIO' (impórtala con gpg --import)" >&2
    exit 1
fi

umask 077                                   # solo el dueño lee los respaldos
mkdir -p "$dir"
archivo="$dir/hogar-$(date +%Y%m%d-%H%M%S).dump.gpg"
destino=""                                  # la copia en el disco externo, si la hay
# Si algo falla, no queda un archivo a medias, ni aquí ni en el disco
trap 'rm -f "$archivo.parcial"; [ -z "$destino" ] || rm -f "$destino.parcial"' EXIT

# Como app_owner, dueño de todas las tablas (ADR-0026). Formato custom: ya va comprimido.
# Sin los datos de axes ni de las sesiones, que no salen del servidor (ADR-0022); su esquema sí va.
docker compose exec -T db pg_dump -U app_owner -d "$POSTGRES_DB" --format=custom \
    --exclude-table-data='axes_*' --exclude-table-data=django_session \
    | gpg --batch --yes --trust-model always --encrypt \
        --recipient "$RESPALDO_DESTINATARIO" --output "$archivo.parcial"
mv "$archivo.parcial" "$archivo"
echo "$(date -Iseconds) respaldo: $archivo ($(du -h "$archivo" | cut -f1))"

# Retención: los últimos $dias días
find "$dir" -maxdepth 1 -name 'hogar-*.dump.gpg' -mtime +"$((dias - 1))" -delete

# Copia al disco externo. Si no está montado, el respaldo local queda, el cron registra el error
# y la marca de éxito no se actualiza, así que el aviso de SSH lo muestra.
if [ -n "$disco" ]; then
    if ! mountpoint -q "$disco" 2>/dev/null; then
        echo "backup_db: el disco externo no está montado en $disco; el respaldo quedó solo en $dir" >&2
        exit 2
    fi
    mkdir -p "$disco/hogar"
    destino="$disco/hogar/$(basename "$archivo")"
    # Sin "&&": con set -e, un fallo dentro de "a && b" no detiene el script, y la marca se escribiría igual
    if ! cp "$archivo" "$destino.parcial"; then
        echo "backup_db: no se pudo copiar al disco externo ($disco): ¿lleno o en solo lectura?; el respaldo quedó solo en $dir" >&2
        exit 3
    fi
    mv "$destino.parcial" "$destino"         # un disco lleno no deja un respaldo truncado
    find "$disco/hogar" -maxdepth 1 -name 'hogar-*.dump.gpg' -mtime +"$((dias - 1))" -delete
fi
date -Iseconds > "$dir/.ultimo-ok"
```

Por qué así:
- **`--trust-model always`:** la llave pública se importa en el servidor sin firmarla. Sin esta opción, `gpg` pregunta si confía en ella, y el cron no puede contestar.
- **`pg_dump` como `app_owner` por el *socket* del contenedor:** `app_owner` es el dueño de todas las tablas, y ADR-0026 le asigna los respaldos. La imagen de PostgreSQL acepta sin contraseña las conexiones locales del propio contenedor, como `dpsql` (`CLAUDE.md`, "Comandos").
- **Sin los datos de `axes` ni de `django_session`:** ADR-0022 dice que esos datos (IP, *user-agent* y, por error, una contraseña escrita en el campo de usuario) no salen del servidor y se purgan a los 30 días. El respaldo lleva su esquema, pero no sus filas: tras una restauración quedan vacías, y cada usuario vuelve a iniciar sesión. Lo prueba `test_el_respaldo_no_lleva_los_datos_de_axes_ni_de_sesiones`.
- **La copia al disco no se puede apagar por accidente:** con `RESPALDO_DISCO` vacía se usa `/mnt/respaldos`. Solo `RESPALDO_SIN_DISCO=1`, que ponen el desarrollo y los tests, la salta. Si no, un `.env` mal editado dejaría respaldos "completos" sin copia externa, y el aviso de SSH nunca saltaría.
- **Un fallo de la copia al disco detiene el script:** `cp` va en su propio `if`, nunca en una lista `a && b`, porque con `set -e` bash no se detiene cuando falla un comando que no es el último de la lista. Con el disco lleno o en solo lectura, el script sale con código 3, el respaldo queda en local y la marca no se escribe, así que el aviso de SSH salta. Lo prueba `test_si_falla_la_copia_al_disco_no_da_por_bueno_el_respaldo`.
- **La copia al disco va primero a `.parcial`:** si el disco se llena a la mitad, no queda un archivo truncado que alguien elija después como el más reciente.
- **Los roles no van en el respaldo:** `pg_dump` respalda una base, no los usuarios. Al restaurar en un volumen nuevo, `db/init/01_roles.sh` los vuelve a crear con las contraseñas de `.env`.
- **La marca `.ultimo-ok`** solo se escribe si todo salió bien, incluida la copia al disco. El servidor no tiene correo, y la marca es lo que revisa el aviso al entrar por SSH (paso 12).

Dale permiso de ejecución también en Git, como `migrate.sh`:

```bash
git add scripts/backup_db.sh scripts/leer_env.sh
git update-index --chmod=+x scripts/backup_db.sh
```

#### Paso 3. La restauración: `restore_db.sh` (≈ 1 h)

```bash
#!/usr/bin/env bash
# Restaura un respaldo de backup_db.sh (readme, sección 2.4, punto 4; HB-10).
# Uso: ./scripts/restore_db.sh ARCHIVO.dump.gpg            en la base de la aplicación, que debe estar vacía
#      ./scripts/restore_db.sh --ensayo ARCHIVO.dump.gpg   en hogar_ensayo: compara con la base en uso y la borra
# ARCHIVO puede ser "-": el respaldo ya descifrado llega por la entrada estándar. Así la llave
# privada no tiene que estar en el servidor (guía de HB-10, sección 8.3).
# RESTAURAR_BASE cambia la base de destino de la restauración normal (por defecto, POSTGRES_DB).
set -euo pipefail

ensayo=false
if [ "${1:-}" = "--ensayo" ]; then ensayo=true; shift; fi
archivo=${1:?Uso: restore_db.sh [--ensayo] ARCHIVO.dump.gpg o -}
# Antes del cd: así sirve una ruta relativa a la carpeta desde la que se llama
if [ "$archivo" != "-" ]; then
    [ -f "$archivo" ] || { echo "restore_db: no existe el respaldo $archivo" >&2; exit 1; }
    archivo="$(cd "$(dirname "$archivo")" && pwd)/$(basename "$archivo")"
fi

cd "$(dirname "$0")/.."
# shellcheck source=scripts/leer_env.sh
. scripts/leer_env.sh
leer_env
base=${RESTAURAR_BASE:-$POSTGRES_DB}
if $ensayo; then base=hogar_ensayo; fi

# </dev/null: "docker compose exec -T" lee la entrada estándar aunque no la necesite. Sin esto, con
# ARCHIVO "-", el primer psql se comería el respaldo antes de que llegue a pg_restore.
psql_su() { docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -AtX -v ON_ERROR_STOP=1 "$@" </dev/null; }
psql_en() { local b=$1; shift; docker compose exec -T db psql -U app_owner -d "$b" -AtX -v ON_ERROR_STOP=1 "$@"; }
respaldo() { if [ "$archivo" = "-" ]; then cat; else gpg --batch --decrypt "$archivo"; fi; }
# Tablas de negocio: sin las de sesiones y registros de acceso, que cambian con cada inicio de sesión
negocio="tablename NOT IN ('django_session', 'django_admin_log') AND tablename NOT LIKE 'axes\\_%'"
conteos() {  # "tabla|filas" de cada tabla de negocio, en orden
    echo "SELECT format('SELECT %L, count(*) FROM %I', tablename, tablename) FROM pg_tables WHERE schemaname = 'public' AND $negocio ORDER BY tablename \gexec" \
        | psql_en "$1"
}

if $ensayo; then
    psql_su -c "DROP DATABASE IF EXISTS hogar_ensayo WITH (FORCE)"
    psql_su -c "CREATE DATABASE hogar_ensayo OWNER app_owner"
    trap 'psql_su -c "DROP DATABASE IF EXISTS hogar_ensayo WITH (FORCE)" >/dev/null' EXIT
else
    tablas=$(psql_en "$base" -c "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'" </dev/null)
    if [ "$tablas" != "0" ]; then
        echo "restore_db: la base $base no está vacía ($tablas tablas); no se restaura encima" >&2
        exit 1
    fi
fi

respaldo | docker compose exec -T db pg_restore -U app_owner -d "$base" --exit-on-error --single-transaction
if ! $ensayo; then
    # Los permisos de la base no van en el respaldo: los mismos que da db/init/01_roles.sh
    psql_su -c "REVOKE ALL ON DATABASE \"$base\" FROM PUBLIC" -c "GRANT CONNECT ON DATABASE \"$base\" TO app_user"
fi
echo "$(date -Iseconds) restaurado en $base"

if $ensayo; then
    pendientes=$(psql_en hogar_ensayo -c "SELECT count(*) FROM v_conciliacion_existencia" </dev/null)
    if [ "$pendientes" != "0" ]; then
        echo "ensayo: v_conciliacion_existencia tiene $pendientes filas en el respaldo" >&2
        exit 1
    fi
    # En variables: con set -e, si una consulta falla, el script se detiene aquí
    en_uso=$(conteos "$POSTGRES_DB")
    restaurada=$(conteos hogar_ensayo)
    if [ -z "$en_uso" ] || [ -z "$restaurada" ]; then
        echo "ensayo: no se pudieron contar las tablas; no se puede decir que cuadra" >&2
        exit 1
    fi
    if [ "$en_uso" = "$restaurada" ]; then
        echo "ensayo: cuadra. $(printf '%s\n' "$restaurada" | wc -l) tablas de negocio con las mismas filas que $POSTGRES_DB, y la conciliación vacía"
    else
        diff <(printf '%s\n' "$en_uso") <(printf '%s\n' "$restaurada") >&2 || true
        echo "ensayo: NO cuadra (arriba las diferencias; < en uso, > restaurada)." >&2
        echo "Si alguien registró algo después del respaldo, repite el ensayo con un respaldo nuevo." >&2
        exit 1
    fi
fi
```

Por qué así:
- **El ensayo crea la base como superusuario** (`POSTGRES_USER`), por el *socket* del contenedor, con `app_owner` como dueño. En producción `app_owner` no tiene `CREATEDB` (`DB_OWNER_CREATEDB=false`), y el ensayo no debe detener la aplicación. ADR-0026 asigna este uso al superusuario.
- **`</dev/null` en cada `psql` que no lee de un *pipe*:** `docker compose exec -T` mantiene la entrada estándar conectada. Con `-`, sin esto, el primer `psql` se queda con el respaldo y `pg_restore` recibe un archivo vacío. Lo prueba `test_el_ensayo_por_la_entrada_estandar`.
- **La restauración normal se niega sobre una base con tablas.** Restaurar encima mezclaría los datos o fallaría a la mitad. Para volver atrás, la base se vacía a propósito (sección 8.2), nunca por accidente.
- **`--single-transaction` y `--exit-on-error`:** o se restaura todo, o nada.
- **Los permisos de la base se ponen al final.** `pg_dump` respalda lo que hay dentro de la base, pero no los permisos de la base misma:
  - sí viajan las tablas, el esquema `public`, las extensiones y los permisos de `app_user` sobre las tablas;
  - no viajan el `REVOKE ALL ... FROM PUBLIC` ni el `GRANT CONNECT ... TO app_user` de `db/init/01_roles.sh`.

  Una base recién creada deja conectarse a cualquier rol (`PUBLIC`), así que el script repone esos 2 permisos.
- **El ensayo compara solo las tablas de negocio con la base en uso.** `django_session`, `django_admin_log` y las de `axes` cambian con cada inicio de sesión, y darían diferencias falsas. El ensayo sirve justo después de un respaldo: si alguien registra un Movimiento entre los 2, esa tabla no cuadra y se repite.
- **La conciliación vacía** (`v_conciliacion_existencia`, TK-01) comprueba que el respaldo es coherente, no solo completo: el conteo de filas no detecta un contenido alterado con el mismo número de filas.
- **Los conteos van a variables antes de compararlos.** Un `diff <(...) <(...)` no se detiene si una consulta falla, y con las 2 salidas vacías diría "cuadra" con 0 tablas.

```bash
git add scripts/restore_db.sh && git update-index --chmod=+x scripts/restore_db.sh
python -m pytest tests/test_respaldos.py -v -p no:cacheprovider      # 13 passed
```

Si `pg_restore` falla en el ensayo, el error nombra el objeto. Arréglalo en el script y anota aquí el porqué. Las 3 extensiones del proyecto (`unaccent`, `pg_trgm` y `btree_gist`) son de confianza, y `app_owner` puede crearlas: la sección 3.4 lo comprobó.

#### Paso 4. `hogar.cron` y el `Makefile` (≈ 45 min)

**`scripts/hogar.cron`.** Las tareas programadas del servidor del hogar. Se instala en el paso 12 como `/etc/cron.d/hogar`:

```
# Tareas programadas del servidor del hogar (HB-10). Se instala como /etc/cron.d/hogar, sin punto en
# el nombre: cron ignora los archivos de /etc/cron.d que lo tienen. Supone el usuario "hogar" y el
# repositorio en /opt/hogar (guía de HB-10, paso 8): cámbialos si tu instalación usa otros.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Respaldo cifrado, todos los días a las 02:30
30 2 * * * hogar cd /opt/hogar && ./scripts/backup_db.sh >> /var/log/hogar/respaldo.log 2>&1

# Sesiones vencidas de Django, todos los días a las 03:15 (nada más las borra)
15 3 * * * hogar cd /opt/hogar && docker compose exec -T web python manage.py clearsessions >> /var/log/hogar/sesiones.log 2>&1

# Datos de axes (ADR-0022), los domingos a las 03:00: registros de acceso y de fallos de más de 30 días,
# y los intentos fallidos, donde puede quedar una contraseña escrita en el campo de usuario. axes_reset
# también desbloquea a quien estuviera bloqueado en ese momento: a esa hora, es aceptable.
0 3 * * 0 hogar cd /opt/hogar && docker compose exec -T web sh -c 'python manage.py axes_reset_logs --age 30 && python manage.py axes_reset_failure_logs --age 30 && python manage.py axes_reset' >> /var/log/hogar/axes.log 2>&1
```

El archivo debe terminar en un salto de línea: cron ignora la última línea si no lo tiene. `.gitattributes` ya lo fuerza a LF.

**`Makefile`.** Agrega 3 *targets* y un candado para `reset` y `mock`, los 2 comandos que nunca deben correr en el servidor del hogar: uno borra la base y el otro carga datos ficticios. Súmalos a `.PHONY` y al conteo de `make help`, como en TK-01:

```make
# Candado (HB-10, ADR-0026): reset y mock solo en desarrollo y en la demo, nunca en el servidor del hogar
DEMO_HOGAR := Hogar Gerontológico Demo
define solo_demo
	@if [ -n "$(RESPALDO_DESTINATARIO)" ] || [ -e /etc/cron.d/hogar ] \
	    || { [ "$(HOGAR_NOMBRE)" != "$(DEMO_HOGAR)" ] && { [ -n "$(HOGAR_NOMBRE)" ] || [ "$(DJANGO_SETTINGS_MODULE)" = "config.settings.prod" ]; }; }; then \
	    echo "make $@: esto parece el servidor del hogar (HOGAR_NOMBRE '$(HOGAR_NOMBRE)', respaldos configurados o /etc/cron.d/hogar). En el servidor del hogar, make $@ no se ejecuta."; \
	    exit 1; fi
endef

backup: ## Respaldo cifrado de la base (antes de cada actualización)
	./scripts/backup_db.sh

restore: ## Restaura un respaldo en la base vacía: make restore F=archivo.dump.gpg (o F=-)
	./scripts/restore_db.sh "$(F)"

restore-ensayo: ## Ensayo de restauración en una base aparte: make restore-ensayo F=archivo.dump.gpg (o F=-)
	./scripts/restore_db.sh --ensayo "$(F)"

candado: ## Comprueba el candado de reset y mock, sin borrar ni cargar nada
	$(solo_demo)
	@echo "candado: deja pasar (desarrollo o demo)"
```

Y la primera línea de la receta de `reset` y la de `mock`, antes de todo lo demás:

```make
reset: ## Borra la base LOCAL y la recrea con las migraciones (solo desarrollo y demo)
	$(solo_demo)
	# ... el resto de la receta de TK-01, sin cambios

mock: ## Carga el dataset mock (solo desarrollo y demo, en una base recién migrada)
	$(solo_demo)
	# ... el resto de la receta de TK-01, sin cambios
```

El candado se niega si ve cualquier señal del servidor del hogar, venga del `.env`, de la línea de comandos o del entorno de la sesión: `make` lee las 3. No se fía solo del nombre, porque `.env.example` trae el de la demo y alguien puede olvidar cambiarlo:
- **`RESPALDO_DESTINATARIO` definida:** solo el servidor tiene respaldos. El paso 8 la define desde el principio, con `pendiente` hasta el paso 12;
- **`/etc/cron.d/hogar`:** el cron de los respaldos (paso 12.5);
- **un `HOGAR_NOMBRE` distinto del de la demo**, o vacío con `config.settings.prod`, porque así está mal configurado un servidor.

Sin ninguna señal, deja pasar el nombre de la demo con cualquier configuración, y ningún nombre solo en desarrollo.

El candado es de `make`: no impide `docker compose down -v` ni cargar `cargar_mock.sql` a mano. Por eso el paso 10 lo advierte. `cargar_mock.sql` se niega además si la base ya tiene datos de negocio, pero en una base recién migrada cargaría.

> El nombre se lee del `.env` (`-include`), que está en UTF-8 como el `Makefile`. En Windows, no pases el nombre de la demo por la línea de comandos (`make mock HOGAR_NOMBRE="Hogar Gerontológico Demo"`): el `make` de GnuWin32 recibe los argumentos en otra codificación, "Gerontológico" no coincide y el candado se niega. Con otro nombre, como en la prueba de abajo, se niega igual, que es lo correcto.

Comprueba el candado con `make candado`, que lo evalúa y no hace nada más. Nunca lo pruebes con `make reset` ni con `make mock`: si fallara abierto, borrarían la base o cargarían el mock. Los mismos casos están en `tests/test_candado.py` (sección 3.2):

```bash
make candado                                                          # candado: deja pasar (desarrollo o demo)
make candado HOGAR_NOMBRE="Hogar San José"                            # make candado: esto parece el servidor del hogar ... (exit 1)
make candado HOGAR_NOMBRE= DJANGO_SETTINGS_MODULE=config.settings.prod # make candado: esto parece el servidor del hogar ... (exit 1)
make candado RESPALDO_DESTINATARIO=pendiente                          # make candado: esto parece el servidor del hogar ... (exit 1)
RESPALDO_DESTINATARIO=pendiente make candado                          # también si llega del entorno de la sesión (exit 1)
```

**ShellCheck en el verificador.** ADR-0024 pide un verificador único, y hoy ShellCheck solo se corre a mano. Agrega a `scripts/verificar.py --herramientas` un paso que ejecute `shellcheck -x` sobre `scripts/*.sh` y `db/init/*.sh`:
- con el `shellcheck` del equipo, o con `koalaman/shellcheck:v0.10.0` por Docker si no lo hay;
- sin ninguno de los 2, solo lo avisa, como hace hoy con ruff.

El *runner* `ubuntu-latest` del CI ya trae `shellcheck`, así que el *job* `herramientas` lo correrá. Agrega a `tests/test_verificar.py` un caso con un script que tenga un aviso de ShellCheck, escrito antes del cambio (en rojo). Corre antes el paso nuevo sobre `scripts/migrate.sh` y `db/init/01_roles.sh`: si dan avisos, corrígelos en este mismo ticket.

**El *job* `respaldos` del CI.** Los tests de `tests/test_respaldos.py` necesitan los contenedores, y el *job* `herramientas` los omite. Agrega a `.github/workflows/ci.yml` un *job* propio, **no obligatorio**, como `contrato` y `herramientas` (readme, sección 7.3, regla 7). Así un cambio en los scripts no se integra sin haberlos probado.

En el *job* `detectar`, su salida y su línea de `si_existe`, para que se active cuando exista el test:

```yaml
    outputs:
      hay_respaldos: ${{ steps.codigo.outputs.respaldos }}       # junto a las otras 4
    ...
          si_existe respaldos tests/test_respaldos.py "respaldos" >> "$GITHUB_OUTPUT"
```

Y el *job*, después de `herramientas`:

```yaml
  # ---------------------------------------------------------------------------
  # No obligatorio: los scripts de respaldo y restauración (HB-10), con los contenedores levantados
  # ---------------------------------------------------------------------------
  respaldos:
    name: respaldos (scripts de HB-10)
    needs: detectar
    if: needs.detectar.outputs.hay_respaldos == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 20
    env:
      PYTHONDONTWRITEBYTECODE: "1"
      RESPALDOS_EXIGIR: "1"        # si algo los omitiría, falla: nunca queda en verde sin haberlos corrido
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - name: Instalar pytest (la versión de app/requirements-dev.txt)
        run: pip install "$(grep -iE '^pytest==' app/requirements-dev.txt)"
      # El env: de todo el workflow define POSTGRES_PASSWORD, DB_OWNER_PASSWORD, ... Compose le da
      # prioridad sobre .env, pero migrate.sh lee .env: si no coinciden, app_owner no se autentica.
      - name: .env de ejemplo, con los valores del entorno del CI, el Hogar de la demo y la imagen sin herramientas de desarrollo
        run: |
          cp .env.example .env
          sed -i 's/^INSTALAR_DEV=.*/INSTALAR_DEV=false/' .env
          for v in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DB_OWNER_PASSWORD DB_APP_PASSWORD DB_OWNER_CREATEDB SECRET_KEY DJANGO_SETTINGS_MODULE; do
            sed -i "s|^$v=.*|$v=${!v}|" .env
          done
      - name: Levantar db y web, y migrar como app_owner (el esquema completo de TK-01)
        run: docker compose up -d --build db web && ./scripts/migrate.sh
      - name: Tests de los respaldos
        run: python -m pytest tests/test_respaldos.py tests/test_candado.py -v -rs -p no:cacheprovider
      - name: Logs de los contenedores, si falla
        if: failure()
        run: docker compose logs --no-color db web
```

**Por qué el `.env` copia el entorno del CI:** el `env:` de todo el *workflow* define las contraseñas de PostgreSQL (`owner-ci`, ...). `docker compose` las toma del entorno antes que del `.env`, así que `db` crea `app_owner` con `owner-ci`. Pero `migrate.sh` lee el `.env` y pisa el entorno. Si el `.env` siguiera con `cambia-esto-owner`, la migración fallaría con `password authentication failed`.

El *runner* `ubuntu-latest` trae Docker, `gpg` y `bash`. `.env.example` trae el Hogar de la demo desde TK-01, así que la guarda de los tests (sección 3.1) deja correrlos. Con `RESPALDOS_EXIGIR=1`, si falta el contenedor `db`, `gpg` o `bash`, la recolección falla en vez de omitir los 13. `tests/test_candado.py` prueba el candado con el GNU Make 4.3 del *runner*, el mismo del servidor. Cuesta unos 3 a 5 minutos por PR, como el *job* `imagen`.

Este *job* no se pudo probar en un *runner* al escribir la guía: se comprueba en el primer PR de HB-10. Revisa que aparece, que corre los 13 tests de los respaldos y los 6 casos del candado, y que queda en verde. No lo agregues a la protección de `main`: si algún día pasa a ser obligatorio, se decide en la sección 7.3.

#### Paso 5. Quita las menciones del VPS y anota los usos de ADR-0026 (≈ 20 min)

ADR-0026 deja fuera el VPS y amplía los usos de `app_owner` y del superusuario. Esto es lo que cambia en el código, en la configuración y en sus copias en las guías:

| Archivo | Antes | Después |
|---|---|---|
| `app/config/settings/prod.py`, línea 1 | `"""Producción: servidor del hogar y VPS (readme, sección 2.4).` | `"""Producción: servidor del hogar y demo local (readme, sección 2.4; ADR-0026).` |
| `.env.example`, comentario de `POSTGRES_*` | `superusuario, solo para la inicialización del contenedor db` | `superusuario: su contraseña solo sirve para la inicialización; la operación lo usa por el socket del contenedor (ADR-0026)` |
| `.env.example`, comentario de `DB_OWNER_PASSWORD` | `solo para migraciones, la carga del mock y los tests` | `solo para migraciones, la carga del mock, los tests y los respaldos (ADR-0026)` |
| `.env.example`, comentario de `DJANGO_SETTINGS_MODULE` | `config.settings.prod en el servidor del hogar y el VPS` | `config.settings.prod en el servidor del hogar y en la demo` |
| `.env.example`, comentario de `CSRF_TRUSTED_ORIGINS` | `En el VPS: https://<dominio>` | `En el servidor del hogar: https://<IP del servidor>` |
| `docker-compose.yml`, comentario de la imagen de `nginx` | `# versión fija (ADR-0025)` | `# versión fija (ADR-0026)` |
| `docs/tickets/HB-02-imagen-web.md` (secciones 1 y 2.4, y la copia de `.env.example`) | Las mismas frases | Las mismas correcciones |
| `docs/tickets/HB-04-nginx.md` (copia de `.env.example`) | `En el VPS: https://<dominio>` | `En el servidor del hogar: https://<IP del servidor>` |

Agrega también a `.env.example`, al final, las variables de los respaldos, comentadas porque solo se usan en el servidor:

```sh
# Respaldos (HB-10): solo en el servidor del hogar; en desarrollo y en la demo no hacen falta.
# Correo o huella de la llave pública GPG del Administrador, carpeta local y disco externo.
# RESPALDO_DESTINATARIO=<huella-de-la-llave-publica>
# RESPALDO_DIR=/var/backups/hogar
# RESPALDO_DISCO=/mnt/respaldos
```

Comprueba que no queda ninguna mención fuera de la historia:

```bash
git grep -n -i "vps\|let's encrypt\|certbot" -- . ':!openspec/changes/archive' ':!0*.md' ':!prompts.md' ':!docs/adr'
# Quedan esta guía y 4 líneas del readme:
#   - la nota "Sin VPS por ahora" (sección 2.4);
#   - el antipatrón de fechas sin zona horaria (sección 3.2, sobre una migración futura);
#   - la decisión de diseño de la habilitación y la ficha de HB-10 (sección 6).
# Y la línea de CLAUDE.md con el orden de ejecución, que dice "sin VPS".
```

#### Paso 6. Ensayo completo en tu equipo (≈ 45 min)

Antes de tocar el servidor, haz en tu equipo lo mismo que harás allá, con una llave GPG de prueba. Esto también prueba la vuelta atrás de la sección 8.2.

```bash
# 1. Instalación desde cero con el mock (integracion.md, sección 3). Antes de exportar las variables
#    de los respaldos: con RESPALDO_DESTINATARIO en la sesión, el candado del paso 4 se niega
make reset && make mock

# 2. Una llave de prueba (en el servidor será la pública del Administrador, paso 12)
POSTGRES_USER=$(grep -m1 '^POSTGRES_USER=' .env | cut -d= -f2-) POSTGRES_DB=$(grep -m1 '^POSTGRES_DB=' .env | cut -d= -f2-)   # solo estas 2, de tu .env
export GNUPGHOME="$(mktemp -d)"
gpg --batch --passphrase '' --quick-gen-key "Ensayo Respaldos <ensayo@respaldos.test>" default default never
export RESPALDO_DESTINATARIO=ensayo@respaldos.test RESPALDO_DIR="$PWD/.respaldos-ensayo" RESPALDO_SIN_DISCO=1

# 3. Respaldo y ensayo, con el archivo y por la entrada estándar (como en el servidor)
make backup                                         # ... respaldo: .../hogar-AAAAMMDD-HHMMSS.dump.gpg (≈ 100K)
ULTIMO="$(ls -t .respaldos-ensayo/*.dump.gpg | head -1)"
make restore-ensayo F="$ULTIMO"
# ensayo: cuadra. NN tablas de negocio con las mismas filas que hogar, y la conciliación vacía
gpg --decrypt "$ULTIMO" | ./scripts/restore_db.sh --ensayo -      # el mismo resultado

# 4. Vuelta atrás completa (sección 8.2): vaciar la base y restaurar el respaldo por la entrada
#    estándar, como en el servidor ("make restore F=archivo" hace lo mismo con el archivo)
docker compose stop web
docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres \
    -c "DROP DATABASE \"$POSTGRES_DB\" WITH (FORCE)" -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER app_owner"
gpg --decrypt "$ULTIMO" | ./scripts/restore_db.sh -         # ... restaurado en hogar
make restore-ensayo F="$ULTIMO"                             # ensayo: cuadra. (la base restaurada = el respaldo)
docker compose start web && make static
# start no espera a Gunicorn: mientras arranca, nginx responde 502, y curl reintenta
curl -sk --retry 10 --retry-delay 2 --retry-connrefused -o /dev/null -w "%{http_code}\n" \
    https://localhost/accounts/login/                                            # 200
# Y a mano: entra como consulta.demo, y las existencias del mock siguen ahí

# 5. Limpieza
rm -rf .respaldos-ensayo "$GNUPGHOME"; unset GNUPGHOME RESPALDO_DESTINATARIO RESPALDO_DIR RESPALDO_SIN_DISCO ULTIMO
```

> Tras `pg_restore` en una base nueva quedan de `app_owner` el esquema `public` y las extensiones. `app_user` conserva sus permisos sobre las tablas y los privilegios por defecto de las tablas futuras. Los permisos de la base los repone `restore_db.sh` (paso 3). Todo esto lo comprobó la sección 3.4.

---

### Parte B · En el servidor del hogar

Haz esta parte con quien administrará el servidor. En los ejemplos, el usuario del servidor es `hogar`, el repositorio vive en `/opt/hogar` y la IP fija es `192.168.1.50`: **usa la tuya en todos los comandos.** Los comandos que dicen "en la PC del Administrador" se ejecutan allí, en Git Bash; los demás, en el servidor.

#### Paso 7. Prepara el servidor (≈ 1 h 30 min)

1. **Instala Ubuntu Server 24.04 LTS con el disco cifrado (LUKS)**, el usuario `hogar` y OpenSSH (ADR-0026). No hace falta entorno gráfico. En la pantalla de almacenamiento del instalador:
   - elige *Use an entire disk*, con *Set up this disk as an LVM group* y **Encrypt the LVM group with LUKS** marcadas;
   - escribe una frase de al menos 20 caracteres. Se escribe en cada arranque, y sin ella el disco no se lee. Guárdala en el gestor de contraseñas del Administrador y, en papel, en un sobre cerrado, en otro lugar que el servidor y la memoria USB.

   Al terminar, comprueba que el sistema está sobre el volumen cifrado, y guarda una copia de la cabecera de LUKS: si la cabecera se daña, ni con la frase se recupera el disco.

   ```bash
   lsblk -f | grep crypto_LUKS          # la partición cifrada, por ejemplo sda3
   sudo cryptsetup luksHeaderBackup /dev/sda3 --header-backup-file ~/luks-cabecera-hogar.img
   sudo chown hogar:hogar ~/luks-cabecera-hogar.img    # la crea root, y sin esto el scp no la puede leer
   ```

   Después del paso 7.4, cópiala a las 2 memorias USB de resguardo desde la PC del Administrador (`scp hogar@192.168.1.50:luks-cabecera-hogar.img /e/ && cp /e/luks-cabecera-hogar.img /f/`; `/e/` y `/f/` son las 2 memorias en Git Bash) y bórrala del servidor (`rm ~/luks-cabecera-hogar.img`). Sola no abre el disco: hace falta la frase. Si algún día cambias la frase (`sudo cryptsetup luksChangeKey /dev/sda3`), rehaz la copia: la de las memorias conserva la frase vieja.

   **Opcional: desbloqueo por SSH.** Sin él, tras cada corte de luz alguien escribe la frase en el teclado del servidor. Con `dropbear-initramfs`, el Administrador la escribe desde su PC. Hazlo después del paso 7.4, porque usa su llave, y compruébalo al ejecutar el ticket:

   ```bash
   sudo apt install -y dropbear-initramfs
   # La llave del paso 7.4, limitada a desbloquear el disco
   sed 's/^/command="cryptroot-unlock",no-port-forwarding,no-agent-forwarding,no-X11-forwarding /' ~/.ssh/authorized_keys \
       | sudo tee /etc/dropbear/initramfs/authorized_keys
   echo 'DROPBEAR_OPTIONS="-p 2222 -s -j -k"' | sudo tee -a /etc/dropbear/initramfs/dropbear.conf
   # La red del arranque: sin ella, dropbear no se alcanza. <interfaz> es la del paso 7.2 (ip link), y el router da la IP reservada
   echo 'IP=:::::<interfaz>:dhcp' | sudo tee -a /etc/initramfs-tools/initramfs.conf
   sudo update-initramfs -u
   ```

   Tras un reinicio, desde la PC del Administrador: `ssh -p 2222 root@192.168.1.50`. Al entrar pide la frase directamente, porque la llave solo ejecuta `cryptroot-unlock`: escribe la frase, no el comando (sección 8.9).
2. **Reserva la IP en el router.** Busca la MAC del servidor: es la de la interfaz con cable en `ip link`. En el panel del router, asígnale siempre `192.168.1.50` ("reserva DHCP" o "IP estática por MAC").

   Reinicia el servidor y comprueba la IP con `ip -4 addr`. **No abras puertos en el router**: el sistema es solo para la red del hogar.
3. **Hora y actualizaciones:**

   ```bash
   sudo timedatectl set-timezone America/Mexico_City      # la hora del cron y del nombre de los respaldos
   sudo systemctl restart cron                            # cron toma la zona horaria al arrancar
   sudo apt update && sudo apt full-upgrade -y
   systemctl is-enabled unattended-upgrades               # enabled: los parches de seguridad se instalan solos
   ```

4. **SSH solo con llave.** En la PC del Administrador:

   ```bash
   ssh-keygen -t ed25519 -C "admin-hogar"                 # si aún no tienes una llave
   ssh-copy-id hogar@192.168.1.50                         # Git Bash lo trae
   ssh hogar@192.168.1.50                                 # entra sin pedir contraseña
   ```

   Ya en el servidor, apaga las contraseñas y el acceso como `root`:

   ```bash
   printf 'PasswordAuthentication no\nPermitRootLogin no\n' | sudo tee /etc/ssh/sshd_config.d/10-hogar.conf
   sudo systemctl restart ssh
   ```

   Antes de cerrar esta sesión, abre otra terminal y comprueba que `ssh hogar@192.168.1.50` sigue entrando.

5. **Firewall:**

   ```bash
   sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
   sudo ufw enable && sudo ufw status
   ```

   > Docker publica sus puertos por fuera de `ufw`. No es un problema aquí: los únicos puertos publicados son el 80 y el 443 de `nginx`, y PostgreSQL no publica ninguno (readme, sección 2.5).

6. **Docker Engine y Compose** desde el repositorio oficial de Docker (<https://docs.docker.com/engine/install/ubuntu/>), no desde el `docker.io` de Ubuntu:

   ```bash
   sudo apt install -y ca-certificates curl
   sudo install -m 0755 -d /etc/apt/keyrings
   sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
   sudo chmod a+r /etc/apt/keyrings/docker.asc
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
       | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   sudo apt update
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   sudo usermod -aG docker hogar                          # cierra la sesión y vuelve a entrar para que aplique
   ```

   > El grupo `docker` equivale a ser `root` en el servidor. Por eso la llave privada GPG y la de la CA no viven aquí (ADR-0026).

7. **Rotación de los logs de Docker:** sin ella, los logs de Gunicorn y nginx crecen sin límite.

   ```bash
   printf '{\n  "log-driver": "local",\n  "log-opts": { "max-size": "10m", "max-file": "5" }\n}\n' | sudo tee /etc/docker/daemon.json
   sudo systemctl restart docker && systemctl is-enabled docker   # enabled: arranca con el equipo
   ```

8. **Herramientas:** `sudo apt install -y git make gnupg`. `mkcert` no hace falta en el servidor: el certificado se emite en la PC del Administrador (paso 9).

#### Paso 8. El código y el `.env` de producción (≈ 30 min)

```bash
sudo mkdir -p /opt/hogar && sudo chown hogar:hogar /opt/hogar
```

Si el repositorio es público, clónalo por HTTPS:

```bash
git clone https://github.com/victorm007/AI4Devs-finalproject-vmrr.git /opt/hogar
```

Si es privado, en vez de ese `git clone`, usa una *deploy key* de solo lectura:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/hogar_deploy -N ''      # sin frase: la usa git en el servidor
cat ~/.ssh/hogar_deploy.pub                              # pégala en GitHub: Settings -> Deploy keys, sin permiso de escritura
printf 'Host github.com\n    IdentityFile ~/.ssh/hogar_deploy\n    IdentitiesOnly yes\n' >> ~/.ssh/config
git clone git@github.com:victorm007/AI4Devs-finalproject-vmrr.git /opt/hogar     # la URL SSH, no la HTTPS
```

En los 2 casos, después:

```bash
cd /opt/hogar && cp .env.example .env && chmod 600 .env
```

Genera cada secreto aparte, solo con letras y números (`.env` no admite `$`, `#` ni comillas):

```bash
for v in POSTGRES_PASSWORD DB_OWNER_PASSWORD DB_APP_PASSWORD; do echo "$v=$(openssl rand -hex 24)"; done
echo "SECRET_KEY=$(openssl rand -hex 32)"
```

Edita `.env` con estos valores. Cada uno tiene una razón:

| Variable | Valor en el servidor | Por qué |
|---|---|---|
| `POSTGRES_PASSWORD`, `DB_OWNER_PASSWORD`, `DB_APP_PASSWORD` | Las 3 generadas, distintas | Una por usuario de PostgreSQL (ADR-0006) |
| `DB_OWNER_CREATEDB` | `false` | En producción `app_owner` no crea bases. Solo surte efecto al crear el volumen: ponla **antes** del primer `make up` |
| `SECRET_KEY` | La generada (64 caracteres) | `check --deploy` pide al menos 50 caracteres variados |
| `DEBUG` | `False` | `prod.py` lo fuerza de todos modos |
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` | Exige `HOGAR_NOMBRE` y silencia los avisos de lo que hace nginx |
| `ALLOWED_HOSTS` | `192.168.1.50,localhost` | La IP para los dispositivos, y `localhost` para las pruebas desde el propio servidor |
| `CSRF_TRUSTED_ORIGINS` | `https://192.168.1.50,https://localhost` | Sin el origen exacto, cada formulario responde `403` |
| `HOGAR_NOMBRE` | El nombre real del hogar, sin comillas | La migración `entidades/0003_hogar` lo usa **una sola vez**, al crear el Hogar: revísalo antes del primer `make migrate`. Con él, además, `make reset` y `make mock` se niegan a correr |
| `INSTALAR_DEV` | `false` | La imagen sin pytest, ruff ni djLint |
| `GUNICORN_CMD_ARGS` | Vacía | Sin `--reload` |
| `APP_UID` | La salida de `id -u` (normalmente `1000`). No viene en `.env.example`: agrega la línea | `web` monta `./app` y su usuario debe poder leer el código |
| `RESPALDO_DESTINATARIO` | `pendiente` ahora, y la huella de la llave del Administrador en el paso 12 | Sin la huella, el respaldo no corre. Definida desde ya, es una de las señales con las que `make reset` y `make mock` saben que esto es el servidor (paso 4) |
| `RESPALDO_DIR`, `RESPALDO_DISCO` | `/var/backups/hogar` y `/mnt/respaldos` | Los valores por defecto de `backup_db.sh`, escritos para que se vean |

Comprueba que no quedó ningún valor de ejemplo y que Compose lee bien el `.env`, sin mostrarlo entero:

```bash
grep -c cambia-esto .env                # 0: check --deploy solo detecta una SECRET_KEY débil, no las contraseñas de la base
grep -c '^HOGAR_NOMBRE=Hogar Gerontológico Demo$' .env   # 0: el servidor lleva el nombre real, y la migración del Hogar no se repite
grep '^HOGAR_NOMBRE=' .env                                   # compáralo con el nombre que te dio la dirección
docker compose config | grep -E "DJANGO_SETTINGS_MODULE|HOGAR_NOMBRE|INSTALAR_DEV|DB_OWNER_CREATEDB"
```

#### Paso 9. El certificado y la CA en los dispositivos (≈ 45 min, más 5 min por dispositivo)

La CA del hogar se crea en la **PC del Administrador**, en una carpeta propia, distinta de la CA de desarrollo de `mkcert`. Su llave privada (`rootCA-key.pem`) nunca va al servidor. Quien la tenga puede emitir certificados que los dispositivos del hogar aceptarían para cualquier sitio (ADR-0026).

En la PC del Administrador:

```bash
export CAROOT="$HOME/ca-hogar"         # la CA del hogar; repite esta línea siempre que uses mkcert para el hogar
mkcert -install                        # crea la CA y la instala en esta PC, que es un dispositivo más del hogar
mkcert -cert-file local.pem -key-file local-key.pem 192.168.1.50 localhost 127.0.0.1
openssl x509 -noout -enddate -in local.pem     # notAfter: anótalo en el calendario (sección 8.5)

# Al servidor, solo el certificado, su llave y la parte pública de la CA (para probar con curl)
scp local.pem local-key.pem hogar@192.168.1.50:/opt/hogar/nginx/certs/
scp "$CAROOT/rootCA.pem" hogar@192.168.1.50:rootCA-hogar.pem
ssh hogar@192.168.1.50 'chmod 600 /opt/hogar/nginx/certs/local-key.pem'
rm local.pem local-key.pem
```

Ahora resguarda la CA, cifrada con su propia frase (distinta de la de GPG), y saca su llave de la PC. Sin el resguardo, renovar el certificado exige instalar una CA nueva en todos los dispositivos:

```bash
# /e/ es la memoria USB de resguardo en Git Bash: usa su letra
tar -C "$HOME" -czf - ca-hogar | gpg --symmetric --cipher-algo AES256 -o /e/ca-hogar.tar.gz.gpg   # pide la frase
gpg --decrypt /e/ca-hogar.tar.gz.gpg | tar -tzf - | grep rootCA-key.pem    # ca-hogar/rootCA-key.pem: el resguardo se lee
cp /e/ca-hogar.tar.gz.gpg /f/                                              # y a la segunda memoria
rm "$CAROOT/rootCA-key.pem"            # en la PC queda solo rootCA.pem, la parte pública
```

La frase de la CA va en el gestor de contraseñas del Administrador, nunca junto a la memoria. Para renovar, la sección 8.5 recupera la llave del resguardo y la vuelve a borrar.

Instala `$CAROOT/rootCA.pem` en cada dispositivo que usará el sistema. Cópialo con otro nombre, por ejemplo `rootCA-hogar.pem`, para reconocerlo:

| Dispositivo | Cómo |
|---|---|
| **Windows** (Edge y Chrome) | Doble clic en el archivo → *Instalar certificado* → *Usuario actual* → *Colocar todos los certificados en el siguiente almacén* → *Entidades de certificación raíz de confianza* |
| **Firefox** (cualquier sistema) | *Ajustes → Privacidad y seguridad → Certificados → Ver certificados → Autoridades → Importar*, y marca "Confiar en esta CA para identificar sitios web" |
| **Android** | Copia el archivo al teléfono → *Ajustes → Seguridad → Más ajustes de seguridad → Cifrado y credenciales → Instalar un certificado → Certificado de CA* (el menú cambia un poco según la marca) |
| **iPhone / iPad** | Envíalo por AirDrop o correo y ábrelo → *Ajustes → Perfil descargado → Instalar*. Después, *Ajustes → General → Información → Ajustes de confianza de certificados*, y activa la confianza total |

El certificado lleva la IP. Si la IP del servidor cambia, el candado se rompe, y por eso la reserva del paso 7 es obligatoria.

#### Paso 10. Primera instalación (≈ 30 min)

```bash
cd /opt/hogar
POSTGRES_USER=$(grep -m1 '^POSTGRES_USER=' .env | cut -d= -f2-) POSTGRES_DB=$(grep -m1 '^POSTGRES_DB=' .env | cut -d= -f2-)   # para los comandos de esta parte
make up                  # al crear el volumen, db/init/01_roles.sh crea app_owner (sin CREATEDB) y app_user
make migrate             # crea el Hogar con HOGAR_NOMBRE, los grupos, los motivos y las presentaciones
make superuser           # el Administrador: usuario y contraseña propios, de 10 caracteres o más
make static
```

En cada sesión SSH nueva, repite la línea de `POSTGRES_USER` y `POSTGRES_DB` antes de los comandos que las usan. Lee solo esas 2: no exportes el `.env` entero a tu sesión, que tiene las contraseñas y la `SECRET_KEY`.

**No ejecutes `make mock` ni `make reset`.** El candado del paso 4 los impide; para comprobarlo, `make candado` (sección 5), que no hace nada más. **Nunca ejecutes `docker compose down -v` en el servidor:** borra el volumen `pgdata`, es decir, la base real, y el candado de `make` no lo impide. Para detener los contenedores, `docker compose down`, sin `-v`.

Comprueba la instalación antes de seguir:

```bash
docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
# solo nginx muestra 0.0.0.0:80 y 0.0.0.0:443; web y db, sin flecha
docker compose exec web python manage.py check --deploy
# System check identified no issues (3 silenced).   (los 3 que silencia prod.py: HSTS, redirección y axes.W006)
docker compose exec -T db psql -U app_owner -d "$POSTGRES_DB" -AtX -c "SELECT nombre FROM entidad WHERE tipo = 'HOGAR'"
# el nombre real del hogar: compáralo con el que te dio la dirección, no con .env. Nunca "Hogar Gerontológico Demo"
docker compose exec -T db psql -U app_owner -d "$POSTGRES_DB" -AtX -c "SELECT count(*) FROM movimiento"
# 0: sin datos del mock
```

#### Paso 11. Usuarios reales (≈ 20 min)

Desde una PC del hogar, entra a `https://192.168.1.50/admin/` como Administrador. En *Usuarios*, crea uno por persona, con **exactamente un grupo**: *Solo lectura* o *Lectura y escritura* (HB-08).

Si tú elegiste la contraseña inicial, pídele a cada persona que la cambie en `https://192.168.1.50/admin/password_change/`. Todos los usuarios con grupo son `is_staff` y pueden hacerlo, pero nada los obliga: confírmalo con cada uno.

Después, comprueba que cada uno tiene su grupo:

```bash
docker compose exec -T db psql -U app_owner -d "$POSTGRES_DB" -AtX -c \
  "SELECT u.username, count(g.group_id) FROM usuario u LEFT JOIN usuario_groups g ON g.usuario_id = u.id WHERE NOT u.is_superuser GROUP BY 1 ORDER BY 1"
# cada usuario con 1
```

`usuario_groups` es la tabla puente entre `usuario` y los grupos. `uq_usuario_un_grupo` (HB-08) ya impide 2 grupos: la consulta confirma que nadie se quedó sin ninguno.

Y que no hay usuarios del mock:

```bash
docker compose exec -T db psql -U app_owner -d "$POSTGRES_DB" -AtX -c "SELECT count(*) FROM usuario WHERE username LIKE '%.demo'"
# 0
```

#### Paso 12. Respaldos, aviso y tareas programadas (≈ 1 h 15 min)

**1. La llave GPG, en la PC del Administrador** (nunca en el servidor):

```bash
gpg --quick-gen-key "Respaldos Hogar <respaldos@hogar.example>" default default never   # pide una frase
gpg --fingerprint respaldos@hogar.example        # la huella: 40 caracteres hexadecimales
gpg --armor --export respaldos@hogar.example > respaldos-hogar.pub.asc
gpg --armor --export-secret-keys respaldos@hogar.example > respaldos-hogar.privada.asc   # SOLO a las 2 memorias USB
gpg --output respaldos-hogar.revocacion.asc --gen-revoke respaldos@hogar.example        # por si se compromete: también a las 2 memorias
#   --gen-revoke pregunta: crearlo (y), el motivo (1 = la llave se comprometió), una descripción (Enter) y confirmar (y)
scp respaldos-hogar.pub.asc hogar@192.168.1.50:
```

- **La frase de la llave** va en el gestor de contraseñas del Administrador, **nunca junto a la memoria USB**: la llave exportada solo se lee con ella.
- **Si pierdes la llave privada y su frase, ningún respaldo se puede restaurar.** La memoria USB de resguardo no es opcional.
- Copia `respaldos-hogar.privada.asc` y `respaldos-hogar.revocacion.asc` a las 2 memorias USB (sección 0.2), y bórralos de la PC en cuanto estén en ellas. `.gitignore` ya ignora los `*.asc` y el hook de secretos los bloquea, por si quedara dentro del repositorio.

**2. En el servidor, la llave pública y el disco externo:**

```bash
gpg --import ~/respaldos-hogar.pub.asc && rm ~/respaldos-hogar.pub.asc
# En .env: RESPALDO_DESTINATARIO=<la huella del paso 1, sin espacios>

lsblk -f                                          # identifica el disco externo y su UUID (por ejemplo, sdb1)
sudo mkfs.ext4 -L respaldos /dev/sdb1             # SOLO si es nuevo: borra todo lo que tenga
sudo mkdir -p /mnt/respaldos
echo "UUID=<uuid-del-disco> /mnt/respaldos ext4 defaults,nofail,x-systemd.device-timeout=10s 0 2" | sudo tee -a /etc/fstab
sudo mount -a && mountpoint /mnt/respaldos        # /mnt/respaldos is a mountpoint
sudo chown hogar:hogar /mnt/respaldos
sudo mkdir -p /var/backups/hogar /var/log/hogar && sudo chown hogar:hogar /var/backups/hogar /var/log/hogar
```

`nofail` deja arrancar el servidor aunque el disco no esté conectado. En ese caso el respaldo avisa en su log, se queda solo en local y no actualiza la marca de éxito.

**3. El aviso al entrar por SSH y la rotación de los logs:**

```bash
sudo tee /etc/update-motd.d/99-hogar-respaldo > /dev/null <<'EOF'
#!/bin/sh
# HB-10: avisa si el último respaldo completo (la marca de backup_db.sh) tiene más de 26 horas
marca=/var/backups/hogar/.ultimo-ok
if [ ! -f "$marca" ] || [ -n "$(find "$marca" -mmin +1560)" ]; then
    echo
    echo "  *** AVISO: el último respaldo completo tiene más de 26 horas. Revisa /var/log/hogar/respaldo.log ***"
    echo
fi
EOF
sudo chmod 755 /etc/update-motd.d/99-hogar-respaldo

printf '/var/log/hogar/*.log {\n    su hogar hogar\n    monthly\n    rotate 12\n    compress\n    missingok\n    notifempty\n}\n' \
    | sudo tee /etc/logrotate.d/hogar
sudo logrotate --debug /etc/logrotate.d/hogar     # sin errores
```

**4. El primer respaldo, a mano:**

```bash
cd /opt/hogar && make backup
ls -l /var/backups/hogar /mnt/respaldos/hogar     # el mismo archivo en los 2 lugares
cat /var/backups/hogar/.ultimo-ok                 # la hora de este respaldo
```

Sal y vuelve a entrar por SSH: no debe aparecer el aviso.

**5. El cron:**

```bash
sudo install -m 644 -o root -g root scripts/hogar.cron /etc/cron.d/hogar
# cron revisa /etc/cron.d cada minuto: no hace falta recargarlo
```

Al día siguiente, revisa que corrió: `tail /var/log/hogar/respaldo.log`.

**6. El primer ensayo de restauración**, en la PC del Administrador, que tiene la llave privada (sección 8.3):

```bash
ssh hogar@192.168.1.50 'cd /opt/hogar && make backup'
ULTIMO=$(ssh hogar@192.168.1.50 'ls -t /var/backups/hogar/*.dump.gpg | head -1')
ssh -n hogar@192.168.1.50 "cat $ULTIMO" | gpg --decrypt \
  | ssh hogar@192.168.1.50 'cd /opt/hogar && ./scripts/restore_db.sh --ensayo -'
# ensayo: cuadra. NN tablas de negocio con las mismas filas que hogar, y la conciliación vacía
```

El respaldo viaja descifrado por el túnel SSH, que va cifrado, y no se escribe descifrado fuera del servidor. En el servidor, `hogar_ensayo` vive unos minutos en el disco cifrado con LUKS y se borra al terminar.

**7. El disco que se guarda fuera del hogar.** Prepáralo como el otro, pero **sin** agregarlo a `/etc/fstab`: se conecta solo una vez al mes. Debe ser del usuario `hogar`, porque la restauración tras una falla (sección 8.4) lo lee sin `sudo`:

```bash
sudo mkfs.ext4 -L respaldos-fuera /dev/sdc1          # SOLO si es nuevo: borra todo lo que tenga
sudo mkdir -p /mnt/respaldos-fuera && sudo mount /dev/sdc1 /mnt/respaldos-fuera
sudo chown hogar:hogar /mnt/respaldos-fuera          # queda guardado en el disco: basta una vez
```

Haz ahora la primera copia, con el procedimiento de la sección 8.3. Esta primera vez, antes de desmontarlo, haz además el ensayo **desde este disco**, en la PC del Administrador, para comprobar que se puede restaurar sin el servidor original:

```bash
ULTIMO=$(ssh hogar@192.168.1.50 'ls -t /mnt/respaldos-fuera/hogar/*.dump.gpg | head -1')
ssh -n hogar@192.168.1.50 "cat $ULTIMO" | gpg --decrypt \
  | ssh hogar@192.168.1.50 'cd /opt/hogar && ./scripts/restore_db.sh --ensayo -'
# ensayo: cuadra. ...
```

Después desmóntalo (`sudo umount /mnt/respaldos-fuera`) y llévatelo.

#### Paso 13. Prueba de humo y aceptación (≈ 30 min)

Desde una PC y un celular de la red del hogar, con la CA instalada:

1. Abre `https://192.168.1.50`: el candado es válido, sin advertencia, y lleva al login.
2. Entra con un usuario de *Lectura y escritura*: la pantalla de existencias carga, y la consola del navegador (en la PC) no muestra violaciones de CSP.
3. **No registres Movimientos de prueba en el servidor:** son inmutables y quedarían para siempre en el historial del hogar. El registro ya se probó en el paso 6 y se prueba en la demo (paso 15). Aquí basta con abrir el formulario de entrada y ver los Medicamentos del catálogo. El primer Movimiento del servidor será la primera Entrada real del hogar.
4. Entra con un usuario de *Solo lectura*: consulta, pero no ve los botones de registro, y un `POST` directo responde `403`.
5. Cierra la sesión.

Desde el servidor:

```bash
curl -sI http://localhost/ | grep -i location                      # Location: https://localhost/
curl -sI --cacert ~/rootCA-hogar.pem https://192.168.1.50/accounts/login/ | head -1   # HTTP/2 200, sin -k
curl -skI https://localhost/accounts/login/ | grep -ci content-security-policy   # 1
docker compose exec -T db psql -U app_owner -d "$POSTGRES_DB" -AtX -c "SELECT count(*) FROM v_conciliacion_existencia"   # 0
```

#### Paso 14. Deja el servidor documentado (≈ 15 min)

Anota en un lugar que el hogar conserve, **fuera del repositorio**:
- la IP, el usuario de SSH y dónde está su llave;
- dónde están las 2 memorias USB de resguardo (con la llave privada GPG exportada, su revocación, la carpeta de la CA y la cabecera de LUKS) y el disco de fuera del hogar;
- quién guarda la frase de la llave GPG: en otro lugar que la memoria, por ejemplo el gestor de contraseñas del Administrador;
- dónde están la frase de LUKS (gestor de contraseñas y sobre cerrado) y la copia de su cabecera (memoria USB), y quién puede escribirla tras un corte de luz (sección 8.9);
- la fecha en que vence el certificado (paso 9);
- el calendario de la sección 8.10.

El PR lleva solo lo que no es secreto: la salida de `docker compose ps`, la de `check --deploy` y la del ensayo, sin datos de residentes.

---

### Parte C · La demo en una máquina local

#### Paso 15. Prepara la máquina de la demo (≈ 45 min la primera vez, 3 min antes de cada demo)

La demo es la misma aplicación que producción, con la misma imagen y la misma configuración, pero con el Hogar de la demo y el mock (ADR-0026).

1. **Instala** Docker Desktop, Git Bash, `make` y `mkcert`, como un equipo de desarrollo (readme, sección 1.4).
2. **El código y el certificado.** Aquí basta la CA de desarrollo de `mkcert`, no la del hogar:

   ```bash
   git clone https://github.com/victorm007/AI4Devs-finalproject-vmrr.git && cd AI4Devs-finalproject-vmrr
   cp .env.example .env
   mkcert -install
   mkcert -cert-file nginx/certs/local.pem -key-file nginx/certs/local-key.pem localhost 127.0.0.1
   ```

3. **El `.env` de la demo**, como el de producción salvo lo que la hace demo:

   | Variable | Valor en la demo |
   |---|---|
   | Las 3 contraseñas y `SECRET_KEY` | Generadas, como en el paso 8 (la demo también debe pasar `check --deploy`) |
   | `DB_OWNER_CREATEDB` | `false` |
   | `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
   | `HOGAR_NOMBRE` | `Hogar Gerontológico Demo` (el único que deja pasar `make reset` y `make mock`) |
   | `INSTALAR_DEV` | `false` |
   | `GUNICORN_CMD_ARGS` | Vacía |
   | `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` | Los de `.env.example` (`localhost`) |
   | `RESPALDO_*` | Sin definir: la demo no tiene respaldos ni cron |
   | `NGINX_IP` | `127.0.0.1`, solo si el plan del ticket adoptó la variable (sección 0.5). Si no, no existe |

4. **Antes de cada demo**, déjala como nueva:

   ```bash
   make reset && make mock          # base desde cero, con los datos del mock (sección 3.4)
   make superuser                   # solo si vas a mostrar /admin/: el mock no trae Administrador
   ```

5. **Ensaya el guion** de la sección 3.4 del readme en <https://localhost>, con `consulta.demo` / `DemoLectura2026!` y `operador.demo` / `DemoEscritura2026!`.

6. **Si la demo es tu equipo de desarrollo:** las 2 son la misma instalación de Compose, porque `docker-compose.yml` fija `name: hogar`. Tienen los mismos volúmenes, y `make reset` borra tu base de desarrollo. Para tenerlas aparte, clona el repositorio en otra carpeta y agrega `COMPOSE_PROJECT_NAME=hogar-demo` a su `.env`: Compose le da prioridad sobre `name:`. Las 2 no pueden correr a la vez, porque usan los puertos 80 y 443.
7. **Sin internet en el lugar de la demo:** el primer `make up` descarga imágenes. Hazlo antes, con conexión. Después, `make reset` y `make mock` ya no necesitan red.
   **No la presentes conectada a una red ajena.** `docker-compose.yml` publica los puertos 80 y 443 de nginx en todas las interfaces, y los usuarios del mock y sus contraseñas son públicos: están en el readme. Un navegador que entre por la IP de tu máquina recibe un `400`, porque `ALLOWED_HOSTS` solo trae `localhost` y `127.0.0.1`. Pero quien comparta la red y mande la cabecera `Host: localhost` a mano (por ejemplo, con `curl`) llega a la aplicación y puede entrar como `operador.demo`. Como la demo no necesita red, desconecta la máquina antes de presentar o usa una red tuya, como el punto de acceso de tu celular. El firewall del sistema puede no bastar: Docker Desktop agrega su propia regla al instalarse. Publicar los puertos solo en `127.0.0.1` queda como pendiente de la sección 0.5.

8. **Para quien evalúe a distancia:** graba el guion completo con la herramienta de grabación de pantalla del sistema. Muestra el candado de HTTPS y una pantalla a 390 px (las herramientas de desarrollo del navegador la simulan).

---

## 3. Tests requeridos

### 3.1 `tests/test_respaldos.py`

Corren en tu equipo, contra el contenedor `db` de desarrollo, con una llave GPG de prueba creada en una carpeta temporal, nunca la del Administrador. Sin el contenedor `db` corriendo, o sin `gpg` ni `bash`, se omiten: el *job* `herramientas` del CI no levanta contenedores. Por eso su salida local va en el PR (sección 6).

```python
"""Respaldo y restauración de la base (HB-10): scripts/backup_db.sh y scripts/restore_db.sh.

Corren en el equipo de desarrollo, contra el contenedor db de docker compose, con una llave GPG
de prueba en una carpeta temporal (nunca la del Administrador). Sin db corriendo, o sin gpg o
bash, se omiten: el job herramientas del CI no levanta contenedores. El job respaldos sí los
levanta y pone RESPALDOS_EXIGIR=1: ahí, lo que los omitiría hace fallar la recolección, para que
nunca pasen en verde sin haber corrido.

Rojo esperado: los scripts no existen, y bash responde "No such file or directory". Los tests
que esperan un error comprueban también su mensaje, para no pasar por accidente.
"""

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
BACKUP = "scripts/backup_db.sh"  # relativas a RAIZ, el cwd de correr()
RESTORE = "scripts/restore_db.sh"
LLAVE = "prueba@respaldos.test"
DIA = 24 * 60 * 60
DEMO_HOGAR = "Hogar Gerontológico Demo"


def _de_git_bash(programa):
    """La ruta completa del programa. En Windows, solo el de Git Bash: "bash" a secas ejecuta el
    de WSL (System32 va antes que el PATH), que no hereda las variables de entorno, y el gpg de
    Gpg4win no entiende las rutas /c/... que les pasa posix()."""
    ruta = shutil.which(programa)
    if ruta and os.name == "nt" and "\\git\\" not in ruta.lower():
        return None
    return ruta


BASH = _de_git_bash("bash")
GPG = _de_git_bash("gpg")


def de_env(clave, defecto):
    """Un valor de .env, como lo leen los scripts, o el de por defecto."""
    env = RAIZ / ".env"
    for linea in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
        if linea.startswith(clave + "="):
            return linea.split("=", 1)[1]
    return defecto


def _db_corriendo():
    if not shutil.which("docker"):
        return False
    r = subprocess.run(
        ["docker", "compose", "ps", "--status", "running", "--services"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    return r.returncode == 0 and "db" in r.stdout.split()


def _parece_el_servidor():
    """Las mismas señales que el candado de make (guía de HB-10, paso 4): del entorno de la sesión o
    del .env, como las lee make. No se fía solo del nombre del Hogar."""

    def valor(clave):
        return os.environ.get(clave) or de_env(clave, "")

    nombre, ajustes = valor("HOGAR_NOMBRE"), valor("DJANGO_SETTINGS_MODULE")
    return (
        valor("RESPALDO_DESTINATARIO") != ""
        or Path("/etc/cron.d/hogar").exists()
        or (nombre != DEMO_HOGAR and (nombre != "" or ajustes == "config.settings.prod"))
    )


OMITIR = [
    (not (GPG and BASH), "sin el gpg y el bash de Git Bash (o de Linux)"),
    # Nunca donde pueda estar la base real: en el servidor del hogar serían superusuario sobre producción
    (
        _parece_el_servidor(),
        "esto parece el servidor del hogar (HOGAR_NOMBRE, RESPALDO_DESTINATARIO o /etc/cron.d/hogar): "
        "estos tests no corren donde puede estar la base real",
    ),
    (not _db_corriendo(), "sin el contenedor db corriendo (make up)"),
]
if os.environ.get("RESPALDOS_EXIGIR") == "1":  # el job respaldos del CI
    for omitir, razon in OMITIR:
        if omitir:
            raise RuntimeError(f"RESPALDOS_EXIGIR=1, pero no pueden correr: {razon}")
pytestmark = [pytest.mark.skipif(omitir, reason=razon) for omitir, razon in OMITIR]


def posix(ruta):
    """La ruta como la entienden bash y gpg. En Windows, los de Git Bash son programas MSYS: no
    entienden C:/... (la toman como relativa), sino /c/... En Linux, la ruta tal cual."""
    texto = Path(ruta).as_posix()
    if os.name == "nt" and texto[1:2] == ":":
        texto = "/" + texto[0].lower() + texto[2:]
    return texto


def psql(sql, base="postgres", usuario=None):
    """Una consulta en el contenedor db (por defecto, como superusuario en la base postgres)."""
    r = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            usuario or de_env("POSTGRES_USER", "postgres"),
            "-d",
            base,
            "-AtX",
            "-c",
            sql,
        ],
        cwd=RAIZ,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return r.stdout.strip()


@pytest.fixture(scope="module")
def gnupg(tmp_path_factory):
    casa = tmp_path_factory.mktemp("gnupg")
    casa.chmod(0o700)
    subprocess.run(
        [
            GPG,
            "--homedir",
            posix(casa),
            "--batch",
            "--passphrase",
            "",
            "--quick-gen-key",
            f"Prueba Respaldos <{LLAVE}>",
            "default",
            "default",
            "never",
        ],
        check=True,
        capture_output=True,
    )
    return casa


@pytest.fixture
def entorno(gnupg, tmp_path):
    return {
        **os.environ,
        "GNUPGHOME": posix(gnupg),
        "RESPALDO_DESTINATARIO": LLAVE,
        "RESPALDO_DIR": posix(tmp_path / "respaldos"),
        "RESPALDO_SIN_DISCO": "1",  # sin disco externo: solo en desarrollo y en los tests
        "_RESPALDO_DIR_PY": str(tmp_path / "respaldos"),
    }


def correr(script, *args, env):
    return subprocess.run([BASH, script, *args], cwd=RAIZ, env=env, capture_output=True, encoding="utf-8", timeout=300)


def carpeta_de(env):
    """La carpeta de respaldos, del lado de Python (la del entorno está en la forma de posix())."""
    return Path(env["_RESPALDO_DIR_PY"])


def respaldos(env):
    carpeta = carpeta_de(env)
    return sorted(carpeta.glob("hogar-*.dump.gpg")) if carpeta.exists() else []


def todo_en(env):
    carpeta = carpeta_de(env)
    return sorted(carpeta.iterdir()) if carpeta.exists() else []


def test_el_respaldo_queda_cifrado(entorno, tmp_path):
    r = correr(BACKUP, env=entorno)
    assert r.returncode == 0, r.stderr
    [archivo] = respaldos(entorno)
    assert not archivo.read_bytes().startswith(b"PGDMP")  # el formato custom de pg_dump empieza así
    claro = subprocess.run([GPG, "--batch", "--decrypt", posix(archivo)], env=entorno, capture_output=True)
    assert claro.returncode == 0 and claro.stdout.startswith(b"PGDMP")
    assert (carpeta_de(entorno) / ".ultimo-ok").exists()  # la marca que revisa el aviso de SSH
    # Control negativo: sin la llave privada no se lee
    vacia = tmp_path / "sin-llave"
    vacia.mkdir(mode=0o700)
    ajeno = subprocess.run(
        [GPG, "--batch", "--decrypt", posix(archivo)],
        env={**entorno, "GNUPGHOME": posix(vacia)},
        capture_output=True,
    )
    assert ajeno.returncode != 0


def test_el_respaldo_no_lleva_los_datos_de_axes_ni_de_sesiones(entorno):
    # ADR-0022: los datos de axes y las sesiones no salen del servidor. Su esquema sí va.
    assert correr(BACKUP, env=entorno).returncode == 0
    [archivo] = respaldos(entorno)
    claro = subprocess.run(
        [GPG, "--batch", "--decrypt", posix(archivo)], env=entorno, capture_output=True, check=True
    ).stdout
    indice = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "pg_restore", "-l"],
        cwd=RAIZ,
        input=claro,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    datos = [linea for linea in indice.splitlines() if " TABLE DATA public " in linea]
    assert any(" medicamento " in linea for linea in datos)  # control: las demás tablas sí llevan sus datos
    for tabla in ("axes_accessattempt", "axes_accesslog", "django_session"):
        assert f" TABLE public {tabla} " in indice
        assert not any(f" {tabla} " in linea for linea in datos)


def test_el_ensayo_cuadra_y_borra_su_base(entorno):
    assert correr(BACKUP, env=entorno).returncode == 0
    [archivo] = respaldos(entorno)
    r = correr(RESTORE, "--ensayo", posix(archivo), env=entorno)
    assert r.returncode == 0, r.stderr
    assert "cuadra" in r.stdout
    assert psql("SELECT count(*) FROM pg_database WHERE datname = 'hogar_ensayo'") == "0"


def test_el_ensayo_por_la_entrada_estandar(entorno):
    # Así lo usan el ensayo mensual y la vuelta atrás: descifrado en la PC del Administrador y
    # recibido por la entrada estándar. Ningún psql previo debe comerse el respaldo.
    assert correr(BACKUP, env=entorno).returncode == 0
    [archivo] = respaldos(entorno)
    claro = subprocess.run(
        [GPG, "--batch", "--decrypt", posix(archivo)], env=entorno, capture_output=True, check=True
    ).stdout
    r = subprocess.run(
        [BASH, RESTORE, "--ensayo", "-"], cwd=RAIZ, env=entorno, input=claro, capture_output=True, timeout=300
    )
    assert r.returncode == 0, r.stderr.decode("utf-8")
    assert "cuadra" in r.stdout.decode("utf-8")


def test_la_retencion_borra_los_de_mas_de_14_dias(entorno):
    carpeta = carpeta_de(entorno)
    carpeta.mkdir()
    viejo, reciente = carpeta / "hogar-20260101-000000.dump.gpg", carpeta / "hogar-20260102-000000.dump.gpg"
    for archivo, dias in ((viejo, 15), (reciente, 13)):
        archivo.write_bytes(b"respaldo anterior")
        antes = time.time() - dias * DIA
        os.utime(archivo, (antes, antes))
    assert correr(BACKUP, env=entorno).returncode == 0
    assert not viejo.exists()
    assert reciente.exists()
    assert len(respaldos(entorno)) == 2  # el reciente y el nuevo


def test_sin_destinatario_no_respalda(entorno):
    r = correr(BACKUP, env={**entorno, "RESPALDO_DESTINATARIO": ""})
    assert r.returncode != 0
    assert "RESPALDO_DESTINATARIO" in r.stderr
    assert todo_en(entorno) == []


def test_con_una_llave_que_no_esta_no_respalda(entorno):
    r = correr(BACKUP, env={**entorno, "RESPALDO_DESTINATARIO": "nadie@respaldos.test"})
    assert r.returncode != 0
    assert "llave pública" in r.stderr
    assert todo_en(entorno) == []  # ni un respaldo sin cifrar ni un archivo a medias


def test_si_pg_dump_falla_no_queda_ningun_archivo(entorno):
    r = correr(BACKUP, env={**entorno, "POSTGRES_DB": "no_existe"})
    assert r.returncode != 0
    assert "no_existe" in r.stderr  # el error de pg_dump, no el de un script que falta
    assert todo_en(entorno) == []


def test_si_falla_la_copia_al_disco_no_da_por_bueno_el_respaldo(entorno, tmp_path):
    # El disco está montado, pero la copia falla (lleno o en solo lectura): un mountpoint que dice
    # "montado" y un cp que falla, delante en el PATH. El script debe fallar y no escribir la marca.
    falsos = tmp_path / "falsos"
    falsos.mkdir()
    for programa, codigo in (("mountpoint", 0), ("cp", 1)):
        ruta = falsos / programa
        ruta.write_text(f"#!/bin/sh\nexit {codigo}\n", encoding="utf-8", newline="\n")
        ruta.chmod(0o755)
    disco = tmp_path / "disco"
    disco.mkdir()
    env = {
        **entorno,
        "RESPALDO_SIN_DISCO": "",
        "RESPALDO_DISCO": posix(disco),
        "PATH": os.pathsep.join([str(falsos), os.environ["PATH"]]),
    }
    r = correr(BACKUP, env=env)
    assert r.returncode != 0
    assert "no se pudo copiar al disco externo" in r.stderr
    assert len(respaldos(entorno)) == 1  # la copia local queda
    assert not (carpeta_de(entorno) / ".ultimo-ok").exists()  # el aviso de SSH lo mostrará


def test_sin_disco_montado_avisa_y_conserva_la_copia_local(entorno):
    # Sin RESPALDO_SIN_DISCO, una RESPALDO_DISCO vacía no salta la copia: usa /mnt/respaldos, que aquí
    # no está montado. En Git Bash no hay mountpoint, así que falla esa orden; en Linux, el caso real
    r = correr(BACKUP, env={**entorno, "RESPALDO_SIN_DISCO": "", "RESPALDO_DISCO": ""})
    assert r.returncode != 0
    assert "disco externo" in r.stderr
    assert len(respaldos(entorno)) == 1
    assert not (carpeta_de(entorno) / ".ultimo-ok").exists()  # el aviso de SSH lo mostrará


def test_no_restaura_sobre_una_base_con_tablas(entorno):
    psql("DROP DATABASE IF EXISTS hogar_prueba_llena WITH (FORCE)")
    psql("CREATE DATABASE hogar_prueba_llena OWNER app_owner")
    try:
        psql("CREATE TABLE ya_estaba (id int)", base="hogar_prueba_llena", usuario="app_owner")
        assert correr(BACKUP, env=entorno).returncode == 0
        [archivo] = respaldos(entorno)
        r = correr(RESTORE, posix(archivo), env={**entorno, "RESTAURAR_BASE": "hogar_prueba_llena"})
        assert r.returncode != 0
        assert "no está vacía" in r.stderr
    finally:
        psql("DROP DATABASE IF EXISTS hogar_prueba_llena WITH (FORCE)")


VACIA = "hogar_prueba_vacia"


def restaurar_en_base_aparte(entorno):
    """La restauración normal (la de la vuelta atrás y la de una falla), en una base vacía aparte."""
    psql(f"DROP DATABASE IF EXISTS {VACIA} WITH (FORCE)")
    psql(f"CREATE DATABASE {VACIA} OWNER app_owner")
    assert correr(BACKUP, env=entorno).returncode == 0
    [archivo] = respaldos(entorno)
    return correr(RESTORE, posix(archivo), env={**entorno, "RESTAURAR_BASE": VACIA})


def test_restaura_en_una_base_vacia_con_sus_permisos(entorno):
    try:
        r = restaurar_en_base_aparte(entorno)
        assert r.returncode == 0, r.stderr
        # Los permisos de la base no van en el respaldo: el script pone los de db/init/01_roles.sh
        permisos = psql(f"SELECT datacl FROM pg_database WHERE datname = '{VACIA}'")
        assert "app_user=c/" in permisos
        assert not permisos.lstrip("{").startswith("=") and ",=" not in permisos  # PUBLIC sin CONNECT
        tablas = "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'"
        original = psql(tablas, base=de_env("POSTGRES_DB", "hogar"), usuario="app_owner")
        assert psql(tablas, base=VACIA, usuario="app_owner") == original
    finally:
        psql(f"DROP DATABASE IF EXISTS {VACIA} WITH (FORCE)")


def test_la_restauracion_conserva_la_inmutabilidad_de_movimiento(entorno):
    # ADR-0006 y ADR-0012 siguen valiendo en la base restaurada (necesita el esquema de TK-01)
    try:
        r = restaurar_en_base_aparte(entorno)
        assert r.returncode == 0, r.stderr
        for permiso in ("UPDATE", "DELETE", "TRUNCATE"):
            sql = f"SELECT has_table_privilege('app_user', 'movimiento', '{permiso}')"
            assert psql(sql, base=VACIA, usuario="app_owner") == "f"
        sql = "SELECT has_table_privilege('app_user', 'movimiento', 'INSERT')"
        assert psql(sql, base=VACIA, usuario="app_owner") == "t"  # control: sí puede registrar
        sql = "SELECT count(*) FROM pg_trigger WHERE tgname = 'tg_movimiento_inmutable' AND NOT tgisinternal"
        assert psql(sql, base=VACIA, usuario="app_owner") == "1"
        # Los privilegios por defecto de las tablas futuras (accounts/0002_privilegios)
        sql = "SELECT count(*) FROM pg_default_acl"
        assert psql(sql, base=VACIA) == psql(sql, base=de_env("POSTGRES_DB", "hogar"))
    finally:
        psql(f"DROP DATABASE IF EXISTS {VACIA} WITH (FORCE)")
```

> **Notas sobre estos tests:**
> - **Antes de TK-01**, los 2 tests del ensayo fallan con `relation "v_conciliacion_existencia" does not exist`, y el de la inmutabilidad, porque no existe `movimiento`. No es un problema: HB-10 va después de TK-01.
> - **No corren donde pueda estar la base real:** se omiten con las mismas señales del candado del paso 4, leídas del `.env` y del entorno de la sesión: un `HOGAR_NOMBRE` que no es el de la demo (o vacío con `config.settings.prod`), `RESPALDO_DESTINATARIO` definida o `/etc/cron.d/hogar`. En el servidor del hogar serían superusuario sobre el clúster de producción.
> - **En Windows**, los tests llaman a bash por su ruta completa (`BASH`) y le pasan las rutas en la forma `/c/...` (`posix()`). Con `bash` a secas, Windows ejecutaría el de WSL, que no recibe las variables de entorno, y el `gpg` de Git Bash no entiende `C:/...`. Si el PATH da el `bash` de WSL o el `gpg` de Gpg4win, los tests se omiten con su razón: córrelos desde Git Bash.
> - **En Git Bash no hay `mountpoint`**, así que `test_sin_disco_montado_avisa_y_conserva_la_copia_local` pasa porque falla esa orden, no porque el disco falte. En Linux sí prueba el caso real. `test_si_falla_la_copia_al_disco_no_da_por_bueno_el_respaldo` pone delante en el `PATH` un `mountpoint` que responde "montado" y un `cp` que falla, así que prueba el caso del disco lleno en los 2 sistemas.
> - **Tu base de desarrollo solo se lee**, para el respaldo. Los tests crean 3 bases aparte (`hogar_ensayo`, `hogar_prueba_llena` y `hogar_prueba_vacia`) y las borran al terminar. Nunca restauran sobre `hogar`.
> - **En el CI** los corre el *job* `respaldos` (paso 4), con los contenedores levantados y `RESPALDOS_EXIGIR=1`: si algo los omitiría, la recolección falla en vez de quedar en verde sin haberlos corrido. El *job* `herramientas` los omite, porque no tiene el contenedor `db`.

### 3.2 `tests/test_candado.py`

Prueba el candado del paso 4 con el `make` del equipo y, en el *job* `respaldos`, con el de `ubuntu-latest` (GNU Make 4.3, el del servidor). Usa solo `make candado`, que evalúa el candado y no hace nada más: nunca `make reset` ni `make mock`.

```python
"""El candado de make reset y make mock (HB-10, paso 4), con el make del equipo o del CI.

Prueba el target candado, que evalúa el candado y no hace nada más: nunca make reset ni make mock.
Cada caso usa un .env propio en una carpeta temporal (make -C), con el Makefile del repositorio.
Sin make o sin Makefile, se omite. /etc/cron.d/hogar no se puede simular sin root: no se prueba.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MAKE = shutil.which("make")
DEMO = "Hogar Gerontológico Demo"
SENALES = ("HOGAR_NOMBRE", "RESPALDO_DESTINATARIO", "DJANGO_SETTINGS_MODULE")

pytestmark = pytest.mark.skipif(
    not (MAKE and (RAIZ / "Makefile").exists()), reason="sin make o sin el Makefile de TK-01"
)


@pytest.mark.parametrize(
    ("archivo_env", "sesion", "pasa"),
    [
        ({"DJANGO_SETTINGS_MODULE": "config.settings.local"}, {}, True),
        ({"HOGAR_NOMBRE": DEMO, "DJANGO_SETTINGS_MODULE": "config.settings.prod"}, {}, True),
        ({"DJANGO_SETTINGS_MODULE": "config.settings.prod"}, {}, False),
        ({"HOGAR_NOMBRE": "Hogar San José", "DJANGO_SETTINGS_MODULE": "config.settings.local"}, {}, False),
        (
            {
                "HOGAR_NOMBRE": DEMO,
                "RESPALDO_DESTINATARIO": "pendiente",
                "DJANGO_SETTINGS_MODULE": "config.settings.prod",
            },
            {},
            False,
        ),
        (
            {"HOGAR_NOMBRE": DEMO, "DJANGO_SETTINGS_MODULE": "config.settings.local"},
            {"RESPALDO_DESTINATARIO": "ensayo@respaldos.test"},
            False,
        ),
    ],
    ids=["desarrollo", "demo", "prod-sin-nombre", "otro-nombre", "con-respaldos", "respaldos-en-la-sesion"],
)
def test_el_candado(tmp_path, archivo_env, sesion, pasa):
    (tmp_path / ".env").write_text(
        "".join(f"{k}={v}\n" for k, v in archivo_env.items()), encoding="utf-8", newline="\n"
    )
    entorno = {k: v for k, v in os.environ.items() if k not in SENALES}
    r = subprocess.run(
        [MAKE, "-s", "-C", str(tmp_path), "-f", str(RAIZ / "Makefile"), "candado"],
        env={**entorno, **sesion},
        capture_output=True,
        encoding="utf-8",
    )
    salida = r.stdout + r.stderr
    assert (r.returncode == 0) is pasa, salida
    if not pasa:
        assert "esto parece el servidor del hogar" in salida
```

### 3.3 Comandos con resultado esperado (van en el PR)

Las partes B y C no se pueden probar con pytest: son la configuración de 2 equipos. Su prueba son los comandos de la sección 5, con su salida en el PR, como en HB-01 y HB-02.

### 3.4 Lo que ya se verificó (2026-11-26)

Se copió el código de referencia de esta guía a archivos temporales del repositorio, que después se borraron. Se corrió en Windows con Git Bash, PostgreSQL 17 en Docker, pytest 9.2.0 y ruff de `requirements-dev.txt`:

| Verificación | Resultado |
|---|---|
| Los 13 tests de `test_respaldos.py` sin los scripts (rojo) | 13 failed, todos porque el script no existe |
| Los 13 tests con los scripts de referencia | 10 passed. Fallan solo los que necesitan el esquema de TK-01: los 2 del ensayo (`v_conciliacion_existencia`) y el de la inmutabilidad (`relation "movimiento" does not exist`). Sin la comprobación de la vista, los 2 del ensayo pasan |
| `test_si_falla_la_copia_al_disco_no_da_por_bueno_el_respaldo` con `cp ... && mv ...` en la misma línea | Falla: bash sigue tras el `cp` fallido y escribiría la marca. Con el `if ! cp` del paso 2, pasa |
| `tests/test_candado.py` con el candado y el *target* `candado` de la guía (GNU Make 3.81) | 6 passed. En el CI correrá con el GNU Make 4.3 de `ubuntu-latest`, el del servidor |
| `test_el_ensayo_por_la_entrada_estandar` sin los `</dev/null` | Falla con `pg_restore: error: input file is too short`: el primer `psql` se come el respaldo |
| `test_el_respaldo_no_lleva_los_datos_de_axes_ni_de_sesiones` sin `--exclude-table-data` | Falla: el respaldo llevaría las filas de `axes` y de las sesiones |
| ShellCheck 0.10.0 (`-x`) sobre los 3 scripts | Sin avisos |
| ruff (`ruff.toml`) sobre el test | Sin errores ni cambios de formato |
| `pg_dump` de `app_owner` restaurado en una base nueva | Quedan de `app_owner` el esquema `public` y las extensiones. `app_user` conserva sus permisos y los privilegios por defecto. Las 21 tablas cuadran, y con los permisos de base repuestos, la base queda igual que `hogar` |
| `check --deploy` con `config.settings.prod` | `System check identified no issues (3 silenced).` |
| Candado de `make reset` y `make mock` (GNU Make 3.81, con `HOGAR_NOMBRE` en un `.env` incluido) | Corre sin nombre con `config.settings.local` y con el de la demo con `config.settings.prod`; se niega sin nombre con `config.settings.prod` y con otro nombre. Con el nombre de la demo por la línea de comandos en Windows se niega, por la codificación (nota del paso 4) |
| El YAML del *job* `respaldos` (paso 4) | Parsea, pero no se corrió en un *runner*: se comprueba en el primer PR de HB-10 |
| El ensayo cuando un conteo falla | Sale con error y no dice "cuadra": los conteos van a variables antes de compararlos |
| La limpieza de `axes` del cron (`axes_reset_logs --age 30`, `axes_reset_failure_logs --age 30` y `axes_reset`) | Corre en el contenedor `web` de django-axes 9.1.0, sin errores |
| El candado con `RESPALDO_DESTINATARIO` exportada en la sesión | Se niega, y tras `unset` deja pasar: por eso el paso 6 hace `make reset && make mock` antes del `export` |
| `COMPOSE_PROJECT_NAME=hogar-demo` en el `.env` (paso 15) | `docker compose config` da `name: hogar-demo`: tiene prioridad sobre `name: hogar` |

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| Nunca hay un respaldo sin cifrar, ni a medias | `test_con_una_llave_que_no_esta_no_respalda` y `test_si_pg_dump_falla_no_queda_ningun_archivo` |
| La restauración por la entrada estándar funciona | `test_el_ensayo_por_la_entrada_estandar` |
| El respaldo no lleva los datos de `axes` ni de sesiones (ADR-0022) | `test_el_respaldo_no_lleva_los_datos_de_axes_ni_de_sesiones` |
| Tras restaurar, `movimiento` sigue siendo inmutable para `app_user` | `test_la_restauracion_conserva_la_inmutabilidad_de_movimiento` |
| La CA está cifrada en la memoria USB y su llave no queda en la PC del Administrador | Paso 9: `ls "$CAROOT"` muestra solo `rootCA.pem` |
| Ni el servidor ni el repositorio tienen la llave privada GPG ni `rootCA-key.pem` | En el servidor, `gpg --list-secret-keys` no muestra nada y `find ~ / -name rootCA-key.pem 2>/dev/null` tampoco. En el repositorio, `git status` no muestra `*.asc` ni `*.pem` |
| La frase GPG no está junto a la memoria USB | Paso 14 |
| En el servidor no se puede borrar la base ni cargar el mock con `make` | `tests/test_candado.py` y `make candado` en el servidor (sección 5), nunca `make mock` |
| Hay una copia fuera del hogar | Paso 12.7 y sección 8.3 |
| Un respaldo fallido se ve al entrar por SSH | Paso 12.3: con el disco desconectado, el aviso aparece al día siguiente |
| El disco del servidor está cifrado (LUKS) y la cabecera tiene copia | `lsblk -f` muestra `crypto_LUKS` (paso 7.1); la copia está en la memoria USB |
| Los tests de los respaldos corren en cada PR | El *job* `respaldos` del CI, en verde |
| Solo `nginx` publica puertos, y el router no abre ninguno | `docker compose ps` (paso 10) y el panel del router |
| `check --deploy` sin advertencias en el servidor | Paso 10 |
| La restauración está probada, no solo escrita | El ensayo del paso 12.6 cuadra, y la vuelta atrás del paso 6 funcionó |
| Los scripts pasan ShellCheck | `python scripts/verificar.py --herramientas`, que lo corre desde el paso 4 (también en el CI) |
| `.env` del servidor con permiso `600` | `stat -c %a /opt/hogar/.env` responde `600` |

---

## 5. Verificación: comandos y resultado esperado

```bash
# --- Parte A, en tu equipo ---
# 1. Tests de los scripts y de las herramientas
python -m pytest tests -q -p no:cacheprovider            # todos pasan: los 13 de test_respaldos.py y los 6 de test_candado.py
python scripts/verificar.py --herramientas               # sin errores, ShellCheck incluido
# 2. El candado (paso 4) y el ensayo completo con la vuelta atrás (paso 6), con su resultado esperado

# --- Parte B, en el servidor del hogar (después de la línea de POSTGRES_USER y POSTGRES_DB del paso 10) ---
# 3. Contenedores y configuración
docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"   # nginx con 80 y 443; web y db sin publicar
docker compose exec web python manage.py check --deploy  # System check identified no issues (3 silenced).
stat -c %a .env                                          # 600
lsblk -f | grep -c crypto_LUKS                           # 1: el disco del servidor, cifrado
grep -c cambia-esto .env                                 # 0
grep -c '^HOGAR_NOMBRE=Hogar Gerontológico Demo$' .env  # 0 (solo la línea de la variable: el comentario también nombra la demo)
make candado                                             # se niega: "make candado: esto parece el servidor del hogar ..."; nunca make mock
# 4. HTTPS
curl -sI http://localhost/ | grep -i location            # Location: https://localhost/
curl -sI --cacert ~/rootCA-hogar.pem https://192.168.1.50/accounts/login/ | head -1   # HTTP/2 200, sin -k
openssl x509 -noout -enddate -in nginx/certs/local.pem   # notAfter: dentro de 2 años y 3 meses
# 5. Datos
docker compose exec -T db psql -U app_owner -d "$POSTGRES_DB" -AtX -c "SELECT nombre FROM entidad WHERE tipo = 'HOGAR'"   # el nombre real
docker compose exec -T db psql -U app_owner -d "$POSTGRES_DB" -AtX -c "SELECT count(*) FROM v_conciliacion_existencia"   # 0
docker compose exec -T db psql -U app_owner -d "$POSTGRES_DB" -AtX -c "SELECT count(*) FROM usuario WHERE username LIKE '%.demo'"   # 0
# 6. Respaldos y secretos
ls -l /var/backups/hogar /mnt/respaldos/hogar            # el respaldo de la noche en los 2 lugares
tail -3 /var/log/hogar/respaldo.log                      # ... respaldo: /var/backups/hogar/hogar-AAAAMMDD-0230NN.dump.gpg
gpg --list-secret-keys                                   # nada: la llave privada no está en el servidor
find ~ /opt/hogar -name 'rootCA-key.pem' 2>/dev/null     # nada: la llave de la CA no está en el servidor
# 7. Ensayo de restauración: paso 12.6, en la PC del Administrador -> "ensayo: cuadra."

# --- Parte C, en la máquina de la demo ---
# 8. La demo
make candado                                             # candado: deja pasar (desarrollo o demo)
make reset && make mock                                  # el resumen del mock: 28 movimientos, 13 existencias...
docker compose exec web python manage.py check --deploy  # System check identified no issues (3 silenced).
```

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] Las decisiones abiertas de la sección 0.4 (4 y 5) quedaron anotadas con su respuesta.
- [ ] Cada fila de la sección 0.5 está cerrada con su evidencia en el PR, o anotada como pendiente con su motivo (las de LUKS y del servidor real, si el PR se abre antes de la parte B).
- [ ] El *job* `respaldos` del CI aparece en el PR, corre los 13 tests de los respaldos y los 6 casos del candado, y queda en verde.
- [ ] La descripción del PR incluye la salida de `docker compose ps`, de `check --deploy` y del ensayo de restauración del servidor, sin IPs públicas ni datos de residentes.
- [ ] Capturas: el login en un celular del hogar con el candado válido, y la demo local con los datos del mock.
- [ ] Si el código de los scripts cambió respecto de la referencia (pasos 2 a 4), esta guía está actualizada.

---

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `./scripts/migrate.sh: line N: ...: command not found` | `HOGAR_NOMBRE` con espacios y TK-01 sin integrar | TK-01, paso 1: la lectura línea por línea |
| `web` se reinicia sin parar, y su log dice `Falta HOGAR_NOMBRE` | `config.settings.prod` sin la variable | Paso 8, y `docker compose up -d` |
| `400 Bad Request` al abrir `https://192.168.1.50` | La IP no está en `ALLOWED_HOSTS` | Paso 8 y `docker compose up -d web` |
| `403 CSRF verification failed` en el login | `CSRF_TRUSTED_ORIGINS` sin `https://192.168.1.50` exacto | Paso 8 |
| El navegador dice que la conexión no es privada | Falta la CA en ese dispositivo, o el certificado no incluye esa IP | Paso 9. Revisa la IP con `openssl x509 -noout -text -in nginx/certs/local.pem \| grep -A1 "Alternative Name"` |
| La PC del Administrador confía en `localhost` pero no en la IP del hogar | `mkcert` usó la CA de desarrollo: faltó `export CAROOT="$HOME/ca-hogar"` | Paso 9, con la línea de `CAROOT` |
| Android instaló el certificado, pero Chrome no confía | Se instaló como certificado "de VPN y aplicaciones" o "de usuario" | Paso 9: debe ser "Certificado de CA" |
| El iPhone sigue sin confiar | Falta activar la confianza total | Paso 9, segundo menú |
| El servidor no vuelve tras un corte de luz o un reinicio | Espera la frase de LUKS | Escríbela en su teclado, o por SSH en el puerto 2222 (sección 8.9) |
| El *job* `respaldos` falla con `RESPALDOS_EXIGIR=1, pero no pueden correr` | Faltó levantar `db`, o `.env` no trae el Hogar de la demo | Los pasos del *job* (paso 4) y la descomentación de `HOGAR_NOMBRE` de TK-01 |
| `permission denied while trying to connect to the Docker daemon` | `hogar` no está en el grupo `docker`, o no volviste a entrar | Paso 7.6, y sal y vuelve a entrar por SSH |
| `backup_db: no está la llave pública` | La llave no se importó en el usuario que corre el cron | Paso 12.2, como `hogar` (no con `sudo`) |
| `backup_db: el disco externo no está montado`, o el aviso al entrar por SSH | El disco se desconectó, o `fstab` tiene otro UUID | `lsblk -f`, `sudo mount -a`, `mountpoint /mnt/respaldos` y `make backup` |
| El cron no deja nada en `/var/log/hogar/` | El archivo de `/etc/cron.d` tiene punto en el nombre, no es de `root` o le falta el salto de línea final | Paso 12.5, con `install -m 644 -o root` y sin `.cron` en el nombre |
| `pg_restore: error: input file is too short` al restaurar con `-` | Un `psql` se comió la entrada estándar | Los `</dev/null` del paso 3 |
| `ensayo: NO cuadra` en una tabla de negocio | Alguien registró algo entre el respaldo y el ensayo | Repite con un respaldo nuevo (sección 8.3) |
| `restore_db: la base hogar no está vacía` | Es la protección del script | Para volver atrás a propósito, sección 8.2 |
| `mkcert` dice `failed to read the CA key` al renovar | La llave de la CA se borró de la PC, como pide el paso 9 | Sección 8.5: recupérala del resguardo |
| `make reset` o `make mock` se niegan en la demo o en desarrollo, con el nombre de la demo | Tu `.env` tiene `RESPALDO_DESTINATARIO` definida, o existe `/etc/cron.d/hogar`: son señales del servidor (paso 4) | Quítala del `.env`: solo el servidor la lleva |
| El Hogar del servidor se llama "Hogar Gerontológico Demo" | No se cambió `HOGAR_NOMBRE` antes del primer `make migrate` | La migración no se repite: con el servidor recién instalado y sin datos, `docker compose down -v`, corrige `.env` y vuelve al paso 10. Con datos, cambia el nombre desde la base, con cuidado |
| `make reset` o `make mock` se niegan aunque `.env` tiene el nombre de la demo | `.env` con fin de línea CRLF: el valor arrastra un `\r` | `sed -i 's/\r$//' .env` |
| `make reset` o `make mock` se niegan en tu equipo de desarrollo o en la demo | Tu `.env` tiene un `HOGAR_NOMBRE` distinto del de la demo, o en Windows lo pasaste por la línea de comandos | Coméntalo o pon el de la demo en `.env` (nota del paso 4) |
| `make reset` se niega durante el ensayo del paso 6 | Exportaste `RESPALDO_DESTINATARIO` en la sesión: el candado la toma como señal del servidor | `unset RESPALDO_DESTINATARIO`, o haz `make reset && make mock` antes del `export` (paso 6). Nunca desactives el candado |
| `backup_db: el disco externo no está montado en /mnt/respaldos` en tu equipo de desarrollo | Sin `RESPALDO_SIN_DISCO=1`, el respaldo exige el disco | `RESPALDO_SIN_DISCO=1`, como en el paso 6. Nunca en el servidor |
| El panel o el login se ven sin estilos | Faltan los estáticos, por ejemplo tras un `down -v` | `make static` |

---

## 8. Operación (después del ticket)

Esta sección es el manual del servidor. Se queda aquí, se mantiene al día y la lee quien lo administre. Los comandos del servidor suponen `cd /opt/hogar` y la línea de `POSTGRES_USER` y `POSTGRES_DB` del paso 10.

### 8.1 Actualizar a una versión nueva

Hazlo cuando nadie esté usando el sistema, con la PC del Administrador a la mano.

```bash
ssh hogar@192.168.1.50
cd /opt/hogar
git rev-parse --short HEAD > ~/commit-anterior     # para volver atrás
docker compose exec -T web python manage.py showmigrations --plan > ~/migraciones-antes   # también las de las dependencias
make backup && ls -t /var/backups/hogar/*.dump.gpg | head -1 > ~/respaldo-anterior \
  && git pull origin main \
  && make actualizar \
  && docker compose restart nginx \
  && sudo install -m 644 -o root -g root scripts/hogar.cron /etc/cron.d/hogar   # por si la versión cambió las tareas
```

Si `make backup` falla, nada más corre: arregla el respaldo antes de actualizar.
- `make actualizar` (TK-01) hace `up -d --build`, `migrate.sh` y `collectstatic`, pero no recrea `nginx` cuando solo cambia `nginx/default.conf`: por eso el `restart`.
- El cron vive fuera del repositorio (`/etc/cron.d/hogar`): el `install` lo pone al día.
- El aviso de SSH y `logrotate` (paso 12.3) tampoco viven en el repositorio. Si la versión los cambia en esta guía, repite ese paso.

Después, la prueba de humo del paso 13, al menos los puntos 1 y 2. Si algo falla, la sección 8.2.

Si la versión trae migraciones que tocan datos existentes, lee antes su nota en la guía del ticket. Por ejemplo, `catalogo/0004` pide antes una consulta de presentaciones duplicadas (guía de HB-09, nota del hallazgo 8). En una primera instalación esa consulta no aplica: la base nace vacía.

### 8.2 Volver atrás

Primero, mira si la actualización aplicó migraciones, también las de las dependencias (por ejemplo, una versión nueva de `django-axes`). El `git diff` de `migrations/` no las ve:

```bash
docker compose exec -T web python manage.py showmigrations --plan | diff ~/migraciones-antes - && echo "sin migraciones nuevas"
```

**Si no hubo migraciones nuevas**, basta con volver al código anterior:

```bash
git checkout "$(cat ~/commit-anterior)" && make actualizar && docker compose restart nginx
```

**Si hubo migraciones nuevas**, vuelve también la base al respaldo de antes de actualizar. Antes de borrar nada, guarda el estado actual y comprueba que el respaldo de destino se lee.

1. En el servidor, detén la aplicación y respalda el estado actual. Ese respaldo guarda lo registrado después de la actualización:

   ```bash
   docker compose stop web && make backup
   ```

2. En la PC del Administrador, restaura el respaldo de destino en la base de ensayo, para comprobar que se descifra y se restaura completo, no solo su índice:

   ```bash
   ssh -n hogar@192.168.1.50 'cat "$(cat ~/respaldo-anterior)"' | gpg --decrypt \
     | ssh hogar@192.168.1.50 'cd /opt/hogar && ./scripts/restore_db.sh --ensayo -'
   ```

   Debe mostrar `restaurado en hogar_ensayo`. Que después diga `NO cuadra` es lo esperado, porque la base en uso tiene lo registrado después. Si no aparece `restaurado en hogar_ensayo`, **detente**: la base sigue intacta. Arregla primero el respaldo (la frase, la llave o el archivo).

3. En el servidor, vacía la base y vuelve al código anterior:

   ```bash
   docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres \
       -c "DROP DATABASE \"$POSTGRES_DB\" WITH (FORCE)" -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER app_owner"
   git checkout "$(cat ~/commit-anterior)"
   ```

En la PC del Administrador, restaura el respaldo de antes de la actualización. `restore_db.sh` repone también los permisos de la base:

```bash
ssh -n hogar@192.168.1.50 'cat "$(cat ~/respaldo-anterior)"' | gpg --decrypt \
  | ssh hogar@192.168.1.50 'cd /opt/hogar && ./scripts/restore_db.sh -'
```

Y de nuevo en el servidor: `make actualizar && docker compose restart nginx`, y la prueba de humo del paso 13.

Lo que se registró entre el respaldo de antes de actualizar y la vuelta atrás no está en la base restaurada, pero sí en el respaldo del punto 1. Para recuperarlo:

1. En el servidor, crea una base aparte, vacía:

   ```bash
   docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE hogar_consulta OWNER app_owner"
   ```

2. En la PC del Administrador, restaura en ella el respaldo del punto 1:

   ```bash
   ULTIMO=$(ssh hogar@192.168.1.50 'ls -t /var/backups/hogar/*.dump.gpg | head -1')
   ssh -n hogar@192.168.1.50 "cat $ULTIMO" | gpg --decrypt \
     | ssh hogar@192.168.1.50 'cd /opt/hogar && RESTAURAR_BASE=hogar_consulta ./scripts/restore_db.sh -'
   ```

3. En el servidor, lista los Movimientos que faltan, más nuevos que el último de la base restaurada:

   ```bash
   docker compose exec -T db psql -U app_owner -d hogar_consulta -c "SELECT * FROM movimiento WHERE fecha_hora > '<fecha_hora del último Movimiento de la base restaurada>' ORDER BY fecha_hora"
   ```

4. Vuelve a registrarlos desde la aplicación, como Movimientos nuevos (los Movimientos no se editan ni se copian por SQL). En su `nota`, anota la fecha y el usuario originales, para conservar la trazabilidad.
5. Borra la base aparte: `docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE hogar_consulta WITH (FORCE)"`.

Al terminar, `git switch main` deja el repositorio listo para la siguiente actualización, que se hace cuando el problema esté corregido en `main`.

### 8.3 Cada mes: copia fuera del hogar y ensayo de restauración

El primer lunes de cada mes:

**1. La copia al disco de fuera.** Conecta el disco de fuera al servidor:

```bash
lsblk -f                                           # el disco con la etiqueta respaldos-fuera (por ejemplo, sdc1)
sudo mkdir -p /mnt/respaldos-fuera && sudo mount /dev/sdc1 /mnt/respaldos-fuera
mkdir -p /mnt/respaldos-fuera/hogar             # el disco es de hogar (paso 12.7): sin sudo
find /var/backups/hogar/.ultimo-ok -mmin -1560 | grep -q . || echo "AVISO: el último respaldo completo tiene más de 26 horas: haz uno (make backup) antes de copiar"
ULTIMO="$(ls -t /var/backups/hogar/*.dump.gpg | head -1)"
cp "$ULTIMO" /mnt/respaldos-fuera/hogar/
sha256sum "$ULTIMO" /mnt/respaldos-fuera/hogar/"$(basename "$ULTIMO")"   # las 2 sumas iguales, y leídas como hogar: así se lee al restaurar
ls -t /mnt/respaldos-fuera/hogar/*.dump.gpg | tail -n +13 | xargs -r rm   # se conservan 12 meses
sudo umount /mnt/respaldos-fuera
```

Desconéctalo y llévatelo de vuelta fuera del hogar.

**2. El ensayo**, en la PC del Administrador:

```bash
ssh hogar@192.168.1.50 'cd /opt/hogar && make backup'
ULTIMO=$(ssh hogar@192.168.1.50 'ls -t /var/backups/hogar/*.dump.gpg | head -1')
ssh -n hogar@192.168.1.50 "cat $ULTIMO" | gpg --decrypt \
  | ssh hogar@192.168.1.50 'cd /opt/hogar && ./scripts/restore_db.sh --ensayo -'
# ensayo: cuadra. ...
```

**3. El disco conectado:** revisa que tenga los respaldos de los últimos días con `ssh hogar@192.168.1.50 'ls -lt /mnt/respaldos/hogar | head'`.

### 8.4 Restaurar tras una falla del servidor

Si el servidor se pierde, en un equipo nuevo:
1. Repite los pasos 7 y 8, con la misma IP y el disco cifrado con LUKS.
2. Emite el certificado en la PC del Administrador con la misma CA, recuperando su llave del resguardo como en la sección 8.5. Si esa PC también se perdió, recupera del resguardo la carpeta completa. Así los dispositivos no necesitan instalar nada.
3. `make up` y `make static`, **sin** `make migrate`: la base debe quedar vacía para restaurar.
4. Conecta al servidor nuevo el disco conectado o, si se perdió, el de fuera del hogar, y móntalo como en la sección 8.3. Los discos son ext4: Windows no los lee, por eso se montan en el servidor. Desde la PC del Administrador, restaura el más reciente: `ssh -n hogar@192.168.1.50 'cat <ruta-del-respaldo>' | gpg --decrypt | ssh hogar@192.168.1.50 'cd /opt/hogar && ./scripts/restore_db.sh -'`.
5. `make migrate`: no aplica nada si el código es el mismo del respaldo.
6. El paso 12 (llave pública, discos, aviso y cron) y la prueba de humo del paso 13.

### 8.5 Renovar el certificado

`mkcert` emite el certificado por 2 años y 3 meses. Un mes antes de la fecha del paso 9, en la PC del Administrador:

```bash
export CAROOT="$HOME/ca-hogar"
gpg --decrypt /e/ca-hogar.tar.gz.gpg | tar -C "$HOME" -xzf - ca-hogar/rootCA-key.pem   # la llave, desde el resguardo
mkcert -cert-file local.pem -key-file local-key.pem 192.168.1.50 localhost 127.0.0.1
rm "$CAROOT/rootCA-key.pem"                                                        # y fuera otra vez
scp local.pem local-key.pem hogar@192.168.1.50:/opt/hogar/nginx/certs/ && rm local.pem local-key.pem
ssh hogar@192.168.1.50 'chmod 600 /opt/hogar/nginx/certs/local-key.pem && cd /opt/hogar && docker compose restart nginx'
```

La CA no cambia, así que los dispositivos no necesitan nada.

### 8.6 Un dispositivo nuevo

Instálale `rootCA.pem` de la CA del hogar (paso 9) y crea su usuario en `/admin/`, con un solo grupo (paso 11).

### 8.7 Actualizaciones de seguridad

- **Ubuntu:** `unattended-upgrades` instala los parches solo. Una vez al mes, `sudo apt full-upgrade`, y `sudo reboot` si lo pide (`/var/run/reboot-required`). Tras el reinicio, el servidor espera la frase de LUKS (sección 8.9), y después los contenedores arrancan solos (`restart: unless-stopped`).
- **nginx:** su versión es fija (ADR-0026). Cada 3 meses, revisa la estable vigente y súbela con un PR que cambie la etiqueta en `docker-compose.yml` y en el readme (sección 2.4.1).
- **Dependencias de Python:** cada 3 meses, `docker run --rm -v "$PWD/app:/app" python:3.12-slim sh -c "pip install -q pip-audit && pip-audit -r /app/requirements.txt"` (readme, sección 2.5). Lo que reporte se corrige con un PR, no en el servidor.

### 8.8 Desbloquear una cuenta

Tras 5 intentos fallidos, `django-axes` bloquea la cuenta 15 minutos (ADR-0022). Para desbloquearla antes:

```bash
docker compose exec web python manage.py axes_reset_username <usuario>
```

### 8.9 Arranque del servidor (LUKS)

Con el disco cifrado, el servidor no arranca solo: tras un corte de luz o un `reboot`, espera la frase de LUKS.

- **En el teclado del servidor:** escribe la frase cuando la pida.
- **Por SSH, si configuraste el desbloqueo del paso 7.1:** `ssh -p 2222 root@192.168.1.50` desde la PC del Administrador. Al entrar pide la frase directamente.

Después, Docker y los contenedores arrancan solos (`restart: unless-stopped`). Al arrancar así, Docker no respeta el orden de `depends_on`: `nginx` puede reiniciarse un par de veces hasta que `web` esté listo. Comprueba con `docker compose ps` al minuto, y si `nginx` sigue reiniciándose, `docker compose restart nginx`. Después entra al login. Si el servidor estuvo apagado a la hora del respaldo, haz uno a mano con `make backup`; el aviso de SSH también lo recordará.

### 8.10 Calendario

| Cada | Qué | Quién | Dónde |
|---|---|---|---|
| Día, 02:30 | Respaldo cifrado, local y en el disco conectado | El cron | `/var/log/hogar/respaldo.log` |
| Día, 03:15 | `clearsessions` (sesiones vencidas) | El cron | `/var/log/hogar/sesiones.log` |
| Domingo, 03:00 | Limpieza de `axes`: registros de acceso y de fallos de más de 30 días, e intentos fallidos | El cron | `/var/log/hogar/axes.log` |
| Cada entrada por SSH | El aviso si el último respaldo completo tiene más de 26 horas | El servidor | Paso 12.3 |
| Cada arranque o corte de luz | Escribir la frase de LUKS | El Administrador | Sección 8.9 |
| Mes, primer lunes | Copia al disco de fuera, ensayo de restauración y revisión del disco conectado | El Administrador | Sección 8.3 |
| Mes | `apt full-upgrade` y reinicio si lo pide | El Administrador | Sección 8.7 |
| 3 meses | Versión de nginx y `pip-audit` | El desarrollador | Sección 8.7 |
| 2 años | Renovar el certificado, un mes antes de vencer | El Administrador | Sección 8.5 |
