"""Motivos de baja semilla (readme, sección 3.1, "Datos semilla"; TK-01).

CORRECCION está reservado: solo lo usa services.corregir (TK-02).
"""

from django.db import migrations

MOTIVOS = [
    ("CONSUMO", "Consumo / administración"),
    ("CADUCIDAD", "Caducidad"),
    ("MERMA", "Merma"),
    ("ROTURA", "Rotura"),
    ("DEVOLUCION_FAMILIA", "Devolución a la familia"),
    ("DEFUNCION", "Defunción"),
    ("EGRESO", "Egreso"),
    ("CORRECCION", "Corrección de un movimiento"),
]


def crear_motivos(apps, schema_editor):
    MotivoBaja = apps.get_model("inventario", "MotivoBaja")
    for clave, descripcion in MOTIVOS:
        MotivoBaja.objects.update_or_create(clave=clave, defaults={"descripcion": descripcion})


def borrar_motivos(apps, schema_editor):
    apps.get_model("inventario", "MotivoBaja").objects.filter(
        clave__in=[clave for clave, _ in MOTIVOS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("inventario", "0001_initial")]
    operations = [migrations.RunPython(crear_motivos, borrar_motivos)]
