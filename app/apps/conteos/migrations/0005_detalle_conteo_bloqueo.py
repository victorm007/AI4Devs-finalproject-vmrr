"""Cierre del conteo y captura de un renglón en paralelo (segunda revisión de TK-01, menor 5).

La función de 0003_detalle_conteo_cerrado leía el estado del conteo sin bloquear su fila. La
FK del renglón es diferida y solo toma FOR KEY SHARE, que no choca con el UPDATE del estado,
así que una captura y un cierre en paralelo se confirmaban los 2: quedaba un renglón en un
conteo cerrado. Ahora las 2 lecturas del estado (el conteo de OLD y el de NEW) llevan
FOR SHARE:
- si la captura llega primero, el UPDATE que cierra el conteo espera a que termine;
- si el cierre llega primero, la captura espera, vuelve a leer la fila confirmada, ve CERRADO
  y la base rechaza el renglón.

FOR SHARE exige UPDATE sobre conteo_fisico, que app_user tiene porque cierra conteos. Nunca se
bloquea movimiento, sobre el que app_user no tiene UPDATE (CLAUDE.md).

Es una migración nueva, y no un cambio de 0003, para que las bases que ya aplicaron 0003 se
pongan al día con ./scripts/migrate.sh. La reversa restaura el cuerpo de 0003, y el trigger
tg_detalle_conteo_cerrado no cambia.
"""

from django.db import migrations

DETALLE_CERRADO = """
CREATE OR REPLACE FUNCTION fn_detalle_conteo_cerrado() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE')
       AND (SELECT estado FROM conteo_fisico WHERE id = OLD.conteo_id FOR SHARE) = 'CERRADO' THEN
        RAISE EXCEPTION 'El conteo % está cerrado', OLD.conteo_id;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE')
       AND (SELECT estado FROM conteo_fisico WHERE id = NEW.conteo_id FOR SHARE) = 'CERRADO' THEN
        RAISE EXCEPTION 'El conteo % está cerrado', NEW.conteo_id;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
"""

# El cuerpo de 0003_detalle_conteo_cerrado, para la vuelta atrás
DETALLE_CERRADO_0003 = """
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


class Migration(migrations.Migration):
    dependencies = [("conteos", "0004_fk_sin_indice")]
    operations = [migrations.RunSQL(DETALLE_CERRADO, DETALLE_CERRADO_0003)]
