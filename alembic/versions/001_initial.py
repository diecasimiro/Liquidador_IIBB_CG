"""Migracion inicial - todas las tablas

Revision ID: 001
Revises:
Create Date: 2026-05-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("activo", sa.Boolean, nullable=False, default=True),
        sa.Column("creado_en", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "jurisdiccion",
        sa.Column("codigo", sa.String(3), primary_key=True),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("nombre_corto", sa.String(50), nullable=False),
        sa.Column("activa", sa.Boolean, nullable=False, default=True),
    )

    op.create_table(
        "contribuyente",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=False, default=1),
        sa.Column("cuit", sa.String(13), nullable=False, unique=True, index=True),
        sa.Column("razon_social", sa.String(300), nullable=False),
        sa.Column("nro_inscripcion_cm", sa.String(50), nullable=True),
        sa.Column("jurisdiccion_sede", sa.String(3), sa.ForeignKey("jurisdiccion.codigo"), nullable=True),
        sa.Column("naturaleza_juridica", sa.String(200), nullable=True),
        sa.Column("cierre_ejercicio_mes", sa.Integer, nullable=True),
        sa.Column("cierre_ejercicio_dia", sa.Integer, nullable=True),
        sa.Column("domicilio_fiscal", sa.String(400), nullable=True),
        sa.Column("domicilio_actividades", sa.String(400), nullable=True),
        sa.Column("tipo_contribuyente", sa.String(50), nullable=True),
        sa.Column("activo", sa.Boolean, nullable=False, default=True),
        sa.Column("notas", sa.String(2000), nullable=True),
        sa.Column("creado_en", sa.DateTime, server_default=sa.func.now()),
        sa.Column("modificado_en", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "jurisdiccion_inscripta",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=False, default=1),
        sa.Column("contribuyente_id", sa.Integer, sa.ForeignKey("contribuyente.id"), nullable=False),
        sa.Column("jurisdiccion_codigo", sa.String(3), sa.ForeignKey("jurisdiccion.codigo"), nullable=False),
        sa.Column("fecha_alta", sa.Date, nullable=True),
        sa.Column("fecha_baja", sa.Date, nullable=True),
        sa.Column("activa", sa.Boolean, nullable=False, default=True),
        sa.UniqueConstraint("contribuyente_id", "jurisdiccion_codigo", name="uq_juris_inscripta"),
    )

    op.create_table(
        "actividad_inscripta",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=False, default=1),
        sa.Column("contribuyente_id", sa.Integer, sa.ForeignKey("contribuyente.id"), nullable=False),
        sa.Column("codigo_cuacm", sa.String(20), nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=False),
        sa.Column("articulo_cm", sa.String(20), nullable=False, default="art2"),
        sa.Column("es_principal", sa.Boolean, nullable=False, default=False),
        sa.Column("fecha_alta", sa.Date, nullable=True),
        sa.Column("fecha_baja", sa.Date, nullable=True),
        sa.Column("activa", sa.Boolean, nullable=False, default=True),
    )

    op.create_table(
        "coeficiente_anual",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=False, default=1),
        sa.Column("contribuyente_id", sa.Integer, sa.ForeignKey("contribuyente.id"), nullable=False),
        sa.Column("anio", sa.Integer, nullable=False),
        sa.Column("jurisdiccion_codigo", sa.String(3), sa.ForeignKey("jurisdiccion.codigo"), nullable=False),
        sa.Column("valor", sa.Numeric(6, 4), nullable=False),
        sa.UniqueConstraint("contribuyente_id", "anio", "jurisdiccion_codigo", name="uq_coef_anual"),
    )

    op.create_table(
        "alicuota",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=False, default=1),
        sa.Column("contribuyente_id", sa.Integer, sa.ForeignKey("contribuyente.id"), nullable=False),
        sa.Column("anio", sa.Integer, nullable=False),
        sa.Column("jurisdiccion_codigo", sa.String(3), sa.ForeignKey("jurisdiccion.codigo"), nullable=False),
        sa.Column("codigo_actividad", sa.String(20), nullable=False),
        sa.Column("valor", sa.Numeric(8, 6), nullable=False),
        sa.UniqueConstraint(
            "contribuyente_id", "anio", "jurisdiccion_codigo", "codigo_actividad", name="uq_alicuota"
        ),
    )

    op.create_table(
        "cliente_receptor",
        sa.Column("cuit", sa.String(13), primary_key=True),
        sa.Column("nombre", sa.String(300), nullable=True),
        sa.Column("domicilio", sa.String(400), nullable=True),
        sa.Column("jurisdiccion_codigo", sa.String(3), sa.ForeignKey("jurisdiccion.codigo"), nullable=True),
        sa.Column("actualizado_en", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "periodo",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=False, default=1),
        sa.Column("contribuyente_id", sa.Integer, sa.ForeignKey("contribuyente.id"), nullable=False),
        sa.Column("formulario", sa.String(10), nullable=False, default="CM03"),
        sa.Column("anio", sa.Integer, nullable=False),
        sa.Column("mes", sa.SmallInteger, nullable=False),
        sa.Column("secuencia", sa.SmallInteger, nullable=False, default=0),
        sa.Column("estado", sa.String(20), nullable=False, default="borrador"),
        sa.Column("ingresos_gravados", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("ingresos_no_gravados", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("ingresos_exentos", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("ingresos_exportaciones", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("ingresos_venta_bienes_uso", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("iva_debito", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("creado_en", sa.DateTime, server_default=sa.func.now()),
        sa.Column("presentado_en", sa.DateTime, nullable=True),
        sa.UniqueConstraint(
            "contribuyente_id", "formulario", "anio", "mes", "secuencia", name="uq_periodo"
        ),
    )

    op.create_table(
        "comprobante_emitido",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=False, default=1),
        sa.Column("periodo_id", sa.Integer, sa.ForeignKey("periodo.id"), nullable=False),
        sa.Column("fecha", sa.Date, nullable=True),
        sa.Column("tipo", sa.String(100), nullable=True),
        sa.Column("punto_venta", sa.Integer, nullable=True),
        sa.Column("numero", sa.Integer, nullable=True),
        sa.Column("receptor_cuit", sa.String(13), nullable=True),
        sa.Column("receptor_nombre", sa.String(300), nullable=True),
        sa.Column("neto_gravado", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("neto_no_gravado", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("op_exentas", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("iva", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("total", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("signo", sa.SmallInteger, nullable=False, default=1),
    )

    op.create_table(
        "saldo_a_favor_anterior",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=False, default=1),
        sa.Column("periodo_id", sa.Integer, sa.ForeignKey("periodo.id"), nullable=False),
        sa.Column("jurisdiccion_codigo", sa.String(3), sa.ForeignKey("jurisdiccion.codigo"), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False, default=0),
        sa.UniqueConstraint("periodo_id", "jurisdiccion_codigo", name="uq_saf"),
    )

    op.create_table(
        "deduccion",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=False, default=1),
        sa.Column("periodo_id", sa.Integer, sa.ForeignKey("periodo.id"), nullable=False),
        sa.Column("jurisdiccion_codigo", sa.String(3), sa.ForeignKey("jurisdiccion.codigo"), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("fecha", sa.Date, nullable=True),
        sa.Column("agente_cuit", sa.String(13), nullable=True),
        sa.Column("agente_nombre", sa.String(300), nullable=True),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("origen", sa.String(20), nullable=False, default="manual"),
    )

    op.create_table(
        "resultado_jurisdiccion",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=False, default=1),
        sa.Column("periodo_id", sa.Integer, sa.ForeignKey("periodo.id"), nullable=False),
        sa.Column("jurisdiccion_codigo", sa.String(3), sa.ForeignKey("jurisdiccion.codigo"), nullable=False),
        sa.Column("jurisdiccion_nombre", sa.String(100), nullable=False),
        sa.Column("coeficiente", sa.Numeric(6, 4), nullable=False),
        sa.Column("alicuota", sa.Numeric(8, 6), nullable=False),
        sa.Column("base_imponible", sa.Numeric(18, 2), nullable=False),
        sa.Column("impuesto_determinado", sa.Numeric(18, 2), nullable=False),
        sa.Column("saf_anterior", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("retenciones", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("percepciones", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("sircreb", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("perc_aduaneras", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("pagos_a_cuenta", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("total_deducciones", sa.Numeric(18, 2), nullable=False),
        sa.Column("monto_a_pagar", sa.Numeric(18, 2), nullable=False),
        sa.Column("saldo_a_favor", sa.Numeric(18, 2), nullable=False, default=0),
    )


def downgrade() -> None:
    op.drop_table("resultado_jurisdiccion")
    op.drop_table("deduccion")
    op.drop_table("saldo_a_favor_anterior")
    op.drop_table("comprobante_emitido")
    op.drop_table("periodo")
    op.drop_table("cliente_receptor")
    op.drop_table("alicuota")
    op.drop_table("coeficiente_anual")
    op.drop_table("actividad_inscripta")
    op.drop_table("jurisdiccion_inscripta")
    op.drop_table("contribuyente")
    op.drop_table("jurisdiccion")
    op.drop_table("tenant")
