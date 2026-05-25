"""
Importador de 'Mis Comprobantes Emitidos' de ARCA/AFIP.
Formato: xlsx con encabezados en fila 2 (indice 1), datos desde fila 3.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from loguru import logger
import openpyxl

from iibb.calculo.cm03 import parse_decimal


TIPOS_NOTA_CREDITO = {"nota de crédito", "nota de credito", "nc"}
# Tipos de exportación: códigos AFIP 019 (Fac. E), 020 (ND E), 021 (NC E)
_CODIGOS_EXPORTACION = {"019", "020", "021", "19", "20", "21"}


@dataclass
class ComprobanteRow:
    fecha: date | None
    tipo: str
    punto_venta: int | None
    numero: int | None
    receptor_cuit: str | None
    receptor_nombre: str | None
    neto_gravado: Decimal = field(default_factory=lambda: Decimal("0"))
    neto_no_gravado: Decimal = field(default_factory=lambda: Decimal("0"))
    op_exentas: Decimal = field(default_factory=lambda: Decimal("0"))
    iva: Decimal = field(default_factory=lambda: Decimal("0"))
    total: Decimal = field(default_factory=lambda: Decimal("0"))
    signo: int = 1          # +1 factura/ND, -1 nota de credito
    es_exportacion: bool = False  # True para tipos 019/020/021 (Factura/ND/NC E)


def _es_nota_credito(tipo: str) -> bool:
    t = tipo.lower()
    return any(nc in t for nc in TIPOS_NOTA_CREDITO)


def _es_exportacion(tipo: str) -> bool:
    """Detecta Factura E (019), Nota de Débito E (020), Nota de Crédito E (021)."""
    t = tipo.strip()
    if t in _CODIGOS_EXPORTACION:
        return True
    partes = t.lower().split()
    # Texto tipo "Factura E", "Nota de Crédito E", "Nota de Débito E"
    if len(partes) >= 2 and partes[-1] == "e":
        return True
    return "exportac" in t.lower()


def _parse_date(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _safe_int(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _clean_cuit(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip().replace("-", "").replace(" ", "")
    if s.isdigit() and len(s) == 11:
        return f"{s[:2]}-{s[2:10]}-{s[10]}"
    return s if s else None


def import_mis_comprobantes_emitidos(path: str | Path) -> list[ComprobanteRow]:
    """
    Lee el archivo xlsx de Mis Comprobantes Emitidos de ARCA.
    Devuelve lista de ComprobanteRow con signo ya aplicado.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {path}")

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    # Fila 1 (indice 0): puede ser metadata, fila 2 (indice 1): headers, datos desde indice 2
    data_start = 2

    resultado: list[ComprobanteRow] = []

    for i, row in enumerate(rows[data_start:], start=data_start + 1):
        # Saltar filas completamente vacías
        if not any(cell is not None for cell in row):
            continue

        try:
            fecha = _parse_date(row[0] if len(row) > 0 else None)
            tipo = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            punto_venta = _safe_int(row[2]) if len(row) > 2 else None
            numero = _safe_int(row[3]) if len(row) > 3 else None
            receptor_cuit = _clean_cuit(row[7]) if len(row) > 7 else None
            receptor_nombre = str(row[8]).strip() if len(row) > 8 and row[8] else None
            neto_gravado = parse_decimal(row[22]) if len(row) > 22 else Decimal("0")
            neto_no_gravado = parse_decimal(row[23]) if len(row) > 23 else Decimal("0")
            op_exentas = parse_decimal(row[24]) if len(row) > 24 else Decimal("0")
            iva = parse_decimal(row[26]) if len(row) > 26 else Decimal("0")
            total = parse_decimal(row[27]) if len(row) > 27 else Decimal("0")
            signo = -1 if _es_nota_credito(tipo) else 1
            es_exp = _es_exportacion(tipo)
        except Exception as e:
            logger.warning(f"Fila {i} ignorada por error: {e}")
            continue

        if not tipo:
            continue

        resultado.append(
            ComprobanteRow(
                fecha=fecha,
                tipo=tipo,
                punto_venta=punto_venta,
                numero=numero,
                receptor_cuit=receptor_cuit,
                receptor_nombre=receptor_nombre,
                neto_gravado=neto_gravado,
                neto_no_gravado=neto_no_gravado,
                op_exentas=op_exentas,
                iva=iva,
                total=total,
                signo=signo,
                es_exportacion=es_exp,
            )
        )

    logger.info(f"Importados {len(resultado)} comprobantes de '{path.name}'.")
    return resultado


def summarize_comprobantes(rows: list[ComprobanteRow]) -> dict:
    """
    Devuelve un resumen con totales para la liquidación.

    Claves del dict:
      cant_facturas, cant_notas_credito, cant_exportacion,
      neto_gravado_facturas, neto_gravado_notas_credito,
      neto_gravado_neto   (base imponible IIBB: excluye exportaciones),
      neto_gravado_bruto  (informativo: incluye exportaciones),
      exportaciones_neto  (informativo: neto de comprobantes tipo E),
      iva_total, exento_total, no_gravado_total
    """
    from iibb.calculo.cm03 import q2

    # Separar exportaciones del resto
    non_exp = [r for r in rows if not r.es_exportacion]
    exp_rows = [r for r in rows if r.es_exportacion]

    facturas = [r for r in non_exp if r.signo == 1]
    notas_credito = [r for r in non_exp if r.signo == -1]

    ng_facturas = q2(sum((r.neto_gravado for r in facturas), Decimal("0")))
    ng_nc = q2(sum((r.neto_gravado for r in notas_credito), Decimal("0")))
    neto_neto = q2(ng_facturas - ng_nc)

    # Exportaciones (informativo, NO incluidas en base imponible)
    exportaciones_neto = q2(sum((r.neto_gravado * r.signo for r in exp_rows), Decimal("0")))

    # Total bruto incluyendo exportaciones (informativo)
    all_fact = [r for r in rows if r.signo == 1]
    all_nc = [r for r in rows if r.signo == -1]
    ng_bruto = q2(
        sum((r.neto_gravado for r in all_fact), Decimal("0")) -
        sum((r.neto_gravado for r in all_nc), Decimal("0"))
    )

    iva_total = q2(sum((r.iva * r.signo for r in rows), Decimal("0")))
    exento_total = q2(sum((r.op_exentas * r.signo for r in rows), Decimal("0")))
    no_gravado_total = q2(sum((r.neto_no_gravado * r.signo for r in rows), Decimal("0")))

    return {
        "cant_facturas": len(all_fact),
        "cant_notas_credito": len(all_nc),
        "cant_exportacion": len(exp_rows),
        "neto_gravado_facturas": ng_facturas,
        "neto_gravado_notas_credito": ng_nc,
        "neto_gravado_neto": neto_neto,         # base imponible IIBB
        "neto_gravado_bruto": ng_bruto,          # informativo
        "exportaciones_neto": exportaciones_neto,  # informativo
        "iva_total": iva_total,                  # informativo
        "exento_total": exento_total,
        "no_gravado_total": no_gravado_total,
    }
