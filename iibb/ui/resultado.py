"""
Pantalla 'Resultado' de la liquidacion CM03.
Muestra KPIs, tabla detallada por jurisdiccion y boton de exportacion.
"""
import streamlit as st
from iibb.calculo.cm03 import LiquidacionCM03, fmt_money
from iibb.exporters.excel_cm03 import exportar_excel_cm03
from iibb.db import get_session
from iibb.service.liquidacion import cerrar_periodo, reabrir_periodo, esta_cerrado
from iibb.service.contribuyente import obtener_contribuyente
from iibb.exporters.drive_helper import guardar_en_drive, DriveNoConfigurado, DriveNoAccesible

MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

FILAS = [
    ("coeficiente",          "Coeficiente"),
    ("alicuota",             "Alícuota"),
    ("base_imponible",       "Base Imponible"),
    ("impuesto_determinado", "Impuesto Determinado"),
    ("saf_anterior",         "(−) SAF Período Anterior"),
    ("retenciones",          "(−) Retenciones"),
    ("percepciones",         "(−) Percepciones"),
    ("sircreb",              "(−) SIRCREB"),
    ("perc_aduaneras",       "(−) Perc. Aduaneras"),
    ("pagos_a_cuenta",       "(−) Pagos a Cuenta"),
    ("total_deducciones",    "Total Deducciones"),
    ("monto_a_pagar",        "MONTO A PAGAR ✅"),
    ("saldo_a_favor",        "Saldo a Favor →"),
]


def render_resultado():
    liq: LiquidacionCM03 | None = st.session_state.get("liquidacion")
    if not liq:
        st.error("No hay liquidación calculada. Volvé a la pantalla anterior.")
        if st.button("← Volver"):
            st.session_state["pantalla"] = "procesar"
            st.rerun()
        return

    comprobantes = st.session_state.get("comprobantes", [])

    # --- Header ---
    col_back, col_title = st.columns([1, 6])
    with col_back:
        if st.button("← Volver"):
            st.session_state["pantalla"] = "procesar"
            st.rerun()
    with col_title:
        mes_str = MESES.get(liq.mes, str(liq.mes))
        st.title(f"Resultado CM03 — {mes_str} {liq.anio}")
        st.markdown(f"*{liq.contribuyente_razon} — CUIT: {liq.contribuyente_cuit}*")

    st.markdown("---")

    # --- KPIs ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Base imponible IIBB", fmt_money(liq.ingresos_totales))
    col2.metric("Comprobantes importados", len(comprobantes))
    col3.metric("TOTAL A PAGAR", fmt_money(liq.monto_total_a_pagar))

    # --- Desglose informativo de ingresos ---
    hay_info = (
        liq.exportaciones > 0
        or liq.bienes_uso_no_gravados > 0
        or liq.iva_total > 0
        or liq.ingresos_brutos != liq.ingresos_totales
    )
    if hay_info:
        with st.expander("Desglose de ingresos (informativo)", expanded=True):
            filas = [
                ("Neto gravado ARCA", fmt_money(liq.ingresos_brutos)),
            ]
            if liq.exportaciones > 0:
                filas.append(("(-) Exportaciones (Fac./NC/ND E)", fmt_money(liq.exportaciones)))
            if liq.bienes_uso_no_gravados > 0:
                filas.append(("(-) Bs. de uso / No gravados y Exentos", fmt_money(liq.bienes_uso_no_gravados)))
            filas.append(("**= Base imponible IIBB**", f"**{fmt_money(liq.ingresos_totales)}**"))
            if liq.iva_total > 0:
                filas.append(("IVA declarado (informativo)", fmt_money(liq.iva_total)))
            tabla_md = "| Concepto | Importe |\n|---|---|\n"
            tabla_md += "\n".join(f"| {c} | {v} |" for c, v in filas)
            st.markdown(tabla_md)

    st.markdown("---")

    # --- Tabla por jurisdicción ---
    st.subheader("Detalle por jurisdicción")

    n_juris = len(liq.resultados)
    juris_labels = [f"{r.codigo} — {r.nombre}" for r in liq.resultados]

    # Construimos la tabla como lista de listas
    import pandas as pd
    from decimal import Decimal

    table_data = {}
    for attr, label in FILAS:
        row_vals = {}
        for r in liq.resultados:
            val = getattr(r, attr)
            if attr == "coeficiente":
                row_vals[f"{r.codigo} {r.nombre}"] = f"{float(val):.4f}"
            elif attr == "alicuota":
                row_vals[f"{r.codigo} {r.nombre}"] = f"{float(val)*100:.2f}%"
            else:
                row_vals[f"{r.codigo} {r.nombre}"] = fmt_money(val)
        table_data[label] = row_vals

    df = pd.DataFrame(table_data).T
    df.index.name = "Concepto"

    # Resaltar fila MONTO A PAGAR
    def highlight_pagar(row):
        if "MONTO A PAGAR" in row.name:
            return ["background-color: #375623; color: white; font-weight: bold"] * len(row)
        if "Total Deducciones" in row.name:
            return ["background-color: #1F4E79; color: white; font-weight: bold"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df.style.apply(highlight_pagar, axis=1),
        use_container_width=True,
        height=520,
    )

    st.markdown("---")

    # --- Acciones ---
    contrib_id = st.session_state.get("contribuyente_id")

    # Consultar la BD para estado del período y carpeta Drive
    _sess = get_session()
    try:
        periodo_cerrado = esta_cerrado(_sess, contrib_id, liq.anio, liq.mes)
        contrib_obj = obtener_contribuyente(_sess, contrib_id)
        carpeta_drive = contrib_obj.carpeta_drive if contrib_obj else None
    finally:
        _sess.close()

    mes_str = MESES.get(liq.mes, str(liq.mes))
    nombre_archivo = f"CM03_{liq.contribuyente_cuit}_{liq.anio}_{liq.mes:02d}.xlsx"

    col_exp, col_estado, col_info = st.columns([2, 2, 3])

    with col_exp:
        with st.popover("📥 Exportar", use_container_width=True):
            st.markdown("**Elegí el destino:**")

            # Opción 1: Descarga directa al navegador
            try:
                import tempfile
                from pathlib import Path as _Path
                with tempfile.TemporaryDirectory() as _tmp:
                    _ruta = _Path(_tmp) / nombre_archivo
                    exportar_excel_cm03(liq, destino=_ruta)
                    _data = _ruta.read_bytes()
                st.download_button(
                    label="💾 Exportar a Excel (descarga)",
                    data=_data,
                    file_name=nombre_archivo,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Error al generar el Excel: {e}")

            st.markdown("---")

            # Opción 2: Guardar directo en carpeta Drive
            if carpeta_drive:
                st.caption(f"📁 `{carpeta_drive}`")
            else:
                st.caption("📁 Sin carpeta Drive configurada")
            if st.button("📁 Exportar al Drive", use_container_width=True,
                         disabled=not carpeta_drive, key="btn_drive_cm03"):
                try:
                    import tempfile
                    from pathlib import Path as _Path2
                    with tempfile.TemporaryDirectory() as _tmp2:
                        _ruta2 = _Path2(_tmp2) / nombre_archivo
                        exportar_excel_cm03(liq, destino=_ruta2)
                        destino_final = guardar_en_drive(_ruta2, carpeta_drive, nombre_archivo)
                    st.success(f"✅ Guardado en Drive: `{destino_final}`")
                except (DriveNoConfigurado, DriveNoAccesible) as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Error inesperado: {e}")

    with col_estado:
        if periodo_cerrado:
            st.success(f"🔒 Cerrado — {mes_str} {liq.anio}")
            if st.button("🔓 Reabrir período", use_container_width=True,
                         key="btn_reabrir"):
                st.session_state["confirmar_reabrir"] = True
                st.rerun()
        else:
            if st.button("🔒 Cerrar DDJJ", type="secondary", use_container_width=True,
                         key="btn_cerrar"):
                st.session_state["confirmar_cierre"] = True
                st.rerun()

    with col_info:
        if periodo_cerrado:
            st.caption("El período está cerrado y figura en el Resumen Anual. "
                       "Reabrilo si necesitás corregir algo.")
        else:
            st.caption("Cerrá la DDJJ para que quede registrada y aparezca en el Resumen Anual.")

    # ── Confirmación de cierre ─────────────────────────────────────────────────
    if st.session_state.get("confirmar_cierre"):
        st.warning(
            f"¿Confirmás el cierre de la DDJJ **{mes_str} {liq.anio}** "
            f"para **{liq.contribuyente_razon}**?  \n"
            "Una vez cerrada queda registrada en la base de datos."
        )
        col_si, col_no, _ = st.columns([1, 1, 4])
        with col_si:
            if st.button("Sí, cerrar", type="primary", key="btn_si_cerrar"):
                session = get_session()
                try:
                    cerrar_periodo(session, contrib_id, liq)
                    session.commit()
                    st.session_state.pop("confirmar_cierre", None)
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Error al cerrar: {e}")
                finally:
                    session.close()
        with col_no:
            if st.button("Cancelar", key="btn_no_cerrar"):
                st.session_state.pop("confirmar_cierre", None)
                st.rerun()

    # ── Confirmación de reapertura ─────────────────────────────────────────────
    if st.session_state.get("confirmar_reabrir"):
        st.warning(
            f"¿Confirmás la reapertura de **{mes_str} {liq.anio}** "
            f"para **{liq.contribuyente_razon}**?  \n"
            "El período quedará en estado abierto y dejará de figurar en el Resumen Anual "
            "hasta que lo vuelvas a cerrar."
        )
        col_si, col_no, _ = st.columns([1, 1, 4])
        with col_si:
            if st.button("Sí, reabrir", type="primary", key="btn_si_reabrir"):
                session = get_session()
                try:
                    reabrir_periodo(session, contrib_id, liq.anio, liq.mes)
                    session.commit()
                    st.session_state.pop("confirmar_reabrir", None)
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Error al reabrir: {e}")
                finally:
                    session.close()
        with col_no:
            if st.button("Cancelar", key="btn_no_reabrir"):
                st.session_state.pop("confirmar_reabrir", None)
                st.rerun()
