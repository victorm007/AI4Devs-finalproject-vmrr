"""Reglas de entidades (readme, sección 3.2, D3). Las usa el panel /admin/ (HB-09)."""

from django.db import transaction

from apps.entidades.models import Entidad, Residente

# Lo que registrar_residente() cambia en el objeto recibido y restaura si el alta falla
_CAMPOS_QUE_CAMBIA = (
    "estado",
    "fecha_baja",
    "primer_nombre",
    "segundo_nombre",
    "primer_apellido",
    "segundo_apellido",
)
_NOMBRES = ("primer_nombre", "segundo_nombre", "primer_apellido", "segundo_apellido")
_NOMBRES_OPCIONALES = ("segundo_nombre", "segundo_apellido")


def registrar_residente(residente: Residente) -> Residente:
    """Da de alta un residente: crea su entidad (supertipo) y el residente (subtipo) juntos.

    Recibe un Residente sin guardar. Quita los espacios de los extremos de los nombres, y el
    segundo nombre o el segundo apellido que queden en blanco se guardan vacíos (NULL).
    Siempre queda ACTIVO y sin fecha de baja. Si sus datos no son válidos, lanza
    ValidationError y no se crea nada. Si el alta falla por cualquier motivo, el Residente
    recibido queda como estaba (estado, fecha de baja, nombres y sin Entidad), para poder
    corregirlo y reintentar.

    Ejemplo:
        registrar_residente(Residente(primer_nombre="Ana", primer_apellido="Ruiz",
                                      fecha_nacimiento=date(1940, 3, 1),
                                      fecha_ingreso=date(2026, 1, 5)))
    """
    # _state.adding solo cambia a False tras un save() correcto o al leerlo de la base;
    # el pk no sirve, porque es la Entidad, que se asigna antes de guardar
    if not residente._state.adding:
        raise ValueError("El residente ya está registrado.")
    originales = {campo: getattr(residente, campo) for campo in _CAMPOS_QUE_CAMBIA}
    estado_original = (residente._state.adding, residente._state.db)
    try:
        # Fuera de la transacción: cuando se restaura, la base ya se revirtió
        return _crear_entidad_y_residente(residente)
    except BaseException:
        for campo, valor in originales.items():
            setattr(residente, campo, valor)
        # Sin Entidad: el pk vuelve a None, y asignar entidad_id borra la Entidad en caché
        residente.entidad_id = None
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
