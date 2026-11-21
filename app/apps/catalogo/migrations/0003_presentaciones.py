"""Presentaciones más comunes (readme, sección 3.1, "Datos semilla"). Idempotente."""

from django.db import migrations

PRESENTACIONES = [
    "tableta", "cápsula", "jarabe", "gotas", "ampolleta", "parche", "crema", "inhalador",
]


def crear(apps, schema_editor):
    presentacion = apps.get_model("catalogo", "Presentacion")
    for nombre in PRESENTACIONES:
        presentacion.objects.get_or_create(nombre=nombre)


def quitar(apps, schema_editor):
    apps.get_model("catalogo", "Presentacion").objects.filter(nombre__in=PRESENTACIONES).delete()


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0002_modelos")]
    operations = [migrations.RunPython(crear, quitar)]
