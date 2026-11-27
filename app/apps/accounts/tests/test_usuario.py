"""Modelo de usuario propio y hash de contraseñas (readme, secciones 2.5 y 3.2, D1)."""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def test_el_proyecto_usa_su_propio_modelo_de_usuario():
    # Scenario: Modelo y tablas del usuario
    assert settings.AUTH_USER_MODEL == "accounts.Usuario"
    usuario = get_user_model()
    assert usuario._meta.label == "accounts.Usuario"
    assert usuario._meta.db_table == "usuario"
    assert usuario.groups.through._meta.db_table == "usuario_groups"


@pytest.mark.django_db
def test_la_contrasena_se_guarda_con_argon2():
    # Scenario: Contraseña nueva con Argon2
    usuario = get_user_model().objects.create_user("prueba.argon", password="Prueba-larga-2026")
    usuario.refresh_from_db()
    assert usuario.password.startswith("argon2$")
    assert usuario.check_password("Prueba-larga-2026")
    assert not usuario.check_password("Otra-clave-2026")


@pytest.mark.django_db
def test_acepta_los_hash_pbkdf2_del_dataset_mock():
    # Scenario: Hash PBKDF2 del mock (demo.json guarda hashes pbkdf2_sha256$...)
    usuario = get_user_model().objects.create_user("prueba.mock")
    usuario.password = make_password("Prueba-mock-2026", hasher="pbkdf2_sha256")
    usuario.save(update_fields=["password"])
    usuario.refresh_from_db()
    # Control: el hash guardado es PBKDF2 y no Argon2, como los del mock
    assert usuario.password.startswith("pbkdf2_sha256$")
    assert usuario.check_password("Prueba-mock-2026")


def test_contrasena_minima_de_10_caracteres():
    # Scenario: Contraseña de 9 y de 10 caracteres
    nueve, diez = "Zorzal-48", "Zorzal-482"
    assert (len(nueve), len(diez)) == (9, 10)

    # Sin validadores configurados validate_password no lanza, y este bloque falla
    with pytest.raises(ValidationError) as error:
        validate_password(nueve)
    assert "password_too_short" in [e.code for e in error.value.error_list]

    # La de 10 (no común ni numérica) se acepta: el mínimo es 10, no más
    validate_password(diez)
