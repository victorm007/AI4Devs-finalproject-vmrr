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
    ids (principios_activos_ids de la V2) o un QuerySet (se evalúa una sola vez). None se
    rechaza como la colección vacía: en la V2, si principios_activos_ids falta en un PATCH no
    se llama a la regla, y un null explícito significa "sin principios activos". Un texto (str
    o bytes) lanza TypeError: es un error de programación, porque list("abc") daría 3
    elementos y la regla pasaría por error. La V2 traduce code="sin_principio_activo" a
    errores[].codigo = CAMPO_VACIO.
    """
    if isinstance(principios_activos, (str, bytes)):
        raise TypeError(
            "exigir_principio_activo: se esperaba una colección de principios activos, no un "
            f"texto ({type(principios_activos).__name__})."
        )
    if principios_activos is None or not list(principios_activos):
        raise ValidationError(SIN_PRINCIPIO_ACTIVO, code="sin_principio_activo")
