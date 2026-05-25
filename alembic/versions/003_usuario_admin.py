"""Agrega columna es_admin a usuario

Revision ID: 003
Revises: 002
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("usuario", sa.Column("es_admin", sa.Boolean(), nullable=False, server_default="0"))
    # Marcar como admin al usuario de Diego
    op.execute("UPDATE usuario SET es_admin = 1 WHERE email = 'dcasimiro@cgestudiocontable.com'")


def downgrade():
    op.drop_column("usuario", "es_admin")
