"""Grupos Solo lectura y Lectura y escritura (readme, secciones 3.1 y 3.2, D1; HB-08).

Permisos sobre los modelos de los habilitadores (catálogo y residentes). Nadie recibe
delete_*: la baja es lógica. Entidad no recibe permisos (el Hogar no se edita y los residentes
se dan de alta con registrar_residente()), ni Pauta, que no está en el panel. TK-01 agrega
después los de inventario (su 0003).
"""

from django.contrib.auth.management import create_permissions
from django.db import migrations

MODELOS = {
    "catalogo": ["presentacion", "principioactivo", "medicamento", "medicamentoprincipioactivo"],
    "entidades": ["residente"],
}
GRUPOS = {
    "Solo lectura": ["view"],
    "Lectura y escritura": ["view", "add", "change"],
}


def crear_grupos(apps, schema_editor):
    # Django crea los permisos al final de migrate; aquí se fuerzan para poder asignarlos
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    grupo = apps.get_model("auth", "Group")
    permiso = apps.get_model("auth", "Permission")
    for nombre, acciones in GRUPOS.items():
        codigos = [
            f"{accion}_{modelo}"
            for modelos in MODELOS.values()
            for modelo in modelos
            for accion in acciones
        ]
        permisos = permiso.objects.filter(
            content_type__app_label__in=MODELOS, codename__in=codigos
        )
        grupo.objects.get_or_create(name=nombre)[0].permissions.add(*permisos)


def quitar_grupos(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=GRUPOS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_privilegios"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("catalogo", "0003_presentaciones"),
        ("entidades", "0004_mensaje_nombres"),
    ]
    operations = [migrations.RunPython(crear_grupos, quitar_grupos)]
