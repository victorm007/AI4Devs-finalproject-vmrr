# HB-09 · Guía paso a paso: catálogo y residentes en el panel `/admin/`

> **Ticket:** [readme, sección 6, HB-09](../../readme.md#tickets-de-habilitación-hb-01-a-hb-09) · **Tipo:** panel de administración · **Estimación:** 2 puntos · **Rama:** `feature/HB-09-admin-catalogo-residentes`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket y en la sección 5 del readme ("Habilitadores en el panel `/admin/` de Django"). Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.

**Resultado al terminar:** desde <https://localhost/admin/>, un usuario de **Lectura y escritura** da de alta y edita medicamentos (con sus principios activos en la misma pantalla), principios activos, presentaciones y residentes. Uno de **Solo lectura** los consulta sin poder cambiarlos. Nadie borra: la baja es lógica (`activo` o `estado`). La búsqueda del panel ignora mayúsculas y acentos ("losartan" encuentra "Losartán"), y las reglas de la base aparecen como mensajes junto al campo, nunca como un error `500`.

---

## 0. Antes de empezar

### 0.1 Lee primero (20 min)

| Qué | Dónde | Para qué |
|---|---|---|
| Habilitadores y "Controles" | readme, sección 5 | Qué se hace en el panel, quién, y las 5 reglas que debe respetar |
| D2 y D3 | readme, sección 3.2 | Campos y reglas de medicamentos y residentes |
| Servicio de alta de residentes | guía de HB-06, paso 5 | `registrar_residente()` |
| `ModelAdmin` | <https://docs.djangoproject.com/en/5.2/ref/contrib/admin/> | `inlines`, `autocomplete_fields`, `get_search_results` |

### 0.2 Requisitos previos

- HB-08 integrado en `main`: existen los 2 grupos con sus permisos y el login.

### 0.3 Crea la rama

```bash
git switch main && git pull
git switch -c feature/HB-09-admin-catalogo-residentes
```

---

## 1. Archivos que vas a crear o modificar

```
app/
├── config/urls.py                         # MODIFICAR: títulos del panel
└── apps/
    ├── panel.py                           # NUEVO: reglas comunes del panel (sin borrado, búsqueda sin acentos)
    ├── catalogo/
    │   ├── admin.py                       # NUEVO
    │   └── tests/test_admin.py            # NUEVO
    └── entidades/
        ├── admin.py                       # NUEVO
        └── tests/test_admin.py            # NUEVO
```

---

## 2. Tareas paso a paso

El orden sigue TDD (`CLAUDE.md`): primero los tests en rojo, después la implementación.

### Paso 1. Tests en rojo (≈ 1 h)

Escribe los tests de la sección 3 y ejecútalos **antes** de implementar:

```bash
dtest apps/catalogo/tests/test_admin.py apps/entidades/tests/test_admin.py -q
```

Solo debe pasar `test_el_hogar_no_se_edita_en_el_panel`, porque `Entidad` nunca se registra en el panel: es un test de regresión.

Así avanza el rojo con cada paso:

| Al terminar | Comando | Resultado esperado |
|---|---|---|
| Paso 3 (catálogo) | `dtest apps/catalogo/tests/test_admin.py -q` | Todos pasan |
| Paso 4 (residentes) | `dtest apps/entidades/tests/test_admin.py -q` | Todos pasan |

### Paso 2. Reglas comunes del panel (≈ 30 min)

`app/apps/panel.py`:

```python
"""Reglas comunes del panel /admin/ (readme, sección 5, "Controles")."""

from django.db.models import Q, Value

from apps.expresiones import sin_acentos


class SinBorrarMixin:
    """Sin la acción "Eliminar": la baja es lógica (activo o estado)."""

    def has_delete_permission(self, request, obj=None):
        return False


class BusquedaSinAcentosMixin:
    """La búsqueda ignora mayúsculas y acentos: "losartan" encuentra "Losartán".

    Compara f_unaccent(lower(campo)) contra f_unaccent(lower(término)), la misma expresión
    de los índices trigram (sección 3.3). La subclase define campos_sin_acentos.
    """

    campos_sin_acentos: tuple[str, ...] = ()

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return queryset, False
        termino = sin_acentos(Value(search_term))
        condicion = Q()
        for posicion, campo in enumerate(self.campos_sin_acentos):
            alias = f"_busqueda_{posicion}"
            queryset = queryset.annotate(**{alias: sin_acentos(campo)})
            condicion |= Q(**{f"{alias}__contains": termino})
        # distinct(): buscar por principio activo une con la tabla puente
        return queryset.filter(condicion).distinct(), True
```

### Paso 3. Catálogo en el panel (≈ 45 min)

`app/apps/catalogo/admin.py`:

```python
"""Catálogo de medicamentos en /admin/ (readme, sección 5, "Habilitadores")."""

from django.contrib import admin

from apps.catalogo.models import (
    Medicamento,
    MedicamentoPrincipioActivo,
    Presentacion,
    PrincipioActivo,
)
from apps.panel import BusquedaSinAcentosMixin, SinBorrarMixin


@admin.register(Presentacion)
class PresentacionAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)  # muestra el buscador; la búsqueda real es sin acentos
    campos_sin_acentos = ("nombre",)
    ordering = ("nombre",)


@admin.register(PrincipioActivo)
class PrincipioActivoAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin):
    list_display = ("nombre", "creado_en")
    search_fields = ("nombre",)
    campos_sin_acentos = ("nombre",)
    ordering = ("nombre",)


class PrincipioActivoEnLinea(admin.TabularInline):
    """Principios activos en la misma pantalla del medicamento (al menos uno).

    La regla la aplica PrincipiosActivosFormSet (apps/catalogo/forms.py) en el alta y en el
    cambio; min_num y extra solo muestran un renglón vacío para capturar.
    """

    model = MedicamentoPrincipioActivo
    formset = PrincipiosActivosFormSet  # from apps.catalogo.forms import PrincipiosActivosFormSet
    extra = 0
    min_num = 1
    can_delete = False  # un renglón equivocado se corrige cambiando el principio activo
    autocomplete_fields = ["principio_activo"]
    verbose_name = "principio activo"
    verbose_name_plural = "principios activos"


@admin.register(Medicamento)
class MedicamentoAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin):
    list_display = ("nombre_comercial", "concentracion", "presentacion", "tipo", "activo")
    list_filter = ("activo", "tipo", "presentacion")
    list_select_related = ("presentacion",)  # sin N+1 en la lista
    search_fields = ("nombre_comercial",)
    campos_sin_acentos = ("nombre_comercial", "principios_activos__nombre")
    fields = ("nombre_comercial", "tipo", "presentacion", "concentracion", "activo")
    inlines = [PrincipioActivoEnLinea]
    ordering = ("nombre_comercial",)
```

> **Al menos un principio activo** (ajuste 2 de la revisión): la regla vive en `apps/catalogo/validadores.py` (`exigir_principio_activo()` y el mensaje "Un medicamento debe tener al menos un principio activo."), y `apps/catalogo/forms.py` la aplica a los renglones con `PrincipiosActivosFormSet.clean()`. No se valida en la base, para mantener la flexibilidad. En la V2, `POST` y `PATCH /medicamentos` llaman a la misma función (readme, sección 4; `openapi.yaml`, `principios_activos_ids`). No uses `validate_min`: el panel no lo pasa al formulario, y su aviso genérico se sumaría al de la regla.

> **Pendiente para TK-01:** desmarcar `activo` en un medicamento con existencias debe dar un mensaje ("No se puede dar de baja: hay existencias de este medicamento"). Esa validación necesita la tabla `existencia`, así que la agrega TK-01 junto con el *trigger* `tg_medicamento_baja`.

### Paso 4. Residentes en el panel (≈ 30 min)

`app/apps/entidades/admin.py`:

```python
"""Residentes en /admin/ (readme, sección 5, "Habilitadores").

El Hogar es fijo (lo crea la migración): Entidad no se registra en el panel.
"""

from django.contrib import admin

from apps.entidades.models import Residente
from apps.entidades.services import registrar_residente
from apps.panel import BusquedaSinAcentosMixin, SinBorrarMixin

CAMPOS_ALTA = (
    "primer_nombre", "segundo_nombre", "primer_apellido", "segundo_apellido",
    "fecha_nacimiento", "fecha_ingreso",
)


@admin.register(Residente)
class ResidenteAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin):
    list_display = ("nombre_completo", "estado", "fecha_ingreso", "fecha_baja")
    list_filter = ("estado",)
    search_fields = ("primer_apellido",)
    campos_sin_acentos = ("primer_nombre", "segundo_nombre", "primer_apellido", "segundo_apellido")
    ordering = ("primer_apellido", "primer_nombre")

    def get_fields(self, request, obj=None):
        # En el alta no se elige el estado: todo residente nuevo empieza ACTIVO
        return CAMPOS_ALTA if obj is None else (*CAMPOS_ALTA, "estado", "fecha_baja")

    def save_model(self, request, obj, form, change):
        if change:
            obj.save()  # cambio de datos, egreso o defunción (lo validan las restricciones)
        else:
            registrar_residente(obj)  # crea la entidad y el residente juntos

    @admin.display(description="Nombre", ordering="primer_apellido")
    def nombre_completo(self, residente):
        return residente.nombre_completo
```

### Paso 5. Títulos del panel (≈ 5 min)

En `app/config/urls.py`, después de los imports:

```python
admin.site.site_header = "Medicamentos del Hogar · Administración"
admin.site.site_title = "Medicamentos del Hogar"
admin.site.index_title = "Catálogo, residentes y usuarios"
```

### Paso 6. Prueba manual (≈ 20 min)

```bash
docker compose up -d && dj collectstatic --noinput
```

En <https://localhost/admin/>, como un usuario de **Lectura y escritura** creado en HB-08:
1. Da de alta "Losartán 50 mg tableta" con el principio activo "Losartán" (créalo con el botón **+** del campo).
2. Intenta dar de alta "LOSARTAN 50 MG tableta": aparece el mensaje de duplicado.
3. Busca "losartan" en la lista de medicamentos: aparece.
4. Da de alta un residente, ábrelo y cámbialo a "Egresado" sin fecha de baja: aparece el mensaje de la fecha.
5. Verifica que en ninguna lista aparece la acción "Eliminar".

### Paso 7. Tests en verde, verificación y *pull request* (≈ 30 min)

Comprueba que los tests de la sección 3 pasan, ejecuta la sección 5 y abre el PR.

---

## 3. Tests requeridos

### 3.1 `apps/catalogo/tests/test_admin.py`

```python
"""Catálogo en /admin/: permisos por grupo, principio activo en línea, sin borrado y búsqueda."""

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.catalogo.models import Medicamento, Presentacion, PrincipioActivo
from apps.entidades.models import Entidad

pytestmark = [pytest.mark.django_db, pytest.mark.http]
URL = "/admin/catalogo/medicamento/"
EN_LINEA = "medicamentoprincipioactivo_set"


@pytest.fixture
def entrar_como(client):
    def entrar(grupo):
        nombre = "prueba." + grupo.split()[0].lower()  # prueba.solo o prueba.lectura
        usuario = get_user_model().objects.create_user(nombre, is_staff=True)
        usuario.groups.add(Group.objects.get(name=grupo))
        client.force_login(usuario)
        return client
    return entrar


@pytest.fixture
def losartan():
    return PrincipioActivo.objects.create(nombre="Losartán")


def formulario(principio_activo, filas=1, **cambios):
    datos = {
        "nombre_comercial": "Losartán", "tipo": "GENERICO", "concentracion": "50 mg",
        "presentacion": Presentacion.objects.get(nombre="tableta").pk, "activo": "on",
        f"{EN_LINEA}-TOTAL_FORMS": str(filas), f"{EN_LINEA}-INITIAL_FORMS": "0",
        f"{EN_LINEA}-MIN_NUM_FORMS": "1", f"{EN_LINEA}-MAX_NUM_FORMS": "1000",
        f"{EN_LINEA}-0-principio_activo": principio_activo.pk,
    }
    return datos | cambios


def test_solo_lectura_consulta_pero_no_cambia(entrar_como):
    cliente = entrar_como("Solo lectura")
    assert cliente.get(URL).status_code == 200
    assert cliente.get(f"{URL}add/").status_code == 403


def test_lectura_y_escritura_da_de_alta_con_su_principio_activo(entrar_como, losartan):
    respuesta = entrar_como("Lectura y escritura").post(f"{URL}add/", formulario(losartan))
    assert respuesta.status_code == 302
    medicamento = Medicamento.objects.get(nombre_comercial="Losartán")
    assert list(medicamento.principios_activos.all()) == [losartan]


def test_sin_principio_activo_el_formulario_avisa(entrar_como, losartan):
    respuesta = entrar_como("Lectura y escritura").post(f"{URL}add/", formulario(losartan, filas=0))
    assert respuesta.status_code == 200
    assert SIN_PRINCIPIO_ACTIVO in respuesta.content.decode()  # from apps.catalogo.validadores
    assert not Medicamento.objects.exists()
    # El cambio sin principio activo también avisa: test_el_cambio_sin_principio_activo_avisa
    # (apps/catalogo/tests/test_admin.py), y la regla sin HTTP, en test_formularios.py


def test_el_duplicado_sin_acentos_da_un_mensaje_y_no_un_500(entrar_como, losartan):
    cliente = entrar_como("Lectura y escritura")
    cliente.post(f"{URL}add/", formulario(losartan))
    respuesta = cliente.post(
        f"{URL}add/", formulario(losartan, nombre_comercial="LOSARTAN", concentracion="50 MG")
    )
    assert respuesta.status_code == 200
    assert "Ya existe un medicamento" in respuesta.content.decode()


def test_la_baja_es_logica(entrar_como, losartan):
    cliente = entrar_como("Lectura y escritura")
    cliente.post(f"{URL}add/", formulario(losartan))
    medicamento = Medicamento.objects.get()
    datos = formulario(losartan) | {
        f"{EN_LINEA}-INITIAL_FORMS": "1",
        f"{EN_LINEA}-0-id": medicamento.medicamentoprincipioactivo_set.get().pk,
        f"{EN_LINEA}-0-medicamento": medicamento.pk,
    }
    del datos["activo"]  # casilla desmarcada
    assert cliente.post(f"{URL}{medicamento.pk}/change/", datos).status_code == 302
    medicamento.refresh_from_db()
    assert medicamento.activo is False


def test_nadie_borra_del_catalogo(entrar_como, admin_client, losartan):
    medicamento = Medicamento.objects.create(
        nombre_comercial="Prueba", tipo="GENERICO", concentracion="1 mg",
        presentacion=Presentacion.objects.get(nombre="tableta"),
    )
    assert admin_client.get(f"{URL}{medicamento.pk}/delete/").status_code == 403
    assert entrar_como("Lectura y escritura").get(f"{URL}{medicamento.pk}/delete/").status_code == 403


def test_la_busqueda_ignora_mayusculas_y_acentos(entrar_como, losartan):
    cliente = entrar_como("Lectura y escritura")
    cliente.post(f"{URL}add/", formulario(losartan, nombre_comercial="Cozaar"))
    assert "Cozaar" in cliente.get(URL, {"q": "COZAAR"}).content.decode()
    assert "Cozaar" in cliente.get(URL, {"q": "losartan"}).content.decode()  # por principio activo


def test_el_hogar_no_se_edita_en_el_panel():
    assert Entidad not in admin.site._registry
```

### 3.2 `apps/entidades/tests/test_admin.py`

```python
"""Residentes en /admin/: alta con el servicio, egreso validado y búsqueda sin acentos."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.entidades.models import Entidad, Residente

pytestmark = [pytest.mark.django_db, pytest.mark.http]
URL = "/admin/entidades/residente/"
ALTA = {
    "primer_nombre": "María", "segundo_nombre": "Guadalupe", "primer_apellido": "Hernández",
    "segundo_apellido": "López", "fecha_nacimiento": "1938-04-12", "fecha_ingreso": "2023-02-01",
}


@pytest.fixture
def operador(client):
    usuario = get_user_model().objects.create_user("prueba.operador", is_staff=True)
    usuario.groups.add(Group.objects.get(name="Lectura y escritura"))
    client.force_login(usuario)
    return client


@pytest.fixture
def maria(operador):
    operador.post(f"{URL}add/", ALTA)
    return Residente.objects.get(primer_apellido="Hernández")


def test_el_alta_crea_la_entidad_y_el_residente_activo(maria):
    assert maria.entidad.tipo == Entidad.Tipo.RESIDENTE
    assert maria.estado == Residente.Estado.ACTIVO


def test_el_alta_no_pide_el_estado(operador):
    respuesta = operador.get(f"{URL}add/")
    assert respuesta.status_code == 200  # sin esto, un 404 también pasaría el test
    html = respuesta.content.decode()
    assert 'name="estado"' not in html and 'name="fecha_baja"' not in html


def test_egresar_sin_fecha_de_baja_da_un_mensaje(operador, maria):
    respuesta = operador.post(f"{URL}{maria.pk}/change/", ALTA | {"estado": "EGRESADO"})
    assert respuesta.status_code == 200
    assert "La fecha de baja es obligatoria" in respuesta.content.decode()


def test_egresar_con_fecha_de_baja(operador, maria):
    datos = ALTA | {"estado": "EGRESADO", "fecha_baja": "2026-02-01"}
    assert operador.post(f"{URL}{maria.pk}/change/", datos).status_code == 302
    assert Entidad.objects.get(pk=maria.pk).activa is False


def test_la_busqueda_ignora_acentos(operador, maria):
    assert "Hernández" in operador.get(URL, {"q": "hernandez"}).content.decode()


def test_nadie_borra_residentes(operador, maria):
    assert operador.get(f"{URL}{maria.pk}/delete/").status_code == 403
```

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| Las 5 reglas de "Controles" (sección 5) se cumplen | Tests y prueba manual (paso 6) |
| Las reglas de la base aparecen como mensaje, nunca como `500` | `test_el_duplicado...` y `test_egresar_sin_fecha...` |
| La lista de medicamentos no hace consultas N+1 | `list_select_related = ("presentacion",)`; revisión del PR |
| Sin lógica de negocio en el panel: el alta pasa por `services.py` | Revisión del PR |
| Sin errores de CSP en el panel (*autocomplete* incluido) | Consola del navegador |
| Textos visibles en español | Revisión del PR |

---

## 5. Verificación: comandos y resultado esperado

```bash
# 1. Calidad del código
docker compose exec web ruff check . && docker compose exec web ruff format --check .
dj check && dj makemigrations --check --dry-run      # No changes detected: el panel no crea migraciones

# 2. Tests (toda la suite de habilitación)
dtest apps/catalogo apps/entidades -q
dtest -q --cov=apps --cov-fail-under=80

# 3. Prueba completa con el mock de usuarios (desarrollo)
#    El mock completo se carga después de TK-01; aquí basta crear un usuario de cada grupo
#    desde el panel como Administrador y repetir el paso 6 con cada uno.
```

> **Diferencias con lo que trae esta guía** (cambio de OpenSpec `hb-09-admin-catalogo-residentes`):
>
> - **`validate_min = True` no basta en el panel:** en Django 5.2 `InlineModelAdmin.get_formset()` no pasa `validate_min` a `inlineformset_factory`. Con el código del paso 3, un medicamento sin principio activo se guardaba. `PrincipioActivoEnLinea.get_formset()` lo pasaba con `kwargs.setdefault("validate_min", self.validate_min)`. En el segundo ajuste lo sustituye `PrincipiosActivosFormSet` (ver el paso 3).
> - **Sin `annotate()`** en `BusquedaSinAcentosMixin`: la expresión va solo al `WHERE`, así `distinct()` quita los repetidos de un medicamento con 2 principios activos (lo usa el *autocomplete*). Primero fue `alias()`; tras la revisión, un `filter()` por palabra (tabla de ajustes, abajo).
> - **Búsqueda del panel sin mínimo de 3 caracteres ni `UNION`:** quedó como precisión en ADR-0017. Esas 2 reglas son de la búsqueda de existencias; el panel conserva `f_unaccent(lower(campo))`.
> - **Orden de residentes sin acentos:** `ordering` y la columna "Nombre" usan `sin_acentos("primer_apellido")` y `sin_acentos("primer_nombre")`, la expresión de `ix_residente_nombre`.
> - **Tests añadidos:**
>   - *Solo lectura* en los 4 modelos (lista `200`, alta `403`) y el `403` al cambiar un medicamento o un residente;
>   - *Lectura y escritura* abre el alta de los 3 modelos del catálogo;
>   - el *autocomplete* de principios activos sin acentos y el principio activo duplicado;
>   - el borrado con `403` para el Administrador y *Lectura y escritura* en los 4 modelos, y la lista sin la acción "Eliminar";
>   - la búsqueda por nombre comercial y los controles negativos;
>   - sin N+1 en la lista de medicamentos (`django_assert_num_queries`);
>   - el alta del medicamento sin código en línea (CSP);
>   - la fecha de baja anterior al ingreso y la defunción.
> - **`test_el_hogar_no_se_edita_en_el_panel`** está en `apps/entidades/tests/test_admin.py`, con controles de `Residente`, así que nace en rojo.
> - **Revisión en el navegador:** se hizo con Chrome *headless* por CDP, detrás de nginx, como un usuario de *Lectura y escritura*: alta con el botón **+** y el *autocomplete*, duplicado, búsqueda, alta y egreso de un residente. No hay violaciones de CSP; el único mensaje de la consola es el 404 de `/favicon.ico`. Capturas en `docs/capturas/HB-09/`.
> - **Etiquetas sin acento, aceptadas:** el panel muestra "Presentacion", "Concentracion", "Fecha ingreso" o "Fecha baja" porque los modelos de HB-05 y HB-06 no tienen `verbose_name`. Corregirlo generaría migraciones, y el panel es provisional hasta las pantallas propias de la V2 (ADR-0020).
> - **Rama:** `feature/entrega-2-vmrr`, por la regla de ramas de `CLAUDE.md`.
>
> **Ajustes de la revisión adversarial** (cambio de OpenSpec `hb-09-ajustes-revision`):
>
> | Hallazgo | Cambio |
> |---|---|
> | 1. La búsqueda no separaba palabras ni recortaba espacios | `palabras_de_busqueda()` divide el término con `smart_split`; un `filter()` por palabra (`OR` entre campos, `AND` entre palabras), así "losartan hidroclorotiazida" encuentra Hyzaar |
> | 2. Presentaciones duplicadas sin acentos | `uq_presentacion_nombre` sobre `f_unaccent(lower(nombre))` en lugar del `UNIQUE` literal (migración `catalogo/0004_presentacion_unica`), con el mensaje "Ya existe esa presentación…" |
> | 3. El alta ofrecía presentaciones dadas de baja | `MedicamentoAdmin.get_form()` ofrece las activas y, al cambiar, la del medicamento |
> | 6. Ningún test del panel corría como `app_user` | Altas de un medicamento y de un residente con `SET LOCAL ROLE app_user`, comprobando el rol y el `LogEntry` |
> | 7. El test de CSP no detectaba `<style>` ni `on*=` | Patrón ampliado, en el alta, la lista y el cambio de medicamentos y residentes |
> | 8. *Solo lectura* en presentaciones y principios activos | `403` al cambiar y búsqueda en sus listas |
> | 9. El *mixin* sin campos devolvía todas las filas | `check()` da el error `panel.E001` |
>
> **Hallazgo 4, atendido en un segundo ajuste** (cambio `hb-09-ajustes-revision-2`): la regla "al menos un principio activo" se conserva y se valida en el formulario, no en la base, para mantener la flexibilidad. Se valida en el alta y en el cambio, con el mensaje "Un medicamento debe tener al menos un principio activo.", desde `apps/catalogo/validadores.py`, que la V2 reutilizará en `POST` y `PATCH /medicamentos`. Sustituye a `validate_min` y al `get_formset()` del primer ajuste. Al editar un medicamento sin principios activos, por ejemplo para darlo de baja, hay que elegir uno: es lo deseado.
>
> **Pendientes, sin cambio** (hallazgos que no se atendieron):
> - **5.** No hay reglas de transición de estado del residente (de `FALLECIDO` a `ACTIVO`, `fecha_baja` futura) ni protección contra residentes duplicados. El ticket no lo exige.
> - **10.** Los títulos del panel no tienen test, `accounts` no usa `SinBorrarMixin`, y `CLAUDE.md` conserva la frase "Todavía no hay funcionalidad de la aplicación".

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] Capturas: alta de un medicamento con su principio activo, mensaje de duplicado y lista de residentes filtrada por "Activo".

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `admin.E039: An admin for model "PrincipioActivo" has to be registered to be referenced by ...autocomplete_fields` | `PrincipioActivoAdmin` no está registrado o no tiene `search_fields` | Paso 3 |
| `ManagementForm data is missing or has been tampered with` en un test | Faltan los campos `TOTAL_FORMS`/`INITIAL_FORMS` del *inline* | Usa `formulario()` de la sección 3.1 |
| Un usuario de grupo no ve "Medicamentos" | Le falta `is_staff` o el grupo | HB-08 |
| `IntegrityError` (`500`) al egresar un residente | La restricción no tiene `violation_error_message` o el formulario no la valida | Revisa `ck_residente_baja` en HB-06 |
| La búsqueda no encuentra "Losartán" con "losartan" | El *mixin* no está antes de `admin.ModelAdmin` en la herencia | `class XAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin)` |
