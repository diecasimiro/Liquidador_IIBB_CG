"""
Formulario de alta y edición de contribuyentes.
Maneja jurisdicciones, actividades, coeficientes y alícuotas.
"""
from datetime import date
from decimal import Decimal, InvalidOperation

import streamlit as st

from iibb.db import get_session
from iibb.models.catalogos import Jurisdiccion
from iibb.service.contribuyente import (
    crear_contribuyente,
    obtener_contribuyente,
    obtener_jurisdicciones_activas,
    obtener_coeficientes,
    obtener_alicuotas,
    actualizar_datos_basicos,
    guardar_coeficientes_anio,
    guardar_alicuotas_anio,
    validar_cuit,
)

ARTICULOS_CM = {
    "art2": "Art. 2 - Régimen General",
    "art6": "Art. 6 - Construcción",
    "art7": "Art. 7 - Seguros",
    "art8": "Art. 8 - Entidades financieras",
    "art9": "Art. 9 - Transporte",
    "art10": "Art. 10 - Profesiones liberales",
    "art11": "Art. 11 - Rematadores / Comisionistas",
    "art12": "Art. 12 - Prestamistas",
    "art13": "Art. 13 - Industria",
    "art14": "Art. 14 - Asignación directa",
}

TIPOS_CONTRIBUYENTE = ["Resto", "Empresa unipersonal", "Sociedad de hecho", "Otro"]
NATURALEZAS = [
    "Sociedad Anónima",
    "Sociedad de Responsabilidad Limitada",
    "Empresa Unipersonal",
    "Sociedad en Comandita",
    "Cooperativa",
    "Asociación Civil",
    "Fundación",
    "Otro",
]
MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _cargar_jurisdicciones_catalogo(session) -> dict[str, str]:
    """Retorna {codigo: nombre} de todas las jurisdicciones."""
    return {j.codigo: f"{j.codigo} - {j.nombre}" for j in session.query(Jurisdiccion).order_by(Jurisdiccion.codigo).all()}


def _init_estado_nuevo(key_prefix: str):
    """Inicializa el session_state para un formulario en blanco."""
    if f"{key_prefix}_juris" not in st.session_state:
        st.session_state[f"{key_prefix}_juris"] = []          # [{"codigo": "901", "fecha_alta": "01/04/2012"}]
        st.session_state[f"{key_prefix}_acts"] = []           # [{"codigo_cuacm": ..., ...}]
        st.session_state[f"{key_prefix}_anio_coef"] = 2026
        st.session_state[f"{key_prefix}_coefs"] = {}          # {"901": "0.6496"}
        st.session_state[f"{key_prefix}_anio_alic"] = 2026
        st.session_state[f"{key_prefix}_alics"] = {}          # {"901__266090": "1.00"}


def _init_estado_edicion(key_prefix: str, contrib_id: int):
    """Carga datos existentes en session_state para edición."""
    if f"{key_prefix}_cargado" in st.session_state:
        return
    session = get_session()
    try:
        contrib = obtener_contribuyente(session, contrib_id)
        if not contrib:
            return
        anio = st.session_state.get(f"{key_prefix}_anio_coef", 2026)
        juris_inscriptas = obtener_jurisdicciones_activas(session, contrib_id)
        coefs = obtener_coeficientes(session, contrib_id, anio)
        alics = obtener_alicuotas(session, contrib_id, anio)

        st.session_state[f"{key_prefix}_juris"] = [
            {"codigo": ji.jurisdiccion_codigo,
             "fecha_alta": ji.fecha_alta.strftime("%d/%m/%Y") if ji.fecha_alta else ""}
            for ji in juris_inscriptas
        ]
        st.session_state[f"{key_prefix}_acts"] = [
            {"codigo_cuacm": a.codigo_cuacm, "descripcion": a.descripcion,
             "articulo_cm": a.articulo_cm, "es_principal": a.es_principal,
             "fecha_alta": a.fecha_alta.strftime("%d/%m/%Y") if a.fecha_alta else ""}
            for a in contrib.actividades_inscriptas if a.activa
        ]
        st.session_state[f"{key_prefix}_coefs"] = {c.jurisdiccion_codigo: str(c.valor) for c in coefs}
        st.session_state[f"{key_prefix}_alics"] = {
            f"{al.jurisdiccion_codigo}__{al.codigo_actividad}": str(float(al.valor) * 100)
            for al in alics
        }
        st.session_state[f"{key_prefix}_cargado"] = True
    finally:
        session.close()


def render_contribuyente_form(modo: str = "nuevo", contribuyente_id: int | None = None):
    """
    modo = "nuevo"  → alta de contribuyente
    modo = "editar" → edición de contribuyente existente
    """
    key = f"cf_{contribuyente_id or 'new'}"

    session = get_session()
    try:
        juris_catalogo = _cargar_jurisdicciones_catalogo(session)
        contrib_actual = obtener_contribuyente(session, contribuyente_id) if contribuyente_id else None

        if contrib_actual:
            # Leer campos antes de cerrar sesión
            campos_actuales = {
                "cuit": contrib_actual.cuit,
                "razon_social": contrib_actual.razon_social,
                "nro_inscripcion_cm": contrib_actual.nro_inscripcion_cm or "",
                "jurisdiccion_sede": contrib_actual.jurisdiccion_sede or list(juris_catalogo.keys())[0],
                "naturaleza_juridica": contrib_actual.naturaleza_juridica or "",
                "cierre_ejercicio_mes": contrib_actual.cierre_ejercicio_mes or 12,
                "cierre_ejercicio_dia": contrib_actual.cierre_ejercicio_dia or 31,
                "domicilio_fiscal": contrib_actual.domicilio_fiscal or "",
                "domicilio_actividades": contrib_actual.domicilio_actividades or "",
                "tipo_contribuyente": contrib_actual.tipo_contribuyente or "Resto",
                "notas": contrib_actual.notas or "",
                "carpeta_drive": contrib_actual.carpeta_drive or "",
            }
        else:
            campos_actuales = None
    finally:
        session.close()

    # Inicializar estado
    if modo == "nuevo":
        _init_estado_nuevo(key)
    else:
        if f"{key}_anio_coef" not in st.session_state:
            st.session_state[f"{key}_anio_coef"] = 2026
        if f"{key}_anio_alic" not in st.session_state:
            st.session_state[f"{key}_anio_alic"] = 2026
        _init_estado_edicion(key, contribuyente_id)

    # ── Header ───────────────────────────────────────────────────────────────
    col_back, col_title = st.columns([1, 6])
    with col_back:
        if st.button("← Volver"):
            _limpiar_estado(key)
            destino = "detalle" if modo == "editar" else "dashboard"
            st.session_state["pantalla"] = destino
            st.rerun()
    with col_title:
        titulo = "Editar contribuyente" if modo == "editar" else "Nuevo contribuyente"
        st.title(titulo)

    tab_basicos, tab_juris, tab_acts, tab_coefs, tab_alics = st.tabs([
        "📋 Datos básicos",
        "🗺️ Jurisdicciones",
        "⚙️ Actividades",
        "📊 Coeficientes",
        "💰 Alícuotas",
    ])

    # ── Tab 1: Datos básicos ──────────────────────────────────────────────────
    with tab_basicos:
        _seccion_datos_basicos(key, modo, campos_actuales, juris_catalogo, contribuyente_id)

    # ── Tab 2: Jurisdicciones ─────────────────────────────────────────────────
    with tab_juris:
        _seccion_jurisdicciones(key, juris_catalogo)

    # ── Tab 3: Actividades ────────────────────────────────────────────────────
    with tab_acts:
        _seccion_actividades(key)

    # ── Tab 4: Coeficientes ───────────────────────────────────────────────────
    with tab_coefs:
        _seccion_coeficientes(key, modo, contribuyente_id)

    # ── Tab 5: Alícuotas ──────────────────────────────────────────────────────
    with tab_alics:
        _seccion_alicuotas(key, modo, contribuyente_id)


# ─────────────────────────────────────────────────────────────────────────────
# Secciones individuales
# ─────────────────────────────────────────────────────────────────────────────

def _seccion_datos_basicos(key, modo, campos, juris_catalogo, contrib_id):
    st.subheader("Datos del contribuyente")

    v = campos or {}
    juris_list = list(juris_catalogo.keys())

    with st.form(f"form_basicos_{key}"):
        col1, col2 = st.columns(2)
        with col1:
            cuit = st.text_input("CUIT *", value=v.get("cuit", ""), placeholder="30-71223438-1",
                                 disabled=(modo == "editar"), help="Formato: XX-XXXXXXXX-X")
            razon_social = st.text_input("Razón Social *", value=v.get("razon_social", ""),
                                         placeholder="EMPRESA S.A.")
            nro_cm = st.text_input("N° Inscripción CM", value=v.get("nro_inscripcion_cm", ""),
                                   placeholder="901-XXXXXX-X")
            tipo = st.selectbox("Tipo de contribuyente", TIPOS_CONTRIBUYENTE,
                                index=TIPOS_CONTRIBUYENTE.index(v.get("tipo_contribuyente", "Resto"))
                                if v.get("tipo_contribuyente") in TIPOS_CONTRIBUYENTE else 0)

        with col2:
            sede_idx = juris_list.index(v["jurisdiccion_sede"]) if v.get("jurisdiccion_sede") in juris_list else 0
            sede = st.selectbox("Jurisdicción Sede *", juris_list,
                                format_func=lambda c: juris_catalogo[c], index=sede_idx)
            nat_idx = NATURALEZAS.index(v["naturaleza_juridica"]) if v.get("naturaleza_juridica") in NATURALEZAS else len(NATURALEZAS) - 1
            naturaleza = st.selectbox("Naturaleza jurídica", NATURALEZAS, index=nat_idx)
            col_mes, col_dia = st.columns(2)
            with col_mes:
                cierre_mes = st.selectbox("Cierre ejercicio — Mes",
                                          list(MESES.keys()),
                                          format_func=lambda m: MESES[m],
                                          index=v.get("cierre_ejercicio_mes", 12) - 1)
            with col_dia:
                cierre_dia = st.number_input("Día", min_value=1, max_value=31,
                                             value=v.get("cierre_ejercicio_dia", 31))

        dom_fiscal = st.text_input("Domicilio fiscal", value=v.get("domicilio_fiscal", ""),
                                   placeholder="Av. Corrientes 1234, Piso 5 - CABA (1043)")
        dom_act = st.text_input("Domicilio principal de actividades", value=v.get("domicilio_actividades", ""),
                                placeholder="Igual al fiscal si no difiere")

        carpeta_drive = st.text_input(
            "📁 Carpeta Drive para exportaciones",
            value=v.get("carpeta_drive", ""),
            placeholder="C:/Users/tu_usuario/Google Drive/Clientes/EMPRESA S.A./IIBB/",
            help="Ruta local de la carpeta sincronizada (Google Drive, OneDrive, etc.). "
                 "Los Excel se guardarán ahí al usar 'Exportar al Drive'.",
        )
        notas = st.text_area("Notas internas", value=v.get("notas", ""), height=80)

        submitted = st.form_submit_button(
            "💾 Guardar datos básicos" if modo == "editar" else "Continuar →",
            type="primary", use_container_width=True,
        )

    if submitted:
        if not razon_social.strip():
            st.error("La razón social es obligatoria.")
            return

        if modo == "nuevo":
            valido, cuit_fmt = validar_cuit(cuit)
            if not valido:
                st.error(f"El CUIT '{cuit}' es inválido. Verificá el dígito verificador.")
                return
            # Guardar temporalmente en session_state para el submit final
            st.session_state[f"{key}_datos_basicos"] = {
                "cuit": cuit_fmt,
                "razon_social": razon_social.strip().upper(),
                "nro_inscripcion_cm": nro_cm.strip() or None,
                "jurisdiccion_sede": sede,
                "naturaleza_juridica": naturaleza,
                "cierre_ejercicio_mes": cierre_mes,
                "cierre_ejercicio_dia": int(cierre_dia),
                "domicilio_fiscal": dom_fiscal.strip() or None,
                "domicilio_actividades": dom_act.strip() or None,
                "tipo_contribuyente": tipo,
                "notas": notas.strip() or None,
                "carpeta_drive": carpeta_drive.strip() or None,
            }
            st.success("✅ Datos básicos guardados. Continuá con las pestañas siguientes.")

        else:
            session = get_session()
            try:
                actualizar_datos_basicos(
                    session, contrib_id,
                    razon_social=razon_social.strip().upper(),
                    nro_inscripcion_cm=nro_cm.strip() or None,
                    jurisdiccion_sede=sede,
                    naturaleza_juridica=naturaleza,
                    cierre_ejercicio_mes=cierre_mes,
                    cierre_ejercicio_dia=int(cierre_dia),
                    domicilio_fiscal=dom_fiscal.strip() or None,
                    domicilio_actividades=dom_act.strip() or None,
                    tipo_contribuyente=tipo,
                    notas=notas.strip() or None,
                    carpeta_drive=carpeta_drive.strip() or None,
                )
                session.commit()
                st.success("✅ Datos actualizados correctamente.")
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                session.close()

    # Botón de guardar final (solo en modo nuevo)
    if modo == "nuevo":
        st.markdown("---")
        st.info("Una vez completadas todas las pestañas, hacé clic en **Crear contribuyente** para guardar todo.")
        if st.button("🏢 Crear contribuyente", type="primary", use_container_width=True):
            _guardar_nuevo_contribuyente(key)


def _seccion_jurisdicciones(key, juris_catalogo):
    st.subheader("Jurisdicciones inscriptas")
    st.caption("Agregá cada jurisdicción donde el contribuyente está inscripto.")

    juris_state: list[dict] = st.session_state[f"{key}_juris"]
    juris_disponibles = list(juris_catalogo.keys())
    ya_agregadas = {j["codigo"] for j in juris_state}

    # Tabla de jurisdicciones actuales
    if juris_state:
        for i, j in enumerate(juris_state):
            col_cod, col_fecha, col_del = st.columns([3, 3, 1])
            with col_cod:
                st.markdown(f"**{juris_catalogo.get(j['codigo'], j['codigo'])}**")
            with col_fecha:
                nueva_fecha = st.text_input(
                    "Fecha alta (DD/MM/AAAA)",
                    value=j.get("fecha_alta", ""),
                    key=f"{key}_juris_fecha_{i}",
                    label_visibility="collapsed",
                    placeholder="01/04/2012",
                )
                juris_state[i]["fecha_alta"] = nueva_fecha
            with col_del:
                if st.button("🗑️", key=f"{key}_del_juris_{i}", help="Quitar"):
                    juris_state.pop(i)
                    st.rerun()
        st.markdown("---")
    else:
        st.info("Sin jurisdicciones. Agregá al menos una.")

    # Agregar nueva
    opciones_libre = [c for c in juris_disponibles if c not in ya_agregadas]
    if opciones_libre:
        col_sel, col_btn = st.columns([4, 1])
        with col_sel:
            nueva_juris = st.selectbox(
                "Agregar jurisdicción",
                opciones_libre,
                format_func=lambda c: juris_catalogo[c],
                key=f"{key}_nueva_juris_sel",
                label_visibility="collapsed",
            )
        with col_btn:
            if st.button("+ Agregar", key=f"{key}_add_juris"):
                juris_state.append({"codigo": nueva_juris, "fecha_alta": ""})
                st.rerun()
    else:
        st.success("Todas las jurisdicciones ya están agregadas.")


def _seccion_actividades(key):
    st.subheader("Actividades económicas")
    st.caption("Podés agregar una o más actividades. Marcá cuál es la principal.")

    acts_state: list[dict] = st.session_state[f"{key}_acts"]

    if acts_state:
        for i, a in enumerate(acts_state):
            with st.expander(f"Actividad {i+1}: {a.get('codigo_cuacm', '-')} - {a.get('descripcion', '')[:50]}", expanded=(i == 0)):
                col1, col2 = st.columns(2)
                with col1:
                    a["codigo_cuacm"] = st.text_input("Código CUACM / NAES", value=a.get("codigo_cuacm", ""),
                                                       key=f"{key}_act_cod_{i}", placeholder="266090")
                    a["descripcion"] = st.text_input("Descripción", value=a.get("descripcion", ""),
                                                      key=f"{key}_act_desc_{i}",
                                                      placeholder="Fabricación de equipos médicos...")
                with col2:
                    art_opciones = list(ARTICULOS_CM.keys())
                    art_idx = art_opciones.index(a.get("articulo_cm", "art2")) if a.get("articulo_cm") in art_opciones else 0
                    a["articulo_cm"] = st.selectbox("Artículo CM", art_opciones,
                                                     format_func=lambda k: ARTICULOS_CM[k],
                                                     index=art_idx, key=f"{key}_act_art_{i}")
                    a["es_principal"] = st.checkbox("Es la actividad principal", value=a.get("es_principal", i == 0),
                                                     key=f"{key}_act_princ_{i}")
                    a["fecha_alta"] = st.text_input("Fecha alta (DD/MM/AAAA)", value=a.get("fecha_alta", ""),
                                                     key=f"{key}_act_fecha_{i}", placeholder="01/04/2012")
                if st.button("🗑️ Quitar actividad", key=f"{key}_del_act_{i}"):
                    acts_state.pop(i)
                    st.rerun()
    else:
        st.info("Sin actividades. Agregá al menos una.")

    if st.button("+ Agregar actividad", key=f"{key}_add_act"):
        acts_state.append({"codigo_cuacm": "", "descripcion": "", "articulo_cm": "art2",
                           "es_principal": len(acts_state) == 0, "fecha_alta": ""})
        st.rerun()


def _seccion_coeficientes(key, modo, contrib_id):
    st.subheader("Coeficientes unificados (CM05)")
    st.caption("Ingresá los coeficientes del CM05 para cada año. Deben sumar 1.0000.")

    anio = st.number_input("Año de los coeficientes", min_value=2020, max_value=2035,
                            value=st.session_state[f"{key}_anio_coef"],
                            key=f"{key}_anio_coef_input", step=1)
    st.session_state[f"{key}_anio_coef"] = int(anio)

    juris_state: list[dict] = st.session_state[f"{key}_juris"]
    coefs_state: dict = st.session_state[f"{key}_coefs"]

    if not juris_state:
        st.warning("Primero agregá las jurisdicciones en la pestaña 🗺️.")
        return

    total = Decimal("0")
    with st.form(f"form_coefs_{key}_{anio}"):
        for j in juris_state:
            val_actual = coefs_state.get(j["codigo"], "0.0000")
            nuevo_val = st.text_input(
                f"Coef. {j['codigo']}",
                value=val_actual,
                key=f"{key}_coef_inp_{j['codigo']}_{anio}",
                placeholder="0.6496",
            )
            coefs_state[j["codigo"]] = nuevo_val
            try:
                total += Decimal(nuevo_val.replace(",", "."))
            except InvalidOperation:
                pass

        st.markdown(f"**Suma actual: `{total:.4f}`** {'✅' if abs(total - Decimal('1')) < Decimal('0.0001') else '⚠️ debe ser 1.0000'}")

        if st.form_submit_button("💾 Guardar coeficientes", type="primary"):
            _guardar_coefs(key, anio, modo, contrib_id)


def _guardar_coefs(key, anio, modo, contrib_id):
    juris_state = st.session_state[f"{key}_juris"]
    coefs_state = st.session_state[f"{key}_coefs"]
    coefs = []
    for j in juris_state:
        val_str = coefs_state.get(j["codigo"], "0")
        try:
            coefs.append({"jurisdiccion_codigo": j["codigo"], "anio": anio,
                          "valor": Decimal(val_str.replace(",", "."))})
        except InvalidOperation:
            st.error(f"Valor inválido para {j['codigo']}: '{val_str}'")
            return

    if modo == "editar" and contrib_id:
        session = get_session()
        try:
            guardar_coeficientes_anio(session, contrib_id, anio, coefs)
            session.commit()
            st.success(f"✅ Coeficientes {anio} guardados.")
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            session.close()
    else:
        st.success(f"✅ Coeficientes {anio} listos. Se guardarán al crear el contribuyente.")


def _seccion_alicuotas(key, modo, contrib_id):
    st.subheader("Alícuotas por jurisdicción")
    st.caption("Ingresá la alícuota en % para cada jurisdicción y actividad.")

    anio = st.number_input("Año de las alícuotas", min_value=2020, max_value=2035,
                            value=st.session_state[f"{key}_anio_alic"],
                            key=f"{key}_anio_alic_input", step=1)
    st.session_state[f"{key}_anio_alic"] = int(anio)

    juris_state = st.session_state[f"{key}_juris"]
    acts_state = st.session_state[f"{key}_acts"]
    alics_state: dict = st.session_state[f"{key}_alics"]

    if not juris_state:
        st.warning("Primero agregá las jurisdicciones en la pestaña 🗺️.")
        return
    if not acts_state:
        st.warning("Primero agregá las actividades en la pestaña ⚙️.")
        return

    with st.form(f"form_alics_{key}_{anio}"):
        for j in juris_state:
            st.markdown(f"**Jurisdicción {j['codigo']}**")
            for a in acts_state:
                cod_act = a.get("codigo_cuacm", "-")
                alic_key = f"{j['codigo']}__{cod_act}"
                val_actual = alics_state.get(alic_key, "0.00")
                nuevo_val = st.text_input(
                    f"Alícuota {j['codigo']} / Actividad {cod_act} (%)",
                    value=val_actual,
                    key=f"{key}_alic_inp_{j['codigo']}_{cod_act}_{anio}",
                    placeholder="1.50",
                    help="Ingresá el porcentaje, ej: 1.50 para 1,50%",
                )
                alics_state[alic_key] = nuevo_val

        if st.form_submit_button("💾 Guardar alícuotas", type="primary"):
            _guardar_alics(key, anio, modo, contrib_id)


def _guardar_alics(key, anio, modo, contrib_id):
    juris_state = st.session_state[f"{key}_juris"]
    acts_state = st.session_state[f"{key}_acts"]
    alics_state = st.session_state[f"{key}_alics"]
    alicuotas = []
    for j in juris_state:
        for a in acts_state:
            cod_act = a.get("codigo_cuacm", "")
            if not cod_act:
                continue
            alic_key = f"{j['codigo']}__{cod_act}"
            val_str = alics_state.get(alic_key, "0")
            try:
                pct = Decimal(val_str.replace(",", ".").replace("%", ""))
                alicuotas.append({
                    "jurisdiccion_codigo": j["codigo"],
                    "anio": anio,
                    "codigo_actividad": cod_act,
                    "valor": pct / Decimal("100"),
                })
            except InvalidOperation:
                st.error(f"Valor inválido para {j['codigo']} / {cod_act}: '{val_str}'")
                return

    if modo == "editar" and contrib_id:
        session = get_session()
        try:
            guardar_alicuotas_anio(session, contrib_id, anio, alicuotas)
            session.commit()
            st.success(f"✅ Alícuotas {anio} guardadas.")
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            session.close()
    else:
        st.success(f"✅ Alícuotas {anio} listas. Se guardarán al crear el contribuyente.")


def _guardar_nuevo_contribuyente(key):
    datos = st.session_state.get(f"{key}_datos_basicos")
    if not datos:
        st.error("Completá los datos básicos primero (pestaña 📋).")
        return

    juris_state = st.session_state[f"{key}_juris"]
    acts_state = st.session_state[f"{key}_acts"]
    anio_coef = st.session_state[f"{key}_anio_coef"]
    coefs_state = st.session_state[f"{key}_coefs"]
    anio_alic = st.session_state[f"{key}_anio_alic"]
    alics_state = st.session_state[f"{key}_alics"]

    if not juris_state:
        st.error("Agregá al menos una jurisdicción inscripta.")
        return
    if not acts_state:
        st.error("Agregá al menos una actividad.")
        return

    # Parsear fecha alta de jurisdicciones
    jurisdicciones = []
    for j in juris_state:
        fa = None
        if j.get("fecha_alta"):
            try:
                from datetime import datetime
                fa = datetime.strptime(j["fecha_alta"], "%d/%m/%Y").date()
            except ValueError:
                pass
        jurisdicciones.append({"codigo": j["codigo"], "fecha_alta": fa})

    # Parsear actividades
    actividades = []
    for a in acts_state:
        fa = None
        if a.get("fecha_alta"):
            try:
                from datetime import datetime
                fa = datetime.strptime(a["fecha_alta"], "%d/%m/%Y").date()
            except ValueError:
                pass
        actividades.append({
            "codigo_cuacm": a["codigo_cuacm"],
            "descripcion": a["descripcion"],
            "articulo_cm": a["articulo_cm"],
            "es_principal": a["es_principal"],
            "fecha_alta": fa,
        })

    # Parsear coeficientes
    coeficientes = []
    for j in juris_state:
        val_str = coefs_state.get(j["codigo"], "0")
        try:
            coeficientes.append({
                "anio": anio_coef,
                "jurisdiccion_codigo": j["codigo"],
                "valor": Decimal(val_str.replace(",", ".")),
            })
        except InvalidOperation:
            st.error(f"Coeficiente inválido para {j['codigo']}.")
            return

    # Parsear alícuotas
    alicuotas = []
    for j in juris_state:
        for a in acts_state:
            cod_act = a.get("codigo_cuacm", "")
            if not cod_act:
                continue
            alic_key = f"{j['codigo']}__{cod_act}"
            val_str = alics_state.get(alic_key, "0")
            try:
                pct = Decimal(val_str.replace(",", ".").replace("%", ""))
                alicuotas.append({
                    "anio": anio_alic,
                    "jurisdiccion_codigo": j["codigo"],
                    "codigo_actividad": cod_act,
                    "valor": pct / Decimal("100"),
                })
            except InvalidOperation:
                st.error(f"Alícuota inválida para {j['codigo']} / {cod_act}.")
                return

    session = get_session()
    try:
        contrib = crear_contribuyente(
            session,
            **datos,
            jurisdicciones=jurisdicciones,
            actividades=actividades,
            coeficientes=coeficientes,
            alicuotas=alicuotas,
        )
        session.commit()
        contrib_id = contrib.id
        razon = contrib.razon_social
    except ValueError as e:
        st.error(str(e))
        return
    except Exception as e:
        st.error(f"Error inesperado: {e}")
        return
    finally:
        session.close()

    st.success(f"✅ Contribuyente **{razon}** creado exitosamente.")
    _limpiar_estado(key)
    st.session_state["contribuyente_id"] = contrib_id
    st.session_state["pantalla"] = "detalle"
    st.rerun()


def _limpiar_estado(key):
    for k in list(st.session_state.keys()):
        if k.startswith(key):
            del st.session_state[k]
