"""Reglas comunes del panel /admin/ (readme, sección 5, "Controles"; HB-09).

Los mixins van antes de admin.ModelAdmin en la herencia, para que sus métodos reemplacen
a los del panel:

    class MedicamentoAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin): ...
"""

from django.db.models import Q, Value

from apps.expresiones import sin_acentos


class SinBorrarMixin:
    """Sin la acción "Eliminar": la baja es lógica (activo o estado).

    El panel quita la acción de la lista y el botón de la página, y responde 403 en
    .../delete/, también al Administrador (superusuario).
    """

    def has_delete_permission(self, request, obj=None):
        return False


class BusquedaSinAcentosMixin:
    """La búsqueda ignora mayúsculas y acentos: "losartan" encuentra "Losartán".

    Compara f_unaccent(lower(campo)) contra f_unaccent(lower(término)), la misma expresión
    de los índices trigram (sección 3.3, ADR-0017). La subclase define campos_sin_acentos;
    search_fields sigue declarado solo para que el panel muestre el buscador y permita el
    autocomplete. Sin mínimo de caracteres ni UNION: eso es de la búsqueda de existencias.
    """

    campos_sin_acentos: tuple[str, ...] = ()

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return queryset, False
        termino = sin_acentos(Value(search_term))
        condicion = Q()
        for posicion, campo in enumerate(self.campos_sin_acentos):
            alias = f"_busqueda_{posicion}"
            # alias() y no annotate(): la expresión va al WHERE, no al SELECT, y así
            # distinct() quita de verdad los duplicados
            queryset = queryset.alias(**{alias: sin_acentos(campo)})
            condicion |= Q(**{f"{alias}__contains": termino})
        # distinct(): buscar por principio activo une con la tabla puente
        return queryset.filter(condicion).distinct(), True
