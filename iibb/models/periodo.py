from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Date, DateTime, Numeric, UniqueConstraint, ForeignKey, func, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from iibb.models.catalogos import Base


class Periodo(Base):
    __tablename__ = "periodo"
    __table_args__ = (
        UniqueConstraint(
            "contribuyente_id", "formulario", "anio", "mes", "secuencia",
            name="uq_periodo"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), default=1)
    contribuyente_id: Mapped[int] = mapped_column(ForeignKey("contribuyente.id"))
    formulario: Mapped[str] = mapped_column(String(10), default="CM03")
    anio: Mapped[int] = mapped_column(Integer)
    mes: Mapped[int] = mapped_column(SmallInteger)
    secuencia: Mapped[int] = mapped_column(SmallInteger, default=0)
    estado: Mapped[str] = mapped_column(String(20), default="borrador")

    # Ingresos del mes
    ingresos_gravados: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    ingresos_no_gravados: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    ingresos_exentos: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    ingresos_exportaciones: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    ingresos_venta_bienes_uso: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    iva_debito: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    presentado_en: Mapped[datetime | None] = mapped_column(DateTime)

    comprobantes: Mapped[list["ComprobanteEmitido"]] = relationship(
        back_populates="periodo", cascade="all, delete-orphan"
    )
    deducciones: Mapped[list["Deduccion"]] = relationship(
        back_populates="periodo", cascade="all, delete-orphan"
    )
    saldos_a_favor_anteriores: Mapped[list["SaldoAFavorAnterior"]] = relationship(
        back_populates="periodo", cascade="all, delete-orphan"
    )
    resultados: Mapped[list["ResultadoJurisdiccion"]] = relationship(
        back_populates="periodo", cascade="all, delete-orphan"
    )


class ComprobanteEmitido(Base):
    __tablename__ = "comprobante_emitido"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), default=1)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo.id"))
    fecha: Mapped[date | None] = mapped_column(Date)
    tipo: Mapped[str | None] = mapped_column(String(100))
    punto_venta: Mapped[int | None] = mapped_column(Integer)
    numero: Mapped[int | None] = mapped_column(Integer)
    receptor_cuit: Mapped[str | None] = mapped_column(String(13))
    receptor_nombre: Mapped[str | None] = mapped_column(String(300))
    neto_gravado: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    neto_no_gravado: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    op_exentas: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    iva: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    signo: Mapped[int] = mapped_column(SmallInteger, default=1)

    periodo: Mapped["Periodo"] = relationship(back_populates="comprobantes")


class SaldoAFavorAnterior(Base):
    __tablename__ = "saldo_a_favor_anterior"
    __table_args__ = (
        UniqueConstraint("periodo_id", "jurisdiccion_codigo", name="uq_saf"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), default=1)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo.id"))
    jurisdiccion_codigo: Mapped[str] = mapped_column(String(3), ForeignKey("jurisdiccion.codigo"))
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    periodo: Mapped["Periodo"] = relationship(back_populates="saldos_a_favor_anteriores")


# Import here to avoid circular at module level
from iibb.models.deduccion import Deduccion, ResultadoJurisdiccion  # noqa: E402, F401
