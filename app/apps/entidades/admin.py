"""Residentes en /admin/ (readme, sección 5, "Habilitadores"; HB-09).

El Hogar es fijo (lo crea la migración): Entidad no se registra en el panel. El alta pasa
por registrar_residente(), que crea la entidad y el residente juntos. Nadie borra: el
egreso o la defunción se registran con el estado y la fecha de baja.
"""

from django.contrib import admin

from apps.entidades.models import Residente
from apps.entidades.services import registrar_residente
from apps.expresiones import sin_acentos
from apps.panel import BusquedaSinAcentosMixin, SinBorrarMixin

CAMPOS_ALTA = (
    "primer_nombre",
    "segundo_nombre",
    "primer_apellido",
    "segundo_apellido",
    "fecha_nacimiento",
    "fecha_ingreso",
)


@admin.register(Residente)
class ResidenteAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin):
    list_display = ("nombre_completo", "estado", "fecha_ingreso", "fecha_baja")
    list_filter = ("estado",)
    search_fields = ("primer_apellido",)  # muestra el buscador; la búsqueda real es sin acentos
    campos_sin_acentos = (
        "primer_nombre",
        "segundo_nombre",
        "primer_apellido",
        "segundo_apellido",
    )
    # Por apellido y nombre sin acentos: la misma expresión de ix_residente_nombre (consulta 3)
    ordering = (sin_acentos("primer_apellido").asc(), sin_acentos("primer_nombre").asc())

    def get_fields(self, request, obj=None):
        # En el alta no se elige el estado: todo residente nuevo empieza ACTIVO
        return CAMPOS_ALTA if obj is None else (*CAMPOS_ALTA, "estado", "fecha_baja")

    def save_model(self, request, obj, form, change):
        if change:
            obj.save()  # cambio de datos, egreso o defunción (el formulario ya validó las reglas)
        else:
            registrar_residente(obj)  # crea la entidad y el residente juntos

    @admin.display(description="Nombre", ordering=sin_acentos("primer_apellido"))
    def nombre_completo(self, residente):
        return residente.nombre_completo
