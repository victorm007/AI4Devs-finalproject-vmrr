"""Los 2 grupos, sus permisos y un solo grupo por usuario (D1, HB-08).

Capa de base de datos: corren como app_owner, sin pasar por HTTP. Los grupos y sus permisos
los crea la migración 0003_grupos, y uq_usuario_un_grupo, la 0004_un_grupo: existen en la base
de tests sin cargar el mock. Antes de TK-01 no hay mock: el único dato propio es el usuario
"prueba.grupos".

Los permisos se comparan como conjuntos exactos (igualdad, no inclusión) y con la app de su
content type, para que un permiso de más (delete_*, de usuario o de grupo, o de otra app) haga
fallar el test.

El error de la base se busca con el nombre de la restricción entre comillas, como lo escribe
PostgreSQL ('... violates unique constraint "uq_usuario_un_grupo"').

"Revertir a 0002 y volver" no es un test de pytest: se comprueba con
./scripts/migrate.sh accounts 0002 y ./scripts/migrate.sh en el cierre del ticket.

Ajuste de la revisión adversarial de HB-08 (hallazgo 11): app_user, el usuario de base de datos
de la aplicación, escribe en las tablas de axes (con ejecutar_sql(..., rol="app_user")).

Ajuste de la 2.ª revisión adversarial de HB-08 (hallazgo 2): app_user también actualiza y borra
en todas las tablas de axes, como hace axes al reiniciar los intentos tras un login correcto.
"""

import pytest
from axes.models import AccessAttempt
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction

from pruebas import ejecutar_sql

pytestmark = pytest.mark.django_db

# Los 5 modelos con permisos, con su app: el catálogo (catalogo) y los residentes (entidades)
MODELOS = (
    ("catalogo", "presentacion"),
    ("catalogo", "principioactivo"),
    ("catalogo", "medicamento"),
    ("catalogo", "medicamentoprincipioactivo"),
    ("entidades", "residente"),
)


def esperados(acciones):
    """Pares (app_label, codename) de las acciones dadas sobre los 5 modelos."""
    return {(app, f"{accion}_{modelo}") for app, modelo in MODELOS for accion in acciones}


def codigos(nombre):
    return set(Group.objects.get(name=nombre).permissions.values_list("codename", flat=True))


def permisos_con_app(nombre):
    return set(
        Group.objects.get(name=nombre).permissions.values_list(
            "content_type__app_label", "codename"
        )
    )


def test_existen_exactamente_los_2_grupos():
    # Scenario: Exactamente 2 grupos (HB-08, criterio 2)
    assert set(Group.objects.values_list("name", flat=True)) == {
        "Solo lectura",
        "Lectura y escritura",
    }
    # Sin nombres repetidos: 2 filas, no más
    assert Group.objects.count() == 2


def test_solo_lectura_solo_puede_ver():
    # Scenario: Permisos de Solo lectura (HB-08, criterio 2)
    permisos = codigos("Solo lectura")
    assert {"view_medicamento", "view_residente", "view_principioactivo"} <= permisos
    assert all(codigo.startswith("view_") for codigo in permisos)
    # Exactamente los 5 view_ (igualdad, no inclusión)
    assert permisos == {
        "view_presentacion",
        "view_principioactivo",
        "view_medicamento",
        "view_medicamentoprincipioactivo",
        "view_residente",
    }
    # Y de los modelos de catalogo y entidades, no de otro modelo con el mismo codename
    assert permisos_con_app("Solo lectura") == esperados(["view"])


def test_lectura_y_escritura_ve_agrega_y_cambia_pero_no_borra():
    # Scenario: Permisos de Lectura y escritura (HB-08, criterio 2)
    permisos = codigos("Lectura y escritura")
    assert {"add_medicamento", "change_residente", "add_medicamentoprincipioactivo"} <= permisos
    assert not any(codigo.startswith("delete_") for codigo in permisos)
    # Exactamente los 15 view_, add_ y change_ de los 5 modelos (igualdad, no inclusión)
    assert len(permisos) == 15
    assert permisos_con_app("Lectura y escritura") == esperados(["view", "add", "change"])
    # Solo de content types de las apps catalogo y entidades
    apps_de_los_permisos = set(
        Group.objects.get(name="Lectura y escritura").permissions.values_list(
            "content_type__app_label", flat=True
        )
    )
    assert apps_de_los_permisos == {"catalogo", "entidades"}


@pytest.mark.parametrize("grupo", ["Solo lectura", "Lectura y escritura"], ids=["sl", "lye"])
def test_ningun_grupo_gestiona_usuarios(grupo):
    # Scenario: Permisos de Lectura y escritura (HB-08, criterio 2): ninguno se refiere a
    # usuarios o grupos (y tampoco los de Solo lectura)
    permisos = codigos(grupo)
    # Control: el grupo tiene permisos; sin ellos, el "not any" de abajo no probaría nada
    assert permisos
    assert not any("usuario" in c or "group" in c for c in permisos)


def test_uq_usuario_un_grupo_con_su_definicion():
    # Scenario: La base rechaza un segundo grupo (HB-08, criterio 3): la definición
    # Desempacar exige exactamente 1 fila: la restricción existe y con ese nombre
    [(tabla, tipo, definicion)] = ejecutar_sql(
        "SELECT conrelid::regclass::text, contype, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'uq_usuario_un_grupo'"
    )
    assert tabla == "usuario_groups"
    assert tipo == "u"
    assert definicion == "UNIQUE (usuario_id)"


def test_un_usuario_solo_puede_tener_un_grupo():
    # Scenario: La base rechaza un segundo grupo (HB-08, criterio 3)
    usuario = get_user_model().objects.create_user("prueba.grupos")
    usuario.groups.add(Group.objects.get(name="Solo lectura"))
    # Control: el primer grupo sí se guarda
    assert list(usuario.groups.values_list("name", flat=True)) == ["Solo lectura"]
    lectura_y_escritura = Group.objects.get(name="Lectura y escritura")
    # INSERT sin ON CONFLICT en la tabla puente: la base lo rechaza por uq_usuario_un_grupo
    with pytest.raises(IntegrityError, match='"uq_usuario_un_grupo"'):
        with transaction.atomic():
            get_user_model().groups.through.objects.create(
                usuario=usuario, group=lectura_y_escritura
            )
    # El usuario conserva solo su grupo
    assert list(usuario.groups.values_list("name", flat=True)) == ["Solo lectura"]
    # groups.add() no lanza: Django inserta en la tabla puente con ON CONFLICT DO NOTHING, así
    # que la base impide el segundo grupo en silencio. Quien avisa es el formulario del panel
    usuario.groups.add(lectura_y_escritura)
    assert list(usuario.groups.values_list("name", flat=True)) == ["Solo lectura"]


def test_app_user_escribe_en_las_tablas_de_axes():
    # Scenario: app_user escribe en las tablas de axes (revisión de HB-08, hallazgo 11; 2.ª
    # revisión de HB-08, hallazgo 2)
    # De regresión: nace en verde, porque app_user recibe los privilegios por defecto de las
    # tablas que crea app_owner. Protege el bloqueo en producción: la aplicación corre como
    # app_user y, sin escribir en axes_accessattempt, axes no contaría los intentos fallidos.
    # Detecta que se le retire INSERT, UPDATE o DELETE en cualquier tabla axes_* (por ejemplo,
    # un ALTER DEFAULT PRIVILEGES que solo conceda INSERT): sin DELETE, axes no podría
    # reiniciar los intentos tras un login correcto
    valores = {
        "user_agent": "pytest",
        "ip_address": "127.0.0.1",
        "username": "prueba.axes",
        "http_accept": "text/html",
        "path_info": "/accounts/login/",
        "get_data": "",
        "post_data": "username=prueba.axes",
        "failures_since_start": 1,
    }
    # Control: el INSERT lleva todas las columnas NOT NULL del modelo de axes (attempt_time va
    # con now()); así, un fallo solo puede ser de privilegios y no de una columna que falte
    obligatorias = {
        campo.column
        for campo in AccessAttempt._meta.concrete_fields
        if not campo.null and not campo.primary_key
    }
    assert obligatorias <= set(valores) | {"attempt_time"}
    columnas = ", ".join([*valores, "attempt_time"])
    marcadores = ", ".join(["%s"] * len(valores) + ["now()"])
    # Desempacar exige exactamente 1 fila: el registro se guardó
    [(id_intento,)] = ejecutar_sql(
        f"INSERT INTO axes_accessattempt ({columnas}) VALUES ({marcadores}) RETURNING id",
        list(valores.values()),
        rol="app_user",
    )
    # axes también actualiza el intento en cada fallo siguiente (failures_since_start)
    [(fallos,)] = ejecutar_sql(
        "UPDATE axes_accessattempt SET failures_since_start = failures_since_start + 1 "
        "WHERE id = %s RETURNING failures_since_start",
        [id_intento],
        rol="app_user",
    )
    assert fallos == 2
    # axes borra los intentos al reiniciarlos tras un login correcto. Desempacar exige
    # exactamente 1 fila: se borró el registro insertado, y solo ese
    [(id_borrado,)] = ejecutar_sql(
        "DELETE FROM axes_accessattempt WHERE id = %s RETURNING id",
        [id_intento],
        rol="app_user",
    )
    assert id_borrado == id_intento
    # Control: el registro ya no está en la base
    assert ejecutar_sql("SELECT id FROM axes_accessattempt WHERE id = %s", [id_intento]) == []
    # Y app_user puede insertar, actualizar y borrar en todas las tablas de axes (también en
    # sus registros de acceso)
    tablas = [
        tabla
        for (tabla,) in ejecutar_sql(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = current_schema() AND tablename LIKE 'axes\\_%' "
            "ORDER BY tablename"
        )
    ]
    # Control: la consulta encuentra las tablas de axes; sin ellas, el bucle no probaría nada
    assert "axes_accessattempt" in tablas
    # Un privilegio por consulta: con varios separados por comas, has_table_privilege devuelve
    # true si app_user tiene cualquiera de ellos, no todos
    for tabla in tablas:
        for privilegio in ("INSERT", "UPDATE", "DELETE"):
            [(puede,)] = ejecutar_sql(
                "SELECT has_table_privilege('app_user', %s, %s)", [tabla, privilegio]
            )
            assert puede, (tabla, privilegio)
