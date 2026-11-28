"""Conteos físicos (readme, sección 3.2, "Conteos físicos"; mecánica en HU-03).

Sin lógica en los modelos: el conteo no ajusta existencias, y los triggers de 0002_triggers
impiden tocar un conteo cerrado o sus renglones.
"""

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now


class ConteoFisico(models.Model):
    class Estado(models.TextChoices):
        EN_PROCESO = "EN_PROCESO", "En proceso"
        CERRADO = "CERRADO", "Cerrado"

    # db_index=False: la cubre ix_conteo_entidad_periodo (sección 3.3)
    entidad = models.ForeignKey(
        "entidades.Entidad", on_delete=models.PROTECT, related_name="conteos", db_index=False
    )
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    estado = models.CharField(max_length=10, choices=Estado.choices, db_default="EN_PROCESO")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="conteos"
    )
    creado_en = models.DateTimeField(db_default=Now())
    cerrado_en = models.DateTimeField(null=True, blank=True)
    nota = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "conteo_fisico"
        verbose_name = "conteo físico"
        verbose_name_plural = "conteos físicos"
        constraints = [
            models.CheckConstraint(
                condition=Q(periodo_fin__gte=F("periodo_inicio")), name="ck_conteo_periodo"
            ),
            models.CheckConstraint(
                condition=Q(estado__in=["EN_PROCESO", "CERRADO"]), name="ck_conteo_estado"
            ),
            # (estado = 'CERRADO') = (cerrado_en IS NOT NULL), como el DDL de la sección 3.1:
            # no se pronuncia sobre un estado desconocido, que es cosa de ck_conteo_estado
            models.CheckConstraint(
                condition=Q(estado="CERRADO", cerrado_en__isnull=False)
                | (~Q(estado="CERRADO") & Q(cerrado_en__isnull=True)),
                name="ck_conteo_cierre",
            ),
        ]
        indexes = [
            models.Index(fields=["entidad", "-periodo_fin"], name="ix_conteo_entidad_periodo"),
        ]


class DetalleConteo(models.Model):
    # db_index=False: las cubren uq_detalle_conteo e ix_detalle_medicamento_conteo
    conteo = models.ForeignKey(
        ConteoFisico, on_delete=models.PROTECT, related_name="detalles", db_index=False
    )
    medicamento = models.ForeignKey(
        "catalogo.Medicamento",
        on_delete=models.PROTECT,
        related_name="detalles_conteo",
        db_index=False,
    )
    cantidad_fisica = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_sistema = models.DecimalField(max_digits=10, decimal_places=2)  # foto del saldo
    # La calcula PostgreSQL: nunca se escribe a mano
    diferencia = models.GeneratedField(
        expression=F("cantidad_fisica") - F("cantidad_sistema"),
        output_field=models.DecimalField(max_digits=10, decimal_places=2),
        db_persist=True,
    )

    class Meta:
        db_table = "detalle_conteo"
        verbose_name = "renglón de conteo"
        verbose_name_plural = "renglones de conteo"
        constraints = [
            models.UniqueConstraint(fields=["conteo", "medicamento"], name="uq_detalle_conteo"),
            models.CheckConstraint(condition=Q(cantidad_fisica__gte=0), name="ck_detalle_fisica"),
            models.CheckConstraint(condition=Q(cantidad_sistema__gte=0), name="ck_detalle_sistema"),
        ]
        indexes = [
            models.Index(
                fields=["medicamento", "conteo"],
                name="ix_detalle_medicamento_conteo",
                include=["cantidad_fisica", "cantidad_sistema", "diferencia"],
            ),
            models.Index(
                fields=["medicamento"],
                name="ix_detalle_con_diferencia",
                condition=~Q(diferencia=0),
            ),
        ]
