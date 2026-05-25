from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from iibb.models.catalogos import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), default=1)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    nombre: Mapped[str] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(default=True)
    es_admin: Mapped[bool] = mapped_column(default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
