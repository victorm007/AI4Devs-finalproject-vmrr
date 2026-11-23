"""Formularios de usuario del panel: un solo grupo por usuario (readme, sección 3.2, D1; HB-08).

"A lo sumo uno" lo garantiza la base (uq_usuario_un_grupo); "al menos uno" lo valida
este formulario, con un mensaje claro en lugar de un error 500.
"""

from django import forms
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.contrib.auth.models import Group

from apps.accounts.models import Usuario

MENSAJE_GRUPO = "Elige exactamente un grupo: Solo lectura o Lectura y escritura."


class GrupoUnicoMixin:
    def clean(self):
        datos = super().clean()
        if not datos.get("is_superuser"):
            grupos = datos.get("groups")
            if grupos is None or len(grupos) != 1:
                self.add_error("groups", MENSAJE_GRUPO)
            # Los usuarios de los 2 grupos entran al panel (habilitadores, sección 5)
            datos["is_staff"] = True
            self.instance.is_staff = True
        return datos


class UsuarioCreationForm(GrupoUnicoMixin, AdminUserCreationForm):
    # required=False: el mensaje lo da GrupoUnicoMixin, igual que en el formulario de cambio
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Grupo",
    )

    class Meta(AdminUserCreationForm.Meta):
        model = Usuario
        fields = ("username", "first_name", "last_name", "email", "groups")


class UsuarioChangeForm(GrupoUnicoMixin, UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = "__all__"
