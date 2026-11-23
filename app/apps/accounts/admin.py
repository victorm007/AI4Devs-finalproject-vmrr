"""Usuarios y grupos en /admin/ (readme, sección 5, "Habilitadores"; HB-08).

Solo el Administrador (superusuario) ve estas secciones: los 2 grupos no tienen permisos
sobre usuarios ni grupos. Nadie borra: la baja de un usuario es is_active = False.
"""

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group

from apps.accounts.forms import UsuarioChangeForm, UsuarioCreationForm
from apps.accounts.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm
    list_display = ("username", "first_name", "last_name", "grupo", "is_active", "is_superuser")
    list_filter = ("is_active", "is_superuser", "groups")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "email")}),
        ("Acceso", {"fields": ("is_active", "is_superuser", "groups")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "email",
                    "groups",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("groups")  # sin N+1 en la lista

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "groups":
            kwargs["widget"] = forms.CheckboxSelectMultiple
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    @admin.display(description="Grupo")
    def grupo(self, usuario):
        return ", ".join(g.name for g in usuario.groups.all()) or "—"

    def has_delete_permission(self, request, obj=None):
        return False  # baja lógica: desmarcar "is_active"


# Los 2 grupos los crea la migración 0003_grupos: no se agregan ni se borran a mano
admin.site.unregister(Group)


@admin.register(Group)
class GrupoAdmin(GroupAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
