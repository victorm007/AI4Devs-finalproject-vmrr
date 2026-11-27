"""Solo se registran pautas de residentes activos y medicamentos activos (sección 3.3).

SQL copiado de la sección 3.3 del readme. La función es SECURITY INVOKER (por defecto):
app_user tiene SELECT sobre residente y medicamento por los privilegios de HB-03.
"""

from django.db import migrations

VALIDAR = """
CREATE FUNCTION fn_pauta_validar() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM residente
                   WHERE entidad_id = NEW.residente_id AND estado = 'ACTIVO') THEN
        RAISE EXCEPTION 'El residente % no está activo', NEW.residente_id;
    END IF;
    IF NOT (SELECT activo FROM medicamento WHERE id = NEW.medicamento_id) THEN
        RAISE EXCEPTION 'El medicamento % está dado de baja', NEW.medicamento_id;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_pauta_validar BEFORE INSERT ON pauta
    FOR EACH ROW EXECUTE FUNCTION fn_pauta_validar();
"""


class Migration(migrations.Migration):
    dependencies = [("pautas", "0001_initial")]
    operations = [
        migrations.RunSQL(
            VALIDAR,
            "DROP TRIGGER tg_pauta_validar ON pauta; DROP FUNCTION fn_pauta_validar();",
        ),
    ]
