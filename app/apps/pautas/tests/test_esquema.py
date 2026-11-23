"""Pautas: dosis, frecuencia, vigencias sin traslape y solo residentes/medicamentos activos.

Esquema de pautas (D6, HB-07). Corren como app_owner, salvo el de registro, que actúa como
app_user con ejecutar_sql(rol=...). Antes de TK-01 no hay mock: los datos son los mínimos de la
guía (un Residente activo, un Medicamento activo con la presentación semilla "tableta" y el
usuario "prueba.pautas").
ejecutar_sql sin params no interpola, así que el SQL literal de abajo no lleva "%"; el que pasa
params tampoco lleva "%" literal (se escribiría "%%").

Los errores se buscan con el nombre de la restricción entre comillas, como lo escribe
PostgreSQL ('... violates check constraint "ck_pauta_dosis"'), y los del trigger con su mensaje
completo, con el id del Residente o del Medicamento.

La definición del trigger va en su propio test, separada de las restricciones y los índices:
la crea otra migración (0002) y su rojo se distingue del de 0001.

"migrate pautas zero revierte todo" no es un test de pytest: se comprueba con
./scripts/migrate.sh pautas zero y ./scripts/migrate.sh en el cierre del ticket.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction

from apps.catalogo.models import Medicamento, Presentacion
from apps.entidades.models import Residente
from apps.entidades.services import registrar_residente
from apps.pautas.models import Pauta
from pruebas import ejecutar_sql

pytestmark = pytest.mark.django_db

MENSAJE_TRASLAPE = (
    "Ya hay una pauta vigente de este medicamento para el residente en esas fechas. "
    "Cierra la anterior antes de registrar la nueva."
)


@pytest.fixture
def datos():
    """Un residente activo, un medicamento activo y quien registra."""
    residente = registrar_residente(
        Residente(
            primer_nombre="Prueba",
            primer_apellido="Pauta",
            fecha_nacimiento=date(1940, 1, 1),
            fecha_ingreso=date(2026, 1, 5),
        )
    )
    medicamento = Medicamento.objects.create(
        nombre_comercial="Prueba",
        tipo="GENERICO",
        concentracion="50 mg",
        presentacion=Presentacion.objects.get(nombre="tableta"),
    )
    usuario = get_user_model().objects.create_user("prueba.pautas")
    return residente, medicamento, usuario


def pauta(datos, **cambios):
    residente, medicamento, usuario = datos
    valores = dict(
        residente=residente,
        medicamento=medicamento,
        dosis=Decimal("1"),
        frecuencia_horas=24,
        fecha_inicio=date(2026, 2, 1),
        registrado_por=usuario,
    )
    return Pauta(**(valores | cambios))


# --- Esquema: nombres, definiciones y tipos ---


@pytest.mark.parametrize(
    ("restriccion", "tipo", "fragmentos"),
    [
        ("ck_pauta_dosis", "c", ["CHECK", "(dosis > "]),
        ("ck_pauta_frecuencia", "c", ["CHECK", "frecuencia_horas >= 1", "frecuencia_horas <= 168"]),
        ("ck_pauta_fechas", "c", ["CHECK", "fecha_fin IS NULL", "fecha_inicio"]),
        (
            "ex_pauta_sin_traslape",
            "x",
            [
                "EXCLUDE USING gist",
                "residente_id WITH =",
                "medicamento_id WITH =",
                "daterange(fecha_inicio, fecha_fin, '[]'",
                "WITH &&",
            ],
        ),
    ],
    ids=["ck-dosis", "ck-frecuencia", "ck-fechas", "ex-sin-traslape"],
)
def test_restricciones_con_sus_nombres(restriccion, tipo, fragmentos):
    # Scenario: Restricciones, índices y trigger con sus nombres exactos (HB-07, criterio 1)
    # Desempacar exige exactamente 1 fila: la restricción existe en pauta y con ese nombre
    [(contype, definicion)] = ejecutar_sql(
        "SELECT contype, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = %s AND conrelid = 'pauta'::regclass",
        [restriccion],
    )
    assert contype == tipo
    for fragmento in fragmentos:
        assert fragmento in definicion


@pytest.mark.parametrize(
    ("indice", "fragmentos"),
    [
        (
            "ix_pauta_vigente",
            [
                "ON public.pauta USING btree",
                "(residente_id, medicamento_id)",
                "WHERE (fecha_fin IS NULL)",
            ],
        ),
        (
            "ix_pauta_residente_inicio",
            ["ON public.pauta USING btree", "(residente_id, fecha_inicio DESC)"],
        ),
    ],
    ids=["vigente", "residente-inicio"],
)
def test_indices_con_su_definicion(indice, fragmentos):
    # Scenario: Restricciones, índices y trigger con sus nombres exactos (HB-07, criterio 1)
    # Desempacar exige exactamente 1 fila: el índice existe en pauta y con ese nombre
    [(definicion,)] = ejecutar_sql(
        "SELECT indexdef FROM pg_indexes WHERE tablename = 'pauta' AND indexname = %s", [indice]
    )
    for fragmento in fragmentos:
        assert fragmento in definicion
    # ix_pauta_residente_inicio no es parcial: solo ix_pauta_vigente lleva WHERE
    if indice == "ix_pauta_residente_inicio":
        assert "WHERE" not in definicion


def test_trigger_con_su_definicion():
    # Scenario: Restricciones, índices y trigger con sus nombres exactos (HB-07, criterio 1)
    # Desempacar exige exactamente 1 fila: el trigger existe y con ese nombre
    [(tabla, definicion)] = ejecutar_sql(
        "SELECT tgrelid::regclass::text, pg_get_triggerdef(oid) FROM pg_trigger "
        "WHERE tgname = 'tg_pauta_validar' AND NOT tgisinternal"
    )
    assert tabla == "pauta"
    # "BEFORE INSERT ON" descarta un trigger que también se dispare con UPDATE
    assert "BEFORE INSERT ON " in definicion
    assert "FOR EACH ROW" in definicion
    assert "EXECUTE FUNCTION fn_pauta_validar()" in definicion
    # La función existe una sola vez, con ese nombre
    [(funcion,)] = ejecutar_sql("SELECT proname FROM pg_proc WHERE proname = 'fn_pauta_validar'")
    assert funcion == "fn_pauta_validar"


def indices_de_una_sola_columna(columna):
    """Nombres de los índices de pauta cuya única columna es `columna`."""
    return {
        nombre
        for (nombre,) in ejecutar_sql(
            "SELECT i.relname FROM pg_index x "
            "JOIN pg_class i ON i.oid = x.indexrelid "
            "JOIN pg_attribute a ON a.attrelid = x.indrelid AND a.attnum = x.indkey[0] "
            "WHERE x.indrelid = 'pauta'::regclass AND x.indnatts = 1 AND a.attname = %s",
            [columna],
        )
    }


def test_ningun_indice_tiene_solo_residente_id():
    # Scenario: Sin índice propio sobre residente_id (HB-07, descripción técnica)
    # Control: la consulta sí encuentra los índices de una sola columna que Django crea para
    # las FK medicamento y registrado_por; sin ellos, el conjunto vacío de abajo no probaría nada
    assert indices_de_una_sola_columna("medicamento_id")
    assert indices_de_una_sola_columna("registrado_por_id")
    # residente_id lo cubre ix_pauta_residente_inicio, que empieza por esa columna
    assert indices_de_una_sola_columna("residente_id") == set()


def test_tipos_de_la_dosis_y_de_la_frecuencia():
    # Scenario: Tipos de la dosis y de la frecuencia (HB-07, descripción técnica)
    # Desempacar exige exactamente 1 fila por columna
    [dosis] = ejecutar_sql(
        "SELECT data_type, numeric_precision, numeric_scale FROM information_schema.columns "
        "WHERE table_name = 'pauta' AND column_name = 'dosis'"
    )
    assert dosis == ("numeric", 6, 2)
    [(frecuencia,)] = ejecutar_sql(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name = 'pauta' AND column_name = 'frecuencia_horas'"
    )
    assert frecuencia == "smallint"


# --- Dosis, frecuencia y fechas válidas ---


@pytest.mark.parametrize(
    ("cambios", "restriccion"),
    [
        # Scenario: Dosis 0 (HB-07, criterio 2)
        ({"dosis": Decimal("0")}, "ck_pauta_dosis"),
        # Scenario: Frecuencia 0 o 169 (HB-07, criterio 2)
        ({"frecuencia_horas": 0}, "ck_pauta_frecuencia"),
        ({"frecuencia_horas": 169}, "ck_pauta_frecuencia"),
        # Scenario: Fin anterior al inicio (HB-07, criterio 2)
        # Los CHECK se evalúan antes de la exclusión: falla por ck_pauta_fechas y no por el
        # error de daterange
        ({"fecha_fin": date(2026, 1, 31)}, "ck_pauta_fechas"),
    ],
    ids=["dosis-0", "frecuencia-0", "frecuencia-169", "fin-antes-del-inicio"],
)
def test_la_base_rechaza_pautas_invalidas(datos, cambios, restriccion):
    # Exigir el nombre de la restricción descarta que falle por otra causa (un NOT NULL o una FK)
    with pytest.raises(IntegrityError, match=f'"{restriccion}"'):
        with transaction.atomic():
            pauta(datos, **cambios).save()


# --- Vigencias sin traslape ---


def test_dos_pautas_traslapadas_se_rechazan(datos):
    # Scenario: Dos Pautas traslapadas se rechazan (HB-07, criterio 3)
    pauta(datos).save()  # vigente desde el 1 de febrero, sin fin
    with pytest.raises(IntegrityError, match='"ex_pauta_sin_traslape"'):
        with transaction.atomic():
            pauta(datos, fecha_inicio=date(2026, 3, 1)).save()


def test_cerrar_la_vigente_permite_registrar_la_nueva(datos):
    # Scenario: Cerrar la vigente permite registrar la nueva (HB-07, criterio 3)
    anterior = pauta(datos)
    anterior.save()
    anterior.fecha_fin = date(2026, 2, 28)
    anterior.save()
    pauta(datos, fecha_inicio=date(2026, 3, 1), dosis=Decimal("0.5")).save()
    assert Pauta.objects.count() == 2
    # La cerrada y la nueva, leídas de la base
    assert list(Pauta.objects.order_by("fecha_inicio").values_list("fecha_fin", "dosis")) == [
        (date(2026, 2, 28), Decimal("1.00")),
        (None, Decimal("0.50")),
    ]


def test_el_mismo_dia_de_fin_e_inicio_se_traslapa(datos):
    # Scenario: El mismo día de fin e inicio se traslapa (HB-07, criterio 3)
    # El rango es '[]': ambos extremos cuentan
    pauta(datos, fecha_fin=date(2026, 2, 28)).save()
    with pytest.raises(IntegrityError, match='"ex_pauta_sin_traslape"'):
        with transaction.atomic():
            pauta(datos, fecha_inicio=date(2026, 2, 28)).save()


def test_la_validacion_del_modelo_avisa_el_traslape(datos):
    # Scenario: La validación del modelo avisa el traslape (HB-07, guía)
    pauta(datos).save()
    with pytest.raises(ValidationError, match="Ya hay una pauta vigente") as error:
        pauta(datos, fecha_inicio=date(2026, 3, 1)).full_clean()
    # El mensaje completo del contrato (match solo busca dentro de str(error))
    assert MENSAJE_TRASLAPE in error.value.messages


# --- Solo Residentes y Medicamentos activos ---


def test_no_se_registra_pauta_a_un_residente_egresado(datos):
    # Scenario: Residente egresado (HB-07, criterio 4)
    residente, _, _ = datos
    residente.estado, residente.fecha_baja = "EGRESADO", date(2026, 1, 20)
    residente.save()
    with pytest.raises(DatabaseError, match=f"El residente {residente.pk} no está activo"):
        with transaction.atomic():
            pauta(datos).save()


def test_no_se_registra_pauta_de_un_medicamento_dado_de_baja(datos):
    # Scenario: Medicamento dado de Baja (HB-07, criterio 4)
    _, medicamento, _ = datos
    medicamento.activo = False
    medicamento.save()
    with pytest.raises(DatabaseError, match=f"El medicamento {medicamento.pk} está dado de baja"):
        with transaction.atomic():
            pauta(datos).save()


def test_app_user_registra_una_pauta_valida(datos):
    # Scenario: app_user registra una Pauta válida (HB-07, criterios de revisión de BD)
    residente, medicamento, usuario = datos
    # Control: no había Pautas antes del INSERT
    assert not Pauta.objects.exists()
    # Sin si_necesario ni creado_en: los pone el DEFAULT de la base
    [(pauta_id,)] = ejecutar_sql(
        "INSERT INTO pauta (residente_id, medicamento_id, dosis, frecuencia_horas, "
        "fecha_inicio, registrado_por_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        [residente.pk, medicamento.pk, Decimal("1.5"), 8, date(2026, 2, 1), usuario.pk],
        rol="app_user",
    )
    registrada = Pauta.objects.get(pk=pauta_id)
    assert registrada.residente_id == residente.pk
    assert registrada.medicamento_id == medicamento.pk
    assert registrada.dosis == Decimal("1.50")
    assert registrada.frecuencia_horas == 8
    assert registrada.fecha_fin is None
    assert registrada.si_necesario is False
    assert registrada.creado_en is not None
