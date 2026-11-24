"""Catálogo en /admin/: permisos por grupo, principio activo en línea, sin borrado y búsqueda.

HB-09. Capa HTTP: el panel /admin/ con el cliente de pruebas de Django. admin_client es el
fixture de pytest-django: un superusuario (el Administrador) con sesión iniciada. Antes de
TK-01 no hay mock: los usuarios de prueba son "prueba.*", creados con create_user; los 2 grupos
los crea la migración 0003_grupos de accounts, y las 8 presentaciones semilla, la de catalogo.

Los usuarios de grupo entran con force_login, nunca con client.login(), que choca con
django-axes. entrar_como da un Client nuevo en cada llamada, para poder usar 2 usuarios en el
mismo test.

Cada 403 lleva un control positivo (la misma persona sí ve otra página del panel), y después
de un 403 de cambio o de borrado se comprueba que el registro sigue igual en la base.

Rojo esperado: antes de HB-09 ninguno de estos modelos está registrado en el panel, así que sus
URL responden 404 (y el autocomplete, 403 por un modelo que el panel no conoce).

Las búsquedas cuentan los resultados con context["cl"].result_count además de buscar el texto,
porque el término buscado también se pinta en la página.

Ajustes de la revisión adversarial de HB-09 (hallazgos 1, 2, 3, 6, 7, 8 y 9): búsqueda por
palabras y sin espacios sobrantes, presentación duplicada sin acentos con mensaje, el alta sin
presentaciones dadas de baja (el cambio conserva la suya), error de configuración panel.E001,
el alta como app_user, la CSP sin <style> ni on*= en el alta, la lista y el cambio, y el 403 y
la búsqueda de las listas de presentaciones y principios activos. El alta como app_user hace
SET LOCAL ROLE app_user en línea, en la conexión del test (la misma que usa el cliente de
Django), después de force_login: el fixture como_app_user nace en TK-01.

Rojo esperado de los ajustes: la búsqueda de varias palabras o con espacios no encuentra nada,
"Tableta" se guarda junto a "tableta", el alta ofrece y guarda la presentación dada de baja, y
panel.E001 no existe. Los de app_user, CSP, 403 de Solo lectura, búsqueda en las listas de
presentaciones y principios activos, y el cambio con la presentación dada de baja son de
regresión: pasan desde el inicio y protegen lo que HB-09 ya entregó.

Ajuste 2 de la revisión de HB-09 (hallazgo 4): sin principio activo, el alta y el cambio
muestran el mensaje legible de apps.catalogo.validadores (SIN_PRINCIPIO_ACTIVO) como único
error del conjunto de renglones, en lugar del aviso genérico de min_num, y no guardan. Rojo
esperado: apps.catalogo.validadores no existe, así que falla la importación de todo el módulo
(sin ella, el panel solo daría el aviso genérico de Django).

Ajuste 3 (segunda revisión de HB-09, hallazgos 1, 4, 5, 7 y 9): la búsqueda con un medicamento
de 2 principios activos (cada palabra coincide con uno distinto y el medicamento sale una sola
vez), los comodines % y _ buscados como texto, el tope de 8 palabras (MAXIMO_PALABRAS y
palabras_de_busqueda de apps.panel), panel.E002 para un campo de búsqueda que no existe, y el
<option> de la presentación dada de baja en el HTML del alta (ausente) y del cambio (presente).
Rojo esperado: con 9 palabras se usan todas y no se encuentra nada; MAXIMO_PALABRAS no existe
(se importa dentro de su test para no tumbar el módulo), y panel.E002 tampoco. Los de varios
principios activos, comodines y el <option> de las presentaciones son de regresión: HB-09 ya
filtra palabra por palabra, escapa los comodines y limita el alta a las presentaciones activas.
"""

import re

import pytest
from django.contrib import admin
from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import Client

from apps.catalogo.models import (
    Medicamento,
    MedicamentoPrincipioActivo,
    Presentacion,
    PrincipioActivo,
)
from apps.catalogo.validadores import SIN_PRINCIPIO_ACTIVO
from apps.entidades.models import Residente
from apps.panel import BusquedaSinAcentosMixin

pytestmark = [pytest.mark.django_db, pytest.mark.http]
URL = "/admin/catalogo/medicamento/"
URL_PRESENTACION = "/admin/catalogo/presentacion/"
EN_LINEA = "medicamentoprincipioactivo_set"
MODELOS = ["presentacion", "principioactivo", "medicamento"]
AVISO_MEDICAMENTO = "Ya existe un medicamento con ese nombre, presentación y concentración"
AVISO_PRINCIPIO = "Ya existe ese principio activo"
AVISO_PRESENTACION = "Ya existe esa presentación"
# Una etiqueta <script> sin atributo src, y cualquier etiqueta con atributo style
SCRIPT_EN_LINEA = re.compile(r"<script\b(?![^>]*\bsrc\s*=)[^>]*>", re.IGNORECASE)
SCRIPT_CON_SRC = re.compile(r"<script\b[^>]*\bsrc\s*=", re.IGNORECASE)
ATRIBUTO_STYLE = re.compile(r"<[^>]*\sstyle\s*=", re.IGNORECASE)
# Una etiqueta <style>, y cualquier etiqueta con un manejador de eventos (onclick=, onload=...)
ETIQUETA_STYLE = re.compile(r"<style\b", re.IGNORECASE)
MANEJADOR_ON = re.compile(r"<[^>]*\son[a-z]+\s*=", re.IGNORECASE)


def codigo_en_linea(html):
    """Lo que la CSP bloquearía: <script> sin src, <style>, atributos style y manejadores on*=."""
    return [
        coincidencia
        for patron in (SCRIPT_EN_LINEA, ETIQUETA_STYLE, ATRIBUTO_STYLE, MANEJADOR_ON)
        for coincidencia in patron.findall(html)
    ]


def rol_actual():
    """El rol con el que corre ahora la conexión del test (y la del cliente de Django)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        return cursor.fetchone()[0]


def campo_presentacion(respuesta):
    """El campo presentación del formulario del medicamento que pintó el panel."""
    return respuesta.context["adminform"].form.fields["presentacion"]


SELECT_PRESENTACION = re.compile(
    r'<select\b[^>]*\bname="presentacion"[^>]*>(.*?)</select>', re.IGNORECASE | re.DOTALL
)


def html_de_presentaciones(respuesta):
    """Las opciones del <select> de presentación tal como llegan en el HTML.

    Solo ese <select>: así un <option> de otro campo (el principio activo del renglón) con el
    mismo valor no cuenta.
    """
    coincidencia = SELECT_PRESENTACION.search(respuesta.content.decode())
    # Control: la página pinta el <select> de presentación
    assert coincidencia, "la página no tiene el <select> de presentación"
    return coincidencia.group(1)


@pytest.fixture
def entrar_como():
    """Devuelve un Client con la sesión de un usuario del grupo dado (un usuario por grupo)."""
    usuarios = {}

    def entrar(grupo):
        if grupo not in usuarios:
            nombre = "prueba." + grupo.split()[0].lower()  # prueba.solo o prueba.lectura
            usuario = get_user_model().objects.create_user(nombre, is_staff=True)
            usuario.groups.add(Group.objects.get(name=grupo))
            usuarios[grupo] = usuario
        cliente = Client()
        cliente.force_login(usuarios[grupo])
        return cliente

    return entrar


@pytest.fixture
def losartan():
    return PrincipioActivo.objects.create(nombre="Losartán")


def formulario(principio_activo, filas=1, **cambios):
    """POST del alta de un medicamento con su principio activo en línea."""
    datos = {
        "nombre_comercial": "Losartán",
        "tipo": "GENERICO",
        "concentracion": "50 mg",
        "presentacion": Presentacion.objects.get(nombre="tableta").pk,
        "activo": "on",
        f"{EN_LINEA}-TOTAL_FORMS": str(filas),
        f"{EN_LINEA}-INITIAL_FORMS": "0",
        f"{EN_LINEA}-MIN_NUM_FORMS": "1",
        f"{EN_LINEA}-MAX_NUM_FORMS": "1000",
        f"{EN_LINEA}-0-principio_activo": principio_activo.pk,
    }
    return datos | cambios


def formulario_de_cambio(medicamento, principio_activo, **cambios):
    """POST del cambio de un medicamento que ya tiene un renglón de principio activo."""
    return formulario(principio_activo, **cambios) | {
        f"{EN_LINEA}-INITIAL_FORMS": "1",
        f"{EN_LINEA}-0-id": medicamento.medicamentoprincipioactivo_set.get().pk,
        f"{EN_LINEA}-0-medicamento": medicamento.pk,
    }


def registrar(
    nombre_comercial, principio_activo=None, presentacion="tableta", concentracion="50 mg"
):
    """Registra un medicamento directamente con el ORM, sin pasar por el panel."""
    medicamento = Medicamento.objects.create(
        nombre_comercial=nombre_comercial,
        tipo="GENERICO",
        concentracion=concentracion,
        presentacion=Presentacion.objects.get(nombre=presentacion),
    )
    if principio_activo is not None:
        MedicamentoPrincipioActivo.objects.create(
            medicamento=medicamento, principio_activo=principio_activo
        )
    return medicamento


@pytest.mark.parametrize("modelo", MODELOS)
def test_solo_lectura_consulta_el_catalogo(entrar_como, modelo):
    # Scenario: Solo lectura consulta el catálogo (HB-09, criterio 1)
    cliente = entrar_como("Solo lectura")
    # Control: la lista responde 200; el 403 del alta no es por falta de sesión
    assert cliente.get(f"/admin/catalogo/{modelo}/").status_code == 200
    assert cliente.get(f"/admin/catalogo/{modelo}/add/").status_code == 403


def test_solo_lectura_no_cambia_un_medicamento(entrar_como, losartan):
    # Scenario: Solo lectura no cambia un medicamento (HB-09, criterio 1)
    medicamento = registrar("Losartán", losartan)
    url = f"{URL}{medicamento.pk}/change/"
    # Control positivo del botón de guardar: en la página editable de Lectura y escritura sí
    # aparece, así que su ausencia de abajo se debe al modo de consulta
    editable = entrar_como("Lectura y escritura").get(url)
    assert editable.status_code == 200
    assert 'name="_save"' in editable.content.decode()
    cliente = entrar_como("Solo lectura")
    consulta = cliente.get(url)
    assert consulta.status_code == 200
    assert 'name="_save"' not in consulta.content.decode()
    datos = formulario_de_cambio(medicamento, losartan, concentracion="100 mg")
    assert cliente.post(url, datos).status_code == 403
    # El medicamento queda igual
    medicamento.refresh_from_db()
    assert medicamento.concentracion == "50 mg"
    assert medicamento.activo is True


@pytest.mark.parametrize("modelo", MODELOS)
def test_lectura_y_escritura_abre_el_alta(entrar_como, modelo):
    # Scenario: Lectura y escritura abre el alta del catálogo (HB-09, criterio 1; readme,
    # sección 5)
    assert (
        entrar_como("Lectura y escritura").get(f"/admin/catalogo/{modelo}/add/").status_code == 200
    )


def test_lectura_y_escritura_da_de_alta_con_su_principio_activo(entrar_como, losartan):
    # Scenario: Alta con su principio activo (HB-09, criterio 2)
    # Control: no hay medicamentos antes del alta
    assert not Medicamento.objects.exists()
    respuesta = entrar_como("Lectura y escritura").post(f"{URL}add/", formulario(losartan))
    assert respuesta.status_code == 302
    medicamento = Medicamento.objects.get(nombre_comercial="Losartán")
    assert list(medicamento.principios_activos.all()) == [losartan]
    assert medicamento.concentracion == "50 mg"
    assert medicamento.presentacion.nombre == "tableta"


def errores_del_conjunto(respuesta):
    """Los errores no de formulario (non_form_errors) de los renglones en línea del panel."""
    return [
        str(error)
        for inline in respuesta.context["inline_admin_formsets"]
        for error in inline.formset.non_form_errors()
    ]


def test_sin_principio_activo_el_formulario_avisa(entrar_como, losartan):
    # Scenario: Sin principio activo, el formulario avisa (HB-09, criterio 2)
    respuesta = entrar_como("Lectura y escritura").post(f"{URL}add/", formulario(losartan, filas=0))
    assert respuesta.status_code == 200
    assert SIN_PRINCIPIO_ACTIVO in respuesta.content.decode()
    # El aviso es del conjunto de renglones de principios activos (PrincipiosActivosFormSet,
    # revisión de HB-09, hallazgo 4), y es el único: sin el aviso genérico de min_num de Django
    assert errores_del_conjunto(respuesta) == [SIN_PRINCIPIO_ACTIVO]
    assert not Medicamento.objects.exists()


@pytest.mark.parametrize("renglones", ["renglon-vacio", "sin-renglones"])
def test_el_cambio_sin_principio_activo_avisa(entrar_como, losartan, renglones):
    # Scenario: Cambio sin principio activo (revisión de HB-09, hallazgo 4)
    # Registrado con el ORM, sin principio activo: como si se hubiera cargado fuera del panel
    medicamento = registrar("Losartán")
    url = f"{URL}{medicamento.pk}/change/"
    # Sin renglones iniciales, el POST del cambio tiene la forma del alta
    if renglones == "renglon-vacio":
        datos = formulario(losartan, concentracion="100 mg") | {
            f"{EN_LINEA}-0-principio_activo": "",
            f"{EN_LINEA}-0-medicamento": medicamento.pk,
        }
    else:
        datos = formulario(losartan, filas=0, concentracion="100 mg")
        del datos[f"{EN_LINEA}-0-principio_activo"]
    cliente = entrar_como("Lectura y escritura")
    respuesta = cliente.post(url, datos)
    assert respuesta.status_code == 200
    assert SIN_PRINCIPIO_ACTIVO in respuesta.content.decode()
    assert SIN_PRINCIPIO_ACTIVO in errores_del_conjunto(respuesta)
    # El medicamento queda igual
    medicamento.refresh_from_db()
    assert medicamento.concentracion == "50 mg"
    assert not medicamento.principios_activos.exists()
    # Control positivo: el mismo cambio, eligiendo un principio activo, sí se guarda; el aviso
    # se debe a la falta de principio activo y no a otro campo del POST
    datos = formulario(losartan, concentracion="100 mg") | {
        f"{EN_LINEA}-0-medicamento": medicamento.pk,
    }
    assert cliente.post(url, datos).status_code == 302
    medicamento.refresh_from_db()
    assert medicamento.concentracion == "100 mg"
    assert list(medicamento.principios_activos.all()) == [losartan]


def test_el_buscador_de_principios_activos_ignora_acentos(entrar_como, losartan):
    # Scenario: El buscador de principios activos ignora los acentos (HB-09, descripción técnica)
    PrincipioActivo.objects.create(nombre="Metformina")
    cliente = entrar_como("Lectura y escritura")
    parametros = {
        "app_label": "catalogo",
        "model_name": "medicamentoprincipioactivo",
        "field_name": "principio_activo",
    }
    respuesta = cliente.get("/admin/autocomplete/", parametros | {"term": "losartan"})
    assert respuesta.status_code == 200
    # Solo Losartán: el buscador filtra (Metformina también existe)
    assert [r["text"] for r in respuesta.json()["results"]] == ["Losartán"]
    # Control negativo: un término que no coincide no devuelve nada
    otra = cliente.get("/admin/autocomplete/", parametros | {"term": "paracetamol"})
    assert otra.status_code == 200
    assert otra.json()["results"] == []


def test_el_duplicado_sin_acentos_da_un_mensaje_y_no_un_500(entrar_como, losartan):
    # Scenario: Medicamento duplicado sin acentos (HB-09, criterio 3)
    cliente = entrar_como("Lectura y escritura")
    # Control: el primer alta sí se guarda
    assert cliente.post(f"{URL}add/", formulario(losartan)).status_code == 302
    respuesta = cliente.post(
        f"{URL}add/", formulario(losartan, nombre_comercial="LOSARTAN", concentracion="50 MG")
    )
    assert respuesta.status_code == 200
    assert AVISO_MEDICAMENTO in respuesta.content.decode()
    assert Medicamento.objects.count() == 1


def test_principio_activo_duplicado_da_un_mensaje(entrar_como, losartan):
    # Scenario: Principio activo duplicado sin acentos (readme, sección 5, "Validaciones
    # incluidas")
    cliente = entrar_como("Lectura y escritura")
    url = "/admin/catalogo/principioactivo/add/"
    respuesta = cliente.post(url, {"nombre": "LOSARTAN"})
    assert respuesta.status_code == 200
    assert AVISO_PRINCIPIO in respuesta.content.decode()
    assert PrincipioActivo.objects.count() == 1
    # Control: el mismo formulario con otro nombre sí guarda; el aviso se debe al duplicado y
    # no a un campo que falte en el POST
    assert cliente.post(url, {"nombre": "Metformina"}).status_code == 302
    assert PrincipioActivo.objects.count() == 2


def test_la_baja_es_logica(entrar_como, losartan):
    # Scenario: Desmarcar activo da de baja el medicamento (HB-09, criterio 4)
    cliente = entrar_como("Lectura y escritura")
    assert cliente.post(f"{URL}add/", formulario(losartan)).status_code == 302
    medicamento = Medicamento.objects.get()
    # Control: empieza activo
    assert medicamento.activo is True
    datos = formulario_de_cambio(medicamento, losartan)
    del datos["activo"]  # casilla desmarcada
    assert cliente.post(f"{URL}{medicamento.pk}/change/", datos).status_code == 302
    medicamento.refresh_from_db()
    assert medicamento.activo is False
    # Sigue registrado, con su principio activo
    assert list(medicamento.principios_activos.all()) == [losartan]


def objeto_del_catalogo(modelo, losartan):
    if modelo == "presentacion":
        return Presentacion.objects.create(nombre="parche prueba")
    if modelo == "principioactivo":
        return losartan
    return registrar("Prueba", losartan, concentracion="1 mg")


@pytest.mark.parametrize("quien", ["administrador", "lectura-escritura"])
@pytest.mark.parametrize("modelo", MODELOS)
def test_nadie_borra_del_catalogo(entrar_como, admin_client, losartan, modelo, quien):
    # Scenario: Nadie borra del catálogo (HB-09, criterio 4)
    cliente = admin_client if quien == "administrador" else entrar_como("Lectura y escritura")
    objeto = objeto_del_catalogo(modelo, losartan)
    url = f"/admin/catalogo/{modelo}/{objeto.pk}/"
    # Control: la misma persona sí abre la página de cambio del mismo registro
    assert cliente.get(f"{url}change/").status_code == 200
    assert cliente.get(f"{url}delete/").status_code == 403
    assert cliente.post(f"{url}delete/", {"post": "yes"}).status_code == 403
    # El registro sigue en la base
    assert type(objeto).objects.filter(pk=objeto.pk).exists()


def test_la_lista_no_ofrece_eliminar(admin_client, losartan):
    # Scenario: Sin la acción "Eliminar" en las listas (readme, sección 5, "Controles")
    registrar("Losartán", losartan)
    respuesta = admin_client.get(URL)
    # Control: la lista se abre y muestra el medicamento
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "Losartán" in html
    assert "delete_selected" not in html


def test_la_busqueda_ignora_mayusculas_y_acentos(entrar_como, losartan):
    # Scenario: Por principio activo (HB-09, criterio 5)
    registrar("Cozaar", losartan)
    cliente = entrar_como("Lectura y escritura")
    for termino in ("COZAAR", "losartan"):  # por nombre comercial y por principio activo
        respuesta = cliente.get(URL, {"q": termino})
        assert respuesta.status_code == 200
        assert respuesta.context["cl"].result_count == 1
        assert "Cozaar" in respuesta.content.decode()
    # Control negativo: otro término no lo incluye
    respuesta = cliente.get(URL, {"q": "paracetamol"})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 0
    assert "Cozaar" not in respuesta.content.decode()


def test_la_busqueda_por_nombre_comercial_ignora_acentos(entrar_como):
    # Scenario: Por nombre comercial (HB-09, criterio 5)
    # Sin principio activo (la base lo permite): "losartan" solo puede coincidir con el nombre
    # comercial, no con un principio activo
    registrar("Losartán")
    cliente = entrar_como("Lectura y escritura")
    respuesta = cliente.get(URL, {"q": "losartan"})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 1
    assert "Losartán" in respuesta.content.decode()
    # Control negativo
    respuesta = cliente.get(URL, {"q": "paracetamol"})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 0
    assert "Losartán" not in respuesta.content.decode()


def test_la_lista_de_medicamentos_no_hace_n_mas_1(
    entrar_como, losartan, django_assert_max_num_queries, django_assert_num_queries
):
    # Scenario: Mismo número de consultas con 1 y con 3 medicamentos (HB-09, descripción técnica)
    registrar("Losartán", losartan)
    cliente = entrar_como("Lectura y escritura")
    # Calienta la sesión y las cachés del proceso (tipos de contenido) antes de medir
    assert cliente.get(URL).status_code == 200
    with django_assert_max_num_queries(100) as consultas:
        respuesta = cliente.get(URL)
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 1
    n = len(consultas)
    # 2 más, en presentaciones distintas y con sus propios principios activos
    omeprazol = PrincipioActivo.objects.create(nombre="Omeprazol")
    paracetamol = PrincipioActivo.objects.create(nombre="Paracetamol")
    registrar("Omeprazol", omeprazol, presentacion="cápsula", concentracion="20 mg")
    registrar("Tempra", paracetamol, presentacion="jarabe", concentracion="160 mg / 5 ml")
    with django_assert_num_queries(n):
        respuesta = cliente.get(URL)
    assert respuesta.status_code == 200
    # Control: la segunda medida sí muestra los 3
    assert respuesta.context["cl"].result_count == 3


def test_el_alta_no_tiene_codigo_en_linea(entrar_como):
    # Scenario: Alta del medicamento sin código en línea (HB-09, definición de hecho)
    respuesta = entrar_como("Lectura y escritura").get(f"{URL}add/")
    assert respuesta.status_code == 200
    assert respuesta.headers.get("Content-Security-Policy")
    html = respuesta.content.decode()
    # Control: es la página con el buscador de principios activos y carga scripts externos;
    # así, la ausencia de código en línea no se debe a una página vacía
    assert "admin-autocomplete" in html
    assert SCRIPT_CON_SRC.search(html)
    # Ampliado en la revisión de HB-09 (hallazgo 7): también sin <style> ni manejadores on*=
    assert codigo_en_linea(html) == []


def test_la_lista_y_el_cambio_no_tienen_codigo_en_linea(entrar_como, losartan):
    # Scenario: Lista y cambio del medicamento sin código en línea (revisión de HB-09,
    # hallazgo 7). Regresión: HB-09 ya cumple la CSP en estas páginas
    medicamento = registrar("Cozaar", losartan)
    cliente = entrar_como("Lectura y escritura")
    lista = cliente.get(URL)
    cambio = cliente.get(f"{URL}{medicamento.pk}/change/")
    for respuesta in (lista, cambio):
        assert respuesta.status_code == 200
        assert respuesta.headers.get("Content-Security-Policy")
    # Control: son las páginas de verdad (la lista con el medicamento y el formulario
    # editable), y cargan scripts externos; no una página vacía
    assert lista.context["cl"].result_count == 1
    assert "Cozaar" in lista.content.decode()
    assert 'name="_save"' in cambio.content.decode()
    for respuesta in (lista, cambio):
        html = respuesta.content.decode()
        assert SCRIPT_CON_SRC.search(html)
        assert codigo_en_linea(html) == []


def test_el_panel_avisa_de_una_presentacion_duplicada(entrar_como):
    # Scenario: El panel avisa de una presentación duplicada (revisión de HB-09, hallazgo 2)
    cliente = entrar_como("Lectura y escritura")
    # Control: las 8 semillas, entre ellas "tableta"
    assert Presentacion.objects.count() == 8
    assert Presentacion.objects.filter(nombre="tableta").exists()
    respuesta = cliente.post(f"{URL_PRESENTACION}add/", {"nombre": "Tableta", "activo": "on"})
    assert respuesta.status_code == 200
    assert AVISO_PRESENTACION in respuesta.content.decode()
    assert Presentacion.objects.count() == 8
    # Control: el mismo formulario con una presentación nueva sí guarda; el aviso se debe al
    # duplicado y no a un campo que falte en el POST
    nueva = cliente.post(f"{URL_PRESENTACION}add/", {"nombre": "supositorio", "activo": "on"})
    assert nueva.status_code == 302
    assert Presentacion.objects.count() == 9


def test_el_alta_no_ofrece_una_presentacion_dada_de_baja(entrar_como, losartan):
    # Scenario: El alta no ofrece una presentación dada de baja (revisión de HB-09, hallazgo 3)
    parche = Presentacion.objects.get(nombre="parche")
    parche.activo = False
    parche.save()
    tableta = Presentacion.objects.get(nombre="tableta")
    cliente = entrar_como("Lectura y escritura")
    respuesta = cliente.get(f"{URL}add/")
    assert respuesta.status_code == 200
    opciones = campo_presentacion(respuesta).queryset
    # Control positivo: ofrece las activas, como "tableta"
    assert opciones.filter(pk=tableta.pk).exists()
    assert not opciones.filter(pk=parche.pk).exists()
    # Ajuste 3 (segunda revisión de HB-09, hallazgo 5): también en el HTML que ve el usuario,
    # no solo en la lista interna del campo. Control positivo: la opción de "tableta" sí está
    opciones_html = html_de_presentaciones(respuesta)
    assert f'<option value="{tableta.pk}"' in opciones_html
    assert f'<option value="{parche.pk}"' not in opciones_html
    # Enviar el alta con "parche" de todos modos: el formulario avisa en ese campo
    respuesta = cliente.post(f"{URL}add/", formulario(losartan, presentacion=parche.pk))
    assert respuesta.status_code == 200
    assert "presentacion" in respuesta.context["adminform"].form.errors
    assert not Medicamento.objects.exists()
    # Control: el mismo alta con "tableta" sí guarda; el aviso se debe a la presentación
    assert cliente.post(f"{URL}add/", formulario(losartan)).status_code == 302
    assert Medicamento.objects.count() == 1


def test_el_cambio_conserva_la_presentacion_dada_de_baja(entrar_como, losartan):
    # Scenario: El cambio conserva la presentación dada de baja (revisión de HB-09, hallazgo 3)
    # Regresión: hoy el panel ofrece todas las presentaciones. Protege que el límite del alta
    # no impida guardar un medicamento cuya presentación se dio de baja después
    medicamento = registrar("Losartán", losartan, presentacion="parche")
    parche = Presentacion.objects.get(nombre="parche")
    parche.activo = False
    parche.save()
    cliente = entrar_como("Lectura y escritura")
    url = f"{URL}{medicamento.pk}/change/"
    respuesta = cliente.get(url)
    assert respuesta.status_code == 200
    assert campo_presentacion(respuesta).queryset.filter(pk=parche.pk).exists()
    # Ajuste 3 (segunda revisión de HB-09, hallazgo 5): también en el HTML que ve el usuario
    assert f'<option value="{parche.pk}"' in html_de_presentaciones(respuesta)
    datos = formulario_de_cambio(
        medicamento, losartan, presentacion=parche.pk, concentracion="100 mg"
    )
    assert cliente.post(url, datos).status_code == 302
    # Se guardó el cambio y conserva su presentación
    medicamento.refresh_from_db()
    assert medicamento.concentracion == "100 mg"
    assert medicamento.presentacion_id == parche.pk


@pytest.mark.parametrize(
    "atributos",
    [{}, {"campos_sin_acentos": ()}],
    ids=["sin-declarar", "vacios"],
)
def test_sin_campos_de_busqueda_hay_error_de_configuracion(atributos):
    # Scenario: Sin campos de búsqueda, error de configuración (revisión de HB-09, hallazgo 9)
    SinCampos = type("SinCampos", (BusquedaSinAcentosMixin, admin.ModelAdmin), atributos)
    errores = SinCampos(Presentacion, admin.AdminSite()).check()
    assert "panel.E001" in [error.id for error in errores]


@pytest.mark.parametrize("modelo", [Presentacion, PrincipioActivo, Medicamento, Residente])
def test_los_registros_del_panel_no_tienen_errores_de_configuracion(modelo):
    # Scenario: Sin campos de búsqueda, error de configuración (revisión de HB-09, hallazgo 9):
    # los registros de presentaciones, principios activos, medicamentos y residentes no
    # devuelven errores
    registro = admin.site._registry[modelo]
    # Control: el registro usa la búsqueda sin acentos, así que su check() sí pasa por la
    # comprobación de panel.E001; sin esto, la lista vacía de abajo no probaría nada
    assert isinstance(registro, BusquedaSinAcentosMixin)
    errores = [error for error in registro.check() if error.is_serious()]
    assert errores == []


def test_alta_de_un_medicamento_como_app_user(entrar_como, losartan):
    # Scenario: Alta de un medicamento como app_user (revisión de HB-09, hallazgo 6)
    # Regresión: el alta de HB-09 ya funciona con los permisos de app_user. Protege que el
    # panel (incluido el historial de cambios, django_admin_log) no necesite los de app_owner
    cliente = entrar_como("Lectura y escritura")  # force_login antes de cambiar de rol
    # Control: los tests corren como app_owner hasta el SET LOCAL ROLE
    assert rol_actual() != "app_user"
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL ROLE app_user")
    assert rol_actual() == "app_user"
    assert not Medicamento.objects.exists()
    respuesta = cliente.post(f"{URL}add/", formulario(losartan))
    assert respuesta.status_code == 302
    # La petición corrió en la misma conexión, que sigue como app_user
    assert rol_actual() == "app_user"
    medicamento = Medicamento.objects.get(nombre_comercial="Losartán")
    assert list(medicamento.principios_activos.all()) == [losartan]
    assert LogEntry.objects.filter(
        content_type__model="medicamento",
        action_flag=ADDITION,
        object_id=str(medicamento.pk),
    ).exists()


def test_la_busqueda_por_varias_palabras(entrar_como, losartan):
    # Scenario: Varias palabras y espacios sobrantes (revisión de HB-09, hallazgo 1)
    registrar("Cozaar", losartan)
    # Un segundo medicamento sin relación: la búsqueda vacía debe mostrar los 2
    paracetamol = PrincipioActivo.objects.create(nombre="Paracetamol")
    registrar("Tempra", paracetamol, presentacion="jarabe", concentracion="160 mg / 5 ml")
    cliente = entrar_como("Lectura y escritura")
    for termino in ("cozaar losartan", "losartan "):
        respuesta = cliente.get(URL, {"q": termino})
        assert respuesta.status_code == 200
        assert respuesta.context["cl"].result_count == 1
        assert "Cozaar" in respuesta.content.decode()
    # Una palabra que no coincide deja fuera a Cozaar, aunque la otra sí coincida
    respuesta = cliente.get(URL, {"q": "cozaar paracetamol"})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 0
    # Solo un espacio: no filtra
    respuesta = cliente.get(URL, {"q": " "})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 2


@pytest.mark.parametrize("modelo", ["presentacion", "principioactivo"])
def test_solo_lectura_no_cambia_presentaciones_ni_principios_activos(entrar_como, losartan, modelo):
    # Scenario: 403 al cambiar una presentación o un principio activo (revisión de HB-09,
    # hallazgo 8). Regresión: los permisos de grupo de HB-08 ya lo impiden
    if modelo == "presentacion":
        objeto = Presentacion.objects.get(nombre="tableta")
    else:
        objeto = losartan
    nombre = objeto.nombre
    url = f"/admin/catalogo/{modelo}/{objeto.pk}/change/"
    # Control positivo del botón de guardar: en la página editable de Lectura y escritura sí
    # aparece, así que su ausencia de abajo se debe al modo de consulta
    editable = entrar_como("Lectura y escritura").get(url)
    assert editable.status_code == 200
    assert 'name="_save"' in editable.content.decode()
    cliente = entrar_como("Solo lectura")
    consulta = cliente.get(url)
    assert consulta.status_code == 200
    assert 'name="_save"' not in consulta.content.decode()
    assert cliente.post(url, {"nombre": "Otro nombre", "activo": "on"}).status_code == 403
    # El nombre queda igual
    objeto.refresh_from_db()
    assert objeto.nombre == nombre


def test_la_busqueda_en_presentaciones_y_principios_activos(entrar_como, losartan):
    # Scenario: Búsqueda en las listas de presentaciones y principios activos (revisión de
    # HB-09, hallazgo 8). Regresión: HB-09 ya busca sin acentos en estas listas
    PrincipioActivo.objects.create(nombre="Metformina")
    cliente = entrar_como("Lectura y escritura")
    # Entre las 8 semillas, solo "cápsula"
    respuesta = cliente.get(URL_PRESENTACION, {"q": "capsula"})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 1
    assert "cápsula" in respuesta.content.decode()
    # Entre Losartán y Metformina, solo Losartán
    respuesta = cliente.get("/admin/catalogo/principioactivo/", {"q": "LOSARTAN"})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 1
    html = respuesta.content.decode()
    assert "Losartán" in html
    assert "Metformina" not in html


def registrar_hyzaar_y_cozaar(losartan):
    """Hyzaar con Losartán e Hidroclorotiazida, y Cozaar solo con Losartán (ambos en tableta)."""
    hidroclorotiazida = PrincipioActivo.objects.create(nombre="Hidroclorotiazida")
    hyzaar = registrar("Hyzaar", losartan, concentracion="50 mg / 12.5 mg")
    MedicamentoPrincipioActivo.objects.create(
        medicamento=hyzaar, principio_activo=hidroclorotiazida
    )
    registrar("Cozaar", losartan)


def test_la_busqueda_con_varios_principios_activos(entrar_como, losartan):
    # Scenario: Cada palabra puede coincidir con un principio activo distinto (segunda revisión
    # de HB-09, hallazgo 1). Regresión: HB-09 ya aplica un filter() por palabra; protege que
    # cada palabra pueda coincidir con un renglón distinto de la tabla puente
    registrar_hyzaar_y_cozaar(losartan)
    cliente = entrar_como("Lectura y escritura")
    respuesta = cliente.get(URL, {"q": "losartan hidroclorotiazida"})
    assert respuesta.status_code == 200
    # Una sola vez: ni duplicado por los 2 renglones de la tabla puente, ni Cozaar
    assert respuesta.context["cl"].result_count == 1
    assert len(respuesta.context["cl"].result_list) == 1
    html = respuesta.content.decode()
    assert "Hyzaar" in html
    assert "Cozaar" not in html
    # Control: con una sola palabra salen los 2 medicamentos con Losartán
    respuesta = cliente.get(URL, {"q": "losartan"})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 2


@pytest.mark.parametrize("comodin", ["%", "_"], ids=["porcentaje", "guion-bajo"])
def test_los_comodines_se_buscan_como_texto(entrar_como, losartan, comodin):
    # Scenario: Los comodines se buscan como texto (segunda revisión de HB-09, hallazgo 1).
    # Regresión: HB-09 ya escapa % y _ en la búsqueda
    registrar_hyzaar_y_cozaar(losartan)
    cliente = entrar_como("Lectura y escritura")
    # Control: sin término, la lista muestra los 2; la lista vacía de abajo se debe al comodín
    respuesta = cliente.get(URL)
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 2
    respuesta = cliente.get(URL, {"q": comodin})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 0


def test_la_busqueda_usa_como_mucho_8_palabras(entrar_como, losartan):
    # Scenario: Tope de 8 palabras (segunda revisión de HB-09, hallazgo 9)
    registrar("Cozaar", losartan)
    cliente = entrar_como("Lectura y escritura")
    # Control: con 8 palabras, "paracetamol" sí se usa y deja fuera a Cozaar
    ocho = " ".join(["cozaar"] * 7 + ["paracetamol"])
    respuesta = cliente.get(URL, {"q": ocho})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 0
    # Con 9, la novena ("paracetamol") no se usa
    nueve = " ".join(["cozaar"] * 8 + ["paracetamol"])
    respuesta = cliente.get(URL, {"q": nueve})
    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 1
    assert "Cozaar" in respuesta.content.decode()


def test_palabras_de_busqueda_corta_en_8():
    # Scenario: Tope de 8 palabras (segunda revisión de HB-09, hallazgo 9), en la función que
    # divide el término. Se importa aquí: MAXIMO_PALABRAS es nueva, y su ausencia no debe
    # tumbar los demás tests del módulo
    from apps.panel import MAXIMO_PALABRAS, palabras_de_busqueda

    assert MAXIMO_PALABRAS == 8
    palabras = list(palabras_de_busqueda(" ".join(str(i) for i in range(20))))
    # Las primeras 8, en su orden
    assert len(palabras) == MAXIMO_PALABRAS
    assert palabras == [str(i) for i in range(8)]


@pytest.mark.parametrize(
    ("campos", "mal_escrito"),
    [
        (("nombre_comercial", "principio_activos__nombre"), "principio_activos__nombre"),
        (("nombre_comercial", "no_existe"), "no_existe"),
        (("nombre_comercial__nombre",), "nombre_comercial__nombre"),
    ],
    ids=["relacion-mal-escrita", "campo-simple", "tramo-sin-relacion"],
)
def test_un_campo_de_busqueda_que_no_existe_da_error(campos, mal_escrito):
    # Scenario: Un campo de búsqueda que no existe (segunda revisión de HB-09, hallazgo 7)
    CampoMal = type(
        "CampoMal", (BusquedaSinAcentosMixin, admin.ModelAdmin), {"campos_sin_acentos": campos}
    )
    errores = CampoMal(Medicamento, admin.AdminSite()).check()
    e002 = [error for error in errores if error.id == "panel.E002"]
    assert e002, errores
    # El mensaje nombra el campo mal escrito
    assert any(mal_escrito in error.msg for error in e002)
    # Control: los mismos campos bien escritos no dan panel.E002
    CampoBien = type(
        "CampoBien",
        (BusquedaSinAcentosMixin, admin.ModelAdmin),
        {"campos_sin_acentos": ("nombre_comercial", "principios_activos__nombre")},
    )
    errores = CampoBien(Medicamento, admin.AdminSite()).check()
    assert "panel.E002" not in [error.id for error in errores]
    assert [error for error in errores if error.is_serious()] == []
