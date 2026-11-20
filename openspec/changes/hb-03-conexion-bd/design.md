# Design

## Context

HB-01 dejó `db` con `app_owner` (con `CREATEDB` en desarrollo) y `app_user`, y `GRANT app_user TO app_owner`. HB-02 dejó `web` con el backend `dummy`. La base local nunca se ha migrado. La motivación está en `proposal.md`, y el comportamiento, en `specs/`.

El código de la guía se ensayó en contenedores desechables con PostgreSQL 17 y las versiones de este diseño. `migrate.sh`, la reversión de `0002` y 11 de los 12 tests funcionan; el que falla se explica en la decisión 1.

## Goals / Non-Goals

**Goals:**

- Que la aplicación nunca corra como dueña de las tablas y que los tests prueben esa separación.
- Dejar el arnés de pytest y de cobertura que usan todos los tickets siguientes.

**Non-Goals:**

- Grupos, login y `/admin/` (HB-08 y HB-09).
- *Fixtures* del mock (`datos_demo`, `demo`, `como_app_user`), que agrega TK-01.

## Decisions

### 1. `%I` en el SQL que se ejecuta sin parámetros

El test de la guía escribe `format('public.%%I', tablename)` porque supone que el SQL pasa por los parámetros de Django. Pero `ejecutar_sql` llama a `cursor.execute(sql, None)`, y con `params=None` ni Django ni psycopg interpretan `%`: PostgreSQL recibe `%%I` y falla con `relation "public.%i" does not exist`. El test usa `%I`.

*Alternativa descartada:* pasar `params=()` para que `%%` se convierta. Funciona, pero obliga a recordar una regla que no aplica al resto de las llamadas.

### 2. `migrate` como `app_user` se comprueba en una base nueva

Sin migraciones pendientes, `migrate` como `app_user` termina con «No migrations to apply» y código 0. Solo falla cuando hay algo que aplicar: en una base nueva con `permission denied for schema public`, y con `0002` pendiente con `permission denied for table django_migrations`. El cierre lo comprueba después de `docker compose down -v`, antes de `migrate.sh`.

### 3. El test de longitud mínima prueba el límite

El test de la guía solo valida que `Corta-1` (7 caracteres) se rechace. El test comprueba el límite: 9 caracteres se rechazan con `password_too_short` y 10 se aceptan.

### 4. Versiones fijadas

`Django[argon2]==5.2.19` (última de la serie LTS, consultada el 2026-11-19) y `psycopg[binary]==3.3.9`. `argon2-cffi` entra como dependencia de Django, igual que `asgiref` y `sqlparse`.

### 5. Los tests corren como `app_owner`

pytest crea la base `test_hogar`, así que se conecta como `app_owner`. Los tests que deben comportarse como la aplicación usan `ejecutar_sql(..., rol="app_user")`, con `SET LOCAL ROLE` dentro de un *savepoint* ([ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md)).

## Risks / Trade-offs

- [El resultado del *job* `tests` solo se conoce en el PR] → El cambio queda sin archivar hasta verlo. La rama se reescribió con el rebase, así que el próximo push necesita `--force-with-lease`.
- [El *healthcheck* del CI usa *socket*] → Riesgo bajo, medido en la sección 7.1 de la guía; se revisa el paso `Crear app_owner y app_user` en el PR.
- [`createsuperuser` es interactivo] → Lo ejecuta el usuario; el cierre comprueba que `app_user` puede leer `usuario`.
