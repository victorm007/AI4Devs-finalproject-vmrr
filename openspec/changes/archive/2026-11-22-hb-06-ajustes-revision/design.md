# Design

## Context

HB-06 está integrado en la rama (`1972ec6`) y su cambio de OpenSpec, archivado. Lo que la revisión adversarial señaló, observado en el código:

- `Entidad.activa` y `__str__` (`models.py:57-64`) acceden a `self.residente` sin protección. Con una Entidad `RESIDENTE` sin fila en `residente`, lanzan `RelatedObjectDoesNotExist`. La base admite ese caso, porque la FK compuesta va del subtipo al supertipo.
- `registrar_residente()` (`services.py:20-26`) usa `residente.pk is not None` y modifica `estado` y `fecha_baja` antes de validar. Si `save()` falla después de crear la Entidad, `atomic` revierte la base, pero el objeto se queda con una `entidad` que ya no existe y su `pk`. Un reintento da `ValueError("El residente ya está registrado.")`, que es falso.
- `ck_residente_nombres` no tiene `violation_error_message`. `clean_fields` no detecta un nombre de solo espacios, así que el mensaje es "Constraint … is violated".
- `HOGAR_NOMBRE` tiene un valor por defecto en `base.py` y en `docker-compose.yml`. `0003_hogar` crea el Hogar una sola vez, y Entidad no está en `/admin/` (guía de HB-09), así que un nombre equivocado solo se corrige por SQL.
- La guía de HB-06 dice que en la demo el Hogar se llama "Hogar Gerontológico Demo". Por eso producción no puede rechazar ese nombre: solo puede exigir que se defina de forma explícita.
- `config.settings.prod` no lo carga ningún test ni el CI. La guía de HB-04 la usa en `check --deploy` dentro del contenedor `web`.

## Goals / Non-Goals

**Goals:**

- Que TK-01, TK-02 y TK-03 consuman `activa` y `__str__` sin errores y sin consultas N+1.
- Que un alta fallida no deje el objeto en un estado engañoso.
- Que el servidor del hogar no pueda crear el Hogar sin haber elegido su nombre.

**Non-Goals:**

- Renombrar el Hogar después de la primera migración (despliegue, sin ticket todavía).
- Leer `.env` con valores con espacios (TK-01).

## Decisions

### 1. `activa` y `__str__` capturan `Residente.DoesNotExist`

`RelatedObjectDoesNotExist` hereda de `Residente.DoesNotExist`, y lo lanza también `select_related` cuando la fila no existe (guarda `None` en la caché sin consultar). Capturarlo cubre los 2 casos:

- `activa` devuelve `False`, porque sin datos del Residente no se puede saber si está `ACTIVO`.
- `__str__` devuelve `f"Entidad {self.pk}"`.

El docstring de la clase indica que las listas usan `select_related("residente")`. Un test lo comprueba con `django_assert_num_queries(1)`. Alternativa descartada: hacer que `activa` consulte `Residente.objects.filter(...).exists()`, porque agrega una consulta por fila.

### 2. `registrar_residente()` normaliza, valida y restaura si falla

- La comprobación de "ya registrado" pasa de `pk` a `residente._state.adding`, que solo cambia a `False` tras un `save()` correcto o al leer el objeto de la base.
- Guarda los valores originales de `estado`, `fecha_baja` y los 4 nombres.
- Quita los espacios de los extremos de los nombres, y convierte en `None` el segundo nombre y el segundo apellido vacíos.
- Después fuerza `ACTIVO` y sin fecha de baja, llama a `full_clean(exclude=["entidad"])`, crea la Entidad y guarda.
- Ante cualquier excepción, restaura los valores originales, desvincula la Entidad (`pk` vuelve a `None`) y vuelve a lanzar la excepción. Con `@transaction.atomic`, la base ya quedó revertida.

Al quitar los espacios, un primer nombre de solo espacios queda vacío, y `full_clean` lo rechaza con el error de campo obligatorio de Django, en el campo `primer_nombre`. El mensaje de la restricción (decisión 3) queda para quien valide sin pasar por el servicio.

### 3. Mensaje de `ck_residente_nombres` en una migración `0004`

`violation_error_message="El primer nombre y el primer apellido no pueden quedar vacíos."`. Django 5.2 genera una migración que no cambia la base; se comprueba con `sqlmigrate entidades 0004`. No se edita `0001_initial`, que ya está aplicada en las bases locales.

### 4. `HOGAR_NOMBRE` explícito en producción ([ADR-0004](../../../docs/adr/0004-configuracion-por-entorno-variables-db.md))

- **`base.py`:** `HOGAR_NOMBRE = os.environ.get("HOGAR_NOMBRE", "").strip() or "Hogar Gerontológico Demo"`. Una variable vacía también toma el valor por defecto.
- **`prod.py`:** vuelve a leer la variable. Si falta o está vacía, lanza `ImproperlyConfigured("Falta HOGAR_NOMBRE en .env: en producción el Hogar debe tener su nombre real (o el de la demo, si es la demo).")`. Es el mismo criterio que `SECRET_KEY`, que no tiene valor por defecto.
- **`docker-compose.yml`:** `HOGAR_NOMBRE: ${HOGAR_NOMBRE:-}`, que pasa el valor de `.env` sin inventarlo.

Alternativas descartadas:
- rechazar el nombre de la demo en producción, porque la demo lo usa;
- un *system check* de despliegue, porque `migrate` no corre los de `--deploy` y la migración del Hogar se aplicaría igual.

Los tests cargan `config.settings.prod` y `config.settings.local` en un subproceso (`python -c "from django.conf import settings; …"`), con el entorno del contenedor sin la variable. No se recarga el módulo de configuración dentro de pytest. Van en `app/config/tests/test_configuracion.py`, con el marcador `infra`.

### 5. Fallo de escritura simulado en un solo test

El escenario "Un fallo al guardar permite reintentar" necesita que `save()` falle después de crear la Entidad. Con datos reales no ocurre: todo lo que la base rechaza, `full_clean` ya lo validó contra ella. El test usa `monkeypatch` para que `Residente.save` lance `IntegrityError` una vez, y comprueba contra PostgreSQL real que no queda ninguna Entidad nueva.

La base no se simula: solo se inyecta la falla. Es el único caso, y se declara en el plan ([ADR-0023](../../../docs/adr/0023-pruebas-contra-postgresql-real.md)).

## Risks / Trade-offs

- **[Producción no arranca sin `HOGAR_NOMBRE`, y hasta TK-01 un valor con espacios rompe `migrate.sh`]** → El despliegue en el servidor del hogar es de la semana 6, después de TK-01. Lo dicen `.env.example`, el readme (2.4) y la guía de HB-06.
- **[La guía de HB-04 corre `check --deploy` con `config.settings.prod` en el contenedor de desarrollo]** → Ahora le pasa `-e HOGAR_NOMBRE=...`. Su Scenario en `infraestructura` lo incluye en el GIVEN.
- **[Cambia el punto de integración 11]** → Solo se amplía: el resultado para el Hogar y los Residentes no cambia. Se actualiza el texto del punto 11 en el readme, sección 6.
- **[`web` se recrea para tomar el `docker-compose.yml` nuevo]** → `docker compose up -d web`, sin borrar datos.
