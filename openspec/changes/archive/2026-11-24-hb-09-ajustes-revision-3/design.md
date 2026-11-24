# Design

## Context

`apps/panel.py` divide el término con `palabras_de_busqueda()` y aplica un `filter()` por palabra. La regla "al menos un principio activo" está en `apps/catalogo/validadores.py` (`exigir_principio_activo()` hace `if not list(...)`). La guía de HB-09 conserva el código del paso 3 con `formset = PrincipiosActivosFormSet`, pero sin el *import* ni el código de los 2 módulos nuevos. Los hallazgos están en `proposal.md`.

## Goals / Non-Goals

**Goals:** que los tests fijen el motivo del `filter()` por palabra, que la configuración del panel falle al arrancar y no en la primera búsqueda, y que la guía vuelva a ser ejecutable.

**Non-Goals:** los hallazgos 6 y 8, que solo se anotan.

## Decisions

### 1. Tope de 8 palabras (`apps/panel.py`)

Se agrega la constante `MAXIMO_PALABRAS = 8`, y `palabras_de_busqueda()` devuelve como mucho esas 8 palabras, ignorando las demás. Cada palabra agrega un `filter()` con su unión a la tabla puente. El tope evita una consulta enorme con miles de palabras; 8 sobran para nombre, concentración y principios activos. **Alternativa descartada:** avisar al usuario. El panel de Django no tiene dónde mostrar ese aviso sin plantillas propias.

### 2. `panel.E002`

`BusquedaSinAcentosMixin.check()` resuelve cada campo de `campos_sin_acentos`, recorriendo los `__` con `_meta.get_field()` y `related_model`. Si un tramo no existe o no tiene modelo relacionado, agrega `checks.Error(id="panel.E002")` con el nombre del campo. Así el error aparece en `dj check` y al arrancar, no como un `500` en la primera búsqueda.

### 3. La regla con `None` y con texto (`apps/catalogo/validadores.py`)

`exigir_principio_activo(None)` lanza la misma `ValidationError` que con la lista vacía: si `principios_activos_ids` falta en un `PATCH`, la V2 no llama a la regla, y un `None` explícito significa "sin principios". Un `str` o `bytes` lanza `TypeError`, porque es un error de programación: `list("abc")` daría 3 elementos y la regla pasaría por error. El *docstring* y la nota de la V2 dicen que la API traduce `code="sin_principio_activo"` a `errores[].codigo = CAMPO_VACIO`.

### 4. Tests

- **Búsqueda:**
  - un medicamento "Hyzaar" con Losartán e Hidroclorotiazida: "losartan hidroclorotiazida" da `result_count == 1`;
  - `q="%"` y `q="_"` dan 0 con 2 medicamentos registrados;
  - 8 × "cozaar" más "paracetamol" encuentra Cozaar.
- **Comprobación del sistema:** `panel.E002` con un campo mal escrito, y los registros reales sin errores.
- **Regla:** `None` lanza la `ValidationError` con su código; un texto lanza `TypeError`.
- **Presentaciones inactivas:** el HTML del alta no tiene `<option value="{parche.pk}"`, y el del cambio sí.

### 5. Documentación

- **Guía de HB-09:**
  - en el paso 3, el bloque de `admin.py` importa `PrincipiosActivosFormSet` y se agregan los bloques completos de `apps/catalogo/validadores.py` y `apps/catalogo/forms.py`;
  - la sección 5 dice que la única migración del ticket es `catalogo/0004_presentacion_unica` y que después `makemigrations --check` no detecta cambios;
  - las notas de los hallazgos 6 y 8: para el 8, la consulta `SELECT f_unaccent(lower(nombre)), count(*) FROM presentacion GROUP BY 1 HAVING count(*) > 1;` antes de migrar en el servidor del hogar.
- **ADR-0005:** sus índices únicos por expresión pasan a ser 3. Es una precisión, no una nueva decisión.
- **readme 4 (nota de la V2), su anexo en `04-api.md` y `openapi.yaml`:** la traducción `sin_principio_activo` → `CAMPO_VACIO`.
- **`CLAUDE.md`:** menciona `validadores.py` y `forms.py`.
- **Transcripto:** `Prompt 25`/`Respuesta 25`.

## Risks / Trade-offs

- [Con más de 8 palabras, la búsqueda ignora las sobrantes sin avisar] → se documenta en el *docstring* y en la guía. Nadie busca con 9 palabras en un catálogo de cientos de filas.
