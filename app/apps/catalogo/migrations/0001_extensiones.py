"""Extensiones y función f_unaccent (readme, sección 3.1).

Van antes que las tablas: los índices y restricciones del catálogo, de residentes y de
pautas las usan. app_owner puede crearlas porque es dueño de la base y las 3 son
extensiones "de confianza" (trusted) de PostgreSQL.
"""

from django.contrib.postgres.operations import (
    BtreeGistExtension,
    TrigramExtension,
    UnaccentExtension,
)
from django.db import migrations

# Envoltura IMMUTABLE de unaccent: PostgreSQL solo acepta funciones IMMUTABLE en índices
F_UNACCENT = """
CREATE FUNCTION f_unaccent(text) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    RETURN public.unaccent('public.unaccent'::regdictionary, $1);
"""


class Migration(migrations.Migration):
    initial = True
    # Las tablas que vienen después deben nacer con los permisos de app_user
    dependencies = [("accounts", "0002_privilegios")]
    operations = [
        BtreeGistExtension(),  # restricción de exclusión de pautas (HB-07)
        TrigramExtension(),    # pg_trgm: búsqueda parcial por nombre (sección 3.3)
        UnaccentExtension(),   # "Losartán" = "losartan"
        migrations.RunSQL(F_UNACCENT, "DROP FUNCTION f_unaccent(text);"),
    ]
