import streamlit as st
from iibb.db import get_session
from iibb.service.contribuyente import listar_contribuyentes


def render_dashboard():
    st.title("IIBB Convenio Multilateral — Estudio CG")
    st.markdown("---")

    # ── Acciones rápidas ──────────────────────────────────────────────────────
    col_nuevo, col_importar, _ = st.columns([2, 2, 4])
    with col_nuevo:
        if st.button("➕ Nuevo contribuyente", use_container_width=True):
            st.session_state["pantalla"] = "nuevo_contribuyente"
            st.rerun()
    with col_importar:
        if st.button("📥 Importar desde Excel", use_container_width=True):
            st.session_state["pantalla"] = "importar_contribuyentes"
            st.rerun()

    st.markdown("---")

    session = get_session()
    try:
        contribuyentes = listar_contribuyentes(session)
    finally:
        session.close()

    if not contribuyentes:
        st.warning(
            "No hay contribuyentes cargados todavía. "
            "Usá **➕ Nuevo contribuyente** para agregar uno a uno, "
            "o **📥 Importar desde Excel** para cargar varios de una vez."
        )
        return

    st.subheader(f"Contribuyentes activos ({len(contribuyentes)})")

    busqueda = st.text_input("Buscar por razón social o CUIT", "")

    if busqueda:
        b = busqueda.lower()
        contribuyentes = [
            c for c in contribuyentes
            if b in c.razon_social.lower() or b in c.cuit
        ]

    if not contribuyentes:
        st.info("No hay contribuyentes que coincidan con la búsqueda.")
        return

    for contrib in contribuyentes:
        col1, col2, col3 = st.columns([4, 2, 2])
        with col1:
            st.markdown(f"**{contrib.razon_social}**  \n`{contrib.cuit}`")
        with col2:
            st.markdown(f"CM: `{contrib.nro_inscripcion_cm or '—'}`")
        with col3:
            if st.button("Ver / Liquidar", key=f"btn_{contrib.id}"):
                st.session_state["pantalla"] = "detalle"
                st.session_state["contribuyente_id"] = contrib.id
                st.rerun()
        st.markdown("---")
