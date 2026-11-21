"""Expresiones SQL compartidas por los modelos (readme, sección 3.3)."""

from django.db import models
from django.db.models import Func
from django.db.models.functions import Length, Lower, Trim
from django.db.models.lookups import GreaterThan


def sin_acentos(campo) -> Func:
    """f_unaccent(lower(campo)): la misma expresión de los índices trigram (sección 3.3).

    Si la consulta no usa exactamente esta expresión, PostgreSQL no usa el índice.
    Ejemplo: Medicamento.objects.annotate(n=sin_acentos("nombre_comercial"))
                                .filter(n__contains="losartan")
    """
    return Func(Lower(campo), function="f_unaccent", output_field=models.CharField())


def no_vacio(campo: str) -> GreaterThan:
    """Equivale a btrim(campo) <> '': el texto no puede ser solo espacios (sección 3.3)."""
    return GreaterThan(Length(Trim(campo)), 0)
