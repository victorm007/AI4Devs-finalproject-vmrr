"""Existencias y movimientos (readme, sección 3.2, D4 y D5).

Los modelos no tienen lógica: solo inventario/services.py escribe en Existencia y
Movimiento (TK-02). Las reglas también viven en la base de datos (última barrera): los CHECK
y UNIQUE aquí, y los triggers, la vista de conciliación y el REVOKE en 0004_sql.
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.indexes import BrinIndex
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now

from apps.expresiones import no_vacio


class MotivoBaja(models.Model):
    id = models.SmallAutoField(primary_key=True)
    clave = models.CharField(max_length=30, unique=True)
    descripcion = models.CharField(max_length=100)
    activo = models.BooleanField(db_default=True)

    class Meta:
        db_table = "motivo_baja"
        verbose_name = "motivo de baja"
        verbose_name_plural = "motivos de baja"

    def __str__(self) -> str:
        return self.descripcion


class Existencia(models.Model):
    # db_index=False: las cubren uq_existencia e ix_existencia_med_entidad (sección 3.3)
    entidad = models.ForeignKey(
        "entidades.Entidad", on_delete=models.PROTECT, related_name="existencias", db_index=False
    )
    medicamento = models.ForeignKey(
        "catalogo.Medicamento", on_delete=models.PROTECT, related_name="existencias", db_index=False
    )
    saldo = models.DecimalField(max_digits=10, decimal_places=2, db_default=Decimal("0"))
    actualizado_en = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "existencia"
        constraints = [
            models.UniqueConstraint(fields=["entidad", "medicamento"], name="uq_existencia"),
            models.CheckConstraint(condition=Q(saldo__gte=0), name="ck_existencia_saldo"),
        ]
        indexes = [
            models.Index(fields=["medicamento", "entidad"], name="ix_existencia_med_entidad"),
        ]


class Movimiento(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        BAJA = "BAJA", "Baja"

    class OrigenEntrada(models.TextChoices):
        FAMILIAR = "FAMILIAR", "Familiar"
        HOGAR = "HOGAR", "Hogar"
        OTRO = "OTRO", "Otro"

    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    # db_index=False en las FK que cubren los índices compuestos de la sección 3.3
    medicamento = models.ForeignKey(
        "catalogo.Medicamento", on_delete=models.PROTECT, related_name="movimientos", db_index=False
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    entidad_origen = models.ForeignKey(
        "entidades.Entidad",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="salidas",
        db_index=False,
    )
    entidad_destino = models.ForeignKey(
        "entidades.Entidad",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="llegadas",
        db_index=False,
    )
    # db_index=False: ninguna consulta de la sección 3.3 filtra por ella (ADR-0018)
    motivo_baja = models.ForeignKey(
        MotivoBaja,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos",
        db_index=False,
    )
    # null=True en textos a propósito: el CHECK por tipo distingue "no aplica" (NULL)
    origen_entrada = models.CharField(
        max_length=10, choices=OrigenEntrada.choices, null=True, blank=True
    )
    entregado_por = models.CharField(max_length=150, null=True, blank=True)
    # ForeignKey + UniqueConstraint (y no OneToOneField) para conservar el nombre
    # uq_movimiento_corrige; ese índice único ya cubre la FK
    corrige_a = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones",
        db_index=False,
    )
    nota = models.TextField(null=True, blank=True)
    # db_index=False: ninguna consulta de la sección 3.3 filtra por ella (ADR-0018)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="movimientos",
        db_index=False,
    )
    fecha_hora = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "movimiento"
        constraints = [
            # Mismo CHECK que el DDL de la sección 3.1: columnas obligatorias y prohibidas por tipo
            models.CheckConstraint(
                name="ck_movimiento_por_tipo",
                condition=(
                    (
                        Q(
                            tipo="ENTRADA",
                            entidad_origen__isnull=True,
                            entidad_destino__isnull=False,
                            motivo_baja__isnull=True,
                        )
                        & (
                            Q(corrige_a__isnull=False)
                            | Q(origen_entrada__isnull=False, entregado_por__isnull=False)
                        )
                    )
                    | (
                        Q(
                            tipo="TRANSFERENCIA",
                            entidad_origen__isnull=False,
                            entidad_destino__isnull=False,
                            motivo_baja__isnull=True,
                            origen_entrada__isnull=True,
                            entregado_por__isnull=True,
                        )
                        & ~Q(entidad_origen=F("entidad_destino"))
                    )
                    | Q(
                        tipo="BAJA",
                        entidad_origen__isnull=False,
                        entidad_destino__isnull=True,
                        motivo_baja__isnull=False,
                        origen_entrada__isnull=True,
                        entregado_por__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(condition=Q(cantidad__gt=0), name="ck_movimiento_cantidad"),
            models.CheckConstraint(
                condition=Q(origen_entrada__isnull=True)
                | Q(origen_entrada__in=["FAMILIAR", "HOGAR", "OTRO"]),
                name="ck_movimiento_origen_entrada",
            ),
            # Equivale a btrim(entregado_por) <> '' (sección 3.3), como en HB-05 a HB-07
            models.CheckConstraint(
                condition=Q(entregado_por__isnull=True) | no_vacio("entregado_por"),
                name="ck_movimiento_entregado",
            ),
            models.CheckConstraint(
                condition=~Q(corrige_a=F("id")), name="ck_movimiento_no_autocorrige"
            ),
            models.UniqueConstraint(fields=["corrige_a"], name="uq_movimiento_corrige"),
        ]
        # ix_movimiento_med_fecha va primero a propósito. Sin estadísticas (una tabla recién
        # creada, como la base de tests), PostgreSQL estima el mismo costo para ese índice y
        # para el compuesto de la entidad, y desempata a favor del creado al final. Así, las
        # consultas por entidad usan su índice compuesto también antes del primer ANALYZE
        indexes = [
            models.Index(fields=["medicamento", "fecha_hora"], name="ix_movimiento_med_fecha"),
            models.Index(
                fields=["entidad_origen", "medicamento", "fecha_hora"],
                name="ix_movimiento_origen_med_fecha",
                condition=Q(entidad_origen__isnull=False),
            ),
            models.Index(
                fields=["entidad_destino", "medicamento", "fecha_hora"],
                name="ix_movimiento_dest_med_fecha",
                condition=Q(entidad_destino__isnull=False),
            ),
            BrinIndex(fields=["fecha_hora"], name="brin_movimiento_fecha"),
        ]
