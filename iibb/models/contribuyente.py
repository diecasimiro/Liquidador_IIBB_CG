from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Date, DateTime, Numeric, UniqueConstraint, ForeignKey, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from iibb.models.catalogos import Base


class Contribuyente(Base):
    __tablename__ = "contribuyente"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), default=1)
    cuit: Mapped[str] = mapped_column(String(13), unique=True, index=True)
    razon_social: Mapped[str] = mapped_column(String(300))
    nro_inscripcion_cm: Mapped[str | None] = mapped_column(String(50))
    jurisdiccion_sede: Mapped[str | None] = mapped_column(String(3), ForeignKey("jurisdiccion.codigo"))
    naturaleza_juridica: Mapped[str | None] = mapped_column(String(200))
    cierre_ejercicio_mes: Mapped[int | None] = mapped_column(Integer)
    cierre_ejercicio_dia: Mapped[int | None] = mapped_column(Integer)
    domicilio_fiscal: Mapped[str | None] = mapped_column(String(400))
    domicilio_actividades: Mapped[str | None] = mapped_column(String(400))
    tipo_contribuyente: Mapped[str | None] = mapped_column(String(50))
    activo: Mapped[bool] = mapped_column(default=True)
    notas: Mapped[str | None] = mapped_column(String(2000))
    carpeta_drive: Mapped[str | None] = mapped_column(String(1000))
    xubio_client_id: Mapped[str | None] = mapped_column(String(200))
    xubio_secret_id: Mapped[str | None] = mapped_column(String(200))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    modificado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    jurisdicciones_inscriptas: Mapped[list["JurisdiccionInscripta"]] = relationship(
        back_populates="contribuyente", cascade="all, delete-orphan"
    )
    actividades_inscriptas: Mapped[list["ActividadInscripta"]] = relationship(
        back_populates="contribuyente", cascade="all, delete-orphan"
    )
    coeficientes: Mapped[list["CoeficienteAnual"]] = relationship(
        back_populates="contribuyente", cascade="all, delete-orphan"
    )
    alicuotas: Mapped[list["Alicuota"]] = relationship(
        back_populates="contribuyente", cascade="all, delete-orphan"
    )


class JurisdiccionInscripta(Base):
    __tablename__ = "jurisdiccion_inscripta"
    __table_args__ = (
        UniqueConstraint("contribuyente_id", "jurisdiccion_codigo", name="uq_juris_inscripta"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), default=1)
    contribuyente_id: Mapped[int] = mapped_column(ForeignKey("contribuyente.id"))
    jurisdiccion_codigo: Mapped[str] = mapped_column(String(3), ForeignKey("jurisdiccion.codigo"))
    fecha_alta: Mapped[date | None] = mapped_column(Date)
    fecha_baja: Mapped[date | None] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(default=True)

    contribuyente: Mapped["Contribuyente"] = relationship(back_populates="jurisdicciones_inscriptas")


class ActividadInscripta(Base):
    __tablename__ = "actividad_inscripta"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), default=1)
    contribuyente_id: Mapped[int] = mapped_column(ForeignKey("contribuyente.id"))
    codigo_cuacm: Mapped[str] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(String(500))
    articulo_cm: Mapped[str] = mapped_column(String(20), default="art2")
    es_principal: Mapped[bool] = mapped_column(default=False)
    fecha_alta: Mapped[date | None] = mapped_column(Date)
    fecha_baja: Mapped[date | None] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(default=True)

    contribuyente: Mapped["Contribuyente"] = relationship(back_populates="actividades_inscriptas")


class CoeficienteAnual(Base):
    __tablename__ = "coeficiente_anual"
    __table_args__ = (
        UniqueConstraint("contribuyente_id", "anio", "jurisdiccion_codigo", name="uq_coef_anual"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), default=1)
    contribuyente_id: Mapped[int] = mapped_column(ForeignKey("contribuyente.id"))
    anio: Mapped[int] = mapped_column(Integer)
    jurisdiccion_codigo: Mapped[str] = mapped_column(String(3), ForeignKey("jurisdiccion.codigo"))
    valor: Mapped[Decimal] = mapped_column(Numeric(6, 4))

    contribuyente: Mapped["Contribuyente"] = relationship(back_populates="coeficientes")


class Alicuota(Base):
    __tablename__ = "alicuota"
    __table_args__ = (
        UniqueConstraint(
            "contribuyente_id", "anio", "jurisdiccion_codigo", "codigo_actividad",
            name="uq_alicuota"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), default=1)
    contribuyente_id: Mapped[int] = mapped_column(ForeignKey("contribuyente.id"))
    anio: Mapped[int] = mapped_column(Integer)
    jurisdiccion_codigo: Mapped[str] = mapped_column(String(3), ForeignKey("jurisdiccion.codigo"))
    codigo_actividad: Mapped[str] = mapped_column(String(20))
    valor: Mapped[Decimal] = mapped_column(Numeric(8, 6))

    contribuyente: Mapped["Contribuyente"] = relationship(back_populates="alicuotas")


class ClienteReceptor(Base):
    """Cache de CUITs receptores con domicilio fiscal (para validacion de jurisdiccion)."""
    __tablename__ = "cliente_receptor"

    cuit: Mapped[str] = mapped_column(String(13), primary_key=True)
    nombre: Mapped[str | None] = mapped_column(String(300))
    domicilio: Mapped[str | None] = mapped_column(String(400))
    jurisdiccion_codigo: Mapped[str | None] = mapped_column(String(3), ForeignKey("jurisdiccion.codigo"))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
