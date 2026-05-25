"""
Importador SIRCREB Buenos Aires - ARBA.
Acepta tanto .xls (antiguo) como .xlsx.

Columnas (0-indexed):
  0 (A): CUIT del agente recaudador
  1 (B): Fecha
  10 (K): Importe a deducir

Las filas de encabezado se detectan porque la columna A no es numerica.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from loguru import logger

from iibb.calculo.cm03 import parse_decimal, q2


@dataclass
class ArbaSircrebRow:
    agente_cuit: str | None
    fecha: date | None
    importe: Decimal


def _parse_date_arba(val) -> date | None:
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


def _is_header_row(col_a) -> bool:
    """Una fila es de encabezado si la columna A no es numerica."""
    if col_a is None:
        return True
    try:
        float(str(col_a).replace("-", "").replace(" ", ""))
        return False
    except ValueError:
        return True


def import_arba_sircreb(path: str | Path) -> list[ArbaSircrebRow]:
    """
    Lee el archivo XLS/XLSX de SIRCREB Buenos Aires (ARBA).
    Ignora filas de encabezado (columna A no numerica).
    Devuelve lista de ArbaSircrebRow.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {path}")

    suffix = path.suffix.lower()
    rows_raw: list[tuple] = []

    if suffix == ".xls":
        try:
            import xlrd
            wb = xlrd.open_workbook(str(path))
            ws = wb.sheet_by_index(0)
            for r in range(ws.nrows):
                rows_raw.append(tuple(ws.row_values(r)))
        except Exception as e:
            raise RuntimeError(f"Error leyendo XLS de ARBA: {e}") from e
    else:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        for row in ws.iter_rows(values_only=True):
            rows_raw.append(row)
        wb.close()

    resultado: list[ArbaSircrebRow] = []

    for i, row in enumerate(rows_raw):
        if not row or all(c is None for c in row):
            continue

        col_a = row[0] if len(row) > 0 else None
        if _is_header_row(col_a):
            continue

        try:
            agente_cuit = str(col_a).strip().replace("-", "").replace(" ", "") or None
            fecha = _parse_date_arba(row[1] if len(row) > 1 else None)
            importe = parse_decimal(row[10]) if len(row) > 10 else Decimal("0")
        except Exception as e:
            logger.warning(f"Fila {i + 1} ARBA ignorada: {e}")
            continue

        resultado.append(
            ArbaSircrebRow(
                agente_cuit=agente_cuit,
                fecha=fecha,
                importe=importe,
            )
        )

    logger.info(f"SIRCREB BsAs: {len(resultado)} filas importadas de '{path.name}'.")
    return resultado


def total_imputado_arba(rows: list[ArbaSircrebRow]) -> Decimal:
    return q2(sum((r.importe for r in rows), Decimal("0")))
