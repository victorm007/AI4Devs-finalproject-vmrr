-- =====================================================================
-- Carga del dataset mock (demo.json) en PostgreSQL usando funciones JSON
--
-- Requisitos:
--   * Base recién migrada (manage.py migrate): existen el HOGAR, los grupos,
--     las presentaciones y los motivos de baja (datos semilla).
--   * No hay datos de negocio cargados (el script lo verifica).
--
-- Uso (desde la raíz del repositorio):
--   docker compose cp app/fixtures/mock/. db:/tmp/mock/
--   docker compose exec db psql -U <usuario> -d <base> -v ON_ERROR_STOP=1 -f /tmp/mock/cargar_mock.sql
--
-- Todo corre en una sola transacción: si cualquier validación falla, no se
-- carga nada. Los triggers y CHECK de la sección 3 del readme siguen activos
-- y también validan los datos.
-- =====================================================================

\set ON_ERROR_STOP on
\set mock_json `cat /tmp/mock/demo.json`

BEGIN;

CREATE TEMP TABLE mock ON COMMIT DROP AS
SELECT :'mock_json'::jsonb AS doc;

-- ---------------------------------------------------------------------
-- 0. Verificaciones previas
-- ---------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM entidad WHERE tipo = 'HOGAR') THEN
        RAISE EXCEPTION 'Falta la entidad HOGAR: ejecute primero las migraciones';
    END IF;
    IF EXISTS (SELECT 1 FROM medicamento) OR EXISTS (SELECT 1 FROM movimiento)
       OR EXISTS (SELECT 1 FROM residente) THEN
        RAISE EXCEPTION 'La base ya tiene datos de negocio: el mock solo se carga en una base recién migrada';
    END IF;
END $$;

-- Nota: las búsquedas de catálogos (grupo, presentación, motivo, usuario,
-- entidad) usan LEFT JOIN a propósito: si una referencia del JSON no existe,
-- la columna queda NULL y la restricción NOT NULL / CHECK aborta la carga,
-- en lugar de omitir la fila en silencio.

-- ---------------------------------------------------------------------
-- 1. Usuarios y su grupo (D1)
-- ---------------------------------------------------------------------
INSERT INTO usuario (username, password, first_name, last_name, email,
                     is_active, is_superuser, is_staff, date_joined)
SELECT u.username, u.password_hash, u.first_name, u.last_name, u.email,
       true, false, true, now()   -- is_staff: entran a /admin/ (habilitadores, sección 5)
FROM mock CROSS JOIN LATERAL
     jsonb_to_recordset(doc -> 'usuarios')
         AS u(username text, password_hash text, first_name text, last_name text, email text);

INSERT INTO usuario_groups (usuario_id, group_id)
SELECT us.id, g.id
FROM mock CROSS JOIN LATERAL
     jsonb_to_recordset(doc -> 'usuarios') AS u(username text, grupo text)
     JOIN usuario us ON us.username = u.username
     LEFT JOIN auth_group g ON g.name = u.grupo;

-- ---------------------------------------------------------------------
-- 2. Catálogo: principios activos, medicamentos y su relación (D2)
-- ---------------------------------------------------------------------
INSERT INTO principio_activo (nombre, creado_en)
SELECT p.nombre, now()
FROM mock CROSS JOIN LATERAL jsonb_array_elements_text(doc -> 'principios_activos') AS p(nombre);

INSERT INTO medicamento (id, nombre_comercial, tipo, presentacion_id, concentracion,
                         activo, creado_en, actualizado_en)
SELECT m.id, m.nombre_comercial, m.tipo, pr.id, m.concentracion, true, now(), now()
FROM mock CROSS JOIN LATERAL
     jsonb_to_recordset(doc -> 'medicamentos')
         AS m(id bigint, nombre_comercial text, tipo text, presentacion text, concentracion text)
     LEFT JOIN presentacion pr
            ON f_unaccent(lower(pr.nombre)) = f_unaccent(lower(m.presentacion));

INSERT INTO medicamento_principio_activo (medicamento_id, principio_activo_id)
SELECT m.id, pa.id
FROM mock CROSS JOIN LATERAL
     jsonb_to_recordset(doc -> 'medicamentos') AS m(id bigint, principios_activos jsonb)
     CROSS JOIN LATERAL jsonb_array_elements_text(m.principios_activos) AS p(nombre)
     LEFT JOIN principio_activo pa
            ON f_unaccent(lower(pa.nombre)) = f_unaccent(lower(p.nombre));

-- ---------------------------------------------------------------------
-- 3. Residentes: supertipo entidad + subtipo residente (D3)
-- ---------------------------------------------------------------------
INSERT INTO entidad (id, tipo, nombre, creado_en, actualizado_en)
SELECT r.id, 'RESIDENTE', NULL, now(), now()
FROM mock CROSS JOIN LATERAL jsonb_to_recordset(doc -> 'residentes') AS r(id bigint);

INSERT INTO residente (entidad_id, tipo, primer_nombre, segundo_nombre, primer_apellido,
                       segundo_apellido, fecha_nacimiento, fecha_ingreso, estado, fecha_baja)
SELECT r.id, 'RESIDENTE', r.primer_nombre, r.segundo_nombre, r.primer_apellido,
       r.segundo_apellido, r.fecha_nacimiento, r.fecha_ingreso, 'ACTIVO', NULL
FROM mock CROSS JOIN LATERAL
     jsonb_to_recordset(doc -> 'residentes')
         AS r(id bigint, primer_nombre text, segundo_nombre text, primer_apellido text,
              segundo_apellido text, fecha_nacimiento date, fecha_ingreso date);

-- Traduce las referencias del JSON ("HOGAR" o id de residente) a entidad.id
CREATE TEMP TABLE ref_entidad ON COMMIT DROP AS
SELECT 'HOGAR'::text AS ref, id AS entidad_id FROM entidad WHERE tipo = 'HOGAR'
UNION ALL
SELECT r.id::text, r.id FROM mock CROSS JOIN LATERAL jsonb_to_recordset(doc -> 'residentes') AS r(id bigint);

-- ---------------------------------------------------------------------
-- 4. Pautas (D6)
-- ---------------------------------------------------------------------
INSERT INTO pauta (residente_id, medicamento_id, dosis, frecuencia_horas, si_necesario,
                   indicaciones, fecha_inicio, fecha_fin, registrado_por_id, creado_en)
SELECT p.residente_id, p.medicamento_id, p.dosis, p.frecuencia_horas, p.si_necesario,
       p.indicaciones, p.fecha_inicio, p.fecha_fin, us.id, p.fecha_inicio::timestamptz
FROM mock CROSS JOIN LATERAL
     jsonb_to_recordset(doc -> 'pautas')
         AS p(residente_id bigint, medicamento_id bigint, dosis numeric, frecuencia_horas smallint,
              si_necesario boolean, indicaciones text, fecha_inicio date, fecha_fin date,
              registrado_por text)
     LEFT JOIN usuario us ON us.username = p.registrado_por;

-- ---------------------------------------------------------------------
-- 5. Movimientos (D5)
-- ---------------------------------------------------------------------
INSERT INTO movimiento (id, tipo, medicamento_id, cantidad, entidad_origen_id, entidad_destino_id,
                        motivo_baja_id, origen_entrada, entregado_por, corrige_a_id, nota,
                        usuario_id, fecha_hora)
SELECT mv.id, mv.tipo, mv.medicamento_id, mv.cantidad, o.entidad_id, d.entidad_id,
       mb.id, mv.origen_entrada, mv.entregado_por, mv.corrige_a_id, mv.nota,
       us.id, mv.fecha_hora
FROM mock CROSS JOIN LATERAL
     jsonb_to_recordset(doc -> 'movimientos')
         AS mv(id bigint, fecha_hora timestamptz, tipo text, medicamento_id bigint, cantidad numeric,
               origen text, destino text, motivo_baja text, origen_entrada text,
               entregado_por text, corrige_a_id bigint, nota text, usuario text)
     LEFT JOIN ref_entidad o ON o.ref = mv.origen
     LEFT JOIN ref_entidad d ON d.ref = mv.destino
     LEFT JOIN motivo_baja mb ON mb.clave = mv.motivo_baja
     LEFT JOIN usuario us ON us.username = mv.usuario
ORDER BY mv.id;

-- Efecto de cada movimiento sobre el saldo de una entidad (+ entra, - sale)
CREATE TEMP VIEW v_delta AS
SELECT id, fecha_hora, entidad_destino_id AS entidad_id, medicamento_id, cantidad AS delta
FROM movimiento WHERE entidad_destino_id IS NOT NULL
UNION ALL
SELECT id, fecha_hora, entidad_origen_id, medicamento_id, -cantidad
FROM movimiento WHERE entidad_origen_id IS NOT NULL;

-- Ningún saldo puede quedar negativo en ningún momento de la historia
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM (SELECT sum(delta) OVER (PARTITION BY entidad_id, medicamento_id
                                      ORDER BY fecha_hora, id) AS saldo_parcial
              FROM v_delta) x
        WHERE saldo_parcial < 0
    ) THEN
        RAISE EXCEPTION 'Los movimientos del mock dejan un saldo negativo en algún momento';
    END IF;
END $$;

-- ---------------------------------------------------------------------
-- 6. Existencias (D4): se calculan desde los movimientos, nunca a mano
-- ---------------------------------------------------------------------
INSERT INTO existencia (entidad_id, medicamento_id, saldo, actualizado_en)
SELECT entidad_id, medicamento_id, sum(delta), max(fecha_hora)
FROM v_delta
GROUP BY entidad_id, medicamento_id;

-- Deben coincidir exactamente con existencias_esperadas del JSON
DO $$
BEGIN
    IF EXISTS (
        (SELECT r.entidad_id, e.medicamento_id, e.saldo
         FROM mock CROSS JOIN LATERAL
              jsonb_to_recordset(doc -> 'existencias_esperadas')
                  AS e(entidad text, medicamento_id bigint, saldo numeric)
              JOIN ref_entidad r ON r.ref = e.entidad
         EXCEPT
         SELECT entidad_id, medicamento_id, saldo FROM existencia)
        UNION ALL
        (SELECT entidad_id, medicamento_id, saldo FROM existencia
         EXCEPT
         SELECT r.entidad_id, e.medicamento_id, e.saldo
         FROM mock CROSS JOIN LATERAL
              jsonb_to_recordset(doc -> 'existencias_esperadas')
                  AS e(entidad text, medicamento_id bigint, saldo numeric)
              JOIN ref_entidad r ON r.ref = e.entidad)
    ) THEN
        RAISE EXCEPTION 'Las existencias calculadas no coinciden con existencias_esperadas del JSON';
    END IF;
END $$;

-- ---------------------------------------------------------------------
-- 7. Conteos físicos: se insertan EN_PROCESO, se agregan renglones y luego
--    se cierran los que corresponda (el trigger impide tocar uno cerrado)
-- ---------------------------------------------------------------------
INSERT INTO conteo_fisico (id, entidad_id, periodo_inicio, periodo_fin, estado, usuario_id,
                           creado_en, cerrado_en, nota)
SELECT c.id, r.entidad_id, c.periodo_inicio, c.periodo_fin, 'EN_PROCESO', us.id,
       c.creado_en, NULL, c.nota
FROM mock CROSS JOIN LATERAL
     jsonb_to_recordset(doc -> 'conteos')
         AS c(id bigint, entidad text, periodo_inicio date, periodo_fin date, usuario text,
              creado_en timestamptz, nota text)
     LEFT JOIN ref_entidad r ON r.ref = c.entidad
     LEFT JOIN usuario us ON us.username = c.usuario;

INSERT INTO detalle_conteo (conteo_id, medicamento_id, cantidad_fisica, cantidad_sistema)
SELECT c.id, d.medicamento_id, d.cantidad_fisica, d.cantidad_sistema
FROM mock CROSS JOIN LATERAL
     jsonb_to_recordset(doc -> 'conteos') AS c(id bigint, detalles jsonb)
     CROSS JOIN LATERAL jsonb_to_recordset(c.detalles)
         AS d(medicamento_id bigint, cantidad_fisica numeric, cantidad_sistema numeric);

-- La foto del saldo de cada renglón debe ser el saldo real a la hora del conteo
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM detalle_conteo dc
        JOIN conteo_fisico cf ON cf.id = dc.conteo_id
        WHERE dc.cantidad_sistema <> COALESCE((
            SELECT sum(v.delta) FROM v_delta v
            WHERE v.entidad_id = cf.entidad_id
              AND v.medicamento_id = dc.medicamento_id
              AND v.fecha_hora <= cf.creado_en), 0)
    ) THEN
        RAISE EXCEPTION 'cantidad_sistema de algún conteo no coincide con el saldo a la hora del conteo';
    END IF;
END $$;

UPDATE conteo_fisico cf
SET estado = 'CERRADO', cerrado_en = c.cerrado_en
FROM mock CROSS JOIN LATERAL
     jsonb_to_recordset(doc -> 'conteos') AS c(id bigint, estado text, cerrado_en timestamptz)
WHERE cf.id = c.id AND c.estado = 'CERRADO';

-- ---------------------------------------------------------------------
-- 8. Reajusta las secuencias de identidad tras insertar ids explícitos
-- ---------------------------------------------------------------------
SELECT setval(pg_get_serial_sequence('medicamento', 'id'),   (SELECT max(id) FROM medicamento));
SELECT setval(pg_get_serial_sequence('entidad', 'id'),       (SELECT max(id) FROM entidad));
SELECT setval(pg_get_serial_sequence('movimiento', 'id'),    (SELECT max(id) FROM movimiento));
SELECT setval(pg_get_serial_sequence('conteo_fisico', 'id'), (SELECT max(id) FROM conteo_fisico));

DROP VIEW v_delta;

-- ---------------------------------------------------------------------
-- 9. Resumen
-- ---------------------------------------------------------------------
SELECT 'usuarios' AS tabla, count(*) AS filas FROM usuario WHERE username LIKE '%.demo'
UNION ALL SELECT 'principios_activos', count(*) FROM principio_activo
UNION ALL SELECT 'medicamentos', count(*) FROM medicamento
UNION ALL SELECT 'residentes', count(*) FROM residente
UNION ALL SELECT 'pautas', count(*) FROM pauta
UNION ALL SELECT 'movimientos', count(*) FROM movimiento
UNION ALL SELECT 'existencias', count(*) FROM existencia
UNION ALL SELECT 'conteos', count(*) FROM conteo_fisico
UNION ALL SELECT 'detalles de conteo', count(*) FROM detalle_conteo;

COMMIT;
