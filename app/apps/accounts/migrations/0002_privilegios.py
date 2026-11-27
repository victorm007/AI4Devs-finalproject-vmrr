"""Privilegios mínimos de app_user (readme, sección 6, HB-03).

Va en una migración, y no en db/init, porque los permisos por defecto son de cada
base de datos: así también se aplican en la base de tests que crea pytest.
Todas las tablas de las migraciones siguientes deben depender de esta.
"""

from django.db import migrations

OTORGAR = """
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
-- Las tablas que creen las migraciones siguientes nacen con estos permisos
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_user;
"""

RETIRAR = """
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE USAGE, SELECT ON SEQUENCES FROM app_user;
REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM app_user;
REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM app_user;
"""


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.RunSQL(OTORGAR, RETIRAR)]
