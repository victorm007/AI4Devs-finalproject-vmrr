# Design

## Context

HB-05 dejó la extensión `btree_gist` (`catalogo.0001_extensiones`) y `Medicamento`; HB-06, `Residente` (con `entidad_id` como clave); HB-03, `Usuario` y los privilegios por defecto de `app_user` (`accounts.0002_privilegios`), que se aplican a las tablas que crean después las migraciones como `app_owner`. Todavía no hay app `pautas`. La motivación está en `proposal.md`, y el comportamiento, en `specs/pautas/spec.md`.

El código de la guía (`docs/tickets/HB-07-pautas.md`) nunca se ha ejecutado. Al leerlo contra el readme y el entorno (Django 5.2.19 en `web`):

- `RangeBoundary`, `RangeOperators` y `DateRangeField` se importan de `django.contrib.postgres.fields` (comprobado en el contenedor).
- `ExclusionConstraint.validate()` de Django 5.2 reemplaza las referencias a campos dentro de expresiones (`replace_expressions`), así que `full_clean()` puede validar el traslape con la función `daterange(...)`. Lo confirma el test de la validación del modelo.
- La guía indica la rama `feature/HB-07-pautas`; `CLAUDE.md` (sección Git) manda seguir en la rama de trabajo actual, `feature/entrega-2-vmrr`.
- La guía no trae tests de los nombres exactos (criterio 1), de los tipos ni del rol `app_user`: se agregan (decisión 6).

## Goals / Non-Goals

**Goals:**

- Que la base, y no solo la aplicación, impida dosis, frecuencias y fechas inválidas, vigencias traslapadas y Pautas de Residentes o Medicamentos inactivos.
- Que el esquema quede con los nombres exactos que usan el mock y TK-01.

**Non-Goals:**

- Un servicio `registrar_pauta()`: sin pantallas no hay quien lo use; llegará con la historia de Pautas.
- El registro en `/admin/` y la carga del mock.

## Decisions

### 1. Restricciones como `Meta.constraints`, con los nombres del readme ([ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md), [ADR-0007](../../../docs/adr/0007-nomenclatura-de-objetos-de-base-de-datos.md))

Los 3 `CheckConstraint` y la `ExclusionConstraint` viven en `Meta.constraints`, para que `full_clean()` los valide. La de exclusión lleva `violation_error_message`, el mensaje que verán las futuras pantallas en lugar de un `500`.

### 2. Vigencia con `daterange(fecha_inicio, fecha_fin, '[]')` ([ADR-0016](../../../docs/adr/0016-pautas-informativas-con-vigencia.md))

Una `Func` propia (`RangoDeFechas`, `function = "daterange"`, `output_field = DateRangeField()`) con `RangeBoundary(True, True)`: ambos extremos cuentan, así que una Pauta que termina el día en que empieza otra se traslapa. `fecha_fin` nula da un rango abierto (vigente). Se descartó guardar una columna `daterange`: el readme define 2 columnas de fecha.

PostgreSQL evalúa los `CHECK` antes de insertar en los índices, así que una Pauta con fin anterior al inicio falla por `ck_pauta_fechas` y no por el error de `daterange` ("range lower bound must be less than or equal to range upper bound").

### 3. Índices guiados por la consulta 3 ([ADR-0018](../../../docs/adr/0018-indices-guiados-por-consultas.md))

`ix_pauta_vigente` es parcial (`condition=Q(fecha_fin__isnull=True)`) e `ix_pauta_residente_inicio` usa `"-fecha_inicio"` (DESC). La FK `residente` lleva `db_index=False` porque la cubre `ix_pauta_residente_inicio` (tabla "Índices de FK que Django no debe crear"). Las FK `medicamento` y `registrado_por` conservan el índice que crea Django: el readme no las excluye.

### 4. El *trigger* va en `RunSQL`, con su inversa

`0002_trigger` copia `fn_pauta_validar` y `tg_pauta_validar` de la sección 3.3, con la inversa `DROP TRIGGER ...; DROP FUNCTION ...`. La función es `SECURITY INVOKER` (por defecto): corre con los permisos de quien inserta. `app_user` tiene `SELECT` sobre `residente` y `medicamento` por los privilegios por defecto de HB-03, así que no hace falta `SECURITY DEFINER`.

### 5. Dependencias de las migraciones ([ADR-0006](../../../docs/adr/0006-dos-usuarios-de-base-de-datos.md))

`makemigrations` genera `0001_initial` con dependencias a `catalogo`, `entidades` y `AUTH_USER_MODEL`. Por la cadena `entidades.0001 → catalogo.0001_extensiones → accounts.0002_privilegios`, `btree_gist` existe y la tabla nace con los permisos de `app_user`. Las migraciones se aplican con `./scripts/migrate.sh` (como `app_owner`).

### 6. Tests además de los de la guía ([ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md))

Todos en `app/apps/pautas/tests/test_esquema.py`, contra PostgreSQL real y como `app_owner`, salvo el de `app_user`:

- los de la sección 3 de la guía, con el nombre de la restricción entre comillas en el `match` (`'"ck_pauta_dosis"'`), la convención de HB-06;
- los nombres y definiciones del criterio 1, leídos de `pg_constraint`, `pg_indexes` y `pg_trigger`;
- que ningún índice tenga `residente_id` como única columna, y los tipos `numeric(6,2)` y `smallint` (`information_schema.columns`);
- una Pauta válida insertada como `app_user` con `ejecutar_sql(..., rol="app_user")` (criterios de revisión de BD: privilegios de `app_user`).

"`migrate pautas zero` revierte todo" no es un test de pytest: se comprueba en el cierre con `./scripts/migrate.sh pautas zero` y `./scripts/migrate.sh`, como en HB-06.

### Diferencias aceptadas entre el DDL del readme y lo que genera Django

| Readme | Lo que genera Django | Por qué se acepta |
|---|---|---|
| `DEFAULT now()` | `DEFAULT STATEMENT_TIMESTAMP()` | `Now()` de Django en PostgreSQL; la misma decisión que en HB-06 |
| FK con `ON DELETE RESTRICT` | FK `DEFERRABLE INITIALLY DEFERRED` sin `ON DELETE` (`NO ACTION`) más `PROTECT` en Django | Igual que en HB-05 y HB-06 ([ADR-0009](../../../docs/adr/0009-bajas-logicas-y-on-delete-restrict.md)): Django 5.2 no declara la acción en la base |

## Risks / Trade-offs

- [El `match` de los mensajes del *trigger* lleva acentos ("no está activo")] → La base y la conexión usan UTF-8; si fallara, el rojo lo mostraría antes de congelar.
- [`RangoDeFechas` vive en `models.py` y la migración la importa] → La migración depende del código de la app; es el patrón de la documentación de Django para `ExclusionConstraint`, y la clase no tiene lógica.
- [Sin servicio, nada impide hoy un `INSERT` directo con datos inválidos] → La base es la barrera: `CHECK`, `EXCLUDE` y el *trigger* rechazan esos casos.

## Migration Plan

`./scripts/migrate.sh` aplica `pautas.0001_initial` y `pautas.0002_trigger`. Reversión: `./scripts/migrate.sh pautas zero`, que borra la tabla, la función y el *trigger*. En la base local no hay Pautas (el mock aún no se carga), así que revertir no pierde datos.
