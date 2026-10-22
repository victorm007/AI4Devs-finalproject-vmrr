# TK-02 · Guía paso a paso: servicio de movimientos de inventario

> **Ticket:** [readme, sección 6, TK-02](../../readme.md#6-tickets-de-trabajo) · **Tipo:** backend · **Estimación:** 5 puntos · **Rama:** `feature/TK-02-servicio-movimientos`
>
> Esta guía explica **cómo** hacerlo. El **qué** y el **porqué** están en el ticket, en HU-01 (sección 5) y en la sección 3.2 (D4 y D5). Si algo de esta guía contradice al readme, manda el readme: avisa en el PR.
>
> **Integración** (readme, sección 6, "Puntos de integración"): este ticket **provee** los puntos 2 y 10 y **consume** los puntos 1, 3, 4, 7, 8 y 11. No cambies un punto que provees sin avisar en el PR. La prueba conjunta de los 3 tickets está en [`integracion.md`](integracion.md).

**Resultado al terminar:** `apps/inventario/services.py` con 4 funciones públicas (`registrar_entrada`, `transferir`, `dar_de_baja` y `corregir`), que son el **único** código que escribe en `movimiento` y `existencia`. Ningún saldo queda negativo, ni siquiera con usuarios simultáneos, y cada error de negocio tiene una excepción con un código estable.

---

## 0. Antes de empezar

### 0.1 Lee primero (30 min)

| Qué | Dónde |
|---|---|
| HU-01: reglas y criterios de aceptación | readme, sección 5 |
| D4 Existencias y D5 Movimientos (reglas por tipo, corrección) | readme, sección 3.2 |
| Códigos de error de la API | readme, sección 4.4 |
| TK-02 | readme, sección 6 |
| Guía de TK-01, pasos 0.4 (atajos) y 9 (fixtures) | [`TK-01-esquema-inventario.md`](TK-01-esquema-inventario.md) |

### 0.2 Requisitos previos

TK-01 debe estar integrado en `main`. Compruébalo:

```bash
git switch main && git pull
set -a && . ./.env && set +a
dj()    { docker compose exec web python manage.py "$@"; }
dtest() { docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" web pytest "$@"; }

dtest apps/inventario/tests/test_esquema.py -q      # todo en verde
dj shell -c "from apps.inventario.models import Movimiento; print(Movimiento.Tipo.values)"
# ['ENTRADA', 'TRANSFERENCIA', 'BAJA']
```

### 0.3 Crea la rama

```bash
git switch -c feature/TK-02-servicio-movimientos
```

### 0.4 Tres conceptos que debes entender antes de programar

1. **Transacción atómica.** Descontar el saldo y registrar el movimiento ocurren juntos o no ocurre ninguno. Se logra con `@transaction.atomic`: si se lanza una excepción, Django revierte todo lo hecho dentro de la función.
2. **Bloqueo de fila (`SELECT ... FOR UPDATE`).** Si 2 usuarios dan de baja la última tableta al mismo tiempo, los 2 leerían "saldo 1" y los 2 descontarían. `select_for_update()` hace que el segundo **espere** a que el primero termine, y entonces lee el saldo ya actualizado (0) y falla con `ExistenciaInsuficiente`.
3. **Orden fijo de bloqueo.** Una transferencia bloquea 2 filas (origen y destino). Si un usuario transfiere Hogar → Carmen y otro Carmen → Hogar, y cada uno bloquea primero "su" origen, se esperan mutuamente para siempre (*deadlock*). Bloquear **siempre en el mismo orden** (por `entidad_id`) lo evita.

> **Restricción importante:** no uses `select_for_update()` sobre `Movimiento`. PostgreSQL exige permiso de `UPDATE` para `FOR UPDATE`, y `app_user` no lo tiene (TK-01). Sí se usa sobre `Existencia`.

---

## 1. Archivos que vas a crear o modificar

```
app/
├── conftest.py                                  # NO SE MODIFICA: usa datos_demo, demo y como_app_user de TK-01
└── apps/inventario/
    ├── exceptions.py                            # NUEVO: excepciones de dominio
    ├── services.py                              # NUEVO: las 4 operaciones
    └── tests/
        ├── test_services.py                     # NUEVO: reglas de negocio
        └── test_concurrencia.py                 # NUEVO: carreras y deadlocks
```

No modifiques `models.py`: si crees que hace falta, pregunta antes en el PR o al Tech Lead.

---

## 2. Tareas paso a paso

Haz un commit al terminar cada paso.

### Paso 1. Excepciones de dominio (≈ 30 min)

`app/apps/inventario/exceptions.py`:

```python
"""Errores de negocio del inventario.

Cada excepción lleva un `code` igual al del contrato de la API (readme, sección 4.4)
y un mensaje en español listo para mostrarse al usuario.
"""

from decimal import Decimal


class ErrorInventario(Exception):
    code = "ERROR_INVENTARIO"
    mensaje = "No se pudo registrar el movimiento."

    def __init__(self, mensaje: str | None = None):
        self.mensaje = mensaje or self.mensaje
        super().__init__(self.mensaje)


class DatoInvalido(ErrorInventario):
    code = "VALIDACION"

    def __init__(self, campo: str, mensaje: str):
        self.campo = campo
        super().__init__(mensaje)


class CantidadInvalida(DatoInvalido):
    def __init__(self, mensaje: str = "La cantidad debe ser mayor a 0 y tener máximo 2 decimales."):
        super().__init__("cantidad", mensaje)


class ExistenciaInsuficiente(ErrorInventario):
    code = "EXISTENCIA_INSUFICIENTE"

    def __init__(self, *, disponible: Decimal, solicitado: Decimal):
        self.disponible = disponible
        self.solicitado = solicitado
        super().__init__(
            f"Existencia insuficiente: hay {disponible.normalize():f} dosis disponible"
            f"{'' if disponible == 1 else 's'}."
        )


class MismaEntidad(ErrorInventario):
    code = "MISMA_ENTIDAD"
    mensaje = "El origen y el destino deben ser distintos."


class EntidadInactiva(ErrorInventario):
    code = "ENTIDAD_INACTIVA"
    mensaje = "El destino no está activo: no puede recibir medicamentos."


class MedicamentoInactivo(ErrorInventario):
    code = "MEDICAMENTO_INACTIVO"
    mensaje = "El medicamento está dado de baja del catálogo."


class MotivoReservado(ErrorInventario):
    code = "MOTIVO_RESERVADO"
    mensaje = "El motivo CORRECCION solo se usa al corregir un movimiento."


class MovimientoYaCorregido(ErrorInventario):
    code = "MOVIMIENTO_YA_CORREGIDO"
    mensaje = "Este movimiento ya fue corregido."


class MovimientoEsCorreccion(ErrorInventario):
    code = "MOVIMIENTO_ES_CORRECCION"
    mensaje = "Una corrección no se puede corregir."
```

> El mensaje "hay 1 dosis disponible" es exactamente el del criterio de aceptación de HU-01.

### Paso 2. Funciones privadas de `services.py` (≈ 1 h)

Crea `app/apps/inventario/services.py` con el encabezado y los *helpers*. Las funciones que empiezan con `_` son privadas: solo se usan dentro de este archivo.

```python
"""Reglas de negocio del inventario (HU-01, readme sección 6, TK-02).

Este es el ÚNICO módulo que escribe en Movimiento y Existencia. Cada función pública:
- recibe argumentos solo por nombre (después del *),
- corre en una transacción atómica,
- valida antes de tocar la base, para dar mensajes claros,
- devuelve el Movimiento creado o lanza una excepción de inventario.exceptions.
"""

import logging
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models.functions import Now
from django.utils import timezone

from .exceptions import (
    CantidadInvalida,
    DatoInvalido,
    EntidadInactiva,
    ExistenciaInsuficiente,
    MedicamentoInactivo,
    MismaEntidad,
    MotivoReservado,
    MovimientoEsCorreccion,
    MovimientoYaCorregido,
)
from .models import Existencia, MotivoBaja, Movimiento

logger = logging.getLogger(__name__)

CENTESIMO = Decimal("0.01")
CANTIDAD_MAXIMA = Decimal("99999999.99")  # numeric(10,2)
CLAVE_CORRECCION = "CORRECCION"


def _validar_cantidad(cantidad) -> Decimal:
    """Convierte a Decimal y valida: > 0, máximo 2 decimales, cabe en numeric(10,2).

    Nunca uses float para cantidades: 0.1 + 0.2 != 0.3 en float.
    """
    try:
        valor = Decimal(str(cantidad))
    except InvalidOperation as exc:
        raise CantidadInvalida() from exc
    if not valor.is_finite() or valor <= 0 or valor > CANTIDAD_MAXIMA:
        raise CantidadInvalida()
    if valor != valor.quantize(CENTESIMO):
        raise CantidadInvalida()
    return valor


def _validar_destino(destino, medicamento) -> None:
    """Un destino solo recibe medicamento si está activo y el medicamento también."""
    if not medicamento.activo:
        raise MedicamentoInactivo()
    if not destino.activa:
        raise EntidadInactiva()


def _bloquear_saldos(medicamento, *entidades) -> dict[int, Existencia]:
    """Garantiza que exista la fila de saldo de cada entidad y la bloquea.

    1. INSERT ... ON CONFLICT DO NOTHING: crea las filas que falten sin carreras.
    2. SELECT ... FOR UPDATE ordenado por entidad_id: orden fijo, sin deadlocks.
    Debe llamarse dentro de una transacción (lo garantizan las funciones públicas).
    """
    Existencia.objects.bulk_create(
        [
            Existencia(entidad=e, medicamento=medicamento, saldo=Decimal("0"),
                       actualizado_en=timezone.now())
            for e in entidades
        ],
        ignore_conflicts=True,
    )
    filas = (
        Existencia.objects.select_for_update()
        .filter(medicamento=medicamento, entidad__in=entidades)
        .order_by("entidad_id")
    )
    return {fila.entidad_id: fila for fila in filas}


def _aplicar(fila: Existencia, delta: Decimal) -> None:
    """Suma (o resta, si delta < 0) al saldo ya bloqueado."""
    if fila.saldo + delta < 0:
        raise ExistenciaInsuficiente(disponible=fila.saldo, solicitado=-delta)
    fila.saldo += delta
    fila.actualizado_en = Now()
    fila.save(update_fields=["saldo", "actualizado_en"])


def _crear_movimiento(**campos) -> Movimiento:
    movimiento = Movimiento.objects.create(**campos)
    movimiento.refresh_from_db(fields=["fecha_hora"])  # la asigna PostgreSQL (db_default)
    logger.info(
        "movimiento_registrado",
        extra={"movimiento_id": movimiento.pk, "tipo": movimiento.tipo,
               "usuario_id": movimiento.usuario_id},
    )  # sin nombres de residentes: LFPDPPP
    return movimiento
```

### Paso 3. Las 4 funciones públicas (≈ 2 h)

Agrégalas al final de `services.py`:

```python
@transaction.atomic
def registrar_entrada(*, usuario, destino, medicamento, cantidad,
                      origen_entrada: str, entregado_por: str, nota: str | None = None) -> Movimiento:
    """Registra medicamento que llega a una entidad (familiar, el Hogar u otro).

    Ejemplo: registrar_entrada(usuario=u, destino=carmen, medicamento=eutirox,
             cantidad="30", origen_entrada="FAMILIAR", entregado_por="Rosa Torres")
    Lanza: CantidadInvalida, DatoInvalido, EntidadInactiva, MedicamentoInactivo.
    """
    cantidad = _validar_cantidad(cantidad)
    if origen_entrada not in Movimiento.OrigenEntrada.values:
        raise DatoInvalido("origen_entrada", "Selecciona de dónde viene el medicamento.")
    entregado_por = (entregado_por or "").strip()
    if not entregado_por:
        raise DatoInvalido("entregado_por", "Indica quién entregó el medicamento.")
    _validar_destino(destino, medicamento)

    saldos = _bloquear_saldos(medicamento, destino)
    _aplicar(saldos[destino.pk], cantidad)
    return _crear_movimiento(
        tipo=Movimiento.Tipo.ENTRADA, usuario=usuario, medicamento=medicamento,
        cantidad=cantidad, entidad_destino=destino, origen_entrada=origen_entrada,
        entregado_por=entregado_por, nota=nota,
    )


@transaction.atomic
def transferir(*, usuario, origen, destino, medicamento, cantidad,
               nota: str | None = None) -> Movimiento:
    """Pasa dosis de una entidad a otra (préstamos, sobrantes tras un egreso).

    El origen puede estar inactivo (un egresado cede sus sobrantes); el destino no.
    Lanza: CantidadInvalida, MismaEntidad, EntidadInactiva, MedicamentoInactivo,
           ExistenciaInsuficiente.
    """
    cantidad = _validar_cantidad(cantidad)
    if origen.pk == destino.pk:
        raise MismaEntidad()
    _validar_destino(destino, medicamento)

    saldos = _bloquear_saldos(medicamento, origen, destino)
    _aplicar(saldos[origen.pk], -cantidad)
    _aplicar(saldos[destino.pk], cantidad)
    return _crear_movimiento(
        tipo=Movimiento.Tipo.TRANSFERENCIA, usuario=usuario, medicamento=medicamento,
        cantidad=cantidad, entidad_origen=origen, entidad_destino=destino, nota=nota,
    )


@transaction.atomic
def dar_de_baja(*, usuario, origen, medicamento, cantidad, motivo: MotivoBaja,
                nota: str | None = None) -> Movimiento:
    """Saca dosis del inventario por un motivo (consumo, caducidad, merma...).

    Lanza: CantidadInvalida, MotivoReservado, DatoInvalido, ExistenciaInsuficiente.
    """
    cantidad = _validar_cantidad(cantidad)
    if motivo.clave == CLAVE_CORRECCION:
        raise MotivoReservado()
    if not motivo.activo:
        raise DatoInvalido("motivo_baja", "El motivo seleccionado ya no está disponible.")

    saldos = _bloquear_saldos(medicamento, origen)
    _aplicar(saldos[origen.pk], -cantidad)
    return _crear_movimiento(
        tipo=Movimiento.Tipo.BAJA, usuario=usuario, medicamento=medicamento,
        cantidad=cantidad, entidad_origen=origen, motivo_baja=motivo, nota=nota,
    )


@transaction.atomic
def corregir(*, usuario, movimiento: Movimiento, nota: str | None = None) -> Movimiento:
    """Registra el movimiento inverso de un error. Cada movimiento se corrige una sola vez.

    ENTRADA a X        -> BAJA desde X con motivo CORRECCION
    BAJA desde X       -> ENTRADA a X (sin origen de entrada ni quién entregó)
    TRANSFERENCIA X->Y -> TRANSFERENCIA Y->X
    Las correcciones quedan exentas de "destino y medicamento activos".
    Lanza: MovimientoEsCorreccion, MovimientoYaCorregido, ExistenciaInsuficiente.
    """
    if movimiento.corrige_a_id is not None:
        raise MovimientoEsCorreccion()
    if movimiento.correcciones.exists():
        raise MovimientoYaCorregido()

    tipo = Movimiento.Tipo
    cantidad = movimiento.cantidad
    medicamento = movimiento.medicamento
    datos = {
        "usuario": usuario, "medicamento": medicamento, "cantidad": cantidad,
        "corrige_a": movimiento, "nota": nota or f"Corrige el movimiento #{movimiento.pk}",
    }
    if movimiento.tipo == tipo.ENTRADA:
        entidad = movimiento.entidad_destino
        saldos = _bloquear_saldos(medicamento, entidad)
        _aplicar(saldos[entidad.pk], -cantidad)
        datos |= {"tipo": tipo.BAJA, "entidad_origen": entidad,
                  "motivo_baja": MotivoBaja.objects.get(clave=CLAVE_CORRECCION)}
    elif movimiento.tipo == tipo.BAJA:
        entidad = movimiento.entidad_origen
        saldos = _bloquear_saldos(medicamento, entidad)
        _aplicar(saldos[entidad.pk], cantidad)
        datos |= {"tipo": tipo.ENTRADA, "entidad_destino": entidad}
    else:
        nuevo_origen, nuevo_destino = movimiento.entidad_destino, movimiento.entidad_origen
        saldos = _bloquear_saldos(medicamento, nuevo_origen, nuevo_destino)
        _aplicar(saldos[nuevo_origen.pk], -cantidad)
        _aplicar(saldos[nuevo_destino.pk], cantidad)
        datos |= {"tipo": tipo.TRANSFERENCIA, "entidad_origen": nuevo_origen,
                  "entidad_destino": nuevo_destino}

    try:
        with transaction.atomic():  # savepoint: aísla el posible IntegrityError
            return _crear_movimiento(**datos)
    except IntegrityError as exc:
        # Otro usuario corrigió el mismo movimiento entre nuestra validación y el INSERT
        if "uq_movimiento_corrige" in str(exc):
            raise MovimientoYaCorregido() from exc
        raise
```

> **Por qué la corrección no bloquea el movimiento original:** no se puede usar `FOR UPDATE` sobre `movimiento` (paso 0.4). Si 2 usuarios corrigen a la vez, la restricción `uq_movimiento_corrige` deja pasar solo a uno; el otro recibe `MovimientoYaCorregido` y su transacción completa, incluido el cambio de saldo, se revierte.

### Paso 4. Comprueba los fixtures que ya trae TK-01 (≈ 10 min)

No crees fixtures nuevos: TK-01 ya dejó los que necesitas, y TK-03 usa los mismos.

| Fixture o helper | Dónde | Para qué |
|---|---|---|
| `datos_demo` | `app/conftest.py` | Carga el mock de la sección 3.4 |
| `demo` | `app/conftest.py` | `demo.carmen`, `demo.med["Eutirox"]`, `demo.motivo["CONSUMO"]`, `demo.operador`... |
| `como_app_user` | `app/conftest.py` | El test corre como `app_user`, igual que la aplicación |
| `ejecutar_sql`, `saldo` | `app/pruebas.py` | SQL directo en un savepoint y saldo actual de una entidad |

```bash
dtest --fixtures apps/inventario | grep -E "datos_demo|demo|como_app_user"   # deben aparecer los 3
```

Si te falta alguno, TK-01 no está completo en `main`: avisa antes de seguir.

### Paso 5. Tests de reglas de negocio (≈ 2 h)

Ver la sección 3.1. Empieza por un test, haz que pase y sigue con el siguiente (*TDD*): es más fácil encontrar el error.

### Paso 6. Tests de concurrencia (≈ 1.5 h)

Ver la sección 3.2. Son los más delicados: léelos completos antes de escribirlos.

### Paso 7. Verificación final y *pull request* (≈ 1 h)

Ejecuta los comandos de la sección 5 y completa la lista de la sección 6.

---

## 3. Tests requeridos

### 3.1 `apps/inventario/tests/test_services.py`

```python
"""Reglas de HU-01 sobre el dataset mock (readme, secciones 3.4 y 5)."""

from decimal import Decimal

import pytest

from apps.entidades.models import Entidad
from apps.inventario import services
from apps.inventario.exceptions import (
    CantidadInvalida, DatoInvalido, EntidadInactiva, ExistenciaInsuficiente, MismaEntidad,
    MotivoReservado, MovimientoEsCorreccion, MovimientoYaCorregido,
)
from apps.inventario.models import Existencia, Movimiento
from pruebas import ejecutar_sql, saldo

pytestmark = pytest.mark.usefixtures("como_app_user")


@pytest.fixture(autouse=True)
def conciliacion_al_terminar():
    """Después de cada test, todos los saldos deben cuadrar con sus movimientos."""
    yield
    assert ejecutar_sql("SELECT count(*) FROM v_conciliacion_existencia") == [(0,)]


# ---------- Entrada ----------

def test_entrada_suma_al_destino_y_guarda_quien_entrego(demo):
    mov = services.registrar_entrada(
        usuario=demo.operador, destino=demo.carmen, medicamento=demo.med["Eutirox"],
        cantidad="30", origen_entrada="FAMILIAR", entregado_por="  Rosa Torres ",
    )
    assert saldo(demo.carmen, demo.med["Eutirox"]) == Decimal("63")
    assert mov.tipo == Movimiento.Tipo.ENTRADA
    assert mov.usuario == demo.operador
    assert mov.entregado_por == "Rosa Torres"          # sin espacios sobrantes
    assert mov.fecha_hora is not None


def test_entrada_sin_quien_entrego_se_rechaza(demo):
    with pytest.raises(DatoInvalido) as error:
        services.registrar_entrada(
            usuario=demo.operador, destino=demo.carmen, medicamento=demo.med["Eutirox"],
            cantidad="30", origen_entrada="FAMILIAR", entregado_por="   ",
        )
    assert error.value.campo == "entregado_por"


# ---------- Transferencia ----------

def test_transferencia_mueve_el_saldo_en_un_solo_movimiento(demo):
    antes = Movimiento.objects.count()
    services.transferir(usuario=demo.operador, origen=demo.hogar, destino=demo.carmen,
                        medicamento=demo.med["Paracetamol"], cantidad=10)
    assert saldo(demo.hogar, demo.med["Paracetamol"]) == 70
    assert saldo(demo.carmen, demo.med["Paracetamol"]) == 24
    assert Movimiento.objects.count() == antes + 1


def test_transferencia_crea_la_fila_de_saldo_si_no_existia(demo):
    assert not Existencia.objects.filter(entidad=demo.maria, medicamento=demo.med["Omeprazol"]).exists()
    services.transferir(usuario=demo.operador, origen=demo.hogar, destino=demo.maria,
                        medicamento=demo.med["Omeprazol"], cantidad=5)
    assert saldo(demo.maria, demo.med["Omeprazol"]) == 5


def test_transferencia_a_la_misma_entidad(demo):
    with pytest.raises(MismaEntidad, match="distintos"):
        services.transferir(usuario=demo.operador, origen=demo.hogar, destino=demo.hogar,
                            medicamento=demo.med["Paracetamol"], cantidad=1)


def test_transferencia_a_residente_egresado(demo):
    ejecutar_sql("UPDATE residente SET estado = 'EGRESADO', fecha_baja = '2026-10-16' "
                 "WHERE entidad_id = 103")
    carmen = Entidad.objects.get(pk=103)   # consulta nueva: sin el residente en caché
    with pytest.raises(EntidadInactiva):
        services.transferir(usuario=demo.operador, origen=demo.hogar, destino=carmen,
                            medicamento=demo.med["Paracetamol"], cantidad=1)


# ---------- Baja ----------

def test_baja_mayor_que_la_existencia_no_cambia_nada(demo):
    antes = Movimiento.objects.count()
    with pytest.raises(ExistenciaInsuficiente, match="hay 1 dosis disponible") as error:
        services.dar_de_baja(usuario=demo.operador, origen=demo.maria,
                             medicamento=demo.med["Atorvastatina"], cantidad=5,
                             motivo=demo.motivo["CONSUMO"])
    assert error.value.disponible == 1
    assert saldo(demo.maria, demo.med["Atorvastatina"]) == 1
    assert Movimiento.objects.count() == antes


def test_baja_con_motivo_correccion_esta_reservada(demo):
    with pytest.raises(MotivoReservado):
        services.dar_de_baja(usuario=demo.operador, origen=demo.hogar,
                             medicamento=demo.med["Omeprazol"], cantidad=1,
                             motivo=demo.motivo["CORRECCION"])


@pytest.mark.parametrize("cantidad", ["0", "-1", "0.555", "abc", "100000000"])
def test_cantidades_invalidas(demo, cantidad):
    with pytest.raises(CantidadInvalida):
        services.dar_de_baja(usuario=demo.operador, origen=demo.hogar,
                             medicamento=demo.med["Omeprazol"], cantidad=cantidad,
                             motivo=demo.motivo["MERMA"])


def test_media_tableta_es_valida(demo):
    services.dar_de_baja(usuario=demo.operador, origen=demo.hogar,
                         medicamento=demo.med["Omeprazol"], cantidad="0.5",
                         motivo=demo.motivo["CONSUMO"])
    assert saldo(demo.hogar, demo.med["Omeprazol"]) == Decimal("58.5")


# ---------- Corrección ----------

@pytest.fixture
def entrada_erronea(demo):
    """La entrada de 600 Metformina de María que ya está corregida en el mock."""
    return Movimiento.objects.get(correcciones__isnull=False)


def test_corregir_una_entrada_genera_una_baja_correccion(demo):
    mov = services.registrar_entrada(
        usuario=demo.operador, destino=demo.carmen, medicamento=demo.med["Eutirox"],
        cantidad="30", origen_entrada="FAMILIAR", entregado_por="Rosa Torres",
    )
    correccion = services.corregir(usuario=demo.operador, movimiento=mov)
    assert correccion.tipo == Movimiento.Tipo.BAJA
    assert correccion.motivo_baja.clave == "CORRECCION"
    assert correccion.corrige_a == mov
    assert saldo(demo.carmen, demo.med["Eutirox"]) == 33


def test_no_se_corrige_dos_veces(demo, entrada_erronea):
    with pytest.raises(MovimientoYaCorregido):
        services.corregir(usuario=demo.operador, movimiento=entrada_erronea)


def test_una_correccion_no_se_corrige(demo, entrada_erronea):
    correccion = entrada_erronea.correcciones.get()
    with pytest.raises(MovimientoEsCorreccion):
        services.corregir(usuario=demo.operador, movimiento=correccion)


def test_corregir_una_transferencia_la_invierte(demo):
    mov = services.transferir(usuario=demo.operador, origen=demo.hogar, destino=demo.carmen,
                              medicamento=demo.med["Paracetamol"], cantidad=10)
    services.corregir(usuario=demo.operador, movimiento=mov)
    assert saldo(demo.hogar, demo.med["Paracetamol"]) == 80
    assert saldo(demo.carmen, demo.med["Paracetamol"]) == 14


def test_no_se_corrige_una_entrada_ya_consumida(demo):
    mov = services.registrar_entrada(
        usuario=demo.operador, destino=demo.maria, medicamento=demo.med["Atorvastatina"],
        cantidad="10", origen_entrada="HOGAR", entregado_por="Dirección",
    )
    services.dar_de_baja(usuario=demo.operador, origen=demo.maria,
                         medicamento=demo.med["Atorvastatina"], cantidad=11,
                         motivo=demo.motivo["CONSUMO"])
    with pytest.raises(ExistenciaInsuficiente):
        services.corregir(usuario=demo.operador, movimiento=mov)
```

Completa con los casos que faltan para cubrir cada rama de `services.py` (la cobertura te dice cuáles): entrada con `origen_entrada` inválido, entrada de un medicamento inactivo, baja con un motivo inactivo y corrección de una baja.

### 3.2 `apps/inventario/tests/test_concurrencia.py`

Estos tests usan transacciones **reales** (`transaction=True`): cada hilo tiene su propia conexión y ve lo que los otros confirman. `serialized_rollback=True` restaura los datos semilla (Hogar, motivos y grupos) que el test borra al terminar.

```python
"""Carreras y deadlocks (TK-02). Corren contra PostgreSQL real, nunca SQLite."""

import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.db import connection
from django.db.transaction import TransactionManagementError

from apps.inventario import services
from apps.inventario.exceptions import ExistenciaInsuficiente
from pruebas import saldo

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)
TIEMPO_LIMITE = 20  # segundos: si un hilo se bloquea, el test falla en lugar de colgarse


def en_hilo_como_app_user(funcion):
    """Ejecuta la función en la conexión del hilo, como app_user, y la cierra al final."""
    def envoltura(*args, **kwargs):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET ROLE app_user")
            return funcion(*args, **kwargs)
        finally:
            connection.close()
    return envoltura


def test_dos_bajas_simultaneas_de_la_ultima_dosis(demo):
    barrera = threading.Barrier(2)            # los 2 hilos arrancan a la vez
    resultados = []

    @en_hilo_como_app_user
    def baja():
        barrera.wait()
        try:
            services.dar_de_baja(usuario=demo.operador, origen=demo.maria,
                                 medicamento=demo.med["Atorvastatina"], cantidad=1,
                                 motivo=demo.motivo["CONSUMO"])
            resultados.append("ok")
        except ExistenciaInsuficiente:
            resultados.append("insuficiente")

    hilos = [threading.Thread(target=baja) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(TIEMPO_LIMITE)

    assert sorted(resultados) == ["insuficiente", "ok"]
    assert saldo(demo.maria, demo.med["Atorvastatina"]) == 0


def test_transferencias_cruzadas_no_provocan_deadlock(demo):
    paracetamol = demo.med["Paracetamol"]

    @en_hilo_como_app_user
    def transferir(origen, destino):
        services.transferir(usuario=demo.operador, origen=origen, destino=destino,
                            medicamento=paracetamol, cantidad=1)

    pares = [(demo.hogar, demo.carmen), (demo.carmen, demo.hogar)] * 10
    with ThreadPoolExecutor(max_workers=10) as pool:
        futuros = [pool.submit(transferir, o, d) for o, d in pares]
        for futuro in futuros:
            futuro.result(timeout=TIEMPO_LIMITE)   # relanza cualquier error del hilo

    assert saldo(demo.hogar, paracetamol) == 80   # 10 de ida y 10 de vuelta
    assert saldo(demo.carmen, paracetamol) == 14


def test_bloquear_fuera_de_una_transaccion_falla(demo):
    with pytest.raises(TransactionManagementError):
        services._bloquear_saldos(demo.med["Paracetamol"], demo.hogar)


def test_si_falla_el_insert_el_saldo_no_cambia(demo, monkeypatch):
    def insert_que_falla(**campos):
        raise RuntimeError("falla simulada después de descontar el saldo")

    monkeypatch.setattr(services, "_crear_movimiento", insert_que_falla)
    with pytest.raises(RuntimeError):
        services.dar_de_baja(usuario=demo.operador, origen=demo.hogar,
                             medicamento=demo.med["Omeprazol"], cantidad=1,
                             motivo=demo.motivo["MERMA"])
    assert saldo(demo.hogar, demo.med["Omeprazol"]) == Decimal("59")
```

> `datos_demo` (y por lo tanto `demo`) funciona igual con `transaction=True`: el SQL del mock se ejecuta como una sola transacción implícita y queda confirmado para que lo vean los hilos.

---

## 4. Criterios de calidad

| Criterio | Cómo se comprueba |
|---|---|
| Solo `services.py` escribe en `Movimiento` y `Existencia` | Comando 4 de la sección 5 |
| Cantidades siempre `Decimal`, nunca `float` | Revisión del PR; `_validar_cantidad` convierte con `Decimal(str(...))` |
| Funciones públicas con argumentos solo por nombre (`*`), *type hints* y *docstring* con ejemplo y excepciones | Revisión del PR |
| Validaciones antes de tocar la base; la base es la última barrera | Cada excepción de dominio tiene su test |
| Sin `select_for_update` sobre `Movimiento` | `git grep` (comando 4) |
| Logs sin datos personales: solo ids y tipo | Revisión del PR |
| Mensajes de error en español, listos para el usuario | Los textos coinciden con los criterios de HU-01 |
| Cobertura ≥ 90 % en `services.py` y 100 % de ramas en `exceptions.py` | Comando 3 de la sección 5 |
| Tests de concurrencia deterministas: pasan 20 veces seguidas | Comando 5 de la sección 5 |

---

## 5. Verificación: comandos y resultado esperado

```bash
# 1. Calidad del código
docker compose exec web ruff check . && docker compose exec web ruff format --check .

# 2. Todos los tests del ticket
dtest apps/inventario -q

# 3. Cobertura (requiere pytest-cov en requirements-dev.txt)
dtest apps/inventario --cov=apps.inventario.services --cov=apps.inventario.exceptions \
      --cov-branch --cov-report=term-missing --cov-fail-under=90
# TOTAL ... >= 90 %; revisa las líneas listadas en "Missing"

# 4. Nadie más escribe en Movimiento o Existencia
git grep -nE "(Movimiento|Existencia)\.objects\.(create|bulk_create|update|get_or_create|update_or_create)|Movimiento\.objects\.select_for_update" \
    -- 'app/apps' ':!*/tests/*' ':!*/migrations/*'
# Solo deben aparecer líneas de app/apps/inventario/services.py

# 5. Los tests de concurrencia no son intermitentes
for i in $(seq 1 20); do dtest apps/inventario/tests/test_concurrencia.py -q -p no:randomly || break; done

# 6. Prueba manual en la base de desarrollo con el mock cargado (TK-01, paso 8)
dj shell
```

```python
>>> from apps.inventario import services
>>> from apps.inventario.models import MotivoBaja
>>> from apps.entidades.models import Entidad
>>> from apps.catalogo.models import Medicamento
>>> from apps.accounts.models import Usuario
>>> u = Usuario.objects.get(username="operador.demo")
>>> hogar, carmen = Entidad.objects.get(tipo="HOGAR"), Entidad.objects.get(pk=103)
>>> p = Medicamento.objects.get(nombre_comercial="Paracetamol")
>>> services.transferir(usuario=u, origen=hogar, destino=carmen, medicamento=p, cantidad=10)
<Movimiento: Movimiento object (29)>
>>> services.transferir(usuario=u, origen=hogar, destino=hogar, medicamento=p, cantidad=1)
Traceback (most recent call last):
  ...
apps.inventario.exceptions.MismaEntidad: El origen y el destino deben ser distintos.
```

Después de probar a mano, vuelve a dejar la base como estaba: `docker compose down -v && docker compose up -d && ./scripts/migrate.sh` y carga el mock otra vez.

---

## 6. Lista para el *pull request*

- [ ] Todos los comandos de la sección 5 dan el resultado esperado.
- [ ] Todos los criterios de aceptación del ticket (readme, sección 6) están marcados.
- [ ] La definición de hecho común y la del ticket se cumplen.
- [ ] La descripción del PR incluye la salida de la cobertura y explica en 2 líneas cómo se evitan las carreras y los *deadlocks*.

## 7. Si te bloqueas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `permission denied for table movimiento` en un test | Usaste `select_for_update()` u `update()` sobre `Movimiento` | Revisa el paso 0.4: la corrección se protege con `uq_movimiento_corrige` |
| `TransactionManagementError: select_for_update cannot be used outside of a transaction` | Llamaste a `_bloquear_saldos` desde una función sin `@transaction.atomic` | Agrega el decorador a la función pública |
| Un test de concurrencia se queda colgado | *Deadlock* o un hilo esperando a la barrera | Revisa el `order_by("entidad_id")`; el tiempo límite hace que el test falle en lugar de colgarse |
| `ExistenciaInsuficiente` en el test de transferencias cruzadas | Algún hilo de vuelta (Carmen → Hogar) llegó antes que los de ida | No debería pasar: Carmen empieza con 14. Si cambiaste las cantidades, que el origen tenga saldo para todas |
| Después de un test de concurrencia, otros tests fallan con "Falta la entidad HOGAR" | Falta `serialized_rollback=True` | Usa el `pytestmark` de la sección 3.2 |
| `mov.fecha_hora` es un objeto `DatabaseDefault` | Falta el `refresh_from_db` en `_crear_movimiento` | Paso 2 |
| `Decimal('0.1') + 0.2` da error de tipos | Mezclaste `float` con `Decimal` | Pasa las cantidades como texto o `Decimal`, nunca como `float` |
