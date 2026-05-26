"""Agrega credenciales Xubio a contribuyente

Revision ID: 006
Revises: 005
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("contribuyente", sa.Column("xubio_client_id", sa.String(200), nullable=True))
    op.add_column("contribuyente", sa.Column("xubio_secret_id", sa.String(200), nullable=True))


def downgrade():
    op.drop_column("contribuyente", "xubio_secret_id")
    op.drop_column("contribuyente", "xubio_client_id")
