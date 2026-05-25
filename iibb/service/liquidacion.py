"""
Servicio de liquidacion: orquesta DB + motor de calculo + persistencia del resultado.
"""
from decimal import Decimal
from sqlalchemy.orm import Session

from iibb.calculo.cm03 import (
    JurisdiccionInput,
    DeduccionInput,
    LiquidacionCM03,
    calcular_cm03,
)
from iibb.models.contribuyente import CoeficienteAnual, Alicuota
from iibb.models.deduccion import ResultadoJurisdiccion
from iibb.models.periodo import Periodo, ComprobanteEmitido, SaldoAFavorAnterior
from iibb.models.deduccion import Deduccion
from iibb.service.contribuyente import (
    obtener_contribuyente,
    obtener_coeficientes,
    obtener_alicuotas,
    obtener_jurisdicciones_activas,
)
from iibb.importers.arca_comprobantes import ComprobanteRow, summarize_comprobantes


def _coef_y_alicuota_para_juris(
    coeficientes: list[CoeficienteAnual],
    alicuotas: list[Alicuota],
    juris_codigo: str,
) -> tuple[Decimal, Decimal]:
    coef = next((c.valor for c in coeficientes if c.jurisdiccion_codigo == juris_codigo), Decimal("0"))
    # Usar la alicuota de la primera actividad que tenga una para esta jurisdiccion
    alic = next((a.valor for a in alicuotas if a.jurisdiccion_codigo == juris_codigo), Decimal("0"))
    return coef, alic


def calcular_y_guardar_cm03(
    session: Session,
    contribuyente_id: int,
    anio: int,
    mes: int,
    comprobantes: list[ComprobanteRow],
    deducciones_extra: list[DeduccionInput] | None = None,
    saf_anteriores: dict[str, Decimal] | None = None,
    tenant_id: int = 1,
) -> tuple[LiquidacionCM03, Periodo]:
    """
    Calcula el CM03, guarda el período y los resultados en la base de datos.
    Devuelve (liquidacion_calculada, periodo_guardado).
    """
    contrib = obtener_contribuyente(session, contribuyente_id)
    if not contrib:
        raise ValueError(f"Contribuyente {contribuyente_id} no encontrado.")

    coefs = obtener_coeficientes(session, contribuyente_id, anio)
    alics = obtener_alicuotas(session, contribuyente_id, anio)
    juris_inscriptas = obtener_jurisdicciones_activas(session, contribuyente_id)

    if not coefs:
        raise ValueError(f"Sin coeficientes para el año {anio}.")

    # Calcular ingresos del mes a partir de los comprobantes
    resumen = summarize_comprobantes(comprobantes)
    ingresos_totales = resumen["neto_gravado_neto"]

    # Construir inputs para el motor
    juris_inputs = []
    for ji in juris_inscriptas:
        coef, alic = _coef_y_alicuota_para_juris(coefs, alics, ji.jurisdiccion_codigo)
        saf = (saf_anteriores or {}).get(ji.jurisdiccion_codigo, Decimal("0"))
        juris_inputs.append(
            JurisdiccionInput(
                codigo=ji.jurisdiccion_codigo,
                nombre=ji.jurisdiccion_codigo,  # se completa con el nombre al mostrar
                coeficiente=coef,
                alicuota=alic,
                saf_anterior=saf,
            )
        )

    # Agregar nombres de jurisdiccion
    from iibb.models.catalogos import Jurisdiccion
    for ji_input in juris_inputs:
        j = session.get(Jurisdiccion, ji_input.codigo)
        if j:
            ji_input.nombre = j.nombre

    # Deducciones (SIRCREB, retenciones, etc.)
    all_deds = list(deducciones_extra or [])

    # Calcular
    liq = calcular_cm03(
        contribuyente_cuit=contrib.cuit,
        contribuyente_razon=contrib.razon_social,
        anio=anio,
        mes=mes,
        ingresos_totales=ingresos_totales,
        jurisdicciones=juris_inputs,
        deducciones=all_deds,
    )

    # Determinar secuencia (rectificativa si ya existe un periodo para este mes)
    secuencia = 0
    existing = (
        session.query(Periodo)
        .filter_by(contribuyente_id=contribuyente_id, formulario="CM03", anio=anio, mes=mes)
        .order_by(Periodo.secuencia.desc())
        .first()
    )
    if existing:
        secuencia = existing.secuencia + 1

    # Crear el periodo
    periodo = Periodo(
        tenant_id=tenant_id,
        contribuyente_id=contribuyente_id,
        formulario="CM03",
        anio=anio,
        mes=mes,
        secuencia=secuencia,
        estado="calculado",
        ingresos_gravados=resumen["neto_gravado_neto"],
        ingresos_no_gravados=resumen["no_gravado_total"],
        ingresos_exentos=resumen["exento_total"],
        iva_debito=resumen["iva_total"],
    )
    session.add(periodo)
    session.flush()

    # Guardar comprobantes
    for row in comprobantes:
        session.add(ComprobanteEmitido(
            tenant_id=tenant_id,
            periodo_id=periodo.id,
            fecha=row.fecha,
            tipo=row.tipo,
            punto_venta=row.punto_venta,
            numero=row.numero,
            receptor_cuit=row.receptor_cuit,
            receptor_nombre=row.receptor_nombre,
            neto_gravado=row.neto_gravado,
            neto_no_gravado=row.neto_no_gravado,
            op_exentas=row.op_exentas,
            iva=row.iva,
            total=row.total,
            signo=row.signo,
        ))

    # Guardar deducciones
    for d in all_deds:
        session.add(Deduccion(
            tenant_id=tenant_id,
            periodo_id=periodo.id,
            jurisdiccion_codigo=d.jurisdiccion,
            tipo=d.tipo,
            monto=d.monto,
            origen="importado",
        ))

    # Guardar SAF anteriores
    for juris_cod, monto in (saf_anteriores or {}).items():
        if monto > Decimal("0"):
            session.add(SaldoAFavorAnterior(
                tenant_id=tenant_id,
                periodo_id=periodo.id,
                jurisdiccion_codigo=juris_cod,
                monto=monto,
            ))

    # Guardar resultados por jurisdiccion
    for r in liq.resultados:
        session.add(ResultadoJurisdiccion(
            tenant_id=tenant_id,
            periodo_id=periodo.id,
            jurisdiccion_codigo=r.codigo,
            jurisdiccion_nombre=r.nombre,
            coeficiente=r.coeficiente,
            alicuota=r.alicuota,
            base_imponible=r.base_imponible,
            impuesto_determinado=r.impuesto_determinado,
            saf_anterior=r.saf_anterior,
            retenciones=r.retenciones,
            percepciones=r.percepciones,
            sircreb=r.sircreb,
            perc_aduaneras=r.perc_aduaneras,
            pagos_a_cuenta=r.pagos_a_cuenta,
            total_deducciones=r.total_deducciones,
            monto_a_pagar=r.monto_a_pagar,
            saldo_a_favor=r.saldo_a_favor,
        ))

    session.commit()
    return liq, periodo


def obtener_ultimo_periodo(
    session: Session,
    contribuyente_id: int,
    anio: int,
    mes: int,
) -> "Periodo | None":
    """Devuelve el período más reciente (mayor secuencia) para ese mes/año."""
    return (
        session.query(Periodo)
        .filter_by(contribuyente_id=contribuyente_id, formulario="CM03",
                   anio=anio, mes=mes)
        .order_by(Periodo.secuencia.desc())
        .first()
    )


def esta_cerrado(
    session: Session,
    contribuyente_id: int,
    anio: int,
    mes: int,
) -> bool:
    p = obtener_ultimo_periodo(session, contribuyente_id, anio, mes)
    return p is not None and p.estado == "cerrado"


def reabrir_periodo(
    session: Session,
    contribuyente_id: int,
    anio: int,
    mes: int,
) -> bool:
    """Cambia el estado del último período a 'abierto'. Devuelve True si lo encontró."""
    p = obtener_ultimo_periodo(session, contribuyente_id, anio, mes)
    if p is None:
        return False
    p.estado = "abierto"
    session.flush()
    return True


def cerrar_periodo(
    session: Session,
    contribuyente_id: int,
    liq: "LiquidacionCM03",
    tenant_id: int = 1,
) -> Periodo:
    """
    Persiste el resultado de una liquidación como período CERRADO.
    Si ya existe un período cerrado para ese mes/año se crea una rectificativa
    (secuencia incremental), respetando la inmutabilidad de períodos presentados.
    Devuelve el Periodo guardado.
    """
    existing = (
        session.query(Periodo)
        .filter_by(
            contribuyente_id=contribuyente_id,
            formulario="CM03",
            anio=liq.anio,
            mes=liq.mes,
        )
        .order_by(Periodo.secuencia.desc())
        .first()
    )
    secuencia = (existing.secuencia + 1) if existing else 0

    periodo = Periodo(
        tenant_id=tenant_id,
        contribuyente_id=contribuyente_id,
        formulario="CM03",
        anio=liq.anio,
        mes=liq.mes,
        secuencia=secuencia,
        estado="cerrado",
        ingresos_gravados=liq.ingresos_totales,
    )
    session.add(periodo)
    session.flush()

    for r in liq.resultados:
        session.add(ResultadoJurisdiccion(
            tenant_id=tenant_id,
            periodo_id=periodo.id,
            jurisdiccion_codigo=r.codigo,
            jurisdiccion_nombre=r.nombre,
            coeficiente=r.coeficiente,
            alicuota=r.alicuota,
            base_imponible=r.base_imponible,
            impuesto_determinado=r.impuesto_determinado,
            saf_anterior=r.saf_anterior,
            retenciones=r.retenciones,
            percepciones=r.percepciones,
            sircreb=r.sircreb,
            perc_aduaneras=r.perc_aduaneras,
            pagos_a_cuenta=r.pagos_a_cuenta,
            total_deducciones=r.total_deducciones,
            monto_a_pagar=r.monto_a_pagar,
            saldo_a_favor=r.saldo_a_favor,
        ))

    session.flush()
    return periodo
