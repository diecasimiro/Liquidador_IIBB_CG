"""
Motor de calculo CM03 - Regimen General Art. 2 Convenio Multilateral.
Funcion pura: no toca la base de datos. Recibe dataclasses, devuelve dataclasses.
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP


def q2(value) -> Decimal:
    """Redondea a 2 decimales con redondeo comercial (ROUND_HALF_UP)."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_decimal(s: str | float | int | Decimal | None) -> Decimal:
    """Convierte string con formato argentino u otro tipo numerico a Decimal."""
    if s is None:
        return Decimal("0")
    if isinstance(s, Decimal):
        return s
    if isinstance(s, (int, float)):
        return Decimal(str(s))
    s = str(s).strip().replace(" ", "").replace("$", "").replace("\xa0", "")
    if not s or s == "-":
        return Decimal("0")
    # Formato argentino: si tiene coma y (no tiene punto, o la coma va despues del punto)
    if "," in s and ("." not in s or s.rfind(",") > s.rfind(".")):
        s = s.replace(".", "").replace(",", ".")
    return Decimal(s)


def fmt_money(value) -> str:
    """Formatea un Decimal como $ 1.234.567,89 (formato argentino)."""
    d = q2(value)
    sign = "-" if d < 0 else ""
    abs_val = abs(d)
    integer, _, decimals = f"{abs_val:.2f}".partition(".")
    integer_with_dots = "{:,}".format(int(integer)).replace(",", ".")
    return f"{sign}$ {integer_with_dots},{decimals}"


@dataclass
class JurisdiccionInput:
    codigo: str
    nombre: str
    coeficiente: Decimal
    alicuota: Decimal
    saf_anterior: Decimal = field(default_factory=lambda: Decimal("0"))


@dataclass
class DeduccionInput:
    jurisdiccion: str
    tipo: str  # retencion | percepcion | sircreb | perc_aduanera | pago_a_cuenta
    monto: Decimal


@dataclass
class ResultadoJurisdiccionCalc:
    codigo: str
    nombre: str
    coeficiente: Decimal
    alicuota: Decimal
    base_imponible: Decimal
    impuesto_determinado: Decimal
    saf_anterior: Decimal
    retenciones: Decimal
    percepciones: Decimal
    sircreb: Decimal
    perc_aduaneras: Decimal
    pagos_a_cuenta: Decimal
    total_deducciones: Decimal
    monto_a_pagar: Decimal
    saldo_a_favor: Decimal


@dataclass
class LiquidacionCM03:
    contribuyente_cuit: str
    contribuyente_razon: str
    anio: int
    mes: int
    ingresos_totales: Decimal       # base imponible neta usada en el cálculo
    resultados: list[ResultadoJurisdiccionCalc]
    monto_total_a_pagar: Decimal
    # Campos informativos (no afectan el cálculo, se muestran en el papel de trabajo)
    ingresos_brutos: Decimal = field(default_factory=lambda: Decimal("0"))
    exportaciones: Decimal = field(default_factory=lambda: Decimal("0"))
    bienes_uso_no_gravados: Decimal = field(default_factory=lambda: Decimal("0"))
    iva_total: Decimal = field(default_factory=lambda: Decimal("0"))


def calcular_cm03(
    contribuyente_cuit: str,
    contribuyente_razon: str,
    anio: int,
    mes: int,
    ingresos_totales: Decimal,
    jurisdicciones: list[JurisdiccionInput],
    deducciones: list[DeduccionInput],
    ingresos_brutos: Decimal | None = None,
    exportaciones: Decimal = Decimal("0"),
    bienes_uso_no_gravados: Decimal = Decimal("0"),
    iva_total: Decimal = Decimal("0"),
) -> LiquidacionCM03:
    """
    Calcula el CM03 para un contribuyente bajo Regimen General (Art. 2 CM).

    Cada jurisdiccion se calcula independientemente.
    Los saldos a favor NO se cruzan entre jurisdicciones.
    Toda la matematica se hace con Decimal y ROUND_HALF_UP.
    """
    ingresos_totales = q2(ingresos_totales)

    # Validar que los coeficientes sumen 1 (tolerancia 0.0001)
    suma_coef = sum((j.coeficiente for j in jurisdicciones), Decimal("0"))
    if abs(suma_coef - Decimal("1.0000")) > Decimal("0.0001"):
        raise ValueError(
            f"La suma de coeficientes debe ser 1.0000 (actual: {suma_coef}). "
            "Verificar coeficientes del contribuyente."
        )

    # Agrupar deducciones por jurisdiccion y tipo
    ded_map: dict[str, dict[str, Decimal]] = {}
    for d in deducciones:
        if d.jurisdiccion not in ded_map:
            ded_map[d.jurisdiccion] = {}
        tipo = d.tipo
        ded_map[d.jurisdiccion][tipo] = ded_map[d.jurisdiccion].get(tipo, Decimal("0")) + q2(d.monto)

    resultados: list[ResultadoJurisdiccionCalc] = []

    for j in jurisdicciones:
        coef = Decimal(str(j.coeficiente))
        alic = Decimal(str(j.alicuota))
        saf_ant = q2(j.saf_anterior)

        base_imponible = q2(ingresos_totales * coef)
        impuesto_determinado = q2(base_imponible * alic)

        juris_deds = ded_map.get(j.codigo, {})
        retenciones = q2(juris_deds.get("retencion", Decimal("0")))
        percepciones = q2(juris_deds.get("percepcion", Decimal("0")))
        sircreb = q2(juris_deds.get("sircreb", Decimal("0")))
        perc_aduaneras = q2(juris_deds.get("perc_aduanera", Decimal("0")))
        pagos_a_cuenta = q2(juris_deds.get("pago_a_cuenta", Decimal("0")))

        total_deducciones = q2(
            saf_ant + retenciones + percepciones + sircreb + perc_aduaneras + pagos_a_cuenta
        )

        diferencia = impuesto_determinado - total_deducciones
        if diferencia > Decimal("0"):
            monto_a_pagar = q2(diferencia)
            saldo_a_favor = Decimal("0.00")
        else:
            monto_a_pagar = Decimal("0.00")
            saldo_a_favor = q2(-diferencia)

        resultados.append(
            ResultadoJurisdiccionCalc(
                codigo=j.codigo,
                nombre=j.nombre,
                coeficiente=coef,
                alicuota=alic,
                base_imponible=base_imponible,
                impuesto_determinado=impuesto_determinado,
                saf_anterior=saf_ant,
                retenciones=retenciones,
                percepciones=percepciones,
                sircreb=sircreb,
                perc_aduaneras=perc_aduaneras,
                pagos_a_cuenta=pagos_a_cuenta,
                total_deducciones=total_deducciones,
                monto_a_pagar=monto_a_pagar,
                saldo_a_favor=saldo_a_favor,
            )
        )

    monto_total = q2(sum((r.monto_a_pagar for r in resultados), Decimal("0")))

    return LiquidacionCM03(
        contribuyente_cuit=contribuyente_cuit,
        contribuyente_razon=contribuyente_razon,
        anio=anio,
        mes=mes,
        ingresos_totales=ingresos_totales,
        resultados=resultados,
        monto_total_a_pagar=monto_total,
        ingresos_brutos=q2(ingresos_brutos) if ingresos_brutos is not None else ingresos_totales,
        exportaciones=q2(exportaciones),
        bienes_uso_no_gravados=q2(bienes_uso_no_gravados),
        iva_total=q2(iva_total),
    )
