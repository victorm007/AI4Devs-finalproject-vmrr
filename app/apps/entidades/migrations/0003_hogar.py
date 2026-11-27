"""Dato semilla: la entidad HOGAR, única (readme, sección 3.1, "Datos semilla").

El nombre viene de settings.HOGAR_NOMBRE (variable de entorno). En una base nueva el
Hogar queda con id = 1, que el dataset mock y TK-01 dan por hecho.
"""

from django.conf import settings
from django.db import migrations


def crear_hogar(apps, schema_editor):
    entidad = apps.get_model("entidades", "Entidad")
    entidad.objects.get_or_create(tipo="HOGAR", defaults={"nombre": settings.HOGAR_NOMBRE})


def quitar_hogar(apps, schema_editor):
    apps.get_model("entidades", "Entidad").objects.filter(tipo="HOGAR").delete()


class Migration(migrations.Migration):
    dependencies = [("entidades", "0002_fk_compuesta")]
    operations = [migrations.RunPython(crear_hogar, quitar_hogar)]
