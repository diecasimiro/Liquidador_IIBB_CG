"""Agrega carpeta_drive a contribuyente

Revision ID: 004
Revises: 003
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("contribuyente", sa.Column("carpeta_drive", sa.String(1000), nullable=True))


def downgrade():
    op.drop_column("contribuyente", "carpeta_drive")
