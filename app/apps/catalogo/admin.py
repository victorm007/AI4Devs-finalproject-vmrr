"""Catálogo de medicamentos en /admin/ (readme, sección 5, "Habilitadores"; HB-09).

Nadie borra: la baja de un medicamento o de una presentación es activo = False. Los
mensajes de duplicado salen del violation_error_message de las restricciones de HB-05, que
el formulario valida antes de guardar. La baja de un medicamento con existencias la avisa
MedicamentoAdminForm, antes que el trigger tg_medicamento_baja (TK-01).
"""

from django import forms
from django.contrib import admin
from django.db.models import Q

from apps.catalogo.forms import PrincipiosActivosFormSet
from apps.catalogo.models import (
    Medicamento,
    MedicamentoPrincipioActivo,
    Presentacion,
    PrincipioActivo,
)
from apps.inventario.models import Existencia
from apps.panel import BusquedaSinAcentosMixin, SinBorrarMixin

CON_EXISTENCIAS = "No se puede dar de baja: hay existencias de este medicamento."


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
    """Principios activos en la misma pantalla del medicamento (al menos uno).

    La regla "al menos uno" la aplica PrincipiosActivosFormSet, con el mensaje de
    apps.catalogo.validadores, en el alta y en el cambio. min_num y extra solo deciden que se
    muestre un renglón vacío: sin validate_min, para que el aviso genérico de Django no se
    sume al de la regla.
    """

    model = MedicamentoPrincipioActivo
    formset = PrincipiosActivosFormSet
    extra = 0
    min_num = 1
    can_delete = False  # un renglón equivocado se corrige cambiando el principio activo
    autocomplete_fields = ["principio_activo"]
    verbose_name = "principio activo"
    verbose_name_plural = "principios activos"


class MedicamentoAdminForm(forms.ModelForm):
    """Avisa en el campo activo, en lugar del error 500 del trigger tg_medicamento_baja.

    La base sigue siendo la última barrera (sección 3.3): este formulario solo da el mensaje
    (readme, sección 5, "Controles"). Solo lectura no tiene el campo editable, así que
    clean_activo no corre para él.
    """

    class Meta:
        model = Medicamento
        fields = "__all__"

    def clean_activo(self):
        activo = self.cleaned_data["activo"]
        # self.instance todavía tiene el valor guardado: los datos nuevos se copian después
        # de clean_activo (ModelForm._post_clean)
        dando_de_baja = self.instance.pk is not None and self.instance.activo and not activo
        if (
            dando_de_baja
            and Existencia.objects.filter(medicamento=self.instance, saldo__gt=0).exists()
        ):
            raise forms.ValidationError(CON_EXISTENCIAS)
        return activo


@admin.register(Medicamento)
class MedicamentoAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin):
    list_display = ("nombre_comercial", "concentracion", "presentacion", "tipo", "activo")
    list_filter = ("activo", "tipo", "presentacion")
    list_select_related = ("presentacion",)  # sin N+1 en la lista
    search_fields = ("nombre_comercial",)
    campos_sin_acentos = ("nombre_comercial", "principios_activos__nombre")
    fields = ("nombre_comercial", "tipo", "presentacion", "concentracion", "activo")
    form = MedicamentoAdminForm
    inlines = [PrincipioActivoEnLinea]
    ordering = ("nombre_comercial",)

    def get_form(self, request, obj=None, change=False, **kwargs):
        # Sin presentaciones dadas de baja en el alta (ADR-0009). Al cambiar un medicamento
        # se conserva la suya aunque esté inactiva, para poder guardarlo. get_form() arma una
        # clase nueva en cada petición: limitar base_fields no afecta a las demás
        form = super().get_form(request, obj, change=change, **kwargs)
        if "presentacion" in form.base_fields:  # Solo lectura no tiene el campo editable
            vigentes = Q(activo=True)
            if obj is not None:
                vigentes |= Q(pk=obj.presentacion_id)
            campo = form.base_fields["presentacion"]
            campo.queryset = Presentacion.objects.filter(vigentes).order_by("nombre")
        return form
