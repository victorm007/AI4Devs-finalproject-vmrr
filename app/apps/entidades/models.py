"""Entidades que poseen existencias: el Hogar y los residentes (readme, sección 3.2, D3).

entidad es el supertipo: existencia, movimiento y conteo_fisico tienen una sola FK real
hacia ella. residente es el subtipo, con la misma clave. Sin lógica en los modelos: las
reglas viven en Meta.constraints, en la base de datos y en services.py.
"""

from datetime import date

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now

from apps.expresiones import no_vacio, sin_acentos


class Entidad(models.Model):
    """Supertipo: el Hogar o un residente (punto de integración 11: activa y __str__).

    activa y __str__ leen el Residente de la Entidad. Las listas deben cargarlo con
    select_related("residente"), o cada fila hará una consulta extra:

        Entidad.objects.select_related("residente")
    """

    class Tipo(models.TextChoices):
        HOGAR = "HOGAR", "Hogar"
        RESIDENTE = "RESIDENTE", "Residente"

    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    # Solo el Hogar tiene nombre aquí; el del residente vive desglosado en residente
    nombre = models.CharField(max_length=150, null=True, blank=True)
    creado_en = models.DateTimeField(db_default=Now(), editable=False)
    actualizado_en = models.DateTimeField(auto_now=True, db_default=Now())

    class Meta:
        db_table = "entidad"
        verbose_name_plural = "entidades"
        constraints = [
            # Índice único parcial: (tipo) WHERE tipo = 'HOGAR'
            models.UniqueConstraint(
                fields=["tipo"],
                condition=Q(tipo="HOGAR"),
                name="uq_entidad_un_hogar",
                violation_error_message="Solo puede existir un Hogar.",
            ),
            # Destino de la FK compuesta de residente: (id, tipo)
            models.UniqueConstraint(fields=["id", "tipo"], name="uq_entidad_id_tipo"),
            models.CheckConstraint(
                condition=Q(tipo__in=["HOGAR", "RESIDENTE"]), name="ck_entidad_tipo"
            ),
            # (tipo = 'HOGAR') = (nombre IS NOT NULL)
            models.CheckConstraint(
                condition=Q(tipo="HOGAR", nombre__isnull=False)
                | (~Q(tipo="HOGAR") & Q(nombre__isnull=True)),
                name="ck_entidad_nombre",
            ),
            models.CheckConstraint(
                condition=Q(nombre__isnull=True) | no_vacio("nombre"),
                name="ck_entidad_nombre_no_vacio",
            ),
        ]

    # Punto de integración 11: lo usan TK-02 (destino activo) y TK-03 (pantalla).
    # Residente.DoesNotExist cubre una Entidad RESIDENTE sin su fila en residente, tanto al
    # consultarla (RelatedObjectDoesNotExist hereda de ella) como con select_related, que
    # guarda None en la caché y lanza la misma excepción sin consultar.
    @property
    def activa(self) -> bool:
        """El Hogar siempre está activo; un residente, solo si su estado es ACTIVO.

        Sin su Residente no se puede saber el estado: no está activa.
        """
        if self.tipo == self.Tipo.HOGAR:
            return True
        try:
            return self.residente.estado == Residente.Estado.ACTIVO
        except Residente.DoesNotExist:
            return False

    def __str__(self) -> str:
        """Nombre del Hogar o nombre completo del residente; sin Residente, "Entidad <id>"."""
        if self.tipo == self.Tipo.HOGAR:
            return self.nombre
        try:
            return self.residente.nombre_completo
        except Residente.DoesNotExist:
            return f"Entidad {self.pk}"


class Residente(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        EGRESADO = "EGRESADO", "Egresado"
        FALLECIDO = "FALLECIDO", "Fallecido"

    # Misma clave que su entidad. db_constraint=False: la FK real es compuesta
    # (entidad_id, tipo) -> entidad (id, tipo) y se crea en 0002_fk_compuesta.
    entidad = models.OneToOneField(
        Entidad,
        on_delete=models.PROTECT,
        primary_key=True,
        related_name="residente",
        db_constraint=False,
    )
    tipo = models.CharField(
        max_length=10, default="RESIDENTE", db_default="RESIDENTE", editable=False
    )
    primer_nombre = models.CharField(max_length=60)
    segundo_nombre = models.CharField(max_length=60, null=True, blank=True)
    primer_apellido = models.CharField(max_length=60)
    segundo_apellido = models.CharField(max_length=60, null=True, blank=True)
    fecha_nacimiento = models.DateField()
    fecha_ingreso = models.DateField()
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.ACTIVO, db_default=Estado.ACTIVO
    )
    fecha_baja = models.DateField(
        null=True, blank=True, help_text="Fecha de egreso o defunción; vacía si está activo."
    )

    class Meta:
        db_table = "residente"
        constraints = [
            models.CheckConstraint(condition=Q(tipo="RESIDENTE"), name="ck_residente_tipo"),
            models.CheckConstraint(
                condition=Q(estado__in=["ACTIVO", "EGRESADO", "FALLECIDO"]),
                name="ck_residente_estado",
            ),
            # (estado = 'ACTIVO') = (fecha_baja IS NULL)
            models.CheckConstraint(
                condition=Q(estado="ACTIVO", fecha_baja__isnull=True)
                | (~Q(estado="ACTIVO") & Q(fecha_baja__isnull=False)),
                name="ck_residente_baja",
                violation_error_message="La fecha de baja es obligatoria si el residente "
                "egresó o falleció, y debe quedar vacía si está activo.",
            ),
            models.CheckConstraint(
                condition=Q(fecha_baja__isnull=True) | Q(fecha_baja__gte=F("fecha_ingreso")),
                name="ck_residente_fechas",
                violation_error_message="La fecha de baja no puede ser anterior al ingreso.",
            ),
            models.CheckConstraint(
                condition=no_vacio("primer_nombre") & no_vacio("primer_apellido"),
                name="ck_residente_nombres",
                violation_error_message="El primer nombre y el primer apellido no pueden "
                "quedar vacíos.",
            ),
            models.CheckConstraint(
                condition=Q(fecha_nacimiento__gte=date(1900, 1, 1))
                & Q(fecha_ingreso__gte=F("fecha_nacimiento")),
                name="ck_residente_nacimiento",
                violation_error_message="Revisa las fechas: el ingreso no puede ser anterior "
                "al nacimiento.",
            ),
        ]
        indexes = [
            # Buscar y ordenar por apellido y nombre, sin acentos (consulta 3, sección 3.3)
            models.Index(
                sin_acentos("primer_apellido"),
                sin_acentos("primer_nombre"),
                name="ix_residente_nombre",
            ),
        ]

    @property
    def nombre_completo(self) -> str:
        """Ejemplo: "Carmen Torres Vega" (sin segundo nombre). Se compone, no se guarda.

        Quita los espacios de los extremos de cada parte y omite las vacías.
        """
        partes = [
            self.primer_nombre,
            self.segundo_nombre,
            self.primer_apellido,
            self.segundo_apellido,
        ]
        return " ".join(parte.strip() for parte in partes if parte and parte.strip())

    def __str__(self) -> str:
        return self.nombre_completo
