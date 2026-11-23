"""Cada usuario pertenece a un solo grupo (readme, sección 3.1, D1; HB-08).

"A lo sumo uno" lo garantiza esta restricción; "al menos uno" lo valida el formulario del
panel (apps/accounts/forms.py). Django no declara restricciones sobre la tabla puente que
genera para Usuario.groups, por eso va en RunSQL.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_grupos")]
    operations = [
        migrations.RunSQL(
            "ALTER TABLE usuario_groups ADD CONSTRAINT uq_usuario_un_grupo UNIQUE (usuario_id);",
            "ALTER TABLE usuario_groups DROP CONSTRAINT uq_usuario_un_grupo;",
        ),
    ]
