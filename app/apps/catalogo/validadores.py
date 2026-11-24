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
    """Lanza ValidationError(code="sin_principio_activo") si la colección está vacía.

    Acepta cualquier colección: los principios activos elegidos en el formulario, una lista de
    ids (principios_activos_ids de la V2) o un QuerySet (se evalúa una sola vez).
    """
    if not list(principios_activos):
        raise ValidationError(SIN_PRINCIPIO_ACTIVO, code="sin_principio_activo")
