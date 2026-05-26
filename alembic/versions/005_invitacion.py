"""Agrega tabla invitacion para sistema de invitaciones por link

Revision ID: 005
Revises: 004
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "invitacion",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("usado", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("creado_en", sa.DateTime, server_default=sa.func.now()),
        sa.Column("expira_en", sa.DateTime, nullable=False),
    )
    op.create_index("ix_invitacion_token", "invitacion", ["token"])


def downgrade():
    op.drop_index("ix_invitacion_token", "invitacion")
    op.drop_table("invitacion")
