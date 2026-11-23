# HB-08 · Guía paso a paso: login, grupos y usuarios

> **Ticket:** [readme, sección 6, HB-08](../../readme.md#tickets-de-habilitación-hb-01-a-hb-09) · **Tipo:** backend y frontend · **Estimación:** 3 puntos · **Rama:** `feature/HB-08-login-grupos`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket y en las secciones 2.5, 3.2 (D1) y 5 ("Habilitadores en el panel `/admin/`") del readme. Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.

**Resultado al terminar:**
- Hay una página de inicio de sesión propia (`/accounts/login/`) con Bootstrap 5 servido desde `static/`, y la plantilla común `base.html` que usarán todas las pantallas (TK-03 en adelante).
- Existen los 2 grupos, **Solo lectura** y **Lectura y escritura**, con sus permisos sobre el catálogo y los residentes. Cada usuario que no es Administrador pertenece a exactamente un grupo.
- Solo el Administrador gestiona usuarios. Nadie los borra: la baja es `is_active = False`.
- La sesión expira tras 30 min de inactividad, y la cuenta se bloquea 15 min tras 5 intentos fallidos (`django-axes`).

---

## 0. Antes de empezar

### 0.1 Lee primero (30 min)

| Qué | Dónde | Para qué |
|---|---|---|
| D1 — Usuarios y grupos | readme, sección 3.2 | Los 2 grupos, sus permisos y la regla de un solo grupo |
| Habilitadores en `/admin/` y "Controles" | readme, sección 5 | Quién gestiona qué y la regla "sin borrado" |
| Contraseñas, sesiones y fuerza bruta | readme, sección 2.5 | Argon2, expiración de 30 min y `django-axes` |
| Patrón de permisos en una migración | guía de TK-01, paso 7b | `create_permissions` dentro de `RunPython` |
| `django-axes` | <https://django-axes.readthedocs.io/en/latest/2_installation.html> | Instalación y `AUTHENTICATION_BACKENDS` |

### 0.2 Requisitos previos

- HB-04, HB-05 y HB-06 integrados en `main`: <https://localhost/admin/> funciona y existen los modelos del catálogo y de residentes.

### 0.3 Crea la rama

```bash
git switch main && git pull
git switch -c feature/HB-08-login-grupos
```

---

## 1. Archivos que vas a crear o modificar

```
app/
├── requirements.txt                          # MODIFICAR: django-axes
├── config/settings/base.py                   # MODIFICAR: axes, sesiones, LOGIN_*
├── config/urls.py                            # MODIFICAR: login, logout y "/"
├── templates/
│   ├── base.html                             # NUEVO: plantilla común (Bootstrap 5)
│   └── registration/
│       ├── login.html                        # NUEVO
│       └── bloqueado.html                    # NUEVO: cuenta bloqueada por intentos fallidos
├── static/
│   ├── css/vendor/bootstrap.min.css          # NUEVO: servido localmente (CSP)
│   └── js/vendor/bootstrap.bundle.min.js     # NUEVO
└── apps/accounts/
    ├── admin.py                              # NUEVO: UsuarioAdmin y GrupoAdmin
    ├── forms.py                              # NUEVO: formularios con un solo grupo
    ├── migrations/0003_grupos.py             # NUEVO: los 2 grupos y sus permisos
    ├── migrations/0004_un_grupo.py           # NUEVO: uq_usuario_un_grupo
    └── tests/
        ├── test_grupos.py                    # NUEVO
        ├── test_login.py                     # NUEVO
        └── test_admin_usuarios.py            # NUEVO
```

---

## 2. Tareas paso a paso

El orden sigue TDD (`CLAUDE.md`): primero los tests en rojo, después la implementación.

### Paso 1. Tests en rojo (≈ 1 h 15 min)

Escribe los tests de la sección 3 y ejecútalos **antes** de implementar:

```bash
dtest apps/accounts/tests/test_grupos.py apps/accounts/tests/test_login.py \
      apps/accounts/tests/test_admin_usuarios.py -q
```

Solo debe pasar `test_sin_sesion_el_panel_pide_login`, porque el panel de Django ya lo hace por defecto: es un test de regresión.

Así avanza el rojo con cada paso:

| Al terminar | Comando | Resultado esperado |
|---|---|---|
| Paso 3 (configuración) | `dtest apps/accounts/tests/test_login.py -k expira -q` | `1 passed` |
| Paso 4 (rutas y login) | `dtest apps/accounts/tests/test_login.py -k "pagina_de_login or raiz" -q` | `2 passed` |
| Paso 5 (grupos) | `dtest apps/accounts/tests/test_grupos.py apps/accounts/tests/test_login.py -q` | Todos pasan |
| Paso 6 (usuarios en el panel) | `dtest apps/accounts/tests/test_admin_usuarios.py -q` | Todos pasan |

### Paso 2. Bootstrap local y `django-axes` (≈ 20 min)

```bash
# Bootstrap 5.3.x desde static/: la CSP de nginx (HB-04) no permite CDN
mkdir -p app/static/css/vendor app/static/js/vendor
curl -sL https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css \
     -o app/static/css/vendor/bootstrap.min.css
curl -sL https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js \
     -o app/static/js/vendor/bootstrap.bundle.min.js
head -c 40 app/static/css/vendor/bootstrap.min.css; echo   # debe empezar con "@charset" o "/*!"

# django-axes con versión fija
docker compose exec web pip index versions django-axes | head -1   # anota la última estable
echo "django-axes==<versión anotada>" >> app/requirements.txt       # y ordena alfabéticamente
docker compose up -d --build web
```

### Paso 3. Configuración (≈ 30 min)

En `app/config/settings/base.py`:

```python
from datetime import timedelta  # junto a los demás imports

INSTALLED_APPS = [
    # ... las de Django y "django.contrib.postgres"
    "axes",  # bloqueo por intentos fallidos (readme, sección 2.5)
    # ... apps del proyecto
]

MIDDLEWARE = [
    # ... las de Django y la de CSP (config.middleware.ContentSecurityPolicyMiddleware, HB-04), sin cambios
    "axes.middleware.AxesMiddleware",  # al final: responde 429 si la cuenta está bloqueada
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # primero: cuenta los intentos fallidos
    "django.contrib.auth.backends.ModelBackend",
]

# Fuerza bruta: 5 intentos fallidos bloquean la cuenta 15 minutos (por usuario, no por IP)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "registration/bloqueado.html"

# Sesiones: expiran tras 30 min sin actividad y al cerrar el navegador (sección 2.5)
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "admin:index"  # TK-03 lo cambia a la pantalla de existencias
LOGOUT_REDIRECT_URL = "login"
```

### Paso 4. Rutas, plantillas y login (≈ 1 h)

**4.1 `app/config/urls.py`:**

```python
"""Rutas del proyecto. Cada app agrega las suyas en su ticket."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="login")),  # TK-03 la apunta a existencias
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),  # solo POST
    path("admin/", admin.site.urls),
]
```

**4.2 `app/templates/base.html`** (sin `<script>` ni `style` en línea: los bloquea la CSP):

```django
{% load static %}
<!DOCTYPE html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}Inicio{% endblock %} · Medicamentos del Hogar</title>
    <link rel="stylesheet" href="{% static 'css/vendor/bootstrap.min.css' %}">
    {% block extra_head %}{% endblock %}
  </head>
  <body class="bg-light">
    <nav class="navbar navbar-expand-md navbar-dark bg-primary mb-4">
      <div class="container">
        <span class="navbar-brand">Medicamentos del Hogar</span>
        {% if user.is_authenticated %}
          <button class="navbar-toggler"
                  type="button"
                  data-bs-toggle="collapse"
                  data-bs-target="#menu"
                  aria-controls="menu"
                  aria-expanded="false"
                  aria-label="Abrir el menú">
            <span class="navbar-toggler-icon"></span>
          </button>
          <div class="collapse navbar-collapse" id="menu">
            <ul class="navbar-nav me-auto">
              {% block menu %}{% endblock %}
              {% if user.is_staff %}
                <li class="nav-item"><a class="nav-link" href="{% url 'admin:index' %}">Administración</a></li>
              {% endif %}
            </ul>
            <form method="post"
                  action="{% url 'logout' %}"
                  class="d-flex align-items-center">
              {% csrf_token %}
              <span class="navbar-text me-3">{{ user.get_full_name|default:user.username }}</span>
              <button type="submit" class="btn btn-outline-light btn-sm">Cerrar sesión</button>
            </form>
          </div>
        {% endif %}
      </div>
    </nav>
    <main class="container">
      {% for message in messages %}
        <div class="alert alert-info" role="status">{{ message }}</div>
      {% endfor %}
      {% block content %}{% endblock %}
    </main>
    <script src="{% static 'js/vendor/bootstrap.bundle.min.js' %}" defer></script>
    {% block scripts %}{% endblock %}
  </body>
</html>
```

**4.3 `app/templates/registration/login.html`:**

```django
{% extends "base.html" %}
{% block title %}Iniciar sesión{% endblock %}
{% block content %}
  <div class="row justify-content-center">
    <div class="col-12 col-sm-8 col-md-5 col-lg-4">
      <h1 class="h3 mb-3">Iniciar sesión</h1>
      {% if form.errors %}
        <div class="alert alert-danger" role="alert">Usuario o contraseña incorrectos.</div>
      {% endif %}
      <form method="post" novalidate>
        {% csrf_token %}
        <div class="mb-3">
          <label class="form-label" for="{{ form.username.id_for_label }}">Usuario</label>
          <input type="text"
                 name="username"
                 id="{{ form.username.id_for_label }}"
                 class="form-control"
                 autocomplete="username"
                 autofocus
                 required
                 value="{{ form.username.value|default:'' }}">
        </div>
        <div class="mb-3">
          <label class="form-label" for="{{ form.password.id_for_label }}">Contraseña</label>
          <input type="password"
                 name="password"
                 id="{{ form.password.id_for_label }}"
                 class="form-control"
                 autocomplete="current-password"
                 required>
        </div>
        <input type="hidden" name="next" value="{{ next }}">
        <button type="submit" class="btn btn-primary w-100">Entrar</button>
      </form>
    </div>
  </div>
{% endblock %}
```

**4.4 `app/templates/registration/bloqueado.html`:**

```django
{% extends "base.html" %}
{% block title %}Cuenta bloqueada{% endblock %}
{% block content %}
  <div class="alert alert-warning" role="alert">
    Demasiados intentos fallidos. La cuenta queda bloqueada 15 minutos.
    Si no recuerdas tu contraseña, pide al Administrador que la restablezca.
  </div>
{% endblock %}
```

> **Formato de las plantillas:** están escritas como las deja djLint (HB-02, `[tool.djlint]` en `pyproject.toml`): 2 espacios de sangría y un atributo por línea cuando la etiqueta no cabe en 120 caracteres. Después de pegar o editar una plantilla, ejecuta `docker compose exec web djlint . --reformat` y luego `djlint . --lint`; el *job* `lint` del CI falla si una plantilla no tiene ese formato.

### Paso 5. Los 2 grupos y sus permisos (≈ 45 min)

```bash
dj makemigrations accounts --empty --name grupos
```

`app/apps/accounts/migrations/0003_grupos.py`:

```python
"""Grupos Solo lectura y Lectura y escritura (readme, secciones 3.1 y 3.2, D1).

Permisos sobre los modelos de los habilitadores (catálogo y residentes). Nadie recibe
delete_*: la baja es lógica. TK-01 agrega después los de inventario (su 0003).
"""

from django.contrib.auth.management import create_permissions
from django.db import migrations

MODELOS = {
    "catalogo": ["presentacion", "principioactivo", "medicamento", "medicamentoprincipioactivo"],
    "entidades": ["residente"],
}
GRUPOS = {
    "Solo lectura": ["view"],
    "Lectura y escritura": ["view", "add", "change"],
}


def crear_grupos(apps, schema_editor):
    # Django crea los permisos al final de migrate; aquí se fuerzan para poder asignarlos
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    grupo = apps.get_model("auth", "Group")
    permiso = apps.get_model("auth", "Permission")
    for nombre, acciones in GRUPOS.items():
        codigos = [
            f"{accion}_{modelo}" for modelos in MODELOS.values() for modelo in modelos
            for accion in acciones
        ]
        permisos = permiso.objects.filter(content_type__app_label__in=MODELOS, codename__in=codigos)
        grupo.objects.get_or_create(name=nombre)[0].permissions.add(*permisos)


def quitar_grupos(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=GRUPOS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_privilegios"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("catalogo", "0003_presentaciones"),
        ("entidades", "0003_hogar"),
    ]
    operations = [migrations.RunPython(crear_grupos, quitar_grupos)]
```

`dj makemigrations accounts --empty --name un_grupo` → `0004_un_grupo.py`:

```python
"""Cada usuario pertenece a un solo grupo (readme, sección 3.1, D1)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_grupos")]
    operations = [
        migrations.RunSQL(
            "ALTER TABLE usuario_groups ADD CONSTRAINT uq_usuario_un_grupo UNIQUE (usuario_id);",
            "ALTER TABLE usuario_groups DROP CONSTRAINT uq_usuario_un_grupo;",
        ),
    ]
```

```bash
./scripts/migrate.sh
```

### Paso 6. Usuarios en el panel: solo el Administrador (≈ 1 h)

**6.1 `app/apps/accounts/forms.py`:**

```python
"""Formularios de usuario del panel: un solo grupo por usuario (readme, sección 3.2, D1).

"A lo sumo uno" lo garantiza la base (uq_usuario_un_grupo); "al menos uno" lo valida
este formulario, con un mensaje claro en lugar de un error 500.
"""

from django import forms
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.contrib.auth.models import Group

from apps.accounts.models import Usuario

MENSAJE_GRUPO = "Elige exactamente un grupo: Solo lectura o Lectura y escritura."


class GrupoUnicoMixin:
    def clean(self):
        datos = super().clean()
        if not datos.get("is_superuser"):
            grupos = datos.get("groups")
            if grupos is None or len(grupos) != 1:
                self.add_error("groups", MENSAJE_GRUPO)
            # Los usuarios de los 2 grupos entran al panel (habilitadores, sección 5)
            datos["is_staff"] = True
            self.instance.is_staff = True
        return datos


class UsuarioCreationForm(GrupoUnicoMixin, AdminUserCreationForm):
    # required=False: el mensaje lo da GrupoUnicoMixin, igual que en el formulario de cambio
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(), widget=forms.CheckboxSelectMultiple, required=False,
        label="Grupo",
    )

    class Meta(AdminUserCreationForm.Meta):
        model = Usuario
        fields = ("username", "first_name", "last_name", "email", "groups")


class UsuarioChangeForm(GrupoUnicoMixin, UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = "__all__"
```

**6.2 `app/apps/accounts/admin.py`:**

```python
"""Usuarios y grupos en /admin/ (readme, sección 5, "Habilitadores").

Solo el Administrador (superusuario) ve estas secciones: los 2 grupos no tienen permisos
sobre usuarios ni grupos. Nadie borra: la baja de un usuario es is_active = False.
"""

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group

from apps.accounts.forms import UsuarioChangeForm, UsuarioCreationForm
from apps.accounts.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm
    list_display = ("username", "first_name", "last_name", "grupo", "is_active", "is_superuser")
    list_filter = ("is_active", "is_superuser", "groups")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "email")}),
        ("Acceso", {"fields": ("is_active", "is_superuser", "groups")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "first_name", "last_name", "email", "groups",
                       "usable_password", "password1", "password2"),
        }),
    )
    readonly_fields = ("last_login", "date_joined")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("groups")  # sin N+1 en la lista

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "groups":
            kwargs["widget"] = forms.CheckboxSelectMultiple
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    @admin.display(description="Grupo")
    def grupo(self, usuario):
        return ", ".join(g.name for g in usuario.groups.all()) or "—"

    def has_delete_permission(self, request, obj=None):
        return False  # baja lógica: desmarcar "is_active"


# Los 2 grupos los crea la migración 0003_grupos: no se agregan ni se borran a mano
admin.site.unregister(Group)


@admin.register(Group)
class GrupoAdmin(GroupAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
```

> Si `AdminUserCreationForm` no existe en tu versión de Django, usa `UserCreationForm` y quita `usable_password` de `add_fieldsets` (Django < 5.1).

### Paso 7. Tests en verde (≈ 15 min)

Ejecuta los de la sección 3 con `dtest apps/accounts -q`: todos deben pasar.

### Paso 8. Verificación final y *pull request* (≈ 30 min)

Ejecuta la sección 5 completa, marca la lista de la sección 6 y abre el PR.

---

## 3. Tests requeridos

### 3.1 `apps/accounts/tests/test_grupos.py`

```python
"""Los 2 grupos, sus permisos y un solo grupo por usuario (D1)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction

pytestmark = pytest.mark.django_db


def codigos(nombre):
    return set(Group.objects.get(name=nombre).permissions.values_list("codename", flat=True))


def test_existen_exactamente_los_2_grupos():
    assert set(Group.objects.values_list("name", flat=True)) == {"Solo lectura", "Lectura y escritura"}


def test_solo_lectura_solo_puede_ver():
    permisos = codigos("Solo lectura")
    assert {"view_medicamento", "view_residente", "view_principioactivo"} <= permisos
    assert all(codigo.startswith("view_") for codigo in permisos)


def test_lectura_y_escritura_ve_agrega_y_cambia_pero_no_borra():
    permisos = codigos("Lectura y escritura")
    assert {"add_medicamento", "change_residente", "add_medicamentoprincipioactivo"} <= permisos
    assert not any(codigo.startswith("delete_") for codigo in permisos)


def test_ningun_grupo_gestiona_usuarios():
    assert not any("usuario" in c or "group" in c for c in codigos("Lectura y escritura"))


def test_un_usuario_solo_puede_tener_un_grupo():
    usuario = get_user_model().objects.create_user("prueba.grupos")
    usuario.groups.add(Group.objects.get(name="Solo lectura"))
    with pytest.raises(IntegrityError, match="uq_usuario_un_grupo"):
        with transaction.atomic():
            usuario.groups.add(Group.objects.get(name="Lectura y escritura"))
```

### 3.2 `apps/accounts/tests/test_login.py`

```python
"""Inicio de sesión, cierre de sesión, sesiones y bloqueo por intentos fallidos (sección 2.5)."""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.http]
CLAVE = "Prueba-operador-2026"


@pytest.fixture
def operador():
    usuario = get_user_model().objects.create_user("prueba.operador", password=CLAVE, is_staff=True)
    usuario.groups.add(Group.objects.get(name="Lectura y escritura"))
    return usuario


def entrar(client, usuario, clave):
    return client.post(reverse("login"), {"username": usuario, "password": clave})


def test_la_pagina_de_login_no_usa_recursos_externos(client):
    respuesta = client.get(reverse("login"))
    html = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert "css/vendor/bootstrap.min.css" in html
    assert "cdn" not in html.lower() and "<script>" not in html
    assert 'for="id_username"' in html and 'for="id_password"' in html  # <label> en cada campo


def test_login_correcto_lleva_al_panel(client, operador):
    respuesta = entrar(client, "prueba.operador", CLAVE)
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("admin:index")


def test_login_incorrecto_muestra_el_error(client, operador):
    respuesta = entrar(client, "prueba.operador", "Prueba-equivocada-1")
    assert respuesta.status_code == 200
    assert "Usuario o contraseña incorrectos" in respuesta.content.decode()


def test_la_raiz_lleva_al_login(client):
    assert client.get("/").url == reverse("login")


def test_sin_sesion_el_panel_pide_login(client):
    respuesta = client.get("/admin/")
    assert respuesta.status_code == 302
    assert respuesta.url.startswith("/admin/login/")


def test_cerrar_sesion_solo_con_post(client, operador):
    client.force_login(operador)
    assert client.get(reverse("logout")).status_code == 405
    respuesta = client.post(reverse("logout"))
    assert respuesta.url == reverse("login")


def test_5_intentos_fallidos_bloquean_la_cuenta(client, operador):
    for _ in range(settings.AXES_FAILURE_LIMIT):
        entrar(client, "prueba.operador", "Prueba-equivocada-1")
    respuesta = entrar(client, "prueba.operador", CLAVE)  # ni con la contraseña correcta
    assert respuesta.status_code == 429
    assert "bloqueada" in respuesta.content.decode()


def test_la_sesion_expira_tras_30_minutos_de_inactividad():
    assert settings.SESSION_COOKIE_AGE == 1800
    assert settings.SESSION_SAVE_EVERY_REQUEST and settings.SESSION_EXPIRE_AT_BROWSER_CLOSE
```

### 3.3 `apps/accounts/tests/test_admin_usuarios.py`

```python
"""Solo el Administrador gestiona usuarios; cada usuario tiene exactamente un grupo."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

pytestmark = [pytest.mark.django_db, pytest.mark.http]
URL_ALTA = "/admin/accounts/usuario/add/"


def alta(admin_client, **cambios):
    datos = {
        "username": "prueba.nuevo", "first_name": "Prueba", "last_name": "Nueva",
        "email": "prueba.nueva@example.com", "usable_password": "true",
        "password1": "Prueba-segura-2026", "password2": "Prueba-segura-2026",
        "groups": [Group.objects.get(name="Solo lectura").pk],
    }
    return admin_client.post(URL_ALTA, datos | cambios)


def test_el_administrador_da_de_alta_un_usuario_con_un_grupo(admin_client):
    assert alta(admin_client).status_code == 302
    usuario = get_user_model().objects.get(username="prueba.nuevo")
    assert usuario.is_staff  # entra al panel
    assert list(usuario.groups.values_list("name", flat=True)) == ["Solo lectura"]
    assert usuario.password.startswith("argon2$")


@pytest.mark.parametrize("grupos", [[], ["Solo lectura", "Lectura y escritura"]])
def test_sin_grupo_o_con_dos_el_formulario_avisa(admin_client, grupos):
    ids = [Group.objects.get(name=nombre).pk for nombre in grupos]
    respuesta = alta(admin_client, groups=ids)
    assert respuesta.status_code == 200
    assert "Elige exactamente un grupo" in respuesta.content.decode()


def test_un_usuario_de_grupo_no_ve_los_usuarios(client):
    usuario = get_user_model().objects.create_user("prueba.lector", is_staff=True)
    usuario.groups.add(Group.objects.get(name="Lectura y escritura"))
    client.force_login(usuario)
    assert client.get("/admin/accounts/usuario/").status_code == 403


def test_nadie_borra_usuarios(admin_client, admin_user):
    assert admin_client.get(f"/admin/accounts/usuario/{admin_user.pk}/delete/").status_code == 403


def test_los_grupos_no_se_crean_a_mano(admin_client):
    assert admin_client.get("/admin/auth/group/add/").status_code == 403
```

> `admin_client` y `admin_user` son *fixtures* de `pytest-django`: un superusuario con sesión iniciada.

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| Sin JavaScript ni estilos en línea; Bootstrap desde `static/` | Consola del navegador sin errores de CSP en <https://localhost/accounts/login/>; djLint (`H021`) rechaza los `style="..."` |
| Plantillas con el formato y el lint de djLint | Sección 5, paso 1 |
| `<label>` visible en cada campo del login | `test_la_pagina_de_login_no_usa_recursos_externos` |
| Login usable en el celular (390 px), sin desplazamiento horizontal | Herramientas del navegador, modo dispositivo |
| La autorización se valida en el servidor, no ocultando enlaces | Tests de `403` |
| Ningún grupo tiene `delete_*` ni permisos sobre usuarios | Tests de `test_grupos.py` |
| Las migraciones `0003` y `0004` se revierten | Sección 5, paso 4 |
| Textos visibles en español | Revisión del PR |

---

## 5. Verificación: comandos y resultado esperado

```bash
# 1. Calidad del código (las primeras plantillas: desde aquí corre djLint en el CI)
docker compose exec web ruff check . && docker compose exec web ruff format --check .
docker compose exec web djlint . --check && docker compose exec web djlint . --lint
# 0 files would be updated. / Linted 3 files, found 0 errors.
dj check && dj makemigrations --check --dry-run

# 2. Tests
dtest apps/accounts -q
dtest -q --cov=apps --cov-fail-under=80

# 3. Grupos y restricción en la base
dpsql -c "SELECT g.name, count(*) FROM auth_group g JOIN auth_group_permissions gp ON gp.group_id = g.id GROUP BY 1"
# Lectura y escritura | 15      (5 modelos × view/add/change)
# Solo lectura        |  5
dpsql -c '\d usuario_groups'      # uq_usuario_un_grupo UNIQUE (usuario_id)

# 4. Las migraciones se revierten
./scripts/migrate.sh accounts 0002
./scripts/migrate.sh

# 5. En el navegador (con la base migrada y collectstatic)
dj collectstatic --noinput
# https://localhost/                 -> redirige a /accounts/login/
# Entra como Administrador           -> llega al panel; ve "Usuarios" y "Grupos"
# Crea un usuario de "Solo lectura"  -> sin grupo, el formulario avisa
# Cierra sesión y entra con él       -> ve el panel, pero no "Usuarios" ni "Grupos"
# 5 contraseñas incorrectas seguidas -> "Demasiados intentos fallidos" (429)
dj axes_reset                       # desbloquea las cuentas (solo desarrollo)
```

> **Diferencias con lo que trae esta guía** (cambio de OpenSpec `hb-08-login-grupos`):
>
> - **Versiones:**
>   - **Bootstrap 5.3.9**, no 5.3.3. Se obtiene con `npm pack bootstrap@5.3.9` en un directorio temporal: npm comprueba la integridad del paquete, y de él se copian sin cambios `dist/css/bootstrap.min.css` y `dist/js/bootstrap.bundle.min.js`. El `curl` del paso 2 no comprobaba la integridad.
>   - **`django-axes==9.1.0`**, sin el extra `ipware`. Las 2 versiones quedaron fijadas en ADR-0002, ADR-0022 y el readme.
> - **`axes.W006` silenciado** en `base.py` y `prod.py`: el bloqueo es por usuario. Agregar `ip_address` detrás de nginx haría que 5 fallos de cualquiera bloquearan a todos, porque todos llegan con la IP del proxy.
> - **Orden del *middleware*:** `AxesMiddleware` va después del de CSP, así la respuesta `429` también lleva la CSP.
> - **`groups.add()` no lanza `IntegrityError`:** Django inserta en la tabla puente con `ON CONFLICT DO NOTHING`, así que `uq_usuario_un_grupo` impide el segundo grupo en silencio. Por eso el test de la restricción inserta directamente en la tabla puente; el formulario del panel es el que avisa.
> - **Tests añadidos:**
>   - los permisos exactos de cada grupo y la definición de `uq_usuario_un_grupo`;
>   - el formulario de cambio con 2 grupos y su control;
>   - la lista de grupos con `403` y el borrado de un grupo;
>   - la cabecera CSP y la ausencia de `style=` en el login;
>   - la configuración de `django-axes` y un control de 4 intentos que no bloquean.
> - **`0003_grupos`** depende de `entidades.0004_mensaje_nombres`, la última migración de entidades.
> - **Revisión en el navegador:** se hizo con Chrome *headless* por CDP y con emulación de dispositivo. A 390 px no hay desplazamiento horizontal, y no aparecen violaciones de CSP ni en escritorio ni en el celular. El único mensaje de la consola es un 404 de `/favicon.ico`, porque el proyecto aún no tiene ícono.
>   - No sirve `--window-size=390` sin emulación: Chrome tiene un ancho mínimo de ventana, dibuja la página más ancha y la captura sale recortada.
> - **Rama:** `feature/entrega-2-vmrr`, no `feature/HB-08-login-grupos` (`CLAUDE.md`, sección Git).

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] Capturas del login en escritorio y a 390 px, y de la consola sin errores de CSP.
- [ ] La versión de `django-axes` fijada está anotada en el PR.

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `djlint . --check` dice `files would be updated` | La plantilla no tiene el formato de djLint | `docker compose exec web djlint . --reformat`, revisa el diff y vuelve a commitear |
| `AxesBackendRequestParameterRequired` en un test | El test usa `client.login()`, que no pasa la petición a `authenticate` | En los tests usa `client.force_login(usuario)` o un `POST` al login |
| `403 CSRF` al cerrar sesión | El formulario de `base.html` no tiene `{% csrf_token %}` | Paso 4.2 |
| `405 Method Not Allowed` al cerrar sesión con un enlace | Desde Django 5, `LogoutView` solo acepta `POST` | Usa el formulario de `base.html` |
| El panel no muestra el catálogo a un usuario de grupo | El usuario no tiene `is_staff` o no tiene grupo | Edítalo como Administrador (el formulario los corrige) |
| `IntegrityError: uq_usuario_un_grupo` al cargar el mock | El mock ya estaba cargado | Recrea la base: `docker compose down -v`, `up -d`, `./scripts/migrate.sh` |
| La página de login sin estilos | Falta `collectstatic` o la descarga de Bootstrap trajo una página de error | Paso 2 (`head -c 40`) y `dj collectstatic --noinput` |
| La cuenta quedó bloqueada en desarrollo | 5 intentos fallidos | `dj axes_reset` |
| La consola de un solo navegador muestra una violación de CSP por un script en línea (`script-src-elem`), con origen `sandbox eval code`, `moz-extension://` o `chrome-extension://` | Una extensión del navegador inyecta el script, y la CSP lo bloquea como debe. Pasó en Firefox; no en Chrome, en Brave ni en la ventana privada de Firefox | Comprueba en una ventana privada, donde no corren las extensiones. **No agregues el hash que sugiere el mensaje a la CSP:** es código de la extensión, no de la aplicación |
