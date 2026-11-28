"""Un conteo cerrado no se modifica, ni sus renglones (readme, sección 3.3; TK-01)."""

from django.db import migrations

CONTEO_CERRADO = """
CREATE FUNCTION fn_conteo_cerrado() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.estado = 'CERRADO' THEN
        RAISE EXCEPTION 'El conteo % está cerrado y no se puede modificar', OLD.id;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_conteo_cerrado BEFORE UPDATE OR DELETE ON conteo_fisico
    FOR EACH ROW EXECUTE FUNCTION fn_conteo_cerrado();
"""

DETALLE_CERRADO = """
CREATE FUNCTION fn_detalle_conteo_cerrado() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_conteo bigint;
BEGIN
    IF TG_OP = 'DELETE' THEN v_conteo := OLD.conteo_id; ELSE v_conteo := NEW.conteo_id; END IF;
    IF (SELECT estado FROM conteo_fisico WHERE id = v_conteo) = 'CERRADO' THEN
        RAISE EXCEPTION 'El conteo % está cerrado', v_conteo;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_detalle_conteo_cerrado BEFORE INSERT OR UPDATE OR DELETE ON detalle_conteo
    FOR EACH ROW EXECUTE FUNCTION fn_detalle_conteo_cerrado();
"""


class Migration(migrations.Migration):
    dependencies = [("conteos", "0001_initial")]
    operations = [
        migrations.RunSQL(
            CONTEO_CERRADO,
            "DROP TRIGGER tg_conteo_cerrado ON conteo_fisico; DROP FUNCTION fn_conteo_cerrado();",
        ),
        migrations.RunSQL(
            DETALLE_CERRADO,
            "DROP TRIGGER tg_detalle_conteo_cerrado ON detalle_conteo; "
            "DROP FUNCTION fn_detalle_conteo_cerrado();",
        ),
    ]
