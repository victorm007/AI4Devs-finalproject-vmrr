"""Un renglón tampoco sale de un conteo cerrado (revisión de TK-01, hallazgo 2).

La función de 0002_triggers miraba solo el conteo de NEW en un UPDATE: un
UPDATE detalle_conteo SET conteo_id = <otro> sacaba un renglón de un conteo CERRADO
hacia uno EN_PROCESO. Ahora rechaza el UPDATE y el DELETE si el conteo de OLD está
cerrado, y el INSERT y el UPDATE si lo está el de NEW. El trigger
tg_detalle_conteo_cerrado no cambia (BEFORE INSERT OR UPDATE OR DELETE).

Es una migración nueva, y no un cambio de 0002, para que las bases que ya aplicaron
0002 se pongan al día con ./scripts/migrate.sh. La reversa restaura el cuerpo de 0002.
"""

from django.db import migrations

DETALLE_CERRADO = """
CREATE OR REPLACE FUNCTION fn_detalle_conteo_cerrado() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE')
       AND (SELECT estado FROM conteo_fisico WHERE id = OLD.conteo_id) = 'CERRADO' THEN
        RAISE EXCEPTION 'El conteo % está cerrado', OLD.conteo_id;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE')
       AND (SELECT estado FROM conteo_fisico WHERE id = NEW.conteo_id) = 'CERRADO' THEN
        RAISE EXCEPTION 'El conteo % está cerrado', NEW.conteo_id;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
"""

# El cuerpo de 0002_triggers, para la vuelta atrás
DETALLE_CERRADO_0002 = """
CREATE OR REPLACE FUNCTION fn_detalle_conteo_cerrado() RETURNS trigger LANGUAGE plpgsql AS $$
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
"""


class Migration(migrations.Migration):
    dependencies = [("conteos", "0002_triggers")]
    operations = [migrations.RunSQL(DETALLE_CERRADO, DETALLE_CERRADO_0002)]
