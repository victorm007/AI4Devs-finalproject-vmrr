# Design

## Context

`hb-06-ajustes-revision` (commit `0861578`) dejó `registrar_residente()` así:
- comprueba "ya registrado" con `not residente._state.adding`;
- guarda los valores originales de 6 campos (`estado`, `fecha_baja` y los 4 nombres);
- ante cualquier excepción los restaura, pone `entidad_id = None` y restaura `_state.adding` y `_state.db`.

El test del reintento hace fallar `Residente.save` con `monkeypatch`. La segunda revisión observó:

- `Residente(entidad=<existente>)` sin guardar tiene `_state.adding = True` y pasa la comprobación. El servicio le crea otra Entidad y lo registra. Antes, `pk is not None` lo rechazaba.
- `full_clean` reemplaza los valores por los que devuelve `to_python`. Por ejemplo, `fecha_ingreso="1930-01-01"` pasa a `date(1930, 1, 1)`. Las fechas no están en los valores guardados.
- Cuando `save` falla, `_state.adding` no llega a cambiar. Por eso ningún test sostiene la restauración de `_state`, que solo importa si la falla ocurre después de un `save` correcto, por ejemplo al confirmar.

Lo comprobé en PostgreSQL 17, dentro de una transacción revertida:
- `ALTER TABLE residente ADD CONSTRAINT ... CHECK (primer_nombre <> 'Ana') NOT VALID` hace fallar el `INSERT` siguiente con `IntegrityError`;
- `UNIQUE (primer_apellido) DEFERRABLE INITIALLY DEFERRED` acepta el `INSERT` duplicado y falla solo al comprobar las restricciones diferidas.

## Goals / Non-Goals

**Goals:**

- Ningún test simula la base de datos (ADR-0023).
- La restauración del objeto recibido es completa, y un test la sostiene.
- Un `HOGAR_NOMBRE` inválido falla con un mensaje claro al arrancar, no en la migración.

**Non-Goals:**

- Renombrar el Hogar después de migrar.
- Leer `.env` con valores con espacios (TK-01).
- El *nit* 8.

## Decisions

### 1. Comprobación de "ya registrado" con las 2 condiciones

`if not residente._state.adding or residente.pk is not None: raise ValueError("El residente ya está registrado.")`.

- La primera condición cubre un objeto guardado o leído de la base.
- La segunda cubre uno al que se le asignó una Entidad.

Después de una falla, la restauración deja `pk = None` y `_state.adding = True`, así que el reintento pasa la comprobación.

### 2. Se guardan todos los campos concretos

Los valores originales pasan a ser `{campo.attname: getattr(residente, campo.attname) for campo in Residente._meta.concrete_fields}`. Así entran las fechas, `tipo` y `entidad_id`, este último siempre `None` gracias a la decisión 1.

La restauración repone esos valores y después `_state.adding` y `_state.db`. Asignar `entidad_id` (`None`) borra la Entidad en caché, como ya comprobó el ajuste anterior.

Alternativa descartada: validar y normalizar sobre una copia del objeto. Obligaría a copiar después los valores normalizados al original, y el contrato actual devuelve el mismo objeto.

### 3. Fallas reales de PostgreSQL en los tests ([ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md))

- **Al guardar** (test normal, dentro de la transacción del test):
  - `ejecutar_sql("ALTER TABLE residente ADD CONSTRAINT ck_prueba_falla CHECK (primer_nombre <> 'Ana') NOT VALID")`.
  - Django no conoce esa restricción, así que `full_clean` pasa, se crea la Entidad y el `INSERT` del Residente falla.
  - Después, `ALTER TABLE residente DROP CONSTRAINT ck_prueba_falla` y el reintento.
  - El DDL se revierte con la transacción del test.
- **Al confirmar** (`@pytest.mark.django_db(transaction=True, serialized_rollback=True)`):
  - Sin transacción envolvente, el `atomic` del servicio es la transacción real y su `COMMIT` comprueba las restricciones diferidas.
  - El test registra a Carmen Torres, agrega `uq_prueba_apellido UNIQUE (primer_apellido) DEFERRABLE INITIALLY DEFERRED` y registra a otro Residente con primer apellido "Torres".
  - El `save` funciona, y el `COMMIT` lanza `IntegrityError`.
  - Comprueba que el objeto vuelve a `_state.adding is True`, `pk is None` y sin Entidad en caché, y que el número de Entidades no cambió. Después quita la restricción y el reintento lo registra.
  - Como el DDL queda confirmado, la restricción se quita en un `finally`. `serialized_rollback` restaura el Hogar al vaciar la base.

Nombres con el prefijo de la nomenclatura (`ck_`, `uq_`) y la palabra `prueba` (ADR-0007).

### 4. Largo de `HOGAR_NOMBRE` en `base.py`; obligatoriedad en `prod.py`

- **`base.py`:** después de leer la variable, si su largo es mayor que 150 lanza `ImproperlyConfigured("HOGAR_NOMBRE tiene N caracteres; el máximo es 150 (entidad.nombre).")`. Como `local.py` y `prod.py` importan `base`, aplica en todos los entornos.
- **`prod.py`:** conserva la comprobación de variable ausente o vacía, y su mensaje agrega que, sin ella, el contenedor `web` no arranca y se reinicia.

## Risks / Trade-offs

- **[El test con `transaction=True` vacía la base al terminar]** → `serialized_rollback=True` la restaura, con el Hogar `id = 1`, como pide `CLAUDE.md`. Si el test falla antes de quitar la restricción diferida, el `finally` la quita igual.
- **[El test con `transaction=True` corre como `app_owner`]** → Correcto: necesita `ALTER TABLE`. El alta como `app_user` ya la cubre otro test.
- **[Endurecer la comprobación de "ya registrado"]** → Un llamador que asignaba una Entidad a mano antes de registrar ahora recibe `ValueError`. Ningún llamador lo hace: el panel (HB-09) todavía no existe.
