"""Reglas de entidades (readme, sección 3.2, D3). Las usa el panel /admin/ (HB-09)."""

from django.db import transaction

from apps.entidades.models import Entidad, Residente


@transaction.atomic
def registrar_residente(residente: Residente) -> Residente:
    """Da de alta un residente: crea su entidad (supertipo) y el residente (subtipo) juntos.

    Recibe un Residente sin guardar; si sus datos no son válidos, lanza ValidationError y
    no se crea nada. Siempre queda ACTIVO y sin fecha de baja.

    Ejemplo:
        registrar_residente(Residente(primer_nombre="Ana", primer_apellido="Ruiz",
                                      fecha_nacimiento=date(1940, 3, 1),
                                      fecha_ingreso=date(2026, 1, 5)))
    """
    if residente.pk is not None:
        raise ValueError("El residente ya está registrado.")
    residente.estado = Residente.Estado.ACTIVO
    residente.fecha_baja = None
    residente.full_clean(exclude=["entidad"])  # mensajes claros antes de tocar la base
    residente.entidad = Entidad.objects.create(tipo=Entidad.Tipo.RESIDENTE)
    residente.save(force_insert=True)
    return residente
