# Design

## Context

La guía de HB-09 conserva el `panel.py` y el `admin.py` iniciales, y no tiene un paso que cree la migración `0004`. `validadores.py` dice que un `null` de la V2 llega a la regla, mientras que el contrato dice que lo rechaza el esquema. `BusquedaSinAcentosMixin.check()` da `panel.E001` y `panel.E002`. Los hallazgos están en `proposal.md`.

## Goals / Non-Goals

**Goals:** una guía que, seguida tal cual, deje los tests actuales en verde, y una sola descripción de `null` en todo el proyecto.

**Non-Goals:** el falso positivo de `"pk"` (hallazgo 5), que se anota en la guía.

## Decisions

### 1. Código vigente en la guía

- **Bloques de código:** los de `panel.py` (paso 2) y `catalogo/admin.py` (paso 3) se copian de los archivos reales, después de implementar este cambio. Así coinciden letra por letra.
- **Paso 3b:** el cambio de `Presentacion.Meta.constraints`, que quita `unique=True` y agrega `uq_presentacion_nombre`. Después, `dj makemigrations catalogo --name presentacion_unica`, `./scripts/migrate.sh` y `\d presentacion`.
- **Sección 1:** agrega `catalogo/models.py`, `migrations/0004_presentacion_unica.py`, `validadores.py`, `forms.py`, `tests/test_modelos.py` y `tests/test_formularios.py`.

**Alternativa descartada:** declarar los bloques como línea base. El usuario prefiere que la guía sea ejecutable.

### 2. `null` en la V2

- **Contrato:** `principios_activos_ids` es un *array* con `minItems: 1`. La V2 traduce `minItems` (la lista vacía) a `CAMPO_VACIO` con el mensaje de la regla, y `type` (cualquier valor que no sea *array*, incluido `null`) a `TIPO_INVALIDO`. Así lo dicen la descripción del campo en `openapi.yaml`, la nota del readme (sección 4) y su anexo en `04-api.md`.
- **Regla:** antes de guardar, la V2 llama a `exigir_principio_activo()` con la lista ya validada. En el *docstring*, `None` es solo un caso defensivo para quien la llame desde dentro: se rechaza como la lista vacía.

### 3. `panel.E003` y tipos de texto

- **`check()`:** si `campos_sin_acentos` es un `str`, agrega un solo `checks.Error(id="panel.E003")` ("debe ser una tupla") y no revisa los campos uno por uno.
- **`exigir_principio_activo()`:** lanza `TypeError` con `str`, `bytes`, `bytearray` y `memoryview`.

### 4. Tests

- **`panel.E003`:** con `campos_sin_acentos = "nombre"`, exactamente 1 error, y ninguno `panel.E002`.
- **Relación inversa:** un registro de `PrincipioActivo` con `("nombre", "medicamentos__nombre_comercial")` no da `panel.E002`. Es de regresión.
- **Texto en la regla:** la parametrización de `test_un_texto_no_es_una_coleccion` suma `bytearray` y `memoryview`.

## Risks / Trade-offs

- [La guía duplica el código del repositorio y puede volver a desfasarse] → al cerrar cada ajuste, la tarea de documentación copia los archivos reales, y la revisión adversarial lo compara.
