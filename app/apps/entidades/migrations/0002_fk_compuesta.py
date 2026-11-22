"""FK compuesta residente -> entidad (readme, sección 3.1).

Garantiza que solo una entidad de tipo RESIDENTE tenga fila en residente: la fila
(entidad_id, 'RESIDENTE') debe existir en entidad. Django no declara FK compuestas,
por eso va en SQL. Su destino, uq_entidad_id_tipo, nace en 0001_initial.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("entidades", "0001_initial")]
    operations = [
        migrations.RunSQL(
            "ALTER TABLE residente ADD CONSTRAINT fk_residente_entidad "
            "FOREIGN KEY (entidad_id, tipo) REFERENCES entidad (id, tipo) ON DELETE RESTRICT;",
            "ALTER TABLE residente DROP CONSTRAINT fk_residente_entidad;",
        ),
    ]
