"""Permisos de los grupos sobre los modelos de inventario (readme, sección 3.2, D1; TK-01).

Los grupos nacen en accounts/0003_grupos (HB-08), antes que estos modelos. Nadie recibe
change_movimiento ni delete_movimiento: los movimientos son inmutables.
"""

from django.contrib.auth.management import create_permissions
from django.db import migrations

SOLO_LECTURA = ["view_existencia", "view_movimiento", "view_motivobaja"]
LECTURA_ESCRITURA = [*SOLO_LECTURA, "add_movimiento"]
GRUPOS = {"Solo lectura": SOLO_LECTURA, "Lectura y escritura": LECTURA_ESCRITURA}


def asignar_permisos(apps, schema_editor):
    # Django crea los permisos al final de migrate; aquí se fuerzan para poder asignarlos
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for grupo, codigos in GRUPOS.items():
        permisos = Permission.objects.filter(
            content_type__app_label="inventario", codename__in=codigos
        )
        Group.objects.get(name=grupo).permissions.add(*permisos)


def retirar_permisos(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    permisos = Permission.objects.filter(content_type__app_label="inventario")
    for grupo in apps.get_model("auth", "Group").objects.filter(name__in=GRUPOS):
        grupo.permissions.remove(*permisos)


class Migration(migrations.Migration):
    dependencies = [("inventario", "0002_motivos_baja"), ("accounts", "0003_grupos")]
    operations = [migrations.RunPython(asignar_permisos, retirar_permisos)]
