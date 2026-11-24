# Design

## Context

HB-05 dejó los modelos del catálogo con `uq_medicamento_nombre_pres_conc` y `uq_principio_activo_nombre` sobre `f_unaccent(lower(...))`, con su `violation_error_message`, y `sin_acentos()` en `apps/expresiones.py`. HB-06 dejó `Residente` con `ck_residente_baja` y `ck_residente_fechas` (también con mensaje), `ix_residente_nombre` y `registrar_residente()`. HB-08 dejó los 2 grupos (`0003_grupos`: *Solo lectura* con `view_*` y *Lectura y escritura* con `view_*`, `add_*` y `change_*` sobre `presentacion`, `principioactivo`, `medicamento`, `medicamentoprincipioactivo` y `residente`), el login y `UsuarioAdmin`. Las plantillas del panel de Django 5.2.19 no tienen `<script>` en línea ni atributos `style` (revisado en la imagen `web`). La motivación está en `proposal.md`, y el comportamiento, en `specs/catalogo/spec.md` y `specs/entidades/spec.md`.

El código de la guía (`docs/tickets/HB-09-admin-catalogo-residentes.md`) nunca se ha ejecutado. Al leerlo contra el readme, los ADR y el código:

- La guía indica la rama `feature/HB-09-admin-catalogo-residentes`; `CLAUDE.md` manda seguir en `feature/entrega-2-vmrr`.
- Sus tests no cubren todos los criterios: *Solo lectura* solo se prueba en la lista y el alta de medicamentos (faltan residentes, presentaciones, principios activos y el `403` al cambiar), no hay prueba de N+1, del *autocomplete*, de la CSP, del mensaje de `ck_residente_fechas` ni de la defunción, y la búsqueda no tiene control negativo.
- `test_el_hogar_no_se_edita_en_el_panel` está en el archivo del catálogo, aunque `Entidad` es de `entidades`.

## Goals / Non-Goals

**Goals:**

- Que el panel no pueda saltarse ninguna regla: sin borrado, alta de residentes por el servicio y reglas de la base como mensajes.
- Que la búsqueda use la misma expresión que los índices (`f_unaccent(lower(campo))`).

**Non-Goals:**

- La validación de la baja con existencias (TK-01) y cualquier modelo de inventario o de pautas en el panel.
- Cambiar el aspecto del panel más allá de sus títulos.

## Decisions

### 1. Reglas comunes en `apps/panel.py` ([ADR-0020](../../../docs/adr/0020-habilitadores-en-panel-admin.md), [ADR-0009](../../../docs/adr/0009-bajas-logicas-y-on-delete-restrict.md))

Dos *mixins*, como en la guía, que van antes de `admin.ModelAdmin` en la herencia:

- `SinBorrarMixin.has_delete_permission()` devuelve `False`: el panel quita la acción "Eliminar" de la lista, el botón de la página y responde `403` en `.../delete/`, también al superusuario.
- `BusquedaSinAcentosMixin.get_search_results()` declara con `alias()` (no con `annotate()`, para que la expresión no vaya al `SELECT` y `distinct()` quite de verdad los repetidos) `sin_acentos(campo)` por cada campo de `campos_sin_acentos` y filtra con `__contains` contra `sin_acentos(Value(término))`, unidos con `OR`. Devuelve `may_have_duplicates = True` porque la búsqueda por principio activo une con la tabla puente; el `ChangeList` de Django los quita con `Exists`, y el *autocomplete*, con `distinct()`. `search_fields` sigue declarado solo para que el panel muestre el buscador y para que el *autocomplete* esté permitido (`admin.E039`/`E040`).

**Alternativa descartada:** los *lookups* de `search_fields` (`unaccent__icontains`), porque generan `UPPER(UNACCENT(...))` y no la expresión de los índices ([ADR-0017](../../../docs/adr/0017-busqueda-sin-acentos-con-trigram.md)).

**Precisión sobre ADR-0017 (sin contradecirlo):** el mínimo de 3 caracteres y la unión con `UNION` en lugar de `OR` son de la búsqueda de existencias por medicamento o principio activo (consulta 1; `q` de la API). El panel conserva la expresión `f_unaccent(lower(campo))`, pero no exige mínimo ni usa `UNION`: busca también entre los medicamentos dados de baja, que el índice parcial `ix_medicamento_nombre_trgm` (`WHERE activo`) no cubre, sobre un catálogo de cientos de filas y por unos pocos usuarios. Exigir 3 caracteres dejaría sin resultados una búsqueda corta en el panel sin un mensaje que lo explique.

### 2. Catálogo (`apps/catalogo/admin.py`)

Como el paso 3 de la guía. `MedicamentoAdmin` usa `list_select_related = ("presentacion",)` para que la lista no haga N+1, y `PrincipioActivoEnLinea` (`TabularInline` de `MedicamentoPrincipioActivo`) con `min_num = 1`, `validate_min = True`, `extra = 0`, `can_delete = False` y `autocomplete_fields = ["principio_activo"]`. **Decidido durante la implementación:** Django 5.2 no pasa `validate_min` de un *inline* a `inlineformset_factory`, así que `PrincipioActivoEnLinea.get_formset()` lo pasa explícitamente. Sin eso, el alta sin principios activos se guardaba. Los mensajes de duplicado salen de `violation_error_message` de las restricciones de HB-05, que el formulario valida antes de guardar (`Model.validate_constraints`).

### 3. Residentes (`apps/entidades/admin.py`, [ADR-0008](../../../docs/adr/0008-supertipo-entidad-subtipo-residente.md), [ADR-0011](../../../docs/adr/0011-capa-de-servicios-unica-via-de-escritura.md))

Como el paso 4 de la guía:

- `get_fields()` omite `estado` y `fecha_baja` en el alta.
- `save_model()` llama a `registrar_residente(obj)` en el alta y a `obj.save()` en el cambio. El formulario ya validó `ck_residente_baja` y `ck_residente_fechas` con sus mensajes, porque en el cambio incluye `estado` y `fecha_baja`.
- `Entidad` no se registra.

**Cambio sobre la guía:** `ordering` y el `ordering` de la columna "Nombre" usan `sin_acentos("primer_apellido")` y `sin_acentos("primer_nombre")` en lugar de los campos crudos, para ordenar sin acentos con la misma expresión de `ix_residente_nombre` (consulta 3, ADR-0017). El panel de Django admite expresiones en `ordering`.

### 4. Títulos del panel

En `config/urls.py`, `site_header`, `site_title` e `index_title` del paso 5 de la guía. Es texto visible y no se prueba con pytest; se revisa en la prueba manual.

### 5. Tests ([ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md))

Capa HTTP (`pytestmark = [pytest.mark.django_db, pytest.mark.http]`), con los datos mínimos de la guía: antes de TK-01 no hay mock. Los usuarios de grupo son `prueba.*`, creados con `create_user(..., is_staff=True)` y con sesión por `force_login` (nunca `client.login()`, por `django-axes`); el Administrador es `admin_client` de pytest-django. Cada `403` lleva un control positivo, como en HB-08. Se agregan a los de la guía los tests de los Scenarios que no tenía (ver "Context"), y `test_el_hogar_no_se_edita_en_el_panel` pasa a `apps/entidades/tests/test_admin.py`. El N+1 se comprueba con los *fixtures* `django_assert_max_num_queries` (para medir con 1 medicamento) y `django_assert_num_queries` (para exigir lo mismo con 3).

## Risks / Trade-offs

- [El *autocomplete* y el botón **+** usan JavaScript del panel (select2 y ventanas emergentes)] → las plantillas no tienen código en línea, un test lo revisa en la página de alta, y la consola del navegador se revisa a mano en la prueba del paso 6.
- [`can_delete = False` en el *inline* impide quitar un principio activo de un medicamento que tiene 2] → se corrige cambiando el principio activo del renglón, como dice la guía. Si hiciera falta quitar renglones, se decide en la V2 con las pantallas propias.
- [Un medicamento con existencias se puede desmarcar como inactivo hasta TK-01] → no hay existencias antes de TK-01; TK-01 agrega el formulario y `tg_medicamento_baja`.
- [El orden por expresión en la lista de residentes depende de que el panel acepte expresiones en `ordering`] → `dj check` lo valida (`admin.E033`), y la lista se abre en los tests.

## Migration Plan

Sin migraciones: el panel no cambia el esquema (`dj makemigrations --check --dry-run` debe decir "No changes detected"). La reversión es quitar los `admin.py` y `panel.py`.
