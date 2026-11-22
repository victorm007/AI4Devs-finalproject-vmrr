"""Reglas de entidades (readme, sección 3.2, D3). Las usa el panel /admin/ (HB-09)."""

from django.db import transaction

from apps.entidades.models import Entidad, Residente

_NOMBRES = ("primer_nombre", "segundo_nombre", "primer_apellido", "segundo_apellido")
_NOMBRES_OPCIONALES = ("segundo_nombre", "segundo_apellido")


def registrar_residente(residente: Residente) -> Residente:
    """Da de alta un residente: crea su entidad (supertipo) y el residente (subtipo) juntos.

    Recibe un Residente sin guardar y sin Entidad; si ya está guardado o trae una Entidad
    asignada, lanza ValueError. Quita los espacios de los extremos de los nombres, y el
    segundo nombre o el segundo apellido que queden en blanco se guardan vacíos (NULL).
    Siempre queda ACTIVO y sin fecha de baja. Si sus datos no son válidos, lanza
    ValidationError y no se crea nada. Si el alta falla por cualquier motivo, también al
    confirmar la transacción, el Residente recibido queda como estaba (todos sus campos tal
    como llegaron, sin guardar y sin Entidad), para poder corregirlo y reintentar.

    Ejemplo:
        registrar_residente(Residente(primer_nombre="Ana", primer_apellido="Ruiz",
                                      fecha_nacimiento=date(1940, 3, 1),
                                      fecha_ingreso=date(2026, 1, 5)))
    """
    # 2 condiciones, porque el pk es la Entidad (supertipo):
    # - _state.adding es False si ya se guardó o se leyó de la base;
    # - pk no es None si se le asignó una Entidad, aunque no esté guardado.
    # Tras un alta fallida, la restauración deja las 2 como al llegar y se puede reintentar.
    if not residente._state.adding or residente.pk is not None:
        raise ValueError("El residente ya está registrado.")
    # Todos los campos, tal como llegaron: full_clean también convierte los valores (por
    # ejemplo, una fecha escrita como texto pasa a date). entidad_id es None por la
    # comprobación anterior.
    originales = {
        campo.attname: getattr(residente, campo.attname)
        for campo in Residente._meta.concrete_fields
    }
    estado_original = (residente._state.adding, residente._state.db)
    try:
        # Fuera de la transacción: cuando se restaura, la base ya se revirtió, también si
        # falló al confirmar
        return _crear_entidad_y_residente(residente)
    except BaseException:
        # Asignar entidad_id (None) también borra la Entidad en caché
        for campo, valor in originales.items():
            setattr(residente, campo, valor)
        residente._state.adding, residente._state.db = estado_original
        raise


@transaction.atomic
def _crear_entidad_y_residente(residente: Residente) -> Residente:
    for campo in _NOMBRES:
        valor = getattr(residente, campo)
        if isinstance(valor, str):
            setattr(residente, campo, valor.strip())
    for campo in _NOMBRES_OPCIONALES:
        if getattr(residente, campo) == "":
            setattr(residente, campo, None)
    residente.estado = Residente.Estado.ACTIVO
    residente.fecha_baja = None
    residente.full_clean(exclude=["entidad"])  # mensajes claros antes de tocar la base
    residente.entidad = Entidad.objects.create(tipo=Entidad.Tipo.RESIDENTE)
    residente.save(force_insert=True)
    return residente
