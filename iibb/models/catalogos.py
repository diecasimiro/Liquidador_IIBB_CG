from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Jurisdiccion(Base):
    __tablename__ = "jurisdiccion"

    codigo: Mapped[str] = mapped_column(String(3), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    nombre_corto: Mapped[str] = mapped_column(String(50))
    activa: Mapped[bool] = mapped_column(default=True)
