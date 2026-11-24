"""Formularios del catálogo para /admin/ (HB-09)."""

from django.forms.models import BaseInlineFormSet

from apps.catalogo.validadores import exigir_principio_activo


class PrincipiosActivosFormSet(BaseInlineFormSet):
    """Renglones de principios activos de un medicamento: exige al menos uno.

    El aviso es el de apps.catalogo.validadores y aparece como error del conjunto
    (non_form_errors), arriba de los renglones. Sustituye a validate_min, cuyo aviso es el
    genérico de Django.
    """

    def clean(self):
        super().clean()
        # Aunque algún renglón tenga errores, la regla se revisa igual: así el aviso aparece
        # también cuando el único renglón está vacío. Un renglón que no validó puede no tener
        # cleaned_data, o no tener la clave principio_activo
        principios_activos = []
        for form in self.forms:
            datos = getattr(form, "cleaned_data", None) or {}
            principio_activo = datos.get("principio_activo")
            if principio_activo and not datos.get("DELETE"):
                principios_activos.append(principio_activo)
        exigir_principio_activo(principios_activos)
