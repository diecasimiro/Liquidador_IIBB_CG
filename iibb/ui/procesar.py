"""
Pantalla 'Procesar período CM03'.
Permite cargar los 3 archivos del período y las deducciones manuales.
"""
import io
import tempfile
from decimal import Decimal
from pathlib import Path

import streamlit as st

from iibb.calculo.cm03 import parse_decimal, DeduccionInput, JurisdiccionInput
from iibb.db import get_session
from iibb.importers.arca_comprobantes import import_mis_comprobantes_emitidos, summarize_comprobantes
from iibb.importers.agip_sircreb import import_agip_sircreb, total_imputado_agip
from iibb.importers.arba_sircreb import import_arba_sircreb, total_imputado_arba
from iibb.importers.deduccion_generica import import_deduccion_generica
from iibb.importers.sifere_deducciones import importar_sifere_deducciones
from iibb.service.liquidacion import esta_cerrado
from iibb.service.contribuyente import (
    obtener_contribuyente,
    obtener_coeficientes,
    obtener_alicuotas,
    obtener_jurisdicciones_activas,
)
from iibb.models.catalogos import Jurisdiccion

MESES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

TIPOS_DEDUCCION = [
    ("sircreb",       "SIRCREB"),
    ("percepcion",    "PERCEPCIONES SUFRIDAS"),
    ("retencion",     "RETENCIONES SUFRIDAS"),
    ("perc_aduanera", "PERCEPCIONES ADUANERAS"),
    ("pago_a_cuenta", "PAGOS A CUENTA"),
    ("saf_anterior",  "SALDO A FAVOR PERÍODO ANTERIOR"),
]


def _guardar_upload_temporal(uploaded_file) -> Path:
    """Guarda un UploadedFile en un archivo temporal y devuelve su Path."""
    suffix = Path(uploaded_file.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getvalue())
    tmp.close()
    return Path(tmp.name)


def render_procesar():
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

        # --- Header ---
        col_back, col_title, col_acciones = st.columns([1, 5, 1])
        with col_back:
            if st.button("← Volver"):
                st.session_state["pantalla"] = "detalle"
                st.rerun()
        with col_title:
            st.title(f"Procesar CM03 — {contrib.razon_social}")
        with col_acciones:
            accion = st.selectbox(
                "Acciones",
                options=["Acciones", "Generar Resumen Anual"],
                key="proc_accion",
                label_visibility="collapsed",
            )
            if accion == "Generar Resumen Anual":
                st.session_state["pantalla"] = "resumen_anual"
                st.rerun()

        # --- Selectores de período ---
        col_anio, col_mes = st.columns(2)
        with col_anio:
            anio = st.selectbox("Año", options=list(range(2024, 2031)),
                                index=list(range(2024, 2031)).index(2026),
                                key="proc_anio")
        with col_mes:
            mes = st.selectbox("Mes", options=list(range(1, 13)),
                               format_func=lambda m: MESES[m],
                               index=3, key="proc_mes")

        st.markdown("---")

        # --- Jurisdicciones del contribuyente ---
        coefs = obtener_coeficientes(session, contrib_id, anio)
        alics = obtener_alicuotas(session, contrib_id, anio)
        juris_inscriptas = obtener_jurisdicciones_activas(session, contrib_id)

        if not coefs:
            st.error(f"Sin coeficientes para el año {anio}. Verificá los datos del contribuyente.")
            return

        juris_codigos = [ji.jurisdiccion_codigo for ji in juris_inscriptas]
        juris_nombres = {}
        for codigo in juris_codigos:
            j = session.get(Jurisdiccion, codigo)
            juris_nombres[codigo] = j.nombre_corto if j else codigo

        # --- Archivo de comprobantes ---
        st.subheader("Ventas del período")
        st.caption(
            "Importá el archivo de Mis Comprobantes de ARCA para calcular la base imponible del período."
        )

        upload_comp = None
        bienes_uso_key = f"bienes_uso_{contrib_id}_{anio}_{mes}"

        with st.expander("📥 IMPORTAR MIS COMPROBANTES", expanded=False):
            st.markdown(
                "Importá el excel de los comprobantes emitidos que se exporta desde el servicio "
                "**MIS COMPROBANTES** de ARCA.  \n"
                "La app detecta automáticamente exportaciones (Factura E / NC E / ND E) y las excluye "
                "de la base imponible."
            )
            upload_comp = st.file_uploader(
                "Archivo Excel de Mis Comprobantes",
                type=["xlsx"],
                key="upload_comprobantes",
                label_visibility="collapsed",
            )
            if upload_comp:
                st.success(f"Archivo cargado: {upload_comp.name}")
                col_bu, col_bu_help = st.columns([2, 3])
                with col_bu:
                    st.text_input(
                        "Ventas de bienes de uso / Montos no Gravados y Exentos ($)",
                        value=st.session_state.get(bienes_uso_key, "0"),
                        key=bienes_uso_key,
                        placeholder="0.00",
                    )
                with col_bu_help:
                    st.caption(
                        "Ingresá el total de ventas de bienes de uso y/o montos no gravados y exentos "
                        "del período. Este importe **se excluye de la base imponible** del CM03 "
                        "y se informa a modo informativo en el papel de trabajo."
                    )

        st.markdown("---")

        # --- Grilla de deducciones ---
        st.subheader("Deducciones por jurisdicción")
        st.caption(
            "Escribí el importe a mano **o** subí un archivo (📂) — la app suma todos los importes "
            "del archivo automáticamente. El SAF se prellena cuando hay un período anterior calculado."
        )

        # Estado de deducciones en session_state
        ded_key = f"ded_{contrib_id}_{anio}_{mes}"
        ded_ver_key = f"ded_ver_{ded_key}"
        if ded_key not in st.session_state:
            st.session_state[ded_key] = {
                tipo: {codigo: "0" for codigo in juris_codigos}
                for tipo, _ in TIPOS_DEDUCCION
            }
        if ded_ver_key not in st.session_state:
            st.session_state[ded_ver_key] = 0
        ded_state = st.session_state[ded_key]
        ded_ver = st.session_state[ded_ver_key]

        # ── Aplicar datos SIFERE pendientes ANTES de renderizar la grilla ─────
        # Estrategia: al aplicar SIFERE se incrementa el contador de versión.
        # Esto hace que todas las claves de los text_input sean nuevas → Streamlit
        # las inicializa desde value= (que ya tiene el dato SIFERE), sin conflicto.
        sifere_pendiente_key = f"sifere_pendiente_{ded_key}"
        if sifere_pendiente_key in st.session_state:
            datos_p = st.session_state.pop(sifere_pendiente_key)
            cargados_p = 0
            for tipo_key, vals_por_jur in datos_p.items():
                for codigo, monto in vals_por_jur.items():
                    if codigo in juris_codigos:
                        ded_state[tipo_key][codigo] = str(monto)
                        if monto != Decimal("0"):
                            cargados_p += 1
            # Incrementar versión → fuerza nuevas claves de widget en la grilla
            st.session_state[ded_ver_key] += 1
            ded_ver = st.session_state[ded_ver_key]
            st.success(
                f"✅ Deducciones SIFERE cargadas: {cargados_p} valor(es) distinto de cero."
            )

        # ── Importar desde SIFERE Web ─────────────────────────────────────────
        with st.expander("📥 IMPORTAR DEDUCCIONES SIFERE WEB", expanded=False):
            st.markdown(
                "**¿Cómo exportar el archivo?**  \n"
                "En SIFERE Web, al finalizar la carga de Deducciones, entrá a "
                "**Datos de Deducciones** y hacé clic en **Exportar a Excel**.  \n"
                "Ese archivo es el que debés subir acá — la app va a completar "
                "automáticamente la grilla con Retenciones, SIRCREB, Percepciones "
                "y Percepciones Aduaneras para cada jurisdicción."
            )
            upload_sifere = st.file_uploader(
                "Archivo Excel de SIFERE Web",
                type=["xlsx"],
                key=f"upload_sifere_{ded_key}",
            )
            if upload_sifere:
                if st.button("⬆️ Cargar deducciones desde SIFERE", type="primary",
                             key=f"btn_sifere_{ded_key}"):
                    tmp_sif = _guardar_upload_temporal(upload_sifere)
                    try:
                        datos_sifere = importar_sifere_deducciones(tmp_sif)
                        st.session_state[sifere_pendiente_key] = datos_sifere
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al leer el archivo: {e}")
                    finally:
                        tmp_sif.unlink(missing_ok=True)

        st.markdown("---")

        # Cabecera de la grilla
        n_juris = len(juris_codigos)
        cols_header = st.columns([3] + [2] * n_juris)
        cols_header[0].markdown("**Concepto**")
        for i, codigo in enumerate(juris_codigos):
            cols_header[i + 1].markdown(f"**{juris_nombres[codigo]}**")

        for tipo_key, tipo_label in TIPOS_DEDUCCION:
            cols = st.columns([3] + [2] * n_juris)
            cols[0].markdown(tipo_label)
            for i, codigo in enumerate(juris_codigos):
                col_inner = cols[i + 1]
                with col_inner:
                    tab_inp, tab_file = st.tabs(["✏️ Manual", "📂 Archivo"])
                    with tab_inp:
                        # La clave incluye ded_ver: al cambiar la versión (import SIFERE)
                        # el widget es nuevo y Streamlit usa value= sin conflicto de estado.
                        val = st.text_input(
                            label=f"{tipo_label} {codigo}",
                            value=ded_state[tipo_key][codigo],
                            key=f"ded_{tipo_key}_{codigo}_{anio}_{mes}_v{ded_ver}",
                            label_visibility="collapsed",
                        )
                        ded_state[tipo_key][codigo] = val
                    with tab_file:
                        up = st.file_uploader(
                            f"Archivo {tipo_label} {codigo}",
                            type=["xlsx", "xls", "csv"],
                            key=f"file_{tipo_key}_{codigo}_{anio}_{mes}",
                            label_visibility="collapsed",
                        )
                        if up:
                            tmp = _guardar_upload_temporal(up)
                            try:
                                total = import_deduccion_generica(tmp)
                                ded_state[tipo_key][codigo] = str(total)
                                st.success(f"${total:,.2f}")
                            except Exception as e:
                                st.error(str(e))
                            finally:
                                tmp.unlink(missing_ok=True)

        st.markdown("---")

        # Avisar si el período ya está cerrado
        if esta_cerrado(session, contrib_id, anio, mes):
            st.warning(
                f"⚠️ El período **{MESES[mes]} {anio}** ya tiene una DDJJ cerrada. "
                "Si procesás de nuevo se guardará como **rectificativa** cuando cierres. "
                "Para editar el cierre existente, andá al resultado anterior y usá **🔓 Reabrir período**."
            )

        # --- Botón procesar ---
        if st.button("⚡ Procesar y calcular", type="primary"):
            _ejecutar_calculo(
                session=session,
                contrib=contrib,
                anio=anio,
                mes=mes,
                upload_comp=upload_comp,
                ded_state=ded_state,
                coefs=coefs,
                alics=alics,
                juris_inscriptas=juris_inscriptas,
                juris_nombres=juris_nombres,
                bienes_uso_str=st.session_state.get(bienes_uso_key, "0"),
            )

    finally:
        session.close()


def _ejecutar_calculo(
    session, contrib, anio, mes, upload_comp,
    ded_state, coefs, alics, juris_inscriptas, juris_nombres,
    bienes_uso_str: str = "0",
):
    from iibb.calculo.cm03 import calcular_cm03, q2

    logs = st.container()

    with st.spinner("Calculando..."):
        try:
            bienes_uso = q2(parse_decimal(bienes_uso_str))

            # --- Comprobantes ---
            comprobantes = []
            exportaciones_neto = Decimal("0")
            ingresos_brutos = Decimal("0")
            iva_total = Decimal("0")
            if upload_comp:
                tmp_comp = _guardar_upload_temporal(upload_comp)
                try:
                    comprobantes = import_mis_comprobantes_emitidos(tmp_comp)
                finally:
                    tmp_comp.unlink(missing_ok=True)
                resumen = summarize_comprobantes(comprobantes)
                exportaciones_neto = resumen["exportaciones_neto"]
                ingresos_brutos = resumen["neto_gravado_bruto"]
                iva_total = resumen["iva_total"]
                # neto_gravado_neto ya excluye exportaciones; restamos bienes de uso
                ingresos_totales = q2(resumen["neto_gravado_neto"] - bienes_uso)
                msg = (
                    f"Comprobantes: {resumen['cant_facturas']} facturas, "
                    f"{resumen['cant_notas_credito']} NC"
                )
                if resumen["cant_exportacion"]:
                    msg += f", {resumen['cant_exportacion']} exportacion(es) excluidas"
                msg += f" — Base imponible IIBB: ${ingresos_totales:,.2f}"
                logs.info(msg)
            else:
                st.warning("No se cargó archivo de comprobantes. Ingresá el neto gravado manualmente.")
                ingresos_totales_str = st.text_input(
                    "Neto gravado del mes ($)", "0", key="ing_manual"
                )
                ingresos_totales = q2(parse_decimal(ingresos_totales_str) - bienes_uso)

            # --- Construir inputs de jurisdicciones ---
            juris_inputs = []
            saf_map = {}
            for ji in juris_inscriptas:
                codigo = ji.jurisdiccion_codigo
                coef = next((c.valor for c in coefs if c.jurisdiccion_codigo == codigo), Decimal("0"))
                alic = next((a.valor for a in alics if a.jurisdiccion_codigo == codigo), Decimal("0"))
                saf = q2(parse_decimal(ded_state.get("saf_anterior", {}).get(codigo, "0")))
                saf_map[codigo] = saf
                juris_inputs.append(
                    JurisdiccionInput(
                        codigo=codigo,
                        nombre=juris_nombres.get(codigo, codigo),
                        coeficiente=coef,
                        alicuota=alic,
                        saf_anterior=saf,
                    )
                )

            # --- Construir deducciones ---
            deducciones = []
            for tipo_key, _ in [
                ("sircreb", ""), ("percepcion", ""), ("retencion", ""),
                ("perc_aduanera", ""), ("pago_a_cuenta", ""),
            ]:
                for ji in juris_inscriptas:
                    codigo = ji.jurisdiccion_codigo
                    val_str = ded_state.get(tipo_key, {}).get(codigo, "0")
                    monto = q2(parse_decimal(val_str))
                    if monto != Decimal("0"):
                        deducciones.append(DeduccionInput(codigo, tipo_key, monto))

            # --- Calcular ---
            liq = calcular_cm03(
                contribuyente_cuit=contrib.cuit,
                contribuyente_razon=contrib.razon_social,
                anio=anio,
                mes=mes,
                ingresos_totales=ingresos_totales,
                jurisdicciones=juris_inputs,
                deducciones=deducciones,
                ingresos_brutos=ingresos_brutos,
                exportaciones=exportaciones_neto,
                bienes_uso_no_gravados=bienes_uso,
                iva_total=iva_total,
            )

            # Guardar en session_state para mostrar en pantalla resultado
            st.session_state["liquidacion"] = liq
            st.session_state["comprobantes"] = comprobantes
            st.session_state["pantalla"] = "resultado"
            st.rerun()

        except Exception as e:
            st.error(f"Error al calcular: {e}")
            raise
