"""Usuarios del sistema (readme, sección 3.2, D1).

Se define desde el inicio del proyecto, como recomienda Django. No agrega campos:
el nivel de acceso lo da el grupo (Solo lectura o Lectura y escritura, HB-08).
"""

from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    class Meta:
        db_table = "usuario"  # su tabla puente de grupos se llama usuario_groups
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
