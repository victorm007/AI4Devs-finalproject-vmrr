# TK-03 · Guía paso a paso: pantalla de consulta de existencias

> **Ticket:** [readme, sección 6, TK-03](../../readme.md#6-tickets-de-trabajo) · **Tipo:** frontend (plantillas Django + Bootstrap 5 + HTMX) · **Estimación:** 3 puntos · **Rama:** `feature/TK-03-pantalla-existencias`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket y en HU-02 (sección 5). Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.
>
> **Integración** (readme, sección 6, "Puntos de integración"): este ticket **provee** los puntos 9 y **consume** los puntos 1, 2, 5, 6, 7 y 11. No cambies un punto que provees sin avisar en el PR. La prueba conjunta de los 3 tickets está en [`integracion.md`](integracion.md).

**Resultado al terminar:** en `/existencias/` el usuario escribe "losartan" y, sin recargar la página, ve cuánto hay de cada medicamento por entidad. En el celular los resultados son tarjetas legibles y sin desplazamiento horizontal. Es la página de inicio después del login.

---

## 0. Antes de empezar

### 0.1 Lee primero (30 min)

| Qué | Dónde |
|---|---|
| HU-02: reglas y criterios de aceptación | readme, sección 5 |
| Consulta 1 (búsqueda sin acentos) y sus índices | readme, sección 3.3 |
| TK-03 | readme, sección 6 |
| Guía de TK-01, pasos 0.4 (atajos) y 9 (fixtures) | [`TK-01-esquema-inventario.md`](TK-01-esquema-inventario.md) |
| HTMX: `hx-get`, `hx-trigger`, `hx-target`, `hx-swap-oob` | <https://htmx.org/docs/> (20 min) |

### 0.2 Requisitos previos

- TK-01 integrado en `main` (tablas y `datos_demo`). TK-02 no es obligatorio: el mock ya trae saldos.
- De la semana 1: `base.html` con Bootstrap 5, el login de Django en `LOGIN_URL` (por defecto `/accounts/login/`), `Entidad.__str__` devuelve el nombre del Hogar o el nombre completo del residente, y `Medicamento` tiene el campo `principios_activos` (muchos a muchos).

```bash
git switch main && git pull
set -a && . ./.env && set +a
dj()    { docker compose exec web python manage.py "$@"; }
dtest() { docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" web pytest "$@"; }

dj shell -c "
from apps.catalogo.models import Medicamento
print(Medicamento._meta.get_field('principios_activos').many_to_many)   # True
"
git switch -c feature/TK-03-pantalla-existencias
```

### 0.3 Cómo funciona la pantalla (lee esto antes de programar)

```
Usuario escribe "losartan"
   │  (HTMX espera 300 ms sin teclear)
   ▼
GET /existencias/?q=losartan   con cabecera HX-Request: true
   │
   ▼
ExistenciasView ── valida FiltroExistenciasForm ── buscar_existencias(...)  (selectors.py)
   │
   ├─ petición HTMX  → responde solo _resultados.html → HTMX lo pone dentro de #resultados
   └─ petición normal → responde la página completa existencias.html (recargar o compartir la URL)
```

- La **misma vista** sirve la página completa y el fragmento. Así la URL con filtros siempre funciona sola, aunque se abra en otra pestaña.
- Toda la lógica de búsqueda vive en **`selectors.py`**, no en la vista: TK-05 (`GET /api/v1/existencias`) la reutilizará.

---

## 1. Archivos que vas a crear o modificar

```
app/
├── requirements.txt                               # MODIFICAR: django-htmx
├── requirements-dev.txt                           # MODIFICAR: pytest-playwright
├── config/settings/base.py                        # MODIFICAR: django_htmx y LOGIN_REDIRECT_URL
├── config/urls.py                                 # MODIFICAR: incluye inventario y redirige "/"
├── static/js/vendor/htmx.min.js                   # NUEVO: HTMX servido localmente (CSP)
├── templates/base.html                            # MODIFICAR: script de HTMX y menú "Existencias"
└── apps/inventario/
    ├── selectors.py                               # NUEVO: buscar_existencias
    ├── forms.py                                   # NUEVO: FiltroExistenciasForm
    ├── views.py                                   # NUEVO: ExistenciasView
    ├── urls.py                                    # NUEVO
    ├── templatetags/__init__.py                   # NUEVO (vacío)
    ├── templatetags/inventario_extras.py          # NUEVO: filtro dosis
    ├── templates/inventario/existencias.html      # NUEVO: página completa
    ├── templates/inventario/_resultados.html      # NUEVO: fragmento de resultados
    ├── templates/inventario/_aviso.html           # NUEVO: aviso "al menos 3 caracteres"
    └── tests/
        ├── test_selectors.py                      # NUEVO
        ├── test_views_existencias.py              # NUEVO
        └── test_templatetags.py                   # NUEVO
app/e2e/
└── test_existencias.py                            # NUEVO: Playwright (dentro de app/ para que el contenedor lo vea)
```

---

## 2. Tareas paso a paso

Haz un commit al terminar cada paso.

### Paso 1. HTMX y `django-htmx` (≈ 30 min)

```bash
# Versiones fijas: el proyecto fija todas sus dependencias (sección 2.5)
docker compose exec web pip index versions django-htmx | head -1   # anota la última versión estable
echo "django-htmx==<versión anotada>" >> app/requirements.txt

# HTMX 2.0.x: usa la última 2.0.x publicada (2.0.4 en este ejemplo)
mkdir -p app/static/js/vendor
curl -sL https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js -o app/static/js/vendor/htmx.min.js
head -c 60 app/static/js/vendor/htmx.min.js; echo     # debe ser JavaScript, no una página de error
docker compose up -d --build web
```

> Anota en el PR las versiones que fijaste. HTMX se sirve desde `static/` y no desde un CDN: la `Content-Security-Policy` de Nginx (sección 2.5) solo permite scripts propios.

En `config/settings/base.py`:

```python
INSTALLED_APPS += ["django_htmx"]
MIDDLEWARE += ["django_htmx.middleware.HtmxMiddleware"]   # agrega request.htmx
LOGIN_REDIRECT_URL = "inventario:existencias"             # página de inicio tras el login
```

En `templates/base.html`, antes de `</head>`, y la entrada del menú:

```django
<script src="{% static 'js/vendor/htmx.min.js' %}" defer></script>
...
<a class="nav-link" href="{% url 'inventario:existencias' %}">Existencias</a>
```

### Paso 2. El selector `buscar_existencias` (≈ 1 h)

`app/apps/inventario/selectors.py`:

```python
"""Consultas de lectura del inventario. Las reutilizan la pantalla (TK-03) y la API (TK-05)."""

import unicodedata

from django.db.models import Func, Q, QuerySet
from django.db.models.functions import Lower

from apps.catalogo.models import Medicamento, PrincipioActivo

from .models import Existencia


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, igual que f_unaccent(lower(...)) en PostgreSQL."""
    descompuesto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def _sin_acentos(campo: str) -> Func:
    """f_unaccent(lower(campo)): EXACTAMENTE la expresión de los índices trigram (sección 3.3).

    Si la expresión cambia, PostgreSQL deja de usar el índice y la búsqueda se vuelve lenta.
    """
    return Func(Lower(campo), function="f_unaccent")


def _medicamentos_por_nombre(texto: str) -> QuerySet:
    return (
        Medicamento.objects.filter(activo=True)          # el índice es parcial: WHERE activo
        .annotate(nombre_normalizado=_sin_acentos("nombre_comercial"))
        .filter(nombre_normalizado__contains=texto)
        .values("id")
    )


def _medicamentos_por_principio_activo(texto: str) -> QuerySet:
    principios = (
        PrincipioActivo.objects.annotate(nombre_normalizado=_sin_acentos("nombre"))
        .filter(nombre_normalizado__contains=texto)
    )
    return Medicamento.objects.filter(activo=True, principios_activos__in=principios).values("id")


def buscar_existencias(*, entidad=None, medicamento=None, principio_activo=None,
                       q: str | None = None, incluir_sin_saldo: bool = False) -> QuerySet[Existencia]:
    """Existencias filtradas, con el Hogar primero y después los residentes por apellido.

    Ejemplo: buscar_existencias(q="losartan") -> Hogar·Losartán 20, José Luis·Cozaar 32, ...
    `q` busca en el nombre comercial y en los principios activos, sin mayúsculas ni acentos.
    """
    existencias = Existencia.objects.select_related(
        "entidad", "entidad__residente", "medicamento", "medicamento__presentacion"
    ).filter(medicamento__activo=True)

    if not incluir_sin_saldo:
        existencias = existencias.filter(saldo__gt=0)
    if entidad is not None:
        existencias = existencias.filter(entidad=entidad)
    if medicamento is not None:
        existencias = existencias.filter(medicamento=medicamento)
    if principio_activo is not None:
        existencias = existencias.filter(medicamento__principios_activos=principio_activo)
    if q:
        texto = normalizar(q)
        existencias = existencias.filter(
            Q(medicamento__in=_medicamentos_por_nombre(texto))
            | Q(medicamento__in=_medicamentos_por_principio_activo(texto))
        )

    return existencias.order_by(
        "entidad__tipo",                       # "HOGAR" < "RESIDENTE": el Hogar va primero
        "entidad__residente__primer_apellido",
        "entidad__residente__primer_nombre",
        "medicamento__nombre_comercial",
        "medicamento__concentracion",
    )
```

> **Pruébalo antes de seguir** (con el mock cargado en tu base de desarrollo):
> ```bash
> dj shell -c "from apps.inventario.selectors import buscar_existencias as b; print([(str(e.entidad), e.medicamento.nombre_comercial, e.saldo) for e in b(q='losartan')])"
> ```

### Paso 3. El formulario de filtros (≈ 45 min)

`app/apps/inventario/forms.py`:

```python
from django import forms

from apps.catalogo.models import Medicamento, PrincipioActivo
from apps.entidades.models import Entidad


class EntidadChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, entidad) -> str:
        # Los egresados o fallecidos aparecen marcados: pueden tener sobrantes
        if entidad.activa:
            return str(entidad)
        return f"{entidad} ({entidad.residente.get_estado_display().lower()})"


class FiltroExistenciasForm(forms.Form):
    q = forms.CharField(
        label="Buscar", required=False, min_length=3, max_length=100, strip=True,
        error_messages={"min_length": "Escribe al menos 3 caracteres."},
        widget=forms.TextInput(attrs={
            "type": "search", "class": "form-control", "autocomplete": "off",
            "placeholder": "Nombre o principio activo", "minlength": 3,
        }),
    )
    entidad = EntidadChoiceField(
        label="Residente u Hogar", required=False, empty_label="Todos",
        queryset=Entidad.objects.none(), widget=forms.Select(attrs={"class": "form-select"}),
    )
    principio_activo = forms.ModelChoiceField(
        label="Principio activo", required=False, empty_label="Todos",
        queryset=PrincipioActivo.objects.order_by("nombre"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    incluir_sin_saldo = forms.BooleanField(
        label="Incluir sin saldo", required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    medicamento = forms.ModelChoiceField(
        required=False, queryset=Medicamento.objects.all(), widget=forms.HiddenInput,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["entidad"].queryset = Entidad.objects.select_related("residente").order_by(
            "tipo", "residente__primer_apellido", "residente__primer_nombre"
        )
```

> Los nombres de los campos coinciden con los argumentos de `buscar_existencias`. Por eso la vista puede hacer `buscar_existencias(**form.cleaned_data)`.

### Paso 4. La vista y las URLs (≈ 45 min)

`app/apps/inventario/views.py`:

```python
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render
from django.views.generic import ListView
from django_htmx.http import HttpResponseClientRedirect

from .forms import FiltroExistenciasForm
from .models import Existencia
from .selectors import buscar_existencias


class ExistenciasView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Consulta de existencias (HU-02). Página completa o fragmento HTMX."""

    permission_required = "inventario.view_existencia"   # lo tienen los 2 grupos
    paginate_by = 20
    context_object_name = "existencias"

    def get(self, request, *args, **kwargs):
        self.form = FiltroExistenciasForm(request.GET)
        if request.htmx and not self.form.is_valid():
            # q demasiado corto: muestra el aviso y deja la lista como estaba
            respuesta = render(request, "inventario/_aviso.html", {"form": self.form, "oob": True})
            respuesta["HX-Reswap"] = "none"
            return respuesta
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if not self.form.is_valid():
            return Existencia.objects.none()
        return buscar_existencias(**self.form.cleaned_data)

    def get_template_names(self):
        if self.request.htmx:
            return ["inventario/_resultados.html"]
        return ["inventario/existencias.html"]

    def get_context_data(self, **kwargs):
        return super().get_context_data(form=self.form, **kwargs)

    def handle_no_permission(self):
        # Sesión vencida durante una búsqueda HTMX: redirige la página entera al login,
        # en lugar de meter el formulario de login dentro de #resultados
        if self.request.htmx and not self.request.user.is_authenticated:
            return HttpResponseClientRedirect(
                f"{settings.LOGIN_URL}?next={self.request.get_full_path()}"
            )
        return super().handle_no_permission()
```

`app/apps/inventario/urls.py`:

```python
from django.urls import path

from .views import ExistenciasView

app_name = "inventario"
urlpatterns = [
    path("existencias/", ExistenciasView.as_view(), name="existencias"),
]
```

En `app/config/urls.py`:

```python
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="inventario:existencias"), name="inicio"),
    path("", include("apps.inventario.urls")),
    # ... las rutas existentes (admin, accounts, api)
]
```

### Paso 5. El filtro `dosis` (≈ 15 min)

`app/apps/inventario/templatetags/inventario_extras.py` (y un `__init__.py` vacío en la carpeta):

```python
from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def dosis(valor) -> str:
    """10.00 -> "10", 0.50 -> "0.5", 62.25 -> "62.25". Sin ceros sobrantes."""
    if valor is None:
        return ""
    return f"{Decimal(valor).normalize():f}"
```

> `floatformat` no sirve aquí: `0.50|floatformat:"-2"` muestra `0.50`, no `0.5`.

### Paso 6. Plantillas (≈ 1.5 h)

`templates/inventario/existencias.html`:

```django
{% extends "base.html" %}
{% block title %}Existencias{% endblock %}

{% block content %}
<h1 class="h3 mb-3">Existencias</h1>

<form id="filtros" method="get" action="{% url 'inventario:existencias' %}" class="row g-2 align-items-end mb-2"
      hx-get="{% url 'inventario:existencias' %}" hx-target="#resultados" hx-push-url="true"
      hx-trigger="input changed delay:300ms from:#id_q, change" hx-indicator="#cargando">
  <div class="col-12 col-md-4">
    <label for="{{ form.q.id_for_label }}" class="form-label">{{ form.q.label }}</label>
    {{ form.q }}
  </div>
  <div class="col-12 col-sm-6 col-md-3">
    <label for="{{ form.entidad.id_for_label }}" class="form-label">{{ form.entidad.label }}</label>
    {{ form.entidad }}
  </div>
  <div class="col-12 col-sm-6 col-md-3">
    <label for="{{ form.principio_activo.id_for_label }}" class="form-label">{{ form.principio_activo.label }}</label>
    {{ form.principio_activo }}
  </div>
  <div class="col-12 col-md-2">
    <div class="form-check py-2">
      {{ form.incluir_sin_saldo }}
      <label for="{{ form.incluir_sin_saldo.id_for_label }}" class="form-check-label">{{ form.incluir_sin_saldo.label }}</label>
    </div>
  </div>
  {{ form.medicamento }}
  <noscript><div class="col-12"><button class="btn btn-primary">Buscar</button></div></noscript>
</form>

{% include "inventario/_aviso.html" %}
<div id="cargando" class="htmx-indicator text-body-secondary small mb-2" role="status">Buscando…</div>

<div id="resultados" aria-live="polite">
  {% include "inventario/_resultados.html" %}
</div>
{% endblock %}
```

`templates/inventario/_aviso.html` (se usa en la página y, con `oob`, en la respuesta HTMX):

```django
<div id="aviso" role="status" {% if oob %}hx-swap-oob="true"{% endif %}>
  {% if form.q.errors %}
    <div class="alert alert-warning py-2">{{ form.q.errors.0 }}</div>
  {% endif %}
</div>
```

`templates/inventario/_resultados.html`:

```django
{% load inventario_extras %}
{# En una respuesta HTMX válida, borra el aviso que pudiera haber quedado #}
{% if request.htmx %}<div id="aviso" role="status" hx-swap-oob="true"></div>{% endif %}

{% if existencias %}
  <p class="small text-body-secondary mb-2">{{ paginator.count }} resultado{{ paginator.count|pluralize }}</p>

  {# Escritorio (≥ 768 px): tabla #}
  <table class="table table-hover align-middle d-none d-md-table">
    <thead>
      <tr>
        <th scope="col">Entidad</th>
        <th scope="col">Medicamento</th>
        <th scope="col" class="text-end">Saldo</th>
        <th scope="col">Último movimiento</th>
      </tr>
    </thead>
    <tbody>
      {% for e in existencias %}
        <tr data-test="existencia">
          <td>{{ e.entidad }}</td>
          <td>
            <a href="?{% querystring medicamento=e.medicamento_id page=None %}">{{ e.medicamento.nombre_comercial }}</a>
            <span class="text-body-secondary">{{ e.medicamento.presentacion }} {{ e.medicamento.concentracion }}</span>
          </td>
          <td class="text-end text-nowrap">
            {% if e.saldo %}{{ e.saldo|dosis }} dosis{% else %}<span class="badge text-bg-secondary">Agotado</span>{% endif %}
          </td>
          <td class="text-nowrap">{{ e.actualizado_en|date:"d/m/Y H:i" }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>

  {# Celular (< 768 px): tarjetas, sin desplazamiento horizontal #}
  <ul class="list-group d-md-none mb-3">
    {% for e in existencias %}
      <li class="list-group-item d-flex justify-content-between align-items-start gap-2" data-test="existencia">
        <div class="text-break">
          <a class="fw-semibold" href="?{% querystring medicamento=e.medicamento_id page=None %}">{{ e.medicamento.nombre_comercial }}</a>
          <span>{{ e.medicamento.presentacion }} {{ e.medicamento.concentracion }}</span>
          <div class="small text-body-secondary">{{ e.entidad }} · {{ e.actualizado_en|date:"d/m/Y H:i" }}</div>
        </div>
        <span class="text-nowrap">
          {% if e.saldo %}{{ e.saldo|dosis }} dosis{% else %}<span class="badge text-bg-secondary">Agotado</span>{% endif %}
        </span>
      </li>
    {% endfor %}
  </ul>

  {% if is_paginated %}
    <nav aria-label="Páginas de resultados">
      <ul class="pagination">
        {% if page_obj.has_previous %}
          <li class="page-item">
            <a class="page-link" href="?{% querystring page=page_obj.previous_page_number %}"
               hx-get="?{% querystring page=page_obj.previous_page_number %}" hx-target="#resultados" hx-push-url="true">Anterior</a>
          </li>
        {% endif %}
        <li class="page-item disabled"><span class="page-link">{{ page_obj.number }} de {{ paginator.num_pages }}</span></li>
        {% if page_obj.has_next %}
          <li class="page-item">
            <a class="page-link" href="?{% querystring page=page_obj.next_page_number %}"
               hx-get="?{% querystring page=page_obj.next_page_number %}" hx-target="#resultados" hx-push-url="true">Siguiente</a>
          </li>
        {% endif %}
      </ul>
    </nav>
  {% endif %}
{% else %}
  <div class="text-center py-5" data-test="sin-resultados">
    <p class="mb-3">No hay existencias que coincidan con la búsqueda.</p>
    <a class="btn btn-outline-secondary" href="{% url 'inventario:existencias' %}">Limpiar filtros</a>
  </div>
{% endif %}
```

> **Reglas de las plantillas:** nada de `<script>` ni `onclick` en línea (los bloquea la CSP); todo campo con su `<label>`; los textos visibles en español; `{% querystring %}` es de Django 5.1+ y conserva los filtros al paginar.

Revisa la pantalla a mano: `https://localhost/existencias/`, con el modo de dispositivo de Chrome (F12 → icono de celular → 390 × 844).

### Paso 7. Tests (≈ 2 h)

Ver la sección 3.

### Paso 8. Verificación final y *pull request* (≈ 1 h)

Ejecuta los comandos de la sección 5, toma las capturas y completa la lista de la sección 6.

---

## 3. Tests requeridos

### 3.1 `apps/inventario/tests/test_selectors.py`: la búsqueda devuelve lo correcto

```python
"""buscar_existencias sobre el dataset mock (criterios de HU-02 y TK-03)."""

import pytest

from apps.catalogo.models import PrincipioActivo
from apps.inventario.selectors import buscar_existencias, normalizar


def filas(existencias):
    return [(str(e.entidad), e.medicamento.nombre_comercial, e.saldo) for e in existencias]


@pytest.mark.parametrize(("texto", "esperado"), [
    ("Losartán", "losartan"), ("ÁCIDO", "acido"), ("Ñandú", "nandu"), ("eutirox", "eutirox"),
])
def test_normalizar_quita_acentos_y_mayusculas(texto, esperado):
    assert normalizar(texto) == esperado


def test_busqueda_sin_acentos_por_nombre_y_principio_activo(demo):
    assert filas(buscar_existencias(q="losartan")) == [
        ("Hogar Gerontológico Demo", "Losartán", 20),
        ("José Luis Ramírez Ortega", "Cozaar", 32),
        ("José Luis Ramírez Ortega", "Losartán", 10),
    ]   # Hyzaar no aparece: no tiene existencias


def test_existencias_de_un_residente(demo):
    assert filas(buscar_existencias(entidad=demo.carmen)) == [
        ("Carmen Torres Vega", "Eutirox", 33),
        ("Carmen Torres Vega", "Exelon", 3),
        ("Carmen Torres Vega", "Paracetamol", 14),
    ]


def test_principio_activo_con_otro_nombre_comercial_e_incluir_sin_saldo(demo):
    assert filas(buscar_existencias(q="paracetamol", incluir_sin_saldo=True)) == [
        ("Hogar Gerontológico Demo", "Paracetamol", 80),
        ("Hogar Gerontológico Demo", "Tempra", 0),
        ("Carmen Torres Vega", "Paracetamol", 14),
    ]


def test_sin_mayusculas_ni_acentos(demo):
    assert filas(buscar_existencias(q="ACIDO")) == [
        ("Hogar Gerontológico Demo", "Aspirina Protect", 58),
    ]


def test_filtro_por_principio_activo(demo):
    losartan = PrincipioActivo.objects.get(nombre="Losartán")
    assert len(buscar_existencias(principio_activo=losartan)) == 3


def test_sin_resultados(demo):
    assert filas(buscar_existencias(q="ibuprofeno")) == []
```

> Si los nombres que imprime `str(e.entidad)` no coinciden (por ejemplo, el formato del nombre del residente), ajusta el test al `__str__` real de la semana 1, no al revés.

### 3.2 `apps/inventario/tests/test_views_existencias.py`: la vista y HTMX

```python
"""ExistenciasView: página completa, fragmento HTMX, avisos, permisos y consultas."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.models import Usuario

URL = reverse("inventario:existencias")
HTMX = {"HX-Request": "true"}


@pytest.fixture
def cliente_consulta(client, demo):
    client.force_login(Usuario.objects.get(username="consulta.demo"))   # solo lectura
    return client


def test_pagina_completa_para_solo_lectura(cliente_consulta):
    respuesta = cliente_consulta.get(URL, {"q": "losartan"})
    assert respuesta.status_code == 200
    assert "inventario/existencias.html" in [t.name for t in respuesta.templates]
    assert respuesta.content.decode().count('data-test="existencia"') == 6   # 3 filas + 3 tarjetas


def test_peticion_htmx_devuelve_solo_el_fragmento(cliente_consulta):
    respuesta = cliente_consulta.get(URL, {"q": "losartan"}, headers=HTMX)
    html = respuesta.content.decode()
    assert "<html" not in html
    assert 'id="aviso"' in html and 'hx-swap-oob="true"' in html   # limpia el aviso anterior


def test_busqueda_corta_no_cambia_la_lista(cliente_consulta):
    respuesta = cliente_consulta.get(URL, {"q": "lo"}, headers=HTMX)
    assert respuesta["HX-Reswap"] == "none"
    assert "Escribe al menos 3 caracteres." in respuesta.content.decode()


def test_estado_vacio(cliente_consulta):
    html = cliente_consulta.get(URL, {"q": "ibuprofeno"}).content.decode()
    assert "No hay existencias que coincidan con la búsqueda." in html
    assert "Limpiar filtros" in html


def test_sin_sesion_redirige_al_login(client, db):
    respuesta = client.get(URL)
    assert respuesta.status_code == 302
    assert "/accounts/login/" in respuesta["Location"]


def test_sin_sesion_en_htmx_redirige_la_pagina_entera(client, db):
    respuesta = client.get(URL, {"q": "losartan"}, headers=HTMX)
    assert respuesta.headers["HX-Redirect"].startswith("/accounts/login/?next=")


def test_inicio_redirige_a_existencias(cliente_consulta):
    assert cliente_consulta.get("/").url == URL


def test_sin_n_mas_1(cliente_consulta):
    with CaptureQueriesContext(connection) as uno:
        cliente_consulta.get(URL, {"q": "ACIDO"})                       # 1 resultado
    with CaptureQueriesContext(connection) as todos:
        cliente_consulta.get(URL, {"incluir_sin_saldo": "on"})          # 13 resultados
    assert len(uno) == len(todos)
```

### 3.3 `apps/inventario/tests/test_templatetags.py`

```python
from decimal import Decimal

import pytest

from apps.inventario.templatetags.inventario_extras import dosis


@pytest.mark.parametrize(("valor", "texto"), [
    (Decimal("10.00"), "10"), (Decimal("0.50"), "0.5"), (Decimal("62.25"), "62.25"),
    (Decimal("0"), "0"), (Decimal("100.00"), "100"), (None, ""),
])
def test_dosis_sin_ceros_sobrantes(valor, texto):
    assert dosis(valor) == texto
```

### 3.4 `app/e2e/test_existencias.py`: Playwright en un navegador real

**Preparación (una vez):** agrega `pytest-playwright` a `app/requirements-dev.txt` y, en la etapa de desarrollo del `Dockerfile`, `RUN playwright install --with-deps chromium`. Reconstruye con `docker compose build web`.

```python
"""Flujo real en Chromium: búsqueda en vivo, celular y teclado (TK-03)."""

import re

import pytest
from playwright.sync_api import expect

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True, serialized_rollback=True)]


@pytest.fixture
def pagina(page, live_server, datos_demo):
    errores = []
    page.on("pageerror", lambda error: errores.append(str(error)))           # excepciones de JS
    page.on("console", lambda m: errores.append(m.text)
            if "Content Security Policy" in m.text else None)                 # violaciones de CSP
    page.goto(f"{live_server.url}/accounts/login/")
    page.fill("#id_username", "consulta.demo")
    page.fill("#id_password", "DemoLectura2026!")
    page.click("button[type=submit]")
    expect(page).to_have_url(re.compile(r"/existencias/"))       # página de inicio
    yield page
    assert errores == []


def test_busqueda_en_vivo(pagina):
    pagina.get_by_label("Buscar").fill("losartan")
    expect(pagina.locator('[data-test="existencia"]:visible')).to_have_count(3)
    expect(pagina).to_have_url(re.compile(r"q=losartan"))


def test_busqueda_corta_muestra_aviso(pagina):
    pagina.get_by_label("Buscar").fill("lo")
    expect(pagina.get_by_text("Escribe al menos 3 caracteres.")).to_be_visible()


def test_celular_sin_desplazamiento_horizontal(pagina):
    pagina.set_viewport_size({"width": 390, "height": 844})
    pagina.get_by_label("Buscar").fill("paracetamol")
    expect(pagina.locator("ul.list-group [data-test=existencia]").first).to_be_visible()
    expect(pagina.locator("table")).to_be_hidden()
    assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_navegacion_con_teclado(pagina):
    pagina.get_by_label("Buscar").focus()
    for campo in ("#id_entidad", "#id_principio_activo", "#id_incluir_sin_saldo"):
        pagina.keyboard.press("Tab")
        expect(pagina.locator(campo)).to_be_focused()
```

Registra el marcador en la configuración de pytest: `markers = [..., "e2e: pruebas de extremo a extremo con Playwright"]`.

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| La búsqueda usa los índices trigram | Comando 4 de la sección 5: el plan muestra `ix_medicamento_nombre_trgm` |
| Sin N+1: mismo número de consultas con 1 y con 13 resultados | `test_sin_n_mas_1` |
| Sin JavaScript propio ni en línea; HTMX servido desde `static/` | Revisión del PR y consola del navegador sin violaciones de CSP |
| Accesible: `<label>` en cada campo, `aria-live` en los resultados, navegación con teclado | `test_navegacion_con_teclado` y Lighthouse ≥ 90 |
| *Responsive*: tarjetas bajo 768 px, sin desplazamiento horizontal, controles táctiles ≥ 44 px | `test_celular_sin_desplazamiento_horizontal` y revisión en 390 px |
| La URL refleja los filtros y funciona sola (recargar, compartir, botón Atrás) | Revisión manual: copia la URL en otra pestaña |
| La vista no contiene lógica de búsqueda: todo está en `selectors.py` | Revisión del PR |
| Textos en español y consistentes con HU-02 ("Escribe al menos 3 caracteres.", "Limpiar filtros") | Tests de la vista |
| El fragmento responde en menos de 300 ms con el mock | Comando 5 de la sección 5 |

---

## 5. Verificación: comandos y resultado esperado

```bash
# 1. Calidad y tests unitarios
docker compose exec web ruff check . && docker compose exec web ruff format --check .
dtest apps/inventario -q

# 2. Pruebas de extremo a extremo (Chromium sin interfaz, dentro del contenedor)
docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" \
    -e DJANGO_ALLOW_ASYNC_UNSAFE=true web pytest -m e2e e2e/ -q
# DJANGO_ALLOW_ASYNC_UNSAFE es necesario porque Playwright y el servidor de pruebas comparten proceso

# 3. Con el mock cargado (TK-01, paso 8): sesión con curl (04-api.md, sección 2)
BASE=https://localhost; JAR=/tmp/hogar.cookies; CURL="curl -s -k"
login() { rm -f "$JAR"; $CURL -c "$JAR" "$BASE/accounts/login/" -o /dev/null
  local csrf; csrf=$(awk '$6 == "csrftoken" { print $7 }' "$JAR")
  $CURL -b "$JAR" -c "$JAR" -o /dev/null -w "login: %{http_code}\n" -X POST "$BASE/accounts/login/" \
    -H "Referer: $BASE/accounts/login/" --data-urlencode "csrfmiddlewaretoken=$csrf" \
    --data-urlencode "username=$1" --data-urlencode "password=$2"; }
login consulta.demo 'DemoLectura2026!'                              # login: 302

$CURL -b "$JAR" -H "HX-Request: true" "$BASE/existencias/?q=losartan" | grep -c 'data-test="existencia"'
# 6  (3 filas de tabla + 3 tarjetas)
$CURL -b "$JAR" -H "HX-Request: true" -D - -o /dev/null "$BASE/existencias/?q=lo" | grep -i '^hx-reswap'
# HX-Reswap: none

# 4. La búsqueda usa el índice trigram (con enable_seqscan off, porque el catálogo es pequeño)
docker compose exec db psql -U app_owner -d "$POSTGRES_DB" -c "
SET enable_seqscan = off;
EXPLAIN SELECT id FROM medicamento
WHERE activo AND f_unaccent(lower(nombre_comercial)) LIKE '%losartan%';"
# Bitmap Index Scan on ix_medicamento_nombre_trgm

# 5. Tiempo de respuesta del fragmento (< 0.3 s)
$CURL -b "$JAR" -H "HX-Request: true" -o /dev/null -w "%{time_total}\n" "$BASE/existencias/?q=losartan"
```

**Revisión manual** (anota el resultado en el PR):
1. Chrome y Firefox de escritorio: escribe "losartan", cambia el residente, marca "Incluir sin saldo", pulsa el nombre de un medicamento, pagina y usa el botón Atrás.
2. Celular (o modo dispositivo de Chrome a 390 × 844): la misma secuencia, sin desplazamiento horizontal.
3. Lighthouse (F12 → Lighthouse → *Accessibility*): puntuación ≥ 90.
4. Consola del navegador: sin errores ni avisos de CSP.

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] Capturas de escritorio y de celular en el PR y en la sección 1.3 del readme.
- [ ] Versiones de `django-htmx` y HTMX fijadas y anotadas en el PR.

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `'WSGIRequest' object has no attribute 'htmx'` | Falta el middleware de `django-htmx` | Paso 1 |
| Al escribir no pasa nada | HTMX no cargó (404 en `htmx.min.js`) o la CSP lo bloqueó | Consola del navegador; ejecuta `collectstatic` y revisa la ruta del `<script>` |
| La página completa aparece dentro de la tabla | La vista no distingue la petición HTMX | `get_template_names` y la cabecera `HX-Request` |
| El aviso "al menos 3 caracteres" no desaparece | Falta el `<div id="aviso" hx-swap-oob="true">` en `_resultados.html` | Paso 6 |
| La búsqueda "losartan" no encuentra "Losartán" | La expresión del ORM no es `f_unaccent(lower(...))` o no se normalizó `q` | Paso 2: `_sin_acentos` y `normalizar` |
| `TemplateSyntaxError: Invalid block tag 'querystring'` | Django menor a 5.1 | El proyecto usa Django 5.2 LTS |
| `SynchronousOnlyOperation` en los tests de Playwright | Falta `DJANGO_ALLOW_ASYNC_UNSAFE=true` | Comando 2 de la sección 5 |
| El login de Playwright falla con el usuario demo | `PASSWORD_HASHERS` de los tests no incluye PBKDF2 | Las contraseñas del mock son PBKDF2 (sección 3.4): mantén `PBKDF2PasswordHasher` en la lista |
