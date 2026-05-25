"""
Importador generico para retenciones, percepciones y otros archivos de deducciones.
Lee xlsx/xls/csv y suma todos los importes de la columna que parezca ser de montos.

Heuristica para detectar la columna de importes:
  1. Header con palabras: importe, monto, valor, total, deduccion, recaudado.
  2. Si no, columna con mas valores numericos no enteros.
  3. Ignorar valores >100_000_000_000 (probablemente CUITs).
"""
from decimal import Decimal
from pathlib import Path
from loguru import logger

from iibb.calculo.cm03 import parse_decimal, q2

_PALABRAS_IMPORTE = {"importe", "monto", "valor", "total", "deduccion", "recaudado", "retencion", "percepcion"}


def _detectar_columna_importe(headers: list[str], data_rows: list[list]) -> int:
    """Retorna el indice de la columna de importes."""
    # Intento 1: buscar por nombre de header
    for i, h in enumerate(headers):
        if h and any(p in h.lower() for p in _PALABRAS_IMPORTE):
            return i

    # Intento 2: columna con mas floats validos no enteros, excluyendo CUITs
    scores = [0] * max((len(r) for r in data_rows), default=1)
    for row in data_rows:
        for j, cell in enumerate(row):
            if j >= len(scores):
                break
            try:
                v = float(str(cell).replace(",", ".").replace("$", "").strip())
                if 0 < abs(v) < 100_000_000_000 and v != int(v):
                    scores[j] += 1
            except (ValueError, TypeError):
                pass

    return scores.index(max(scores)) if any(s > 0 for s in scores) else 0


def import_deduccion_generica(path: str | Path) -> Decimal:
    """
    Lee el archivo y devuelve la suma de todos los importes detectados.
    Acepta xlsx, xls, csv.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {path}")

    suffix = path.suffix.lower()
    headers: list[str] = []
    data_rows: list[list] = []

    if suffix == ".csv":
        import csv
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            lines = f.readlines()
        # Saltar "sep=," si existe
        start = 1 if lines and lines[0].strip().lower().startswith("sep=") else 0
        reader = csv.reader(lines[start:])
        all_rows = list(reader)
        if all_rows:
            headers = [str(c).strip() for c in all_rows[0]]
            data_rows = [list(r) for r in all_rows[1:]]

    elif suffix == ".xls":
        import xlrd
        wb = xlrd.open_workbook(str(path))
        ws = wb.sheet_by_index(0)
        all_raw = [ws.row_values(r) for r in range(ws.nrows)]
        if all_raw:
            headers = [str(c).strip() for c in all_raw[0]]
            data_rows = [list(r) for r in all_raw[1:]]

    else:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        all_raw = list(ws.iter_rows(values_only=True))
        wb.close()
        if all_raw:
            headers = [str(c).strip() if c is not None else "" for c in all_raw[0]]
            data_rows = [list(r) for r in all_raw[1:]]

    if not data_rows:
        logger.warning(f"'{path.name}' no tiene datos.")
        return Decimal("0")

    col_idx = _detectar_columna_importe(headers, data_rows)
    logger.info(f"'{path.name}': usando columna {col_idx} ('{headers[col_idx] if col_idx < len(headers) else '?'}') para importes.")

    total = Decimal("0")
    for row in data_rows:
        if col_idx >= len(row):
            continue
        val = row[col_idx]
        if val is None:
            continue
        try:
            d = parse_decimal(val)
            if abs(d) < Decimal("100000000000"):
                total += d
        except Exception:
            pass

    return q2(total)
