"""
Pantalla de gestión de usuarios (crear / desactivar).
Solo accesible desde la barra superior cuando hay sesión activa.
"""
import streamlit as st
from iibb.db import get_session
from iibb.models.usuario import Usuario
from iibb.service.auth import crear_usuario, cambiar_password, autenticar
from iibb.service.invitacion import crear_invitacion, url_invitacion


def render_usuarios():
    # Solo el administrador puede gestionar usuarios
    if not st.session_state.get("usuario_es_admin", False):
        st.error("⛔ Solo el administrador puede gestionar usuarios.")
        if st.button("← Volver"):
            st.session_state["pantalla"] = "dashboard"
            st.rerun()
        return

    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("← Volver"):
            st.session_state["pantalla"] = "dashboard"
            st.rerun()
    with col_title:
        st.title("Gestión de usuarios")

    st.markdown("---")

    session = get_session()
    try:
        usuarios = session.query(Usuario).order_by(Usuario.nombre).all()
        # Leer atributos antes de cerrar sesión
        datos_usuarios = [
            {
                "id": u.id,
                "nombre": u.nombre,
                "email": u.email,
                "activo": u.activo,
                "ultimo_acceso": u.ultimo_acceso,
            }
            for u in usuarios
        ]
    finally:
        session.close()

    # ── Lista de usuarios actuales ──────────────────────────────────────────
    st.subheader(f"Usuarios registrados ({len(datos_usuarios)})")

    usuario_propio_id = st.session_state.get("usuario_id")

    for u in datos_usuarios:
        col_nombre, col_email, col_acceso, col_estado, col_accion = st.columns([2, 3, 2, 1, 1])

        with col_nombre:
            st.markdown(f"**{u['nombre']}**")
        with col_email:
            st.markdown(f"`{u['email']}`")
        with col_acceso:
            if u["ultimo_acceso"]:
                st.caption(f"Último: {u['ultimo_acceso'].strftime('%d/%m/%Y %H:%M')}")
            else:
                st.caption("Nunca ingresó")
        with col_estado:
            if u["activo"]:
                st.markdown("🟢 Activo")
            else:
                st.markdown("🔴 Inactivo")
        with col_accion:
            es_propio = u["id"] == usuario_propio_id
            if es_propio:
                st.caption("(vos)")
            else:
                if u["activo"]:
                    if st.button("Desactivar", key=f"deact_{u['id']}", type="secondary"):
                        st.session_state[f"confirmar_deact_{u['id']}"] = True
                        st.rerun()
                else:
                    if st.button("Reactivar", key=f"react_{u['id']}"):
                        _cambiar_estado_usuario(u["id"], True)
                        st.rerun()

        # Confirmación de desactivación
        if st.session_state.get(f"confirmar_deact_{u['id']}"):
            st.warning(
                f"¿Seguro que querés desactivar a **{u['nombre']}** ({u['email']})? "
                "No podrá ingresar a la app."
            )
            col_si, col_no, _ = st.columns([1, 1, 4])
            with col_si:
                if st.button("Sí, desactivar", key=f"si_{u['id']}", type="primary"):
                    _cambiar_estado_usuario(u["id"], False)
                    st.session_state.pop(f"confirmar_deact_{u['id']}", None)
                    st.rerun()
            with col_no:
                if st.button("Cancelar", key=f"no_{u['id']}"):
                    st.session_state.pop(f"confirmar_deact_{u['id']}", None)
                    st.rerun()

        st.markdown("---")

    # ── Invitar usuario por link ────────────────────────────────────────────
    st.subheader("Invitar usuario por link")
    st.caption("Generá un link de invitación válido por 7 días. El invitado elige su propio nombre y contraseña.")

    with st.form("form_invitar", clear_on_submit=True):
        email_inv = st.text_input("Correo del invitado", placeholder="ana@estudio.com")
        submitted_inv = st.form_submit_button("Generar link de invitación", type="primary")

    if submitted_inv:
        if not email_inv.strip():
            st.error("Ingresá un correo.")
        else:
            tenant_id = st.session_state.get("usuario_tenant_id", 1)
            session = get_session()
            try:
                inv = crear_invitacion(session, email=email_inv, tenant_id=tenant_id)
                session.commit()
                link = url_invitacion(inv.token)
                st.success("Link generado. Copialo y envialo al invitado:")
                st.code(link, language=None)
                st.caption("El link expira en 7 días y solo puede usarse una vez.")
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                session.close()

    st.markdown("---")

    # ── Crear nuevo usuario ─────────────────────────────────────────────────
    st.subheader("Crear nuevo usuario")

    with st.form("form_nuevo_usuario", clear_on_submit=True):
        col_n, col_e = st.columns(2)
        with col_n:
            nuevo_nombre = st.text_input("Nombre completo", placeholder="Ana García")
        with col_e:
            nuevo_email = st.text_input("Correo electrónico", placeholder="ana@estudio.com")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            nueva_pwd = st.text_input("Contraseña", type="password", placeholder="Mínimo 6 caracteres")
        with col_p2:
            nueva_pwd2 = st.text_input("Repetir contraseña", type="password", placeholder="Igual que arriba")

        submitted = st.form_submit_button("Crear usuario", type="primary", use_container_width=True)

    if submitted:
        if not nuevo_nombre or not nuevo_email or not nueva_pwd:
            st.error("Completá todos los campos.")
        elif nueva_pwd != nueva_pwd2:
            st.error("Las contraseñas no coinciden.")
        elif len(nueva_pwd) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres.")
        else:
            session = get_session()
            try:
                crear_usuario(session, email=nuevo_email, password=nueva_pwd, nombre=nuevo_nombre)
                session.commit()
                st.success(f"✅ Usuario **{nuevo_nombre}** creado. Ya puede ingresar con `{nuevo_email}`.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Error inesperado: {e}")
            finally:
                session.close()


def _cambiar_estado_usuario(usuario_id: int, activo: bool):
    session = get_session()
    try:
        u = session.get(Usuario, usuario_id)
        if u:
            u.activo = activo
            session.commit()
            estado = "reactivado" if activo else "desactivado"
            st.success(f"Usuario {estado} correctamente.")
    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        session.close()
