"""
Entry point de la app Streamlit.
Corre con: streamlit run iibb/main.py
"""
from pathlib import Path
import streamlit as st

# ── Logo como page_icon (si ya fue copiado a static/) ──────────────────────
_LOGO_PATH = Path(__file__).parent / "static" / "logo.png"

if _LOGO_PATH.exists():
    try:
        from PIL import Image
        _icon = Image.open(_LOGO_PATH)
    except Exception:
        _icon = "🏦"
else:
    _icon = "🏦"

st.set_page_config(
    page_title="IIBB · CG Consultoría Integral",
    page_icon=_icon,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS personalizado — paleta del logo ────────────────────────────────────
st.markdown(
    """
    <style>
    /* Botones primarios con el color del logo */
    div.stButton > button[kind="primary"] {
        background-color: #8FADB8;
        color: #1B2838;
        font-weight: 700;
        border: none;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #A8C4CE;
        color: #1B2838;
    }

    /* Inputs de texto */
    input, textarea {
        background-color: #243447 !important;
        color: #D4E8EE !important;
        border: 1px solid #8FADB8 !important;
        border-radius: 6px !important;
    }

    /* Métricas */
    div[data-testid="metric-container"] {
        background-color: #243447;
        border: 1px solid #8FADB8;
        border-radius: 8px;
        padding: 12px 16px;
    }

    /* Tablas */
    div[data-testid="stDataFrame"] {
        border: 1px solid #8FADB8;
        border-radius: 6px;
    }

    /* Separadores */
    hr {
        border-color: #8FADB8 !important;
        opacity: 0.3;
    }

    /* Header de la barra superior */
    .top-bar {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 4px 0 8px 0;
    }
    .top-bar img {
        height: 38px;
        border-radius: 50%;
    }
    .top-bar-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #8FADB8;
    }

    /* Alertas de éxito con el verde del tema */
    div[data-testid="stAlert"][data-baseweb="notification"] {
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Inicializar estado ──────────────────────────────────────────────────────
if "pantalla" not in st.session_state:
    st.session_state["pantalla"] = "login"
if "usuario_id" not in st.session_state:
    st.session_state["usuario_id"] = None

# ── Verificar sesión ────────────────────────────────────────────────────────
pantalla = st.session_state["pantalla"]
logueado = st.session_state["usuario_id"] is not None

if pantalla == "login" or not logueado:
    from iibb.ui.login import render_login
    render_login()
    st.stop()

# ── Barra superior con logo + usuario ──────────────────────────────────────
nombre = st.session_state.get("usuario_nombre", "")

col_logo, col_titulo, col_usuario, col_pwd, col_usr, col_salir = st.columns([1, 5, 2, 1, 1, 1])
with col_logo:
    if _LOGO_PATH.exists():
        import base64
        _logo_b64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode()
        st.markdown(
            f'<img src="data:image/jpeg;base64,{_logo_b64}" '
            f'style="width:44px;height:44px;border-radius:50%;object-fit:cover;margin-top:4px;">',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("**🏦**")
with col_titulo:
    st.markdown('<span class="top-bar-title">IIBB Convenio Multilateral · CG Consultoría Integral</span>', unsafe_allow_html=True)
with col_usuario:
    st.markdown(f"👤 *{nombre}*")
with col_pwd:
    if st.button("🔑", help="Cambiar mi contraseña"):
        st.session_state["pantalla"] = "cambiar_password"
        st.rerun()
with col_usr:
    if st.session_state.get("usuario_es_admin", False):
        if st.button("👥", help="Gestionar usuarios"):
            st.session_state["pantalla"] = "usuarios"
            st.rerun()
with col_salir:
    if st.button("🚪 Salir"):
        for key in ["usuario_id", "usuario_nombre", "usuario_email",
                    "pantalla", "contribuyente_id", "liquidacion", "comprobantes"]:
            st.session_state.pop(key, None)
        st.session_state["pantalla"] = "login"
        st.rerun()

st.markdown("---")

# ── Navegación ──────────────────────────────────────────────────────────────
if pantalla == "dashboard":
    from iibb.ui.dashboard import render_dashboard
    render_dashboard()

elif pantalla == "detalle":
    from iibb.ui.detalle_contribuyente import render_detalle
    render_detalle()

elif pantalla == "procesar":
    from iibb.ui.procesar import render_procesar
    render_procesar()

elif pantalla == "resultado":
    from iibb.ui.resultado import render_resultado
    render_resultado()

elif pantalla == "cambiar_password":
    from iibb.ui.login import render_cambiar_password
    render_cambiar_password()

elif pantalla == "usuarios":
    from iibb.ui.usuarios import render_usuarios
    render_usuarios()

elif pantalla == "nuevo_contribuyente":
    from iibb.ui.contribuyente_form import render_contribuyente_form
    render_contribuyente_form(modo="nuevo")

elif pantalla == "editar_contribuyente":
    from iibb.ui.contribuyente_form import render_contribuyente_form
    render_contribuyente_form(modo="editar", contribuyente_id=st.session_state.get("contribuyente_id"))

elif pantalla == "importar_contribuyentes":
    from iibb.ui.contribuyente_importar import render_importar_contribuyentes
    render_importar_contribuyentes()

elif pantalla == "resumen_anual":
    from iibb.ui.resumen_anual import render_resumen_anual
    render_resumen_anual()

else:
    st.error(f"Pantalla desconocida: {pantalla}")
    if st.button("Ir al inicio"):
        st.session_state["pantalla"] = "dashboard"
        st.rerun()
