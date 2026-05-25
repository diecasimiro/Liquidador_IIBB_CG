"""
Pantalla de Resumen Anual CM03.
"""
import tempfile
from pathlib import Path

import streamlit as st

from iibb.db import get_session
from iibb.service.contribuyente import obtener_contribuyente
from iibb.service.resumen_anual import obtener_resumen_anual
from iibb.exporters.excel_resumen_anual import exportar_excel_resumen_anual, MESES
from iibb.exporters.drive_helper import guardar_en_drive, DriveNoConfigurado, DriveNoAccesible

COLS = [
    ("Base Imponible",        "base_imponible"),
    ("Impuesto Det.",         "impuesto_determinado"),
    ("Retenciones",           "retenciones"),
    ("Percepciones",          "percepciones"),
    ("Perc. Aduaneras",       "perc_aduaneras"),
    ("SIRCREB",               "sircreb"),
    ("Saldo a Favor (Dic.)",  "saldo_a_favor_dic"),
    ("IIBB a Pagar",          "iibb_a_pagar"),
]


def _fmt(v) -> str:
    return f"$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_resumen_anual():
    contrib_id = st.session_state.get("contribuyente_id")
    if not contrib_id:
        st.error("No se seleccionó ningún contribuyente.")
        return

    session = get_session()
    try:
        contrib = obtener_contribuyente(session, contrib_id)
        if not contrib:
            st.error("Contribuyente no encontrado.")
            return
        razon_social = contrib.razon_social
        cuit = contrib.cuit
        carpeta_drive = contrib.carpeta_drive
    finally:
        session.close()

    # ── Header ────────────────────────────────────────────────────────────────
    col_back, col_title = st.columns([1, 6])
    with col_back:
        if st.button("← Volver"):
            st.session_state["pantalla"] = "procesar"
            st.rerun()
    with col_title:
        st.title(f"Resumen Anual — {razon_social}")
        st.caption(f"CUIT: {cuit}")

    st.markdown("---")

    # ── Selector de año ───────────────────────────────────────────────────────
    col_anio, col_btn, _ = st.columns([2, 2, 4])
    with col_anio:
        anio = st.selectbox(
            "Año a consultar",
            options=list(range(2024, 2032)),
            index=list(range(2024, 2032)).index(2026),
            key="resumen_anio",
        )

    # ── Cargar datos ──────────────────────────────────────────────────────────
    session = get_session()
    try:
        resumen = obtener_resumen_anual(session, contrib_id, anio)
    finally:
        session.close()

    if not resumen.filas:
        st.warning(
            f"No hay períodos liquidados para {razon_social} en {anio}. "
            "Procesá al menos un mes desde la pantalla CM03."
        )
        return

    meses_str = ", ".join(MESES.get(m, str(m)) for m in resumen.meses_liquidados)
    st.info(f"**Meses liquidados:** {meses_str}")

    # ── Tabla de resumen ──────────────────────────────────────────────────────
    st.subheader(f"Consolidado anual {anio} — por jurisdicción")

    import pandas as pd
    from decimal import Decimal

    rows = []
    for f in resumen.filas:
        rows.append({
            "Jurisdicción": f"{f.codigo} — {f.nombre}",
            "Base Imponible": float(f.base_imponible),
            "Impuesto Det.": float(f.impuesto_determinado),
            "Retenciones": float(f.retenciones),
            "Percepciones": float(f.percepciones),
            "Perc. Aduaneras": float(f.perc_aduaneras),
            "SIRCREB": float(f.sircreb),
            "Saldo a Favor (Dic.)": float(f.saldo_a_favor_dic),
            "IIBB a Pagar": float(f.iibb_a_pagar),
        })

    # Fila de totales
    totales = {"Jurisdicción": "TOTAL"}
    for col_label, attr in COLS:
        totales[col_label] = sum(float(getattr(f, attr)) for f in resumen.filas)

    df = pd.DataFrame(rows)
    df_tot = pd.DataFrame([totales])
    df_full = pd.concat([df, df_tot], ignore_index=True)

    money_cols = [c for c, _ in COLS]

    def highlight_total(row):
        if row["Jurisdicción"] == "TOTAL":
            return ["background-color: #1F4E79; color: white; font-weight: bold"] * len(row)
        return [""] * len(row)

    fmt_dict = {c: "${:,.2f}" for c in money_cols}

    st.dataframe(
        df_full.style
            .apply(highlight_total, axis=1)
            .format(fmt_dict),
        use_container_width=True,
        height=min(60 + 35 * (len(resumen.filas) + 2), 600),
    )

    st.markdown("---")

    # ── Exportar ──────────────────────────────────────────────────────────────
    st.subheader("Exportar")
    nombre_archivo = f"resumen_anual_{cuit}_{anio}.xlsx"

    with st.popover("📥 Exportar", use_container_width=False):
        st.markdown("**Elegí el destino:**")

        # Opción 1: Descarga directa
        with tempfile.TemporaryDirectory() as tmp:
            destino_tmp = Path(tmp) / nombre_archivo
            exportar_excel_resumen_anual(resumen, razon_social, cuit, destino_tmp)
            data = destino_tmp.read_bytes()

        st.download_button(
            label="💾 Exportar a Excel (descarga)",
            data=data,
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.markdown("---")

        # Opción 2: Guardar en Drive
        if carpeta_drive:
            st.caption(f"📁 `{carpeta_drive}`")
        else:
            st.caption("📁 Sin carpeta Drive configurada")
        if st.button("📁 Exportar al Drive", use_container_width=True,
                     disabled=not carpeta_drive, key="btn_drive_resumen"):
            try:
                with tempfile.TemporaryDirectory() as tmp2:
                    destino_tmp2 = Path(tmp2) / nombre_archivo
                    exportar_excel_resumen_anual(resumen, razon_social, cuit, destino_tmp2)
                    destino_final = guardar_en_drive(destino_tmp2, carpeta_drive, nombre_archivo)
                st.success(f"✅ Guardado en Drive: `{destino_final}`")
            except (DriveNoConfigurado, DriveNoAccesible) as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Error inesperado: {e}")
