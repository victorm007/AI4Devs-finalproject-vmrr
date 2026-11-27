"""Catálogo de medicamentos (readme, sección 3.2, D2).

Los modelos no tienen lógica: las reglas viven en Meta.constraints (que Django valida en
los formularios del panel) y en la base de datos, que es la última barrera.
"""

from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now

from apps.expresiones import no_vacio, sin_acentos


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


class PrincipioActivo(models.Model):
    """Sustancia activa: paracetamol, losartán..."""

    nombre = models.CharField(max_length=150)
    creado_en = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "principio_activo"
        verbose_name = "principio activo"
        verbose_name_plural = "principios activos"
        constraints = [
            # Índice único por expresión: "Paracetamol" = "paracetamol" = "PARACETAMOL"
            models.UniqueConstraint(
                sin_acentos("nombre"),
                name="uq_principio_activo_nombre",
                violation_error_message="Ya existe ese principio activo "
                "(sin distinguir mayúsculas ni acentos).",
            ),
            models.CheckConstraint(condition=no_vacio("nombre"), name="ck_principio_activo_nombre"),
        ]
        indexes = [
            GinIndex(
                OpClass(sin_acentos("nombre"), name="gin_trgm_ops"),
                name="ix_principio_activo_trgm",
            ),
        ]

    def __str__(self) -> str:
        return self.nombre


class Medicamento(models.Model):
    """Producto del catálogo. La baja es lógica (activo = False)."""

    class Tipo(models.TextChoices):
        GENERICO = "GENERICO", "Genérico"
        ORIGINAL = "ORIGINAL", "Original"

    nombre_comercial = models.CharField(max_length=150)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    presentacion = models.ForeignKey(
        Presentacion, on_delete=models.PROTECT, related_name="medicamentos"
    )
    concentracion = models.CharField(max_length=60, help_text="Ejemplo: 500 mg, 50 mg / 12.5 mg")
    activo = models.BooleanField(default=True, db_default=True)
    creado_en = models.DateTimeField(db_default=Now(), editable=False)
    actualizado_en = models.DateTimeField(auto_now=True, db_default=Now())
    principios_activos = models.ManyToManyField(
        PrincipioActivo, through="MedicamentoPrincipioActivo", related_name="medicamentos"
    )

    class Meta:
        db_table = "medicamento"
        constraints = [
            # Sin duplicados de nombre + presentación + concentración, sin distinguir
            # mayúsculas ni acentos. Aplica también a los inactivos: se reactivan.
            models.UniqueConstraint(
                sin_acentos("nombre_comercial"),
                "presentacion",
                sin_acentos("concentracion"),
                name="uq_medicamento_nombre_pres_conc",
                violation_error_message="Ya existe un medicamento con ese nombre, presentación "
                "y concentración. Si está dado de baja, reactívalo.",
            ),
            models.CheckConstraint(
                condition=Q(tipo__in=["GENERICO", "ORIGINAL"]), name="ck_medicamento_tipo"
            ),
            models.CheckConstraint(
                condition=no_vacio("nombre_comercial") & no_vacio("concentracion"),
                name="ck_medicamento_textos",
            ),
        ]
        indexes = [
            # Búsqueda parcial por nombre, solo en el catálogo vigente (consulta 1)
            GinIndex(
                OpClass(sin_acentos("nombre_comercial"), name="gin_trgm_ops"),
                name="ix_medicamento_nombre_trgm",
                condition=Q(activo=True),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nombre_comercial} {self.concentracion}"


class MedicamentoPrincipioActivo(models.Model):
    """Tabla puente: un medicamento tiene uno o más principios activos."""

    # db_index=False: ya los cubren el UNIQUE y ix_mpa_principio_medicamento (sección 3.3)
    medicamento = models.ForeignKey(Medicamento, on_delete=models.PROTECT, db_index=False)
    principio_activo = models.ForeignKey(PrincipioActivo, on_delete=models.PROTECT, db_index=False)

    class Meta:
        db_table = "medicamento_principio_activo"
        verbose_name = "principio activo del medicamento"
        verbose_name_plural = "principios activos del medicamento"
        constraints = [
            models.UniqueConstraint(
                fields=["medicamento", "principio_activo"], name="uq_mpa_medicamento_principio"
            ),
        ]
        indexes = [
            models.Index(
                fields=["principio_activo", "medicamento"], name="ix_mpa_principio_medicamento"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.medicamento} · {self.principio_activo}"
