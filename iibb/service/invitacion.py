import os
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from iibb.models.invitacion import Invitacion
from iibb.models.usuario import Usuario
from iibb.service.auth import crear_usuario


def _base_url() -> str:
    return os.environ.get("APP_URL", "http://localhost:8501").rstrip("/")


def crear_invitacion(
    session: Session,
    email: str,
    tenant_id: int = 1,
    dias: int = 7,
) -> Invitacion:
    token = secrets.token_urlsafe(32)
    inv = Invitacion(
        tenant_id=tenant_id,
        token=token,
        email=email.lower().strip(),
        usado=False,
        expira_en=datetime.now() + timedelta(days=dias),
    )
    session.add(inv)
    session.flush()
    return inv


def url_invitacion(token: str) -> str:
    return f"{_base_url()}/?invite={token}"


def validar_token(session: Session, token: str) -> Invitacion | None:
    inv = session.query(Invitacion).filter_by(token=token).first()
    if inv is None or inv.usado or inv.expira_en < datetime.now():
        return None
    return inv


def canjear_invitacion(
    session: Session,
    token: str,
    nombre: str,
    password: str,
) -> Usuario:
    inv = validar_token(session, token)
    if inv is None:
        raise ValueError("El link de invitación no es válido o ya fue utilizado.")
    usuario = crear_usuario(session, email=inv.email, password=password, nombre=nombre, tenant_id=inv.tenant_id)
    inv.usado = True
    session.flush()
    return usuario
