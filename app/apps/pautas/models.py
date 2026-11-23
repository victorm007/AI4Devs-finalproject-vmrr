"""Pauta del residente: dosis y frecuencia, con vigencia (readme, sección 3.2, D6).

Es informativa: no mueve existencias. Para cambiar una pauta se cierra la vigente
(fecha_fin) y se crea otra, así se conserva el historial. Sin lógica en el modelo: las
reglas viven en Meta.constraints y en el trigger tg_pauta_validar (0002_trigger).
"""

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeBoundary, RangeOperators
from django.db import models
from django.db.models import F, Func, Q
from django.db.models.functions import Now


class RangoDeFechas(Func):
    """daterange(fecha_inicio, fecha_fin, '[]'): la vigencia, con ambos extremos incluidos."""

    function = "daterange"
    output_field = DateRangeField()


class Pauta(models.Model):
    # db_index=False: lo cubre ix_pauta_residente_inicio (sección 3.3)
    residente = models.ForeignKey(
        "entidades.Residente",
        on_delete=models.PROTECT,
        related_name="pautas",
        db_index=False,
    )
    medicamento = models.ForeignKey(
        "catalogo.Medicamento", on_delete=models.PROTECT, related_name="pautas"
    )
    dosis = models.DecimalField(
        max_digits=6, decimal_places=2, help_text="Dosis por toma: 0.5, 1, 2…"
    )
    frecuencia_horas = models.SmallIntegerField(
        help_text="Cada cuántas horas: 8, 12, 24; semanal = 168"
    )
    si_necesario = models.BooleanField(default=False, db_default=False)
    indicaciones = models.TextField(null=True, blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True, help_text="Vacía = vigente")
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pautas_registradas"
    )
    creado_en = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "pauta"
        constraints = [
            models.CheckConstraint(condition=Q(dosis__gt=0), name="ck_pauta_dosis"),
            models.CheckConstraint(
                condition=Q(frecuencia_horas__gte=1, frecuencia_horas__lte=168),
                name="ck_pauta_frecuencia",
            ),
            models.CheckConstraint(
                condition=Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=F("fecha_inicio")),
                name="ck_pauta_fechas",
            ),
            # Sin vigencias traslapadas para el mismo residente y medicamento (usa btree_gist)
            ExclusionConstraint(
                name="ex_pauta_sin_traslape",
                expressions=[
                    ("residente", RangeOperators.EQUAL),
                    ("medicamento", RangeOperators.EQUAL),
                    (
                        RangoDeFechas("fecha_inicio", "fecha_fin", RangeBoundary(True, True)),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                violation_error_message="Ya hay una pauta vigente de este medicamento para el "
                "residente en esas fechas. Cierra la anterior antes de registrar la nueva.",
            ),
        ]
        indexes = [
            # Consulta 3a: pautas abiertas (casi todas las vigentes)
            models.Index(
                fields=["residente", "medicamento"],
                condition=Q(fecha_fin__isnull=True),
                name="ix_pauta_vigente",
            ),
            # Consulta 3b: pautas de un residente, las más recientes primero
            models.Index(fields=["residente", "-fecha_inicio"], name="ix_pauta_residente_inicio"),
        ]

    def __str__(self) -> str:
        return f"{self.medicamento} · {self.dosis} cada {self.frecuencia_horas} h"
