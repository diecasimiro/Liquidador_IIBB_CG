"""
Consulta el resumen anual de un contribuyente a partir de los ResultadoJurisdiccion
ya guardados en la BD por cada período liquidado.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from iibb.models.deduccion import ResultadoJurisdiccion
from iibb.models.periodo import Periodo


@dataclass
class FilaResumenAnual:
    codigo: str
    nombre: str
    base_imponible: Decimal = Decimal("0")
    impuesto_determinado: Decimal = Decimal("0")
    retenciones: Decimal = Decimal("0")
    percepciones: Decimal = Decimal("0")
    perc_aduaneras: Decimal = Decimal("0")
    sircreb: Decimal = Decimal("0")
    saldo_a_favor_dic: Decimal = Decimal("0")   # saldo_a_favor del mes 12
    iibb_a_pagar: Decimal = Decimal("0")         # suma de monto_a_pagar


@dataclass
class ResumenAnual:
    contribuyente_id: int
    anio: int
    meses_liquidados: list[int] = field(default_factory=list)
    filas: list[FilaResumenAnual] = field(default_factory=list)


def obtener_resumen_anual(
    session: Session,
    contribuyente_id: int,
    anio: int,
) -> ResumenAnual:
    """
    Devuelve el resumen anual consolidado.
    Para cada jurisdicción suma todos los campos de los meses liquidados.
    El saldo_a_favor_dic viene del período de mes=12 (última secuencia).
    """
    # Solo períodos CERRADOS, ordenados por mes y secuencia desc (última rectificativa)
    periodos = (
        session.query(Periodo)
        .filter_by(contribuyente_id=contribuyente_id, formulario="CM03",
                   anio=anio, estado="cerrado")
        .order_by(Periodo.mes, Periodo.secuencia.desc())
        .all()
    )

    if not periodos:
        return ResumenAnual(contribuyente_id=contribuyente_id, anio=anio)

    # Un período por mes: quedar con la última secuencia (la primera en la lista por el ORDER)
    ultimo_por_mes: dict[int, Periodo] = {}
    for p in periodos:
        if p.mes not in ultimo_por_mes:
            ultimo_por_mes[p.mes] = p

    meses_liquidados = sorted(ultimo_por_mes.keys())

    # Acumular resultados por jurisdicción
    acumulado: dict[str, FilaResumenAnual] = {}

    for mes, periodo in ultimo_por_mes.items():
        resultados = (
            session.query(ResultadoJurisdiccion)
            .filter_by(periodo_id=periodo.id)
            .all()
        )
        for r in resultados:
            if r.jurisdiccion_codigo not in acumulado:
                acumulado[r.jurisdiccion_codigo] = FilaResumenAnual(
                    codigo=r.jurisdiccion_codigo,
                    nombre=r.jurisdiccion_nombre,
                )
            fila = acumulado[r.jurisdiccion_codigo]
            fila.base_imponible       += r.base_imponible
            fila.impuesto_determinado += r.impuesto_determinado
            fila.retenciones          += r.retenciones
            fila.percepciones         += r.percepciones
            fila.perc_aduaneras       += r.perc_aduaneras
            fila.sircreb              += r.sircreb
            fila.iibb_a_pagar         += r.monto_a_pagar
            # Saldo a favor: solo del mes 12
            if mes == 12:
                fila.saldo_a_favor_dic = r.saldo_a_favor

    filas = sorted(acumulado.values(), key=lambda f: f.codigo)
    return ResumenAnual(
        contribuyente_id=contribuyente_id,
        anio=anio,
        meses_liquidados=meses_liquidados,
        filas=filas,
    )
