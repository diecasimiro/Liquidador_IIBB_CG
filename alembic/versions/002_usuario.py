"""Agregar tabla usuario

Revision ID: 002
Revises: 001
Create Date: 2026-05-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=False, default=1),
        sa.Column("email", sa.String(200), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, default=True),
        sa.Column("creado_en", sa.DateTime, server_default=sa.func.now()),
        sa.Column("ultimo_acceso", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("usuario")
