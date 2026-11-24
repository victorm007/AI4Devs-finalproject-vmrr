# Design

## Context

HB-09 (`6c345f0`) dejó el catálogo y los residentes en el panel. HB-05 declaró `Presentacion.nombre` como `CharField(unique=True)`, que en la base es la restricción literal `presentacion_nombre_key` más su índice `presentacion_nombre_..._like` (`varchar_pattern_ops`). Las otras 2 unicidades del catálogo, `uq_principio_activo_nombre` y `uq_medicamento_nombre_pres_conc`, son índices únicos por expresión `f_unaccent(lower(...))` con `violation_error_message`. El mock (`cargar_mock.sql`) ya une las presentaciones con `f_unaccent(lower(...))`, y las 8 semillas no chocan entre sí sin acentos. La motivación y los hallazgos están en `proposal.md`, y el comportamiento, en `specs/`.

## Goals / Non-Goals

**Goals:**

- Que ninguna vía, ni el panel ni un `INSERT` directo, pueda duplicar una presentación y, con ella, un medicamento.
- Que la documentación del modelo de datos (readme, anexos, ADR y guías) diga lo mismo que la base.

**Non-Goals:**

- Los hallazgos 4, 5 y 10, que se anotan en la guía de HB-09 (`proposal.md`, "Fuera de alcance").
- Cambiar la búsqueda de existencias de TK-03 o de la API, que tiene sus propias reglas (ADR-0017).

## Decisions

### 1. `uq_presentacion_nombre` en lugar del `UNIQUE` literal ([ADR-0017](../../../docs/adr/0017-busqueda-sin-acentos-con-trigram.md), [ADR-0005](../../../docs/adr/0005-postgresql-ultima-barrera-de-integridad.md), [ADR-0007](../../../docs/adr/0007-nomenclatura-de-objetos-de-base-de-datos.md))

En `Presentacion`, se quita `unique=True` de `nombre` y se agrega a `Meta.constraints`:

```python
models.UniqueConstraint(
    sin_acentos("nombre"),
    name="uq_presentacion_nombre",
    violation_error_message="Ya existe esa presentación (sin distinguir mayúsculas ni acentos).",
)
```

Sigue el mismo patrón que `uq_principio_activo_nombre`. El formulario del panel valida la restricción antes de guardar (`validate_constraints`), y la base es la última barrera. La migración `catalogo/0004_presentacion_unica` la genera `makemigrations` (`AlterField` y `AddConstraint`) y es reversible. Al revertirla, vuelve el `UNIQUE` literal, que las semillas también cumplen. Se aplica con `./scripts/migrate.sh`, como `app_owner`. La base de desarrollo solo tiene las 8 semillas, así que la migración aplica sin conflictos.

**Alternativas descartadas:**

- **Validar solo en el formulario del panel:** un `INSERT` directo, el mock o la API de la V2 (`GET /presentaciones` y, después, su alta) podrían duplicar igual. La base es la última barrera (ADR-0005).
- **Conservar el `UNIQUE` literal además del índice por expresión:** sería redundante, porque el índice por expresión ya impide los duplicados exactos, y dejaría 2 índices más sin uso.

### 2. Búsqueda por palabras (`apps/panel.py`)

`get_search_results` divide el término con `smart_split`, como el panel estándar de Django, y quita las comillas de una frase con `unescape_string_literal`. Por cada palabra arma un `OR` entre los campos (`f_unaccent(lower(campo)) LIKE %f_unaccent(lower(palabra))%`), y une las palabras con `AND`. Un término vacío o solo con espacios no filtra. **Decidido durante la implementación:** un `filter()` por palabra, como el panel estándar de Django, en lugar de declarar los campos con `alias()` una sola vez. Con alias únicos, todas las palabras se comparaban contra el mismo principio activo, y "losartan hidroclorotiazida" no encontraba Hyzaar. Las expresiones van solo al `WHERE`, y `distinct()` quita los repetidos.

### 3. Presentaciones activas en el alta (ADR-0009)

`MedicamentoAdmin.get_form()` limita el campo `presentacion` a `activo=True` o a la presentación actual del medicamento (`Q(activo=True) | Q(pk=obj.presentacion_id)`). `get_form()` arma una clase nueva en cada petición, así que limitar `base_fields` no afecta a otras peticiones. El botón **+** del campo sigue creando presentaciones activas.

### 4. `panel.E001`

`BusquedaSinAcentosMixin.check()` agrega un `checks.Error(id="panel.E001")` cuando `campos_sin_acentos` está vacío. Así lo detectan `dj check` y el arranque del servidor, en lugar de que la búsqueda devuelva todas las filas en silencio. **Alternativa descartada:** lanzar `ImproperlyConfigured` dentro de la búsqueda, porque solo fallaría cuando alguien buscara.

### 5. Tests

- **`app_user`:** dentro de la transacción del test, `SET LOCAL ROLE app_user` en la misma conexión que usa el cliente de Django, después de `force_login`. El patrón de `como_app_user` de TK-01, que aún no existe, se escribe aquí en línea y sin crear *fixtures* compartidos. El test comprueba con `SELECT current_user` que corre como `app_user`.
- **CSP:** el patrón de HB-09 se amplía con `<style\b` y `\son[a-z]+\s*=` y se aplica a más páginas.
- Los archivos de tests de HB-09 y `test_modelos.py` de HB-05 se modifican y se vuelven a congelar.

### 6. Documentación viva

| Documento | Cambio |
|---|---|
| `readme.md` 3.1 | Mermaid: `nombre UK "60, NOT NULL, unico sin distinguir mayusculas ni acentos"`. En el DDL, `CREATE UNIQUE INDEX uq_presentacion_nombre ON presentacion (f_unaccent(lower(nombre)));` junto a `uq_principio_activo_nombre`. En el párrafo de restricciones avanzadas, los 3 índices únicos por expresión |
| `readme.md` 3.2 (D2) | `presentacion.nombre`: "NOT NULL, UNIQUE sin distinguir mayúsculas ni acentos (`uq_presentacion_nombre`)" |
| `readme.md` 6 (ficha de HB-09) | La descripción técnica nombra `uq_presentacion_nombre` (migración `catalogo/0004`) y la búsqueda por palabras; un criterio nuevo: "Una presentación duplicada sin acentos da un mensaje y la base la rechaza" |
| `03-modelo-datos.md` | El mismo cambio, a mano, dentro de su anexo (formato propio) |
| `06-tickets-trabajo.md` | Anexo regenerado desde la sección 6 del readme, más las entradas `Prompt 22`/`Respuesta 22` (implementación de HB-09) y `Prompt 23`/`Respuesta 23` (esta revisión) |
| ADR-0017 | La unicidad del catálogo nombra `uq_presentacion_nombre`, como precisión que extiende la decisión sin cambiarla |
| Guía de HB-05 | Nota: desde los ajustes de HB-09, `presentacion.nombre` no tiene `UNIQUE` literal ni índice `_like`, sino `uq_presentacion_nombre` |
| Guía de HB-09 | Diferencias: los ajustes y los hallazgos 4, 5 y 10 anotados como pendientes |
| `CLAUDE.md` | Estado: `uq_presentacion_nombre` y la búsqueda por palabras |
| `diagramas/` | El usuario regenera el PNG del modelo de datos desde el Mermaid |

La ficha de HB-05 del readme no se toca: describe lo que entregó ese ticket. El cambio queda en la ficha de HB-09, que lo introduce.

## Risks / Trade-offs

- [Revertir `0004` con datos que solo difieren en acentos] → el `UNIQUE` literal sí los admite ("Tableta" y "tableta" son distintos para él), así que revertir no falla.
- [Una búsqueda de muchas palabras genera un `WHERE` con muchas condiciones] → el panel lo usan de 1 a 3 personas, sobre cientos de filas.
- [El `SET LOCAL ROLE` del test depende de que el cliente use la misma conexión] → el test comprueba con `SELECT current_user` que la conexión sigue como `app_user` antes y después de la petición, y exige la entrada de `django_admin_log`, que solo existe si el `INSERT` se hizo con ese rol.

## Migration Plan

1. `./scripts/migrate.sh` aplica `catalogo.0004_presentacion_unica` en desarrollo. No hay datos que choquen.
2. Reversión: `./scripts/migrate.sh catalogo 0003` y después `./scripts/migrate.sh`.
3. Sin comandos destructivos: no hace falta `docker compose down -v`.
