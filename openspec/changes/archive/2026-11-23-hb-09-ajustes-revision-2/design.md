# Design

## Context

`PrincipioActivoEnLinea` (HB-09) exige al menos un renglón con `min_num = 1` y `validate_min = True`. Lo hace con un `get_formset()` que pasa `validate_min`, porque el panel de Django 5.2 no lo pasa. El aviso es el genérico de Django ("Envíe 1 formulario o más"), y la regla solo existe dentro del *inline*. La base no la garantiza: `medicamento_principio_activo` es una tabla puente, y "al menos un renglón" no se puede expresar con un `CHECK`. Los 15 medicamentos del mock tienen al menos un principio activo. La motivación está en `proposal.md`.

## Goals / Non-Goals

**Goals:**

- Un mensaje legible, el mismo en el alta, en el cambio y, en la V2, en la API.
- Una sola definición de la regla, que no dependa del panel.

**Non-Goals:**

- La API de escritura (V2) y una barrera en la base (proposal, "Fuera de alcance").

## Decisions

### 1. La regla en `apps/catalogo/validadores.py`

```python
SIN_PRINCIPIO_ACTIVO = "Un medicamento debe tener al menos un principio activo."

def exigir_principio_activo(principios_activos) -> None:
    """Lanza ValidationError(code="sin_principio_activo") si la colección está vacía."""
```

Recibe cualquier colección (los principios elegidos en el formulario, o los `principios_activos_ids` de la V2). No toca la base. **Alternativa descartada:** ponerla en `services.py`. El catálogo no tiene servicios de escritura (el panel guarda con el ORM), y la regla es de validación de entrada, no de una transacción.

### 2. El conjunto de renglones del panel (`apps/catalogo/forms.py`)

`PrincipiosActivosFormSet(BaseInlineFormSet).clean()` junta los principios activos de los renglones válidos, con datos y no marcados para borrar, y llama a `exigir_principio_activo()`. Su `ValidationError` aparece como error del conjunto (`non_form_errors`), arriba de los renglones. `PrincipioActivoEnLinea` usa `formset = PrincipiosActivosFormSet` y conserva `min_num = 1` y `extra = 0`, para mostrar un renglón vacío.

Se quitan `validate_min = True` y el `get_formset()` de HB-09: con los 2 mecanismos, el usuario vería 2 avisos (el genérico y el legible).

Un renglón vacío dentro de `min_num` se crea con `empty_permitted = False`, así que también da "Este campo es obligatorio" en el renglón. **Decidido durante la implementación:** `clean()` revisa la regla aunque algún renglón tenga errores, para que el aviso legible aparezca también en ese caso. El test del cambio con el renglón vacío exige el aviso con `in`, no con igualdad.

### 3. La V2 (nota en el readme y en `openapi.yaml`)

`POST /medicamentos` y `PATCH /medicamentos/{id}` (si trae `principios_activos_ids`) llamarán a `exigir_principio_activo()` antes de guardar. Responderán `400 VALIDACION` con `errores[] = { campo: principios_activos_ids, codigo: CAMPO_VACIO, mensaje: "Un medicamento debe tener al menos un principio activo." }`. `CAMPO_VACIO` ya existe en el `enum` de `ErrorCampo`, así que el contrato no cambia de forma: solo se documenta en la descripción del campo. El esquema ya tiene `minItems: 1`.

### 4. Documentación viva

| Documento | Cambio |
|---|---|
| readme 3.2 (D2) | "El 'al menos uno' se valida en el formulario" → dónde (alta y cambio del panel; en la V2, `POST`/`PATCH /medicamentos` con la misma regla) y por qué no en la base |
| readme 4 (tras la tabla de endpoints V2) | Nota: la regla y su respuesta `400 VALIDACION` con `CAMPO_VACIO` |
| readme 6 (ficha de HB-09) | Criterio 2: "sin principio activo, en el alta o en el cambio, el formulario muestra 'Un medicamento debe tener al menos un principio activo.' y no guarda" |
| `openapi.yaml` | `description` de `principios_activos_ids` en `MedicamentoCrear` y `MedicamentoActualizar`; `npx @redocly/cli lint` sin errores nuevos |
| Anexos | `03-modelo-datos.md` (a mano), `04-api.md` (sección 4, conservando los ejemplos con curl) y `06-tickets-trabajo.md` |
| Guía de HB-09 | Paso 3 (el *inline* con `formset`) y el hallazgo 4 pasa a "atendido" |
| Transcripto | `Prompt 24`/`Respuesta 24` en `06-tickets-trabajo.md` |

## Risks / Trade-offs

- [Sin barrera en la base, un `INSERT` directo puede dejar un medicamento sin principio activo] → aceptado por el usuario para mantener la flexibilidad. El panel y la V2 lo validan, y al editar ese medicamento el formulario exige elegir uno.
- [Al editar un medicamento sin principios activos (por ejemplo, para darlo de baja), hay que elegir uno] → es la regla deseada, y el mensaje lo explica.
