"""Reglas de validación de entrada del catálogo, sin acceso a la base.

"Al menos un principio activo" no se puede expresar con un CHECK, porque los principios
activos viven en la tabla puente medicamento_principio_activo (readme, sección 3.2). Por eso
la regla se valida en la entrada, con un solo texto:

- En el MVP, el alta y el cambio del medicamento en /admin/ (PrincipiosActivosFormSet de
  apps.catalogo.forms).
- En la V2, POST /medicamentos y PATCH /medicamentos/{id} (si trae principios_activos_ids) la
  llamarán antes de guardar y responderán 400 VALIDACION con
  errores[] = {campo: principios_activos_ids, codigo: CAMPO_VACIO, mensaje: SIN_PRINCIPIO_ACTIVO}.
"""

from django.core.exceptions import ValidationError

SIN_PRINCIPIO_ACTIVO = "Un medicamento debe tener al menos un principio activo."


def exigir_principio_activo(principios_activos) -> None:
    """Lanza ValidationError(code="sin_principio_activo") si la colección está vacía o es None.

    Acepta cualquier colección: los principios activos elegidos en el formulario, una lista de
    ids (principios_activos_ids de la V2) o un QuerySet (se evalúa una sola vez). None es un
    caso defensivo para quien la llame desde dentro: se rechaza como la colección vacía.

    En la V2, el esquema de principios_activos_ids (array, minItems: 1) rechaza antes de llegar
    aquí: la lista vacía se traduce a errores[].codigo = CAMPO_VACIO con el mensaje de esta
    regla, y un valor que no es array (incluido null) a TIPO_INVALIDO. Si el campo falta en un
    PATCH no se llama a la regla; si no, la V2 la llama con la lista ya validada, antes de
    guardar, y traduce code="sin_principio_activo" a CAMPO_VACIO.

    Un texto o una secuencia de bytes (str, bytes, bytearray o memoryview) lanza TypeError: es
    un error de programación, porque list("abc") daría 3 elementos y la regla pasaría por error.
    """
    if isinstance(principios_activos, (str, bytes, bytearray, memoryview)):
        raise TypeError(
            "exigir_principio_activo: se esperaba una colección de principios activos, no un "
            f"texto ni bytes ({type(principios_activos).__name__})."
        )
    if principios_activos is None or not list(principios_activos):
        raise ValidationError(SIN_PRINCIPIO_ACTIVO, code="sin_principio_activo")
