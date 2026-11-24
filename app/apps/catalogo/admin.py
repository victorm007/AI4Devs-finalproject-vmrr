"""Catálogo de medicamentos en /admin/ (readme, sección 5, "Habilitadores"; HB-09).

Nadie borra: la baja de un medicamento o de una presentación es activo = False. Los
mensajes de duplicado salen del violation_error_message de las restricciones de HB-05, que
el formulario valida antes de guardar.
"""

from django.contrib import admin

from apps.catalogo.models import (
    Medicamento,
    MedicamentoPrincipioActivo,
    Presentacion,
    PrincipioActivo,
)
from apps.panel import BusquedaSinAcentosMixin, SinBorrarMixin


@admin.register(Presentacion)
class PresentacionAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)  # muestra el buscador; la búsqueda real es sin acentos
    campos_sin_acentos = ("nombre",)
    ordering = ("nombre",)


@admin.register(PrincipioActivo)
class PrincipioActivoAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin):
    list_display = ("nombre", "creado_en")
    search_fields = ("nombre",)  # también habilita el autocomplete del medicamento
    campos_sin_acentos = ("nombre",)
    ordering = ("nombre",)


class PrincipioActivoEnLinea(admin.TabularInline):
    """Principios activos en la misma pantalla del medicamento (al menos uno)."""

    model = MedicamentoPrincipioActivo
    extra = 0
    min_num = 1
    validate_min = True
    can_delete = False  # un renglón equivocado se corrige cambiando el principio activo
    autocomplete_fields = ["principio_activo"]
    verbose_name = "principio activo"
    verbose_name_plural = "principios activos"

    def get_formset(self, request, obj=None, **kwargs):
        # El panel no pasa validate_min a inlineformset_factory (Django 5.2): sin esto,
        # min_num solo decide cuántos renglones se muestran y el alta sin renglones se guarda
        kwargs.setdefault("validate_min", self.validate_min)
        return super().get_formset(request, obj, **kwargs)


@admin.register(Medicamento)
class MedicamentoAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin):
    list_display = ("nombre_comercial", "concentracion", "presentacion", "tipo", "activo")
    list_filter = ("activo", "tipo", "presentacion")
    list_select_related = ("presentacion",)  # sin N+1 en la lista
    search_fields = ("nombre_comercial",)
    campos_sin_acentos = ("nombre_comercial", "principios_activos__nombre")
    fields = ("nombre_comercial", "tipo", "presentacion", "concentracion", "activo")
    inlines = [PrincipioActivoEnLinea]
    ordering = ("nombre_comercial",)
