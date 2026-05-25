"""
Pantalla de login y cambio de contraseña.
"""
import base64
from pathlib import Path
import streamlit as st
from iibb.db import get_session
from iibb.service.auth import autenticar, cambiar_password

_LOGO_PATH = Path(__file__).parent.parent / "static" / "logo.png"


def _logo_base64() -> str | None:
    """Devuelve el logo como string base64, o None si no existe."""
    if not _LOGO_PATH.exists():
        return None
    try:
        data = _LOGO_PATH.read_bytes()
        return base64.b64encode(data).decode()
    except Exception:
        return None


def render_login():
    logo_b64 = _logo_base64()

    st.markdown(
        """
        <style>
        /* Fondo completo igual al logo */
        html, body, [data-testid="stAppViewContainer"],
        [data-testid="stApp"], .main, section.main {
            background-color: #1B2838 !important;
        }
        /* Ocultar el header de Streamlit en la pantalla de login */
        header[data-testid="stHeader"] {
            background-color: #1B2838 !important;
        }
        /* Sin padding lateral excesivo */
        .block-container {
            padding-top: 2rem !important;
            max-width: 480px !important;
            margin: 0 auto !important;
        }
        .login-logo {
            display: block;
            margin: 0 auto 1.5rem auto;
            width: 160px;
            height: 160px;
            border-radius: 50%;
            object-fit: cover;
        }
        .login-titulo {
            text-align: center;
            font-size: 1.6rem;
            font-weight: 700;
            color: #8FADB8;
            margin: 0 0 0.2rem 0;
        }
        .login-sub {
            text-align: center;
            font-size: 1rem;
            color: #8FADB8;
            opacity: 0.7;
            margin-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        # Logo
        if logo_b64:
            st.markdown(
                f'<img class="login-logo" src="data:image/jpeg;base64,{logo_b64}" alt="Logo CG">',
                unsafe_allow_html=True,
            )
        else:
            st.markdown("<h1 style='text-align:center;'>🏦</h1>", unsafe_allow_html=True)

        st.markdown('<p class="login-titulo">CG Consultoría Integral</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-sub">IIBB · Convenio Multilateral</p>', unsafe_allow_html=True)

        with st.form("form_login", clear_on_submit=False):
            email = st.text_input(
                "Correo electrónico",
                placeholder="usuario@estudio.com",
            )
            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="••••••••",
            )
            submitted = st.form_submit_button(
                "Ingresar",
                use_container_width=True,
                type="primary",
            )

        if submitted:
            if not email or not password:
                st.error("Ingresá el correo y la contraseña.")
                return

            session = get_session()
            try:
                usuario = autenticar(session, email, password)
                if usuario:
                    uid      = usuario.id
                    unombre  = usuario.nombre
                    uemail   = usuario.email
                    ues_admin = usuario.es_admin
                session.commit()
            finally:
                session.close()

            if usuario:
                st.session_state["usuario_id"]       = uid
                st.session_state["usuario_nombre"]   = unombre
                st.session_state["usuario_email"]    = uemail
                st.session_state["usuario_es_admin"] = ues_admin
                st.session_state["pantalla"]         = "dashboard"
                st.rerun()
            else:
                st.error("Correo o contraseña incorrectos.")


def render_cambiar_password():
    usuario_id = st.session_state.get("usuario_id")
    if not usuario_id:
        st.session_state["pantalla"] = "login"
        st.rerun()
        return

    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("← Volver"):
            st.session_state["pantalla"] = "dashboard"
            st.rerun()
    with col_title:
        st.title("Cambiar contraseña")

    st.markdown(f"*Usuario: {st.session_state.get('usuario_email', '')}*")
    st.markdown("---")

    with st.form("form_cambiar_pwd"):
        pwd_actual   = st.text_input("Contraseña actual", type="password")
        pwd_nueva    = st.text_input("Nueva contraseña", type="password")
        pwd_conf     = st.text_input("Confirmar nueva contraseña", type="password")
        submitted    = st.form_submit_button("Cambiar contraseña", type="primary")

    if submitted:
        if not pwd_actual or not pwd_nueva or not pwd_conf:
            st.error("Completá todos los campos.")
            return
        if pwd_nueva != pwd_conf:
            st.error("La nueva contraseña y la confirmación no coinciden.")
            return
        if len(pwd_nueva) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres.")
            return

        session = get_session()
        try:
            uemail  = st.session_state.get("usuario_email", "")
            usuario = autenticar(session, uemail, pwd_actual)
            if not usuario:
                st.error("La contraseña actual es incorrecta.")
                return
            cambiar_password(session, usuario_id, pwd_nueva)
            session.commit()
            st.success("✅ Contraseña cambiada exitosamente.")
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            session.close()
