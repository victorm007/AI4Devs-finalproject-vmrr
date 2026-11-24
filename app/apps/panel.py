"""Reglas comunes del panel /admin/ (readme, sección 5, "Controles"; HB-09).

Los mixins van antes de admin.ModelAdmin en la herencia, para que sus métodos reemplacen
a los del panel:

    class MedicamentoAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin): ...
"""

from django.core import checks
from django.db.models import Q, Value
from django.db.models.lookups import Contains
from django.utils.text import smart_split, unescape_string_literal

from apps.expresiones import sin_acentos


class SinBorrarMixin:
    """Sin la acción "Eliminar": la baja es lógica (activo o estado).

    El panel quita la acción de la lista y el botón de la página, y responde 403 en
    .../delete/, también al Administrador (superusuario).
    """

    def has_delete_permission(self, request, obj=None):
        return False


def palabras_de_busqueda(search_term: str) -> list[str]:
    """Divide el término en palabras, como el panel de Django: "cozaar losartan" da 2.

    Una frase entre comillas cuenta como una sola palabra, sin las comillas. Los espacios
    sobrantes no cuentan: " losartan " da ["losartan"] y " " no da ninguna.
    """
    palabras = []
    for bit in smart_split(search_term):
        if len(bit) > 1 and bit[0] in "\"'" and bit[0] == bit[-1]:
            bit = unescape_string_literal(bit)
        if bit.strip():
            palabras.append(bit.strip())
    return palabras


class BusquedaSinAcentosMixin:
    """La búsqueda ignora mayúsculas y acentos: "losartan" encuentra "Losartán".

    Compara f_unaccent(lower(campo)) contra f_unaccent(lower(palabra)), la misma expresión
    de los índices trigram (sección 3.3, ADR-0017). Cada palabra debe aparecer en alguno de
    los campos, y todas las palabras deben coincidir. La subclase define campos_sin_acentos
    (sin ellos, check() da el error panel.E001); search_fields sigue declarado solo para que
    el panel muestre el buscador y permita el autocomplete. Sin mínimo de caracteres ni
    UNION: eso es de la búsqueda de existencias.
    """

    campos_sin_acentos: tuple[str, ...] = ()

    def check(self, **kwargs):
        errores = super().check(**kwargs)
        if not getattr(self, "campos_sin_acentos", ()):
            errores.append(
                checks.Error(
                    f"{self.__class__.__name__} usa BusquedaSinAcentosMixin y no declara "
                    "campos_sin_acentos: su búsqueda devolvería todas las filas.",
                    hint="Declara campos_sin_acentos con los campos donde buscar, por "
                    'ejemplo ("nombre",).',
                    obj=self.__class__,
                    id="panel.E001",
                )
            )
        return errores

    def get_search_results(self, request, queryset, search_term):
        palabras = palabras_de_busqueda(search_term)
        if not palabras:
            return queryset, False
        for palabra in palabras:
            termino = sin_acentos(Value(palabra))
            # Un filter() por palabra, como el panel de Django: en los campos de varios
            # valores (principios_activos__nombre) cada palabra tiene su propia unión con la
            # tabla puente, y "losartan hidroclorotiazida" encuentra Hyzaar. Las expresiones
            # van al WHERE, no al SELECT, y así distinct() quita de verdad los duplicados
            queryset = queryset.filter(
                Q(
                    *(Contains(sin_acentos(campo), termino) for campo in self.campos_sin_acentos),
                    _connector=Q.OR,
                )
            )
        # distinct(): buscar por principio activo une con la tabla puente
        return queryset.distinct(), True
