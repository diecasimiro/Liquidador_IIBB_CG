from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Date, DateTime, Numeric, ForeignKey, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from iibb.models.catalogos import Base


class Deduccion(Base):
    __tablename__ = "deduccion"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), default=1)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo.id"))
    jurisdiccion_codigo: Mapped[str] = mapped_column(String(3), ForeignKey("jurisdiccion.codigo"))
    # retencion | percepcion | sircreb | perc_aduanera | pago_a_cuenta
    tipo: Mapped[str] = mapped_column(String(30))
    fecha: Mapped[date | None] = mapped_column(Date)
    agente_cuit: Mapped[str | None] = mapped_column(String(13))
    agente_nombre: Mapped[str | None] = mapped_column(String(300))
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    origen: Mapped[str] = mapped_column(String(20), default="manual")

    periodo: Mapped["Periodo"] = relationship(back_populates="deducciones")


class ResultadoJurisdiccion(Base):
    __tablename__ = "resultado_jurisdiccion"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), default=1)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo.id"))
    jurisdiccion_codigo: Mapped[str] = mapped_column(String(3), ForeignKey("jurisdiccion.codigo"))
    jurisdiccion_nombre: Mapped[str] = mapped_column(String(100))
    coeficiente: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    alicuota: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    base_imponible: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    impuesto_determinado: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    saf_anterior: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    retenciones: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    percepciones: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    sircreb: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    perc_aduaneras: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    pagos_a_cuenta: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_deducciones: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    monto_a_pagar: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    saldo_a_favor: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    periodo: Mapped["Periodo"] = relationship(back_populates="resultados")


# Resolve forward reference in periodo.py
from iibb.models.periodo import Periodo  # noqa: E402, F401
Periodo.deducciones  # touch to ensure relationship is registered
