"""Solo el Administrador gestiona usuarios; cada usuario tiene exactamente un grupo.

HB-08. Capa HTTP: el panel /admin/ con el cliente de pruebas de Django. admin_client y
admin_user son fixtures de pytest-django: un superusuario (el Administrador) con sesión
iniciada. Antes de TK-01 no hay mock: los usuarios de prueba son "prueba.*", creados con
create_user, y los 2 grupos los crea la migración 0003_grupos.

Los usuarios de grupo entran con client.force_login(usuario), nunca con client.login(), que
choca con django-axes.

Cada 403 lleva un control positivo (la misma persona sí ve otra página del panel), para que el
403 no se confunda con una sesión que no se inició o con un panel que no responde.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

pytestmark = [pytest.mark.django_db, pytest.mark.http]
URL_ALTA = "/admin/accounts/usuario/add/"
AVISO = "Elige exactamente un grupo: Solo lectura o Lectura y escritura."


def alta(admin_client, **cambios):
    datos = {
        "username": "prueba.nuevo",
        "first_name": "Prueba",
        "last_name": "Nueva",
        "email": "prueba.nueva@example.com",
        "usable_password": "true",
        "password1": "Prueba-segura-2026",
        "password2": "Prueba-segura-2026",
        "groups": [Group.objects.get(name="Solo lectura").pk],
    }
    return admin_client.post(URL_ALTA, datos | cambios)


def grupos_de(usuario):
    return list(usuario.groups.values_list("name", flat=True))


@pytest.fixture
def de_solo_lectura():
    """Un usuario del grupo Solo lectura, para editarlo desde el panel."""
    usuario = get_user_model().objects.create_user(
        "prueba.cambio",
        first_name="Prueba",
        last_name="Cambio",
        email="prueba.cambio@example.com",
        is_staff=True,
    )
    usuario.groups.add(Group.objects.get(name="Solo lectura"))
    return usuario


def cambio(admin_client, usuario, grupos):
    """POST al formulario de cambio con los campos editables y los grupos dados."""
    datos = {
        "username": usuario.username,
        "first_name": usuario.first_name,
        "last_name": usuario.last_name,
        "email": usuario.email,
        "is_active": "on",
        "groups": [Group.objects.get(name=nombre).pk for nombre in grupos],
    }
    return admin_client.post(f"/admin/accounts/usuario/{usuario.pk}/change/", datos)


def test_el_administrador_da_de_alta_un_usuario_con_un_grupo(admin_client):
    # Scenario: Alta con un grupo (HB-08, criterio 3)
    assert alta(admin_client).status_code == 302
    usuario = get_user_model().objects.get(username="prueba.nuevo")
    assert usuario.is_staff  # entra al panel
    assert grupos_de(usuario) == ["Solo lectura"]
    assert usuario.password.startswith("argon2$")
    assert usuario.check_password("Prueba-segura-2026")


@pytest.mark.parametrize(
    "grupos", [[], ["Solo lectura", "Lectura y escritura"]], ids=["sin-grupo", "con-dos"]
)
def test_sin_grupo_o_con_dos_el_formulario_avisa(admin_client, grupos):
    # Scenario: Alta sin grupo o con 2 (HB-08, criterio 3)
    ids = [Group.objects.get(name=nombre).pk for nombre in grupos]
    respuesta = alta(admin_client, groups=ids)
    assert respuesta.status_code == 200
    assert AVISO in respuesta.content.decode()
    # El usuario no se crea
    assert not get_user_model().objects.filter(username="prueba.nuevo").exists()


def test_el_cambio_a_dos_grupos_avisa_y_conserva_el_grupo(admin_client, de_solo_lectura):
    # Scenario: Cambio a 2 grupos (HB-08, criterio 3)
    respuesta = cambio(admin_client, de_solo_lectura, ["Solo lectura", "Lectura y escritura"])
    assert respuesta.status_code == 200
    assert AVISO in respuesta.content.decode()
    # El usuario conserva solo "Solo lectura"
    assert grupos_de(de_solo_lectura) == ["Solo lectura"]


def test_el_cambio_a_un_solo_grupo_se_guarda(admin_client, de_solo_lectura):
    # Scenario: Cambio a 2 grupos (HB-08, criterio 3)
    # Control: con los mismos campos y un solo grupo, el formulario de cambio sí guarda. Así,
    # el aviso del test anterior se debe a los 2 grupos y no a un campo que falte en el POST
    respuesta = cambio(admin_client, de_solo_lectura, ["Lectura y escritura"])
    assert respuesta.status_code == 302
    assert grupos_de(de_solo_lectura) == ["Lectura y escritura"]


@pytest.mark.parametrize(
    "url", ["/admin/accounts/usuario/", "/admin/auth/group/"], ids=["usuarios", "grupos"]
)
def test_un_usuario_de_grupo_no_ve_los_usuarios(client, url):
    # Scenario: Un usuario de grupo no ve usuarios ni grupos (HB-08, criterio 4)
    usuario = get_user_model().objects.create_user("prueba.lector", is_staff=True)
    usuario.groups.add(Group.objects.get(name="Lectura y escritura"))
    client.force_login(usuario)
    # Control: tiene sesión y entra al panel; el 403 no es por falta de sesión
    assert client.get("/admin/").status_code == 200
    assert client.get(url).status_code == 403


def test_nadie_borra_usuarios(admin_client, admin_user):
    # Scenario: Nadie borra usuarios (HB-08, criterio 4)
    # Control: el Administrador sí abre el formulario de cambio del mismo usuario; el 403 no
    # es un usuario que no exista ni un modelo fuera del panel
    assert admin_client.get(f"/admin/accounts/usuario/{admin_user.pk}/change/").status_code == 200
    assert admin_client.get(f"/admin/accounts/usuario/{admin_user.pk}/delete/").status_code == 403
    # Y el usuario sigue en la base
    assert get_user_model().objects.filter(pk=admin_user.pk).exists()


def test_los_grupos_no_se_crean_a_mano(admin_client):
    # Scenario: Los grupos no se crean ni se borran a mano (HB-08, descripción técnica)
    # Control: el Administrador sí ve la lista de grupos
    assert admin_client.get("/admin/auth/group/").status_code == 200
    assert admin_client.get("/admin/auth/group/add/").status_code == 403


def test_los_grupos_no_se_borran_a_mano(admin_client):
    # Scenario: Los grupos no se crean ni se borran a mano (HB-08, descripción técnica)
    solo_lectura = Group.objects.get(name="Solo lectura")
    # Control: el Administrador sí abre el grupo
    assert admin_client.get(f"/admin/auth/group/{solo_lectura.pk}/change/").status_code == 200
    assert admin_client.get(f"/admin/auth/group/{solo_lectura.pk}/delete/").status_code == 403
    assert Group.objects.filter(pk=solo_lectura.pk).exists()
