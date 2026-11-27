# HB-09 · Guía paso a paso: catálogo y residentes en el panel `/admin/`

> **Ticket:** [readme, sección 6, HB-09](../../readme.md#tickets-de-habilitación-hb-01-a-hb-10) · **Tipo:** panel de administración · **Estimación:** 2 puntos · **Rama:** `feature/HB-09-admin-catalogo-residentes`
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
    │   ├── forms.py                       # NUEVO: renglones de principios activos (al menos uno)
    │   ├── validadores.py                 # NUEVO: regla "al menos un principio activo" (su mensaje lo comparte la V2)
    │   ├── models.py                      # MODIFICAR: uq_presentacion_nombre (paso 3b)
    │   ├── migrations/0004_presentacion_unica.py   # NUEVO (paso 3b)
    │   └── tests/
    │       ├── test_admin.py              # NUEVO
    │       ├── test_formularios.py        # NUEVO
    │       └── test_modelos.py            # MODIFICAR: uq_presentacion_nombre
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
dtest apps/catalogo/tests/test_admin.py apps/entidades/tests/test_admin.py apps/catalogo/tests/test_modelos.py -q
```

Solo deben pasar `test_el_hogar_no_se_edita_en_el_panel` (en `apps/entidades/tests/test_admin.py`), porque `Entidad` nunca se registra en el panel, y los tests de HB-05 que ya estaban en `test_modelos.py`: son de regresión. Los 2 de la sección 3.3 fallan hasta el paso 3b.

`test_formularios.py` (sección 3.4) se ejecuta aparte, porque importa `validadores.py` y `forms.py` al inicio y falla en la recolección hasta el paso 3. En el mismo comando, ese error interrumpiría a los demás archivos:

```bash
dtest apps/catalogo/tests/test_formularios.py -q
```

Resultado esperado: `1 error` en la recolección, con `ModuleNotFoundError: No module named 'apps.catalogo.forms'`.

Así avanza el rojo con cada paso:

| Al terminar | Comando | Resultado esperado |
|---|---|---|
| Paso 3 (catálogo) | `dtest apps/catalogo/tests/test_admin.py apps/catalogo/tests/test_formularios.py -q` | Todos pasan |
| Paso 3b (presentaciones) | `dtest apps/catalogo/tests/test_modelos.py -q` | Todos pasan |
| Paso 4 (residentes) | `dtest apps/entidades/tests/test_admin.py -q` | Todos pasan |

### Paso 2. Reglas comunes del panel (≈ 30 min)

`app/apps/panel.py`:

```python
"""Reglas comunes del panel /admin/ (readme, sección 5, "Controles"; HB-09).

Los mixins van antes de admin.ModelAdmin en la herencia, para que sus métodos reemplacen
a los del panel:

    class MedicamentoAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin): ...
"""

from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q, Value
from django.db.models.lookups import Contains
from django.utils.text import smart_split, unescape_string_literal

from apps.expresiones import sin_acentos


class SinBorrarMixin:
    """Sin la acción "Eliminar": la baja es lógica (activo o estado).

    El panel quita la acción de la lista y el botón de la página, y responde 403 en
    .../delete/, también al Administrador (superusuario).
    """

    def has_delete_permission(self, request, obj=None):
        return False


# Cada palabra agrega un filter() con su propia unión a la tabla puente (principios activos):
# el tope evita una consulta enorme con cientos de palabras, y 8 sobran para nombre,
# concentración y principios activos
MAXIMO_PALABRAS = 8


def palabras_de_busqueda(search_term: str) -> list[str]:
    """Divide el término en palabras, como el panel de Django: "cozaar losartan" da 2.

    Una frase entre comillas cuenta como una sola palabra, sin las comillas. Los espacios
    sobrantes no cuentan: " losartan " da ["losartan"] y " " no da ninguna. Devuelve como
    mucho las primeras MAXIMO_PALABRAS palabras, en su orden; las demás se ignoran sin avisar.
    """
    palabras = []
    for bit in smart_split(search_term):
        if len(palabras) == MAXIMO_PALABRAS:
            break
        if len(bit) > 1 and bit[0] in "\"'" and bit[0] == bit[-1]:
            bit = unescape_string_literal(bit)
        if bit.strip():
            palabras.append(bit.strip())
    return palabras


class BusquedaSinAcentosMixin:
    """La búsqueda ignora mayúsculas y acentos: "losartan" encuentra "Losartán".

    Compara f_unaccent(lower(campo)) contra f_unaccent(lower(palabra)), la misma expresión
    de los índices trigram (sección 3.3, ADR-0017). Cada palabra debe aparecer en alguno de
    los campos, y todas las palabras deben coincidir. La subclase define campos_sin_acentos
    como tupla (sin ellos, check() da panel.E001; como texto, panel.E003; con un campo que no
    existe, panel.E002); search_fields sigue declarado solo para que
    el panel muestre el buscador y permita el autocomplete. Sin mínimo de caracteres ni
    UNION: eso es de la búsqueda de existencias.
    """

    campos_sin_acentos: tuple[str, ...] = ()

    def check(self, **kwargs):
        errores = super().check(**kwargs)
        campos = getattr(self, "campos_sin_acentos", ())
        if isinstance(campos, str):
            # Un texto se recorrería letra por letra: un solo error, sin revisar los campos
            errores.append(
                checks.Error(
                    f"{self.__class__.__name__}.campos_sin_acentos es un texto ({campos!r}) y "
                    "debe ser una tupla: se recorrería letra por letra.",
                    hint='Declara una tupla, por ejemplo ("nombre",), con la coma final.',
                    obj=self.__class__,
                    id="panel.E003",
                )
            )
            return errores
        if not campos:
            errores.append(
                checks.Error(
                    f"{self.__class__.__name__} usa BusquedaSinAcentosMixin y no declara "
                    "campos_sin_acentos: su búsqueda devolvería todas las filas.",
                    hint="Declara campos_sin_acentos con los campos donde buscar, por "
                    'ejemplo ("nombre",).',
                    obj=self.__class__,
                    id="panel.E001",
                )
            )
        for campo in campos:
            if not self._campo_existe(campo):
                errores.append(
                    checks.Error(
                        f"{self.__class__.__name__}.campos_sin_acentos incluye {campo!r}, que "
                        f"no existe en {self.model.__name__}: la búsqueda fallaría con un 500.",
                        hint="Escribe el campo como en un filter(), por ejemplo "
                        '"nombre" o "principios_activos__nombre".',
                        obj=self.__class__,
                        id="panel.E002",
                    )
                )
        return errores

    def _campo_existe(self, campo: str) -> bool:
        """Recorre los tramos de campo ("a__b__c") desde self.model, como haría filter()."""
        modelo = self.model
        tramos = campo.split("__")
        for posicion, tramo in enumerate(tramos):
            try:
                field = modelo._meta.get_field(tramo)
            except FieldDoesNotExist:
                return False
            if posicion < len(tramos) - 1:
                modelo = field.related_model
                if modelo is None:
                    return False
        return True

    def get_search_results(self, request, queryset, search_term):
        palabras = palabras_de_busqueda(search_term)
        if not palabras:
            return queryset, False
        for palabra in palabras:
            termino = sin_acentos(Value(palabra))
            # Un filter() por palabra, como el panel de Django: en los campos de varios
            # valores (principios_activos__nombre) cada palabra tiene su propia unión con la
            # tabla puente, y "losartan hidroclorotiazida" encuentra Hyzaar. Las expresiones
            # van al WHERE, no al SELECT, y así distinct() quita de verdad los duplicados
            queryset = queryset.filter(
                Q(
                    *(Contains(sin_acentos(campo), termino) for campo in self.campos_sin_acentos),
                    _connector=Q.OR,
                )
            )
        # distinct(): buscar por principio activo une con la tabla puente
        return queryset.distinct(), True
```

### Paso 3. Catálogo en el panel (≈ 45 min)

Primero la regla "al menos un principio activo", que no depende del panel. La V2 de la API comparte su mensaje: allí el esquema rechaza la lista vacía, y la función protege a quien guarde sin pasar por él. `app/apps/catalogo/validadores.py`:

```python
"""Reglas de validación de entrada del catálogo, sin acceso a la base.

"Al menos un principio activo" no se puede expresar con un CHECK, porque los principios
activos viven en la tabla puente medicamento_principio_activo (readme, sección 3.2). Por eso
la regla se valida en la entrada, con un solo texto:

- En el MVP, el alta y el cambio del medicamento en /admin/ (PrincipiosActivosFormSet de
  apps.catalogo.forms).
- En la V2, en POST /medicamentos y PATCH /medicamentos/{id} la lista vacía la rechaza el
  esquema de principios_activos_ids (minItems: 1) con 400 VALIDACION y
  errores[] = {campo: principios_activos_ids, codigo: CAMPO_VACIO, mensaje: SIN_PRINCIPIO_ACTIVO}:
  el mensaje es el de esta regla. La función protege a quien guarde sin pasar por ese esquema.
"""

from django.core.exceptions import ValidationError

SIN_PRINCIPIO_ACTIVO = "Un medicamento debe tener al menos un principio activo."


def exigir_principio_activo(principios_activos) -> None:
    """Lanza ValidationError(code="sin_principio_activo") si la colección está vacía o es None.

    Acepta cualquier colección: los principios activos elegidos en el formulario, una lista de
    ids (principios_activos_ids de la V2) o un QuerySet (se evalúa una sola vez). None es un
    caso defensivo para quien la llame desde dentro: se rechaza como la colección vacía.

    En la V2, el esquema de principios_activos_ids (array, minItems: 1) responde antes: la lista
    vacía con CAMPO_VACIO y el mensaje SIN_PRINCIPIO_ACTIVO, y un valor que no es array
    (incluido null) con TIPO_INVALIDO. Esta función no la necesita la API para esos casos: es
    la misma regla para el panel y para cualquier código que guarde sin pasar por el esquema.

    Un texto o una secuencia de bytes (str, bytes, bytearray o memoryview) lanza TypeError: es
    un error de programación, porque list("abc") daría 3 elementos y la regla pasaría por error.
    """
    if isinstance(principios_activos, (str, bytes, bytearray, memoryview)):
        raise TypeError(
            "exigir_principio_activo: se esperaba una colección de principios activos, no un "
            f"texto ni bytes ({type(principios_activos).__name__})."
        )
    if principios_activos is None or not list(principios_activos):
        raise ValidationError(SIN_PRINCIPIO_ACTIVO, code="sin_principio_activo")
```

`app/apps/catalogo/forms.py`, el conjunto de renglones que la aplica en el alta y en el cambio:

```python
"""Formularios del catálogo para /admin/ (HB-09)."""

from django.forms.models import BaseInlineFormSet

from apps.catalogo.validadores import exigir_principio_activo


class PrincipiosActivosFormSet(BaseInlineFormSet):
    """Renglones de principios activos de un medicamento: exige al menos uno.

    El aviso es el de apps.catalogo.validadores y aparece como error del conjunto
    (non_form_errors), arriba de los renglones. Sustituye a validate_min, cuyo aviso es el
    genérico de Django.
    """

    def clean(self):
        super().clean()
        # Aunque algún renglón tenga errores, la regla se revisa igual: así el aviso aparece
        # también cuando el único renglón está vacío. Un renglón que no validó puede no tener
        # cleaned_data, o no tener la clave principio_activo
        principios_activos = []
        for form in self.forms:
            datos = getattr(form, "cleaned_data", None) or {}
            principio_activo = datos.get("principio_activo")
            if principio_activo and not datos.get("DELETE"):
                principios_activos.append(principio_activo)
        exigir_principio_activo(principios_activos)
```

`app/apps/catalogo/admin.py`:

```python
"""Catálogo de medicamentos en /admin/ (readme, sección 5, "Habilitadores"; HB-09).

Nadie borra: la baja de un medicamento o de una presentación es activo = False. Los
mensajes de duplicado salen del violation_error_message de las restricciones de HB-05, que
el formulario valida antes de guardar.
"""

from django.contrib import admin
from django.db.models import Q

from apps.catalogo.forms import PrincipiosActivosFormSet
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
    search_fields = ("nombre",)  # también habilita el autocomplete del medicamento
    campos_sin_acentos = ("nombre",)
    ordering = ("nombre",)


class PrincipioActivoEnLinea(admin.TabularInline):
    """Principios activos en la misma pantalla del medicamento (al menos uno).

    La regla "al menos uno" la aplica PrincipiosActivosFormSet, con el mensaje de
    apps.catalogo.validadores, en el alta y en el cambio. min_num y extra solo deciden que se
    muestre un renglón vacío: sin validate_min, para que el aviso genérico de Django no se
    sume al de la regla.
    """

    model = MedicamentoPrincipioActivo
    formset = PrincipiosActivosFormSet
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

    def get_form(self, request, obj=None, change=False, **kwargs):
        # Sin presentaciones dadas de baja en el alta (ADR-0009). Al cambiar un medicamento
        # se conserva la suya aunque esté inactiva, para poder guardarlo. get_form() arma una
        # clase nueva en cada petición: limitar base_fields no afecta a las demás
        form = super().get_form(request, obj, change=change, **kwargs)
        if "presentacion" in form.base_fields:  # Solo lectura no tiene el campo editable
            vigentes = Q(activo=True)
            if obj is not None:
                vigentes |= Q(pk=obj.presentacion_id)
            campo = form.base_fields["presentacion"]
            campo.queryset = Presentacion.objects.filter(vigentes).order_by("nombre")
        return form
```

> **Al menos un principio activo** (ajuste 2 de la revisión): la regla vive en `apps/catalogo/validadores.py` (`exigir_principio_activo()` y el mensaje "Un medicamento debe tener al menos un principio activo."), y `apps/catalogo/forms.py` la aplica a los renglones con `PrincipiosActivosFormSet.clean()`. No se valida en la base, para mantener la flexibilidad. En la V2, el esquema de `POST` y `PATCH /medicamentos` rechaza la lista vacía con el mismo mensaje (readme, sección 4; `openapi.yaml`, `principios_activos_ids`), y la función protege a quien guarde sin pasar por el esquema. No uses `validate_min`: el panel no lo pasa al formulario, y su aviso genérico se sumaría al de la regla.

> **Pendiente para TK-01:** desmarcar `activo` en un medicamento con existencias debe dar un mensaje ("No se puede dar de baja: hay existencias de este medicamento"). Esa validación necesita la tabla `existencia`, así que la agrega TK-01 junto con el *trigger* `tg_medicamento_baja`.

### Paso 3b. Presentaciones sin duplicados sin acentos (≈ 15 min)

Desde este ticket el panel da de alta presentaciones. Por eso el `UNIQUE` literal de `presentacion.nombre` (HB-05) se reemplaza por un índice único sobre `f_unaccent(lower(nombre))`, como `uq_principio_activo_nombre`. Sin él, "Tableta" junto a "tableta" permitiría registrar 2 veces el mismo medicamento. En `app/apps/catalogo/models.py`, `Presentacion` queda así:

```python
class Presentacion(models.Model):
    """Forma farmacéutica: tableta, cápsula, jarabe..."""

    id = models.SmallAutoField(primary_key=True)
    nombre = models.CharField(max_length=60)
    # default para los formularios y db_default para la base (INSERT directo, mock)
    activo = models.BooleanField(default=True, db_default=True)

    class Meta:
        db_table = "presentacion"
        verbose_name = "presentación"
        verbose_name_plural = "presentaciones"
        constraints = [
            # Índice único por expresión, en lugar del UNIQUE literal de HB-05: "Tableta" =
            # "tableta" = "TABLETA"; sin él, se podría duplicar también el medicamento
            models.UniqueConstraint(
                sin_acentos("nombre"),
                name="uq_presentacion_nombre",
                violation_error_message="Ya existe esa presentación "
                "(sin distinguir mayúsculas ni acentos).",
            ),
            models.CheckConstraint(condition=no_vacio("nombre"), name="ck_presentacion_nombre"),
        ]

    def __str__(self) -> str:
        return self.nombre
```

Genera la migración y aplícala como `app_owner`:

```bash
dj makemigrations catalogo --name presentacion_unica   # AlterField (sin unique) y AddConstraint
./scripts/migrate.sh
dpsql -c '\d presentacion'   # "uq_presentacion_nombre" UNIQUE, btree (f_unaccent(lower(nombre::text))), sin UNIQUE literal ni índice _like
```

Verifica con `dtest apps/catalogo/tests/test_modelos.py -q`: los 2 tests de la sección 3.3 pasan. Reversión: `./scripts/migrate.sh catalogo 0003`, que devuelve el `UNIQUE` literal, y otra vez `./scripts/migrate.sh`.

### Paso 4. Residentes en el panel (≈ 30 min)

`app/apps/entidades/admin.py`:

```python
"""Residentes en /admin/ (readme, sección 5, "Habilitadores"; HB-09).

El Hogar es fijo (lo crea la migración): Entidad no se registra en el panel. El alta pasa
por registrar_residente(), que crea la entidad y el residente juntos. Nadie borra: el
egreso o la defunción se registran con el estado y la fecha de baja.
"""

from django.contrib import admin

from apps.entidades.models import Residente
from apps.entidades.services import registrar_residente
from apps.expresiones import sin_acentos
from apps.panel import BusquedaSinAcentosMixin, SinBorrarMixin

CAMPOS_ALTA = (
    "primer_nombre",
    "segundo_nombre",
    "primer_apellido",
    "segundo_apellido",
    "fecha_nacimiento",
    "fecha_ingreso",
)


@admin.register(Residente)
class ResidenteAdmin(SinBorrarMixin, BusquedaSinAcentosMixin, admin.ModelAdmin):
    list_display = ("nombre_completo", "estado", "fecha_ingreso", "fecha_baja")
    list_filter = ("estado",)
    search_fields = ("primer_apellido",)  # muestra el buscador; la búsqueda real es sin acentos
    campos_sin_acentos = (
        "primer_nombre",
        "segundo_nombre",
        "primer_apellido",
        "segundo_apellido",
    )
    # Por apellido y nombre sin acentos: la misma expresión de ix_residente_nombre (consulta 3)
    ordering = (sin_acentos("primer_apellido").asc(), sin_acentos("primer_nombre").asc())

    def get_fields(self, request, obj=None):
        # En el alta no se elige el estado: todo residente nuevo empieza ACTIVO
        return CAMPOS_ALTA if obj is None else (*CAMPOS_ALTA, "estado", "fecha_baja")

    def save_model(self, request, obj, form, change):
        if change:
            obj.save()  # cambio de datos, egreso o defunción (el formulario ya validó las reglas)
        else:
            registrar_residente(obj)  # crea la entidad y el residente juntos

    @admin.display(description="Nombre", ordering=sin_acentos("primer_apellido"))
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

> Los bloques de esta sección son la base del ticket. Los tests completos, con los añadidos de las revisiones adversariales, están en `app/apps/catalogo/tests/` (`test_admin.py`, `test_formularios.py` y `test_modelos.py`) y en `app/apps/entidades/tests/test_admin.py`. Con el código de la sección 2, los 2 conjuntos pasan.

### 3.1 `apps/catalogo/tests/test_admin.py`

```python
"""Catálogo en /admin/: permisos por grupo, principio activo en línea, sin borrado y búsqueda."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.catalogo.models import Medicamento, Presentacion, PrincipioActivo

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
    # Dentro del test: hasta el paso 3 el módulo no existe, y un import al inicio tumbaría
    # todo el archivo en la recolección
    from apps.catalogo.validadores import SIN_PRINCIPIO_ACTIVO

    respuesta = entrar_como("Lectura y escritura").post(f"{URL}add/", formulario(losartan, filas=0))
    assert respuesta.status_code == 200
    assert SIN_PRINCIPIO_ACTIVO in respuesta.content.decode()
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
```

### 3.2 `apps/entidades/tests/test_admin.py`

```python
"""Residentes en /admin/: alta con el servicio, egreso validado y búsqueda sin acentos."""

import pytest
from django.contrib import admin
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


def test_el_hogar_no_se_edita_en_el_panel():
    assert Entidad not in admin.site._registry
```

### 3.3 `apps/catalogo/tests/test_modelos.py` (agregar al archivo de HB-05)

Para el paso 3b: presentaciones sin duplicados sin acentos. Agrega `Presentacion` a los *imports* de `apps.catalogo.models` si no está.

```python
def test_presentacion_duplicada_sin_acentos():
    # La base rechaza "CAPSULA" si existe la semilla "cápsula" (uq_presentacion_nombre)
    with pytest.raises(IntegrityError, match="uq_presentacion_nombre"):
        with transaction.atomic():
            Presentacion.objects.create(nombre="CAPSULA")


def test_el_formulario_avisa_la_presentacion_duplicada():
    # El formulario del panel avisa antes de llegar a la base, con el mensaje de la restricción
    Presentacion(nombre="supositorio").full_clean()  # control: un nombre nuevo sí pasa
    with pytest.raises(ValidationError, match="Ya existe esa presentación"):
        Presentacion(nombre="Tableta").full_clean()
```

### 3.4 `apps/catalogo/tests/test_formularios.py`

Para el paso 3: la regla "al menos un principio activo" y el conjunto de renglones, sin pasar por HTTP. El conjunto se arma como lo hace el *inline* del panel (`min_num=1`, `extra=0`), así que el único aviso es el de la regla.

```python
"""La regla "al menos un principio activo" y el conjunto de renglones del medicamento."""

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
def medicamento():
    return Medicamento.objects.create(
        nombre_comercial="Cozaar",
        tipo="GENERICO",
        concentracion="50 mg",
        presentacion=Presentacion.objects.get(nombre="tableta"),
    )


def renglones(*principios_activos):
    datos = {
        f"{PREFIJO}-TOTAL_FORMS": str(len(principios_activos)),
        f"{PREFIJO}-INITIAL_FORMS": "0",
        f"{PREFIJO}-MIN_NUM_FORMS": "1",
        f"{PREFIJO}-MAX_NUM_FORMS": "1000",
    }
    for i, principio_activo in enumerate(principios_activos):
        datos[f"{PREFIJO}-{i}-principio_activo"] = principio_activo
    return datos


def test_la_regla_rechaza_una_lista_vacia():
    assert SIN_PRINCIPIO_ACTIVO == "Un medicamento debe tener al menos un principio activo."
    with pytest.raises(ValidationError) as error:
        exigir_principio_activo([])
    assert error.value.code == "sin_principio_activo"


def test_la_regla_acepta_un_principio_activo():
    assert exigir_principio_activo([1]) is None


def test_el_conjunto_sin_principio_activo_avisa(medicamento):
    formset = ConjuntoDePrincipios(renglones(), instance=medicamento, prefix=PREFIJO)
    assert not formset.is_valid()
    assert list(formset.non_form_errors()) == [SIN_PRINCIPIO_ACTIVO]


def test_el_conjunto_con_un_principio_activo_es_valido(medicamento):
    losartan = PrincipioActivo.objects.create(nombre="Losartán")
    formset = ConjuntoDePrincipios(renglones(losartan.pk), instance=medicamento, prefix=PREFIJO)
    assert formset.is_valid(), formset.errors
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
dj check && dj makemigrations --check --dry-run      # No changes detected: la única migración del ticket es catalogo/0004_presentacion_unica (ajustes)

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
> - **`test_el_hogar_no_se_edita_en_el_panel`** está en `apps/entidades/tests/test_admin.py`. La versión base de la sección 3.2 es de regresión; la del repositorio lleva además controles de `Residente` y nace en rojo.
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
> **Hallazgo 4, atendido en un segundo ajuste** (cambio `hb-09-ajustes-revision-2`): la regla "al menos un principio activo" se conserva y se valida en el formulario, no en la base, para mantener la flexibilidad. Se valida en el alta y en el cambio, con el mensaje "Un medicamento debe tener al menos un principio activo.", desde `apps/catalogo/validadores.py`, cuyo mensaje comparte el esquema de `POST` y `PATCH /medicamentos` en la V2. Sustituye a `validate_min` y al `get_formset()` del primer ajuste. Al editar un medicamento sin principios activos, por ejemplo para darlo de baja, hay que elegir uno: es lo deseado.
>
> **Pendientes, sin cambio** (hallazgos que no se atendieron):
> - **5.** No hay reglas de transición de estado del residente (de `FALLECIDO` a `ACTIVO`, `fecha_baja` futura) ni protección contra residentes duplicados. El ticket no lo exige.
> - **10.** Los títulos del panel no tienen test, `accounts` no usa `SinBorrarMixin`, y `CLAUDE.md` conserva la frase "Todavía no hay funcionalidad de la aplicación".
>
> **Ajustes de la segunda revisión adversarial** (cambio de OpenSpec `hb-09-ajustes-revision-3`):
>
> | Hallazgo | Cambio |
> |---|---|
> | 1. La búsqueda con varios principios activos no tenía test | Tests: "Hyzaar" (Losartán e Hidroclorotiazida) aparece una vez con "losartan hidroclorotiazida", y `%` y `_` se buscan como texto |
> | 2. El paso 3 de esta guía no se podía seguir | El *import* de `PrincipiosActivosFormSet` y el código de `validadores.py` y `forms.py` en el paso 3; la sección 5 nombra la migración `0004` |
> | 3. ADR-0005 listaba 2 índices únicos por expresión | Lista los 3, con `uq_presentacion_nombre` |
> | 4. `None` y texto en la regla | `None` se rechaza como la lista vacía; un texto lanza `TypeError`; la V2 traduce `sin_principio_activo` a `CAMPO_VACIO` (readme, sección 4, y `openapi.yaml`) |
> | 5. El test de presentaciones inactivas no miraba el HTML | También comprueba el `<option>` del campo |
> | 7. Un campo de búsqueda mal escrito daba un `500` | `check()` da `panel.E002`, que nombra el campo |
> | 9. La búsqueda no tenía tope | Usa como mucho las primeras 8 palabras (`MAXIMO_PALABRAS`); las demás se ignoran |
> | 10. `CLAUDE.md` no mencionaba la regla | Nombra `validadores.py` y `forms.py` |
>
> **Notas, sin cambio de código:**
> - **6. El botón + de presentación.** Desde el alta de un medicamento, el botón **+** del campo presentación abre el alta de una presentación, que incluye la casilla `activo`. Si se desmarca, la presentación nueva no aparece en el campo, porque el alta solo ofrece las activas. Basta con dejarla activa.
> - **8. Antes de aplicar `catalogo/0004` en el servidor del hogar** (HB-10, semana 6): si el panel de `6c345f0` ya se usó ahí, puede haber presentaciones duplicadas sin acentos, y `uq_presentacion_nombre` no se podría crear. Compruébalo antes de migrar; debe devolver 0 filas:
>
>   ```sql
>   SELECT f_unaccent(lower(nombre)) AS nombre, count(*) FROM presentacion GROUP BY 1 HAVING count(*) > 1;
>   ```
>
>   Si devuelve filas, se renombra la presentación sobrante, o se reasignan sus medicamentos a la otra, y se da de baja (`activo = False`) antes de migrar.
>
> **Ajustes de la tercera revisión adversarial** (cambio de OpenSpec `hb-09-ajustes-revision-4`):
>
> | Hallazgo | Cambio |
> |---|---|
> | 1. La guía no se podía seguir completa | La sección 1 lista todos los archivos; los pasos 2, 3 y 4 traen el código vigente (copiado de los archivos y comprobado); el paso 3b crea `uq_presentacion_nombre` y la migración `0004`; el test base de la sección 3 importa `SIN_PRINCIPIO_ACTIVO` |
> | 2. `null` en la V2 se describía de 2 formas | Una sola: el esquema rechaza la lista vacía (`minItems`, `CAMPO_VACIO` con el mensaje de la regla) y lo que no es *array*, incluido `null` (`TIPO_INVALIDO`); en `exigir_principio_activo()`, `None` es un caso defensivo |
> | 3. Escenario no verificable en el MVP | La traducción a `CAMPO_VACIO` pasa a la descripción del requisito |
> | 4. `bytearray` y `memoryview` pasaban la regla | También lanzan `TypeError` |
> | 6. `campos_sin_acentos` escrito como texto | Un solo error `panel.E003` |
> | 7. Sin test de relación inversa | `medicamentos__nombre_comercial` desde `PrincipioActivo` no da `panel.E002` |
>
> **Nota, sin cambio de código (hallazgo 5):** `panel.E002` marca `"pk"` como campo inexistente, porque `_meta.get_field("pk")` no lo resuelve, aunque `filter(pk=...)` sí funciona. Ningún registro busca por `pk`; si hiciera falta, usa el nombre real del campo (`id`).
>
> **Ajustes de la cuarta revisión adversarial** (cambio de OpenSpec `hb-09-ajustes-revision-5`, solo documentación):
>
> | Hallazgo | Cambio |
> |---|---|
> | 1. El paso 1 no se cumplía: el *import* de `SIN_PRINCIPIO_ACTIVO` tumbaba el módulo | El *import* va dentro de su test, en la sección 3.1 |
> | 2. Dónde estaba el test del Hogar | Pasa a la sección 3.2 (`entidades`), como en el repositorio |
> | 3. Una rama de la V2 que nunca se ejecuta | La nota del readme, `openapi.yaml`, el *docstring* de `validadores.py` y el escenario de la spec dicen una sola cosa: el esquema rechaza la lista vacía con `CAMPO_VACIO` y el mensaje de la regla, y la función protege a quien guarde sin pasar por el esquema |
> | 5. El paso 3b no tenía test en rojo | Sección 3.3 y su verificación en el paso 3b |
> | 7. `CLAUDE.md` no nombraba `panel.E003` | Lo nombra |
>
> **Notas, sin cambio:**
> - **4.** El contrato no define el mapeo general de los errores de esquema del cuerpo (por ejemplo, `maxItems` → `VALOR_FUERA_DE_RANGO`); solo `principios_activos_ids` documenta `minItems` y `type`. Se decide al implementar la API de escritura (V2), partiendo de lo que ya fija ese campo: `minItems` → `CAMPO_VACIO` y `type` → `TIPO_INVALIDO`.
> - **6.** `check()` lanza una excepción, en lugar de un `panel.E00x`, si `campos_sin_acentos` contiene `None` o un número. Es improbable y se vería al arrancar (`dj check`).
>
> **Ajustes de la sexta revisión adversarial** (cambio de OpenSpec `hb-09-ajustes-revision-6`, solo documentación; la quinta revisión se atendió sin cambio de OpenSpec, en `5f031f4`):
>
> | Hallazgo | Cambio |
> |---|---|
> | 1. La nota de la V2 decía que el esquema "aplica la misma regla" | Ahora dice que exige lo mismo (al menos uno) y comparte su mensaje (readme, sección 4, y `04-api.md`) |
> | 2. La spec mezclaba la reutilización de la regla con el esquema de la V2 | La descripción del requisito separa las 2 ideas |
> | 3. El paso 1 y la tabla del rojo no ejecutaban `test_formularios.py` | Se ejecuta aparte en el paso 1, porque falla en la recolección hasta el paso 3; el paso 3 de la tabla lo incluye, y la sección 3.4 trae su versión base |

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
