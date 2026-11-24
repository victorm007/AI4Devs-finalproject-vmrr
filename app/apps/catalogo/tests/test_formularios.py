"""La regla "al menos un principio activo" y el conjunto de renglones del medicamento.

Revisión adversarial de HB-09, hallazgo 4. Capa de formularios: la regla de
apps.catalogo.validadores (exigir_principio_activo, que no toca la base y reutilizará la API
de escritura de la V2) y el conjunto de renglones de apps.catalogo.forms
(PrincipiosActivosFormSet), sin pasar por HTTP. El panel /admin/ se prueba en test_admin.py.

El conjunto se arma con inlineformset_factory, como lo hace el inline del panel (min_num=1,
extra=0 y sin validate_min), así que el único aviso por falta de principio activo es el de la
regla, no el genérico de min_num de Django.

Antes de TK-01 no hay mock: los datos mínimos son el principio activo "Losartán" y un
medicamento en la presentación semilla "tableta" (la crea la migración de catalogo).

Rojo esperado: apps.catalogo.validadores y apps.catalogo.forms no existen, así que falla la
importación del módulo.

Ajuste 3 (segunda revisión de HB-09, hallazgos 1, 4, 5, 7 y 9): la regla con None (sin
colección) se rechaza con la misma ValidationError que la lista vacía, y un texto (str o bytes)
en lugar de una colección es un TypeError, un error de programación y no una regla de negocio.
Rojo esperado: hoy None da TypeError, "abc" y b"x" pasan la regla (list() les da elementos) y ""
da ValidationError.
"""

import pytest
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory

from apps.catalogo.forms import PrincipiosActivosFormSet
from apps.catalogo.models import (
    Medicamento,
    MedicamentoPrincipioActivo,
    Presentacion,
    PrincipioActivo,
)
from apps.catalogo.validadores import SIN_PRINCIPIO_ACTIVO, exigir_principio_activo

pytestmark = pytest.mark.django_db
MENSAJE = "Un medicamento debe tener al menos un principio activo."
PREFIJO = "medicamentoprincipioactivo_set"

ConjuntoDePrincipios = inlineformset_factory(
    Medicamento,
    MedicamentoPrincipioActivo,
    formset=PrincipiosActivosFormSet,
    fields=["principio_activo"],
    extra=0,
    min_num=1,
    can_delete=False,
)


@pytest.fixture
def losartan():
    return PrincipioActivo.objects.create(nombre="Losartán")


@pytest.fixture
def medicamento():
    """Un medicamento guardado sin principios activos (el dueño de los renglones)."""
    return Medicamento.objects.create(
        nombre_comercial="Cozaar",
        tipo="GENERICO",
        concentracion="50 mg",
        presentacion=Presentacion.objects.get(nombre="tableta"),
    )


def renglones(*principios_activos):
    """Los datos del conjunto, con un renglón nuevo por cada valor (un pk o "")."""
    datos = {
        f"{PREFIJO}-TOTAL_FORMS": str(len(principios_activos)),
        f"{PREFIJO}-INITIAL_FORMS": "0",
        f"{PREFIJO}-MIN_NUM_FORMS": "1",
        f"{PREFIJO}-MAX_NUM_FORMS": "1000",
    }
    for i, principio_activo in enumerate(principios_activos):
        datos[f"{PREFIJO}-{i}-principio_activo"] = principio_activo
    return datos


def conjunto(medicamento, datos):
    return ConjuntoDePrincipios(datos, instance=medicamento, prefix=PREFIJO)


@pytest.mark.parametrize(
    "vacia",
    [[], (), PrincipioActivo.objects.none()],
    ids=["lista", "tupla", "queryset"],
)
def test_la_regla_rechaza_una_lista_vacia(vacia):
    # Scenario: La regla se puede reutilizar fuera del panel (revisión de HB-09, hallazgo 4)
    # El texto del contrato, literal: es el que verá el usuario en el panel y en la V2
    assert SIN_PRINCIPIO_ACTIVO == MENSAJE
    with pytest.raises(ValidationError) as error:
        exigir_principio_activo(vacia)
    assert error.value.code == "sin_principio_activo"
    assert error.value.messages == [MENSAJE]


def test_la_regla_acepta_un_principio_activo(losartan):
    # Scenario: La regla se puede reutilizar fuera del panel (revisión de HB-09, hallazgo 4):
    # una lista con un principio activo se acepta, sea de ids (como principios_activos_ids de
    # la V2) o de objetos (como los elige el formulario)
    assert exigir_principio_activo([1]) is None
    assert exigir_principio_activo([losartan]) is None


def test_la_regla_rechaza_sin_coleccion():
    # Scenario: La regla se puede reutilizar fuera del panel (segunda revisión de HB-09,
    # hallazgo 4): sin colección (None) se rechaza con el mismo mensaje y código
    with pytest.raises(ValidationError) as error:
        exigir_principio_activo(None)
    assert error.value.code == "sin_principio_activo"
    assert error.value.messages == [MENSAJE]


@pytest.mark.parametrize("texto", ["abc", "", b"x"], ids=["texto", "texto-vacio", "bytes"])
def test_un_texto_no_es_una_coleccion(texto):
    # Scenario: La regla se puede reutilizar fuera del panel (segunda revisión de HB-09,
    # hallazgo 4): un texto en lugar de una colección es un error de programación (TypeError),
    # no una regla de negocio. ValidationError no hereda de TypeError, así que el texto vacío
    # no pasa por rechazarse como lista vacía
    with pytest.raises(TypeError):
        exigir_principio_activo(texto)


def test_el_conjunto_sin_renglones_avisa(medicamento):
    # Scenario: Cambio sin principio activo (revisión de HB-09, hallazgo 4), en la capa del
    # formulario: sin renglones, el conjunto avisa con la regla y solo con ella
    formset = conjunto(medicamento, renglones())
    assert not formset.is_valid()
    assert list(formset.non_form_errors()) == [SIN_PRINCIPIO_ACTIVO]


def test_el_conjunto_con_renglon_vacio_avisa(medicamento):
    # Scenario: Sin principio activo, el formulario avisa (HB-09, criterio 2), en la capa del
    # formulario: el renglón vacío que muestra el panel no cuenta como principio activo
    formset = conjunto(medicamento, renglones(""))
    assert not formset.is_valid()
    assert SIN_PRINCIPIO_ACTIVO in formset.non_form_errors()


def test_el_conjunto_con_un_principio_activo_es_valido(medicamento, losartan):
    # Scenario: Alta con su principio activo (HB-09, criterio 2), en la capa del formulario:
    # control positivo de los 2 anteriores, con los mismos datos salvo el principio activo
    formset = conjunto(medicamento, renglones(losartan.pk))
    assert formset.is_valid(), formset.errors
    assert list(formset.non_form_errors()) == []
