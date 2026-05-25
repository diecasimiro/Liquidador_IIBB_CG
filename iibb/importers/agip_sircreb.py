"""
Importador SIRCREB CABA - Rentas Ciudad / AGIP.
Formato: CSV con primera linea 'sep=,' y header en segunda linea.

Columnas (0-indexed):
  0: cuit
  1: razonSocial
  2: fechaPresentacion
  3: importeCR
  4: importeRecaudado
  5: coeficienteJurisdiccion
  6: importeRecaudadoPorJuris  <- este es el importe a imputar a CABA
  7: tipoCuenta
  8: CBU
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from loguru import logger

from iibb.calculo.cm03 import parse_decimal, q2


@dataclass
class AgipSircrebRow:
    cuit: str | None
    razon_social: str | None
    fecha_presentacion: date | None
    importe_recaudado: Decimal
    coeficiente_jurisdiccion: Decimal
    importe_imputado: Decimal  # importeRecaudadoPorJuris -> el que va a CABA


def _parse_date_agip(val: str) -> date | None:
    if not val:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            continue
    return None


def import_agip_sircreb(path: str | Path) -> list[AgipSircrebRow]:
    """
    Lee el CSV de SIRCREB CABA (Rentas Ciudad / AGIP).
    Salta la primera linea 'sep=,' y la segunda con los headers.
    Devuelve lista de AgipSircrebRow.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {path}")

    resultado: list[AgipSircrebRow] = []

    with open(path, encoding="utf-8-sig", errors="replace") as f:
        lines = f.readlines()

    # Encontrar donde empiezan los datos (saltar "sep=," y el header)
    data_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if stripped.startswith("sep=") or stripped.startswith("cuit"):
            data_start = i + 1
        else:
            if data_start > 0:
                break

    import csv
    import io
    content = "".join(lines[data_start:])
    reader = csv.reader(io.StringIO(content))

    for i, row in enumerate(reader):
        if not row or not any(r.strip() for r in row):
            continue
        if len(row) < 7:
            logger.warning(f"Fila {i + data_start + 1} con menos columnas de las esperadas: {row}")
            continue
        try:
            cuit = row[0].strip() or None
            razon_social = row[1].strip() or None
            fecha = _parse_date_agip(row[2].strip())
            importe_recaudado = parse_decimal(row[4])
            coef = parse_decimal(row[5]) if row[5].strip() else Decimal("1")
            importe_imputado = parse_decimal(row[6])
        except Exception as e:
            logger.warning(f"Fila {i + data_start + 1} ignorada: {e} — {row}")
            continue

        resultado.append(
            AgipSircrebRow(
                cuit=cuit,
                razon_social=razon_social,
                fecha_presentacion=fecha,
                importe_recaudado=importe_recaudado,
                coeficiente_jurisdiccion=coef,
                importe_imputado=importe_imputado,
            )
        )

    logger.info(f"SIRCREB CABA: {len(resultado)} filas importadas de '{path.name}'.")
    return resultado


def total_imputado_agip(rows: list[AgipSircrebRow]) -> Decimal:
    return q2(sum((r.importe_imputado for r in rows), Decimal("0")))
