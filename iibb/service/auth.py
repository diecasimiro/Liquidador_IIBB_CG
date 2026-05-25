"""
Autenticación de usuarios. Usa PBKDF2-HMAC-SHA256 (built-in de Python, sin deps extra).
"""
import hashlib
import hmac
import os
from datetime import datetime
from sqlalchemy.orm import Session
from iibb.models.usuario import Usuario


def _hash_password(password: str, salt: bytes | None = None) -> str:
    """Devuelve 'salt_hex:hash_hex' listo para guardar en BD."""
    if salt is None:
        salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return f"{salt.hex()}:{key.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    """Verifica la contraseña contra el hash almacenado."""
    try:
        salt_hex, key_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


def crear_usuario(
    session: Session,
    email: str,
    password: str,
    nombre: str,
    tenant_id: int = 1,
) -> Usuario:
    existente = session.query(Usuario).filter_by(email=email.lower().strip()).first()
    if existente:
        raise ValueError(f"Ya existe un usuario con el email {email}.")
    u = Usuario(
        tenant_id=tenant_id,
        email=email.lower().strip(),
        password_hash=_hash_password(password),
        nombre=nombre,
        activo=True,
    )
    session.add(u)
    session.flush()
    return u


def cambiar_password(session: Session, usuario_id: int, nueva_password: str) -> None:
    u = session.get(Usuario, usuario_id)
    if not u:
        raise ValueError("Usuario no encontrado.")
    u.password_hash = _hash_password(nueva_password)
    session.flush()


def autenticar(session: Session, email: str, password: str) -> Usuario | None:
    """Retorna el Usuario si las credenciales son válidas, None si no."""
    u = session.query(Usuario).filter_by(
        email=email.lower().strip(), activo=True
    ).first()
    if not u:
        return None
    if not _verify_password(password, u.password_hash):
        return None
    u.ultimo_acceso = datetime.now()
    session.flush()
    return u
