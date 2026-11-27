"""Reglas de validación de entrada del catálogo, sin acceso a la base.

"Al menos un principio activo" no se puede expresar con un CHECK, porque los principios
activos viven en la tabla puente medicamento_principio_activo (readme, sección 3.2). Por eso
la regla se valida en la entrada, con un solo texto:

- En el MVP, el alta y el cambio del medicamento en /admin/ (PrincipiosActivosFormSet de
  apps.catalogo.forms).
- En la V2, en POST /medicamentos y PATCH /medicamentos/{id} la lista vacía la rechaza el
  esquema de principios_activos_ids (minItems: 1) con 400 VALIDACION y
  errores[] = {campo: principios_activos_ids, codigo: CAMPO_VACIO, mensaje: SIN_PRINCIPIO_ACTIVO}:
  el mensaje es el de esta regla. La función protege a quien guarde sin pasar por ese esquema.
"""

from django.core.exceptions import ValidationError

SIN_PRINCIPIO_ACTIVO = "Un medicamento debe tener al menos un principio activo."


def exigir_principio_activo(principios_activos) -> None:
    """Lanza ValidationError(code="sin_principio_activo") si la colección está vacía o es None.

    Acepta cualquier colección: los principios activos elegidos en el formulario, una lista de
    ids (principios_activos_ids de la V2) o un QuerySet (se evalúa una sola vez). None es un
    caso defensivo para quien la llame desde dentro: se rechaza como la colección vacía.

    En la V2, el esquema de principios_activos_ids (array, minItems: 1) responde antes: la lista
    vacía con CAMPO_VACIO y el mensaje SIN_PRINCIPIO_ACTIVO, y un valor que no es array
    (incluido null) con TIPO_INVALIDO. Esta función no la necesita la API para esos casos: es
    la misma regla para el panel y para cualquier código que guarde sin pasar por el esquema.

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
