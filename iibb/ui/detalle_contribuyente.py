import streamlit as st
from iibb.db import get_session
from iibb.service.contribuyente import (
    obtener_contribuyente,
    obtener_coeficientes,
    obtener_alicuotas,
    obtener_jurisdicciones_activas,
    validar_suma_coeficientes,
)
from iibb.models.catalogos import Jurisdiccion

MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def render_detalle():
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

        # Año seleccionado para ver coeficientes/alicuotas
        anio_actual = st.session_state.get("anio_detalle", 2026)

        # --- Header ---
        col_back, col_title, col_edit = st.columns([1, 5, 1])
        with col_back:
            if st.button("← Volver"):
                st.session_state["pantalla"] = "dashboard"
                st.rerun()
        with col_title:
            st.title(contrib.razon_social)
        with col_edit:
            if st.button("✏️ Editar", use_container_width=True):
                st.session_state["pantalla"] = "editar_contribuyente"
                st.rerun()

        st.markdown(f"**CUIT:** `{contrib.cuit}`  |  **N° CM:** `{contrib.nro_inscripcion_cm or '—'}`")
        st.markdown(f"**Domicilio fiscal:** {contrib.domicilio_fiscal or '—'}")
        st.markdown(f"**Domicilio actividades:** {contrib.domicilio_actividades or '—'}")
        st.markdown("---")

        # --- Jurisdicciones inscriptas ---
        st.subheader("Jurisdicciones inscriptas")
        juris_inscriptas = obtener_jurisdicciones_activas(session, contrib_id)
        if juris_inscriptas:
            for ji in juris_inscriptas:
                j = session.get(Jurisdiccion, ji.jurisdiccion_codigo)
                nombre_j = j.nombre if j else ji.jurisdiccion_codigo
                alta = ji.fecha_alta.strftime("%d/%m/%Y") if ji.fecha_alta else "—"
                st.markdown(f"- **{ji.jurisdiccion_codigo}** — {nombre_j}  *(alta: {alta})*")
        else:
            st.warning("Sin jurisdicciones inscriptas.")

        st.markdown("---")

        # --- Coeficientes y alícuotas ---
        col_anio, _ = st.columns([2, 5])
        with col_anio:
            anio_sel = st.selectbox(
                "Año de coeficientes/alícuotas",
                options=list(range(2024, 2031)),
                index=list(range(2024, 2031)).index(anio_actual),
                key="anio_detalle_sel",
            )
        st.session_state["anio_detalle"] = anio_sel

        coefs = obtener_coeficientes(session, contrib_id, anio_sel)
        alics = obtener_alicuotas(session, contrib_id, anio_sel)

        col_coef, col_alic = st.columns(2)

        with col_coef:
            st.subheader(f"Coeficientes {anio_sel}")
            if coefs:
                ok, suma = validar_suma_coeficientes(coefs)
                for c in coefs:
                    j = session.get(Jurisdiccion, c.jurisdiccion_codigo)
                    nombre_j = j.nombre_corto if j else c.jurisdiccion_codigo
                    st.markdown(f"- **{c.jurisdiccion_codigo}** {nombre_j}: `{c.valor:.4f}`")
                suma_str = f"{suma:.4f}"
                if ok:
                    st.success(f"Suma: {suma_str} ✓")
                else:
                    st.error(f"Suma: {suma_str} — ¡no suma 1.0000!")
            else:
                st.info(f"Sin coeficientes para {anio_sel}.")

        with col_alic:
            st.subheader(f"Alícuotas {anio_sel}")
            if alics:
                for a in alics:
                    j = session.get(Jurisdiccion, a.jurisdiccion_codigo)
                    nombre_j = j.nombre_corto if j else a.jurisdiccion_codigo
                    pct = float(a.valor) * 100
                    st.markdown(f"- **{a.jurisdiccion_codigo}** {nombre_j} ({a.codigo_actividad}): `{pct:.2f}%`")
            else:
                st.info(f"Sin alícuotas para {anio_sel}.")

        st.markdown("---")

        # --- Botón para procesar período ---
        st.subheader("Nueva liquidación")
        if st.button("📋 Procesar nuevo período CM03", type="primary"):
            st.session_state["pantalla"] = "procesar"
            st.rerun()

    finally:
        session.close()
