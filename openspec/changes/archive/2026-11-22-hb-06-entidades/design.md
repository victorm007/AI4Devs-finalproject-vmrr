# Design

## Context

HB-05 dejó `f_unaccent`, `apps/expresiones.py` (`sin_acentos()` y `no_vacio()`) y los privilegios por defecto de `app_user` (`accounts.0002_privilegios`), que se aplican a las tablas de las migraciones siguientes. Todavía no hay tablas de Entidades. La motivación está en `proposal.md`, y el comportamiento, en `specs/`.

El código de la guía (`docs/tickets/HB-06-entidades.md`) nunca se ha ejecutado. Al leerlo contra el readme y el entorno aparece **un defecto** y **dos puntos por verificar**:

- **Defecto:** la línea `HOGAR_NOMBRE=Hogar Gerontológico Demo` de `.env.example` rompe `. ./.env`, que cargan `scripts/migrate.sh` y los atajos `dtest`, `dj` y `dpsql`. El shell la lee como `HOGAR_NOMBRE=Hogar` seguido del comando `Gerontológico`, y con `set -e` el script falla (comprobado con un `.env` de prueba: `command not found`, código 127). Ver la decisión 6.
- **Por verificar:** que `DateTimeField(auto_now=True, db_default=Now())` y `OneToOneField(primary_key=True, db_constraint=False)` generen las columnas y las migraciones que describe la sección 3.2.
- **Por verificar:** que `makemigrations` produzca un `0001_initial` sin cambios pendientes después de agregar la dependencia a `catalogo.0001_extensiones`.

## Goals / Non-Goals

**Goals:**

- Que la base, y no solo el servicio, impida un segundo Hogar, un subtipo incoherente y fechas o nombres inválidos.
- Que `Entidad.activa` y `Entidad.__str__` queden como el contrato del punto de integración 11.

**Non-Goals:**

- El panel `/admin/` (HB-09) y la regla de que el Hogar no se da de Baja.
- Cargar Residentes del mock.

## Decisions

### 1. Supertipo y subtipo con la misma clave ([ADR-0008](../../../docs/adr/0008-supertipo-entidad-subtipo-residente.md))

`Residente.entidad` es un `OneToOneField` con `primary_key=True`, `related_name="residente"`, `on_delete=PROTECT` y `db_constraint=False`. El `db_constraint=False` es porque la FK real es compuesta `(entidad_id, tipo)` y no la declara Django. `Residente.tipo` lleva `default` y `db_default` `RESIDENTE`, y `editable=False`.

### 2. La FK compuesta va en SQL

`0002_fk_compuesta` es un `RunSQL` con su inversa, que agrega `fk_residente_entidad ... ON DELETE RESTRICT`. Depende de `0001_initial`, donde nace `uq_entidad_id_tipo`, el destino de la FK. Django no declara FK compuestas.

### 3. Restricciones como `Meta.constraints`, con los nombres del readme ([ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md), [ADR-0007](../../../docs/adr/0007-nomenclatura-de-objetos-de-base-de-datos.md))

Así `full_clean()` valida las restricciones y, con `violation_error_message`, el servicio y el panel muestran un mensaje en lugar de un `500`. Los 2 `CHECK` de doble condición del DDL, `(a) = (b)`, se escriben con `Q` en su forma equivalente `(a AND b) OR (NOT a AND NOT b)`.

| Readme | Lo que genera Django | Por qué se acepta |
|---|---|---|
| `CHECK (btrim(x) <> '')` | `CHECK (LENGTH(TRIM(x)) > 0)` | Equivalentes. Es la misma decisión que en HB-05 (`no_vacio()`) |
| `DEFAULT now()` | `DEFAULT STATEMENT_TIMESTAMP()` | `Now()` de Django en PostgreSQL. Solo cambia el instante dentro de una transacción larga |
| `CREATE UNIQUE INDEX uq_entidad_un_hogar ... WHERE tipo = 'HOGAR'` | `UniqueConstraint(fields=["tipo"], condition=...)`, un índice único parcial con el mismo nombre | Es el mismo índice, y `validate_constraints()` lo entiende |

### 4. El Hogar lo crea una migración de datos

`0003_hogar` hace `get_or_create(tipo="HOGAR", defaults={"nombre": settings.HOGAR_NOMBRE})`, idempotente, y su inversa borra el Hogar. En una base nueva queda con `id = 1`, que el mock y TK-01 dan por hecho. Usa el modelo histórico de `apps.get_model`, así que `activa` y `__str__` no existen en él, y no los necesita.

### 5. `registrar_residente()` es la única vía de alta ([ADR-0011](../../../docs/adr/0011-capa-de-servicios-unica-via-de-escritura.md))

Dentro de `transaction.atomic`: rechaza con `ValueError` un Residente ya guardado, fuerza `ACTIVO` y sin fecha de baja, llama a `full_clean(exclude=["entidad"])` antes de tocar la base y solo entonces crea la Entidad y guarda el Residente con `force_insert=True`. Los modelos no sobrescriben `save()` ni usan señales.

### 6. `HOGAR_NOMBRE` desde el entorno ([ADR-0004](../../../docs/adr/0004-configuracion-por-entorno-variables-db.md))

`settings.HOGAR_NOMBRE = os.environ.get("HOGAR_NOMBRE", "Hogar Gerontológico Demo")`, y `docker-compose.yml` lo pasa a `web` con el mismo valor por defecto. Es el nombre que esperan los tests de TK-03.

**Decisión (aprobada la opción A el 2026-11-22): cómo documentarlo en `.env.example`.** Los 3 lectores de `.env` se contradicen con un valor con espacios:

| Lector | Sin comillas | Con comillas |
|---|---|---|
| `. ./.env` (`migrate.sh`, `dtest`) | Falla | Funciona |
| `docker compose` | Funciona | Funciona |
| `make` (`-include .env` y `export`, TK-01) | Funciona | Exporta las comillas literales, y ese valor pisa el de `.env` en `docker compose` |

Opciones:

- **A (recomendada):** en `.env.example` la variable va **comentada** (`# HOGAR_NOMBRE=...`) con su explicación. El valor por defecto de `settings` y de `docker-compose.yml` cubre el desarrollo y la demo. No toca la regla "sin comillas" de `CLAUDE.md`.
- **B:** valor con comillas en `.env.example`, y `settings` les quita las comillas de los extremos. Funciona con los 3 lectores, pero agrega código solo para absorber un defecto de formato.

Para el servidor del hogar, con un nombre real, la opción A obliga a cambiar la regla de `.env` en otro ticket. Se anota en el PR.

### 7. Rojo inicial por importación

Como en HB-05, el rojo inicial es `ModuleNotFoundError: apps.entidades.models`. Con el esqueleto de `registrar_residente` (`NotImplementedError`), pasan los tests de esquema y fallan los de alta.

## Risks / Trade-offs

- [`./scripts/migrate.sh entidades zero` en el cierre borra el Hogar y las tablas de la base local] → Se vuelven a crear en el mismo paso con `./scripts/migrate.sh`. La base local no tiene Residentes ni Existencias todavía.
- [El paso 5 de la sección 5 de la guía da de alta a "Ana Ruiz" en la base local, y el mock solo se carga en una base sin Residentes] → Se declara en el plan: o se omite ese paso, o se recrea la base con `docker compose down -v` antes de TK-01. Solo lo ejecuta quien aprobó el plan.
- [Los tests de HB-03 (`test_privilegios.py`) ahora revisan también las tablas de Entidades] → Es lo esperado: comprueban dueño `app_owner` y los 4 permisos de `app_user`.
- [`ejecutar_sql` sin `params` no interpola, y con `params` sí] → Los tests con `UPDATE ... WHERE entidad_id = %s` pasan `params`, y el resto no lleva `%` en su SQL.
