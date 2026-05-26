"""Pantalla de registro para usuarios invitados via link."""
import streamlit as st
from iibb.db import get_session
from iibb.service.invitacion import validar_token, canjear_invitacion


def render_registro(token: str):
    st.title("Crear tu cuenta — IIBB CG")

    session = get_session()
    try:
        inv = validar_token(session, token)
        email_inv = inv.email if inv else None
    finally:
        session.close()

    if inv is None:
        st.error("Este link de invitación no es válido o ya fue utilizado.")
        st.info("Pedile al administrador que te genere un nuevo link.")
        return

    st.success(f"Fuiste invitado/a con el correo **{email_inv}**.")
    st.markdown("Completá tus datos para acceder a la app:")
    st.markdown("")

    with st.form("form_registro"):
        nombre = st.text_input("Tu nombre completo", placeholder="Ana García")
        pwd1 = st.text_input("Elegí una contraseña", type="password", placeholder="Mínimo 6 caracteres")
        pwd2 = st.text_input("Repetí la contraseña", type="password")
        submitted = st.form_submit_button("Crear cuenta y entrar", type="primary", use_container_width=True)

    if submitted:
        if not nombre.strip():
            st.error("Ingresá tu nombre.")
        elif len(pwd1) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres.")
        elif pwd1 != pwd2:
            st.error("Las contraseñas no coinciden.")
        else:
            session = get_session()
            try:
                usuario = canjear_invitacion(session, token, nombre.strip(), pwd1)
                session.commit()
                st.session_state["usuario_id"] = usuario.id
                st.session_state["usuario_nombre"] = usuario.nombre
                st.session_state["usuario_email"] = usuario.email
                st.session_state["usuario_es_admin"] = usuario.es_admin
                st.session_state["pantalla"] = "dashboard"
                st.query_params.clear()
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Error inesperado: {e}")
            finally:
                session.close()
