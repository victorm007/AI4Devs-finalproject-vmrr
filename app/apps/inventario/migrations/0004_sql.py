"""Triggers, vista de conciliación, fillfactor y REVOKE de inventario (readme, sección 3.3).

Cada RunSQL lleva su reversa, para que migrate inventario zero funcione.
"""

from django.db import migrations

INMUTABLE = """
CREATE FUNCTION fn_movimiento_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Los movimientos son inmutables: registre un movimiento de corrección';
END $$;
CREATE TRIGGER tg_movimiento_inmutable BEFORE UPDATE OR DELETE ON movimiento
    FOR EACH ROW EXECUTE FUNCTION fn_movimiento_inmutable();
"""

# Las correcciones quedan exentas: devuelven lo que salió aunque el destino ya no esté activo
VALIDAR_DESTINO = """
CREATE FUNCTION fn_movimiento_validar_destino() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.entidad_destino_id IS NOT NULL AND NEW.corrige_a_id IS NULL THEN
        IF NOT (SELECT activo FROM medicamento WHERE id = NEW.medicamento_id) THEN
            RAISE EXCEPTION 'El medicamento % está dado de baja', NEW.medicamento_id;
        END IF;
        IF EXISTS (SELECT 1 FROM residente
                   WHERE entidad_id = NEW.entidad_destino_id AND estado <> 'ACTIVO') THEN
            RAISE EXCEPTION 'La entidad destino % no está activa', NEW.entidad_destino_id;
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_movimiento_validar_destino BEFORE INSERT ON movimiento
    FOR EACH ROW EXECUTE FUNCTION fn_movimiento_validar_destino();
"""

# Es del catálogo (HB-05), pero consulta existencia: nace con esta tabla (sección 3.3)
MEDICAMENTO_BAJA = """
CREATE FUNCTION fn_medicamento_baja_sin_existencias() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.activo AND NOT NEW.activo AND EXISTS (
        SELECT 1 FROM existencia WHERE medicamento_id = NEW.id AND saldo > 0) THEN
        RAISE EXCEPTION 'No se puede dar de baja el medicamento %: tiene existencias', NEW.id;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_medicamento_baja BEFORE UPDATE OF activo ON medicamento
    FOR EACH ROW EXECUTE FUNCTION fn_medicamento_baja_sin_existencias();
"""

# Las existencias cuyo saldo no es la suma de sus movimientos. Vacía = todo cuadra
CONCILIACION = """
CREATE VIEW v_conciliacion_existencia AS
WITH suma AS (
    SELECT entidad_destino_id AS entidad_id, medicamento_id, cantidad FROM movimiento
     WHERE entidad_destino_id IS NOT NULL
    UNION ALL
    SELECT entidad_origen_id, medicamento_id, -cantidad FROM movimiento
     WHERE entidad_origen_id IS NOT NULL
)
SELECT coalesce(e.entidad_id, s.entidad_id)         AS entidad_id,
       coalesce(e.medicamento_id, s.medicamento_id) AS medicamento_id,
       coalesce(e.saldo, 0)                         AS saldo,
       coalesce(s.total, 0)                         AS suma_movimientos
FROM existencia e
FULL JOIN (SELECT entidad_id, medicamento_id, sum(cantidad) AS total
           FROM suma GROUP BY 1, 2) s
  ON s.entidad_id = e.entidad_id AND s.medicamento_id = e.medicamento_id
WHERE coalesce(e.saldo, 0) <> coalesce(s.total, 0);
"""


class Migration(migrations.Migration):
    dependencies = [("inventario", "0003_permisos_grupos")]
    operations = [
        migrations.RunSQL(
            INMUTABLE,
            "DROP TRIGGER tg_movimiento_inmutable ON movimiento; "
            "DROP FUNCTION fn_movimiento_inmutable();",
        ),
        migrations.RunSQL(
            VALIDAR_DESTINO,
            "DROP TRIGGER tg_movimiento_validar_destino ON movimiento; "
            "DROP FUNCTION fn_movimiento_validar_destino();",
        ),
        migrations.RunSQL(
            MEDICAMENTO_BAJA,
            "DROP TRIGGER tg_medicamento_baja ON medicamento; "
            "DROP FUNCTION fn_medicamento_baja_sin_existencias();",
        ),
        migrations.RunSQL(
            "ALTER TABLE existencia SET (fillfactor = 90);",
            "ALTER TABLE existencia RESET (fillfactor);",
        ),
        migrations.RunSQL(CONCILIACION, "DROP VIEW v_conciliacion_existencia;"),
        # Doble barrera de la inmutabilidad: además del trigger, app_user no tiene el permiso.
        # La reversa devuelve lo que daba accounts/0002_privilegios (TRUNCATE nunca lo tuvo)
        migrations.RunSQL(
            "REVOKE UPDATE, DELETE, TRUNCATE ON movimiento FROM app_user;",
            "GRANT UPDATE, DELETE ON movimiento TO app_user;",
        ),
    ]
