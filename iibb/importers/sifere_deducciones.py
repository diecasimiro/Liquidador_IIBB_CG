"""
Importador del Excel de Deducciones exportado desde SIFERE Web.

Columnas esperadas (fila 1 = header, datos desde fila 2):
  A: JURISDICCION           → "901 - CABA", "902 - BUENOS AIRES", etc.
  B: TOTAL_RETENCIONES      → Retenciones Sufridas
  D: TOTAL_RECAUDACIONES_BANCARIAS → SIRCREB
  F: TOTAL_PERCEPCIONES     → Percepciones Sufridas
  H: TOTAL_PERCEPCIONES_ADUANERAS → Percepciones Aduaneras

Devuelve un dict con claves iguales a los tipos de deducción usados en procesar.py:
  {
    "retencion":    {"901": Decimal("470623.99"), ...},
    "sircreb":      {"901": Decimal("142976.49"), ...},
    "percepcion":   {"901": Decimal("207191.09"), ...},
    "perc_aduanera":{"901": Decimal("0.00"), ...},
  }
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl


def _codigo(valor_celda) -> str | None:
    """Extrae el código de 3 dígitos de 'NNN - Nombre Jurisdiccion'."""
    if valor_celda is None:
        return None
    s = str(valor_celda).strip()
    # Acepta "901 - CABA", "901-CABA", "901" a secas
    parte = s.split("-")[0].split("–")[0].strip()
    if parte.isdigit() and len(parte) == 3:
        return parte
    return None


def _decimal(valor_celda) -> Decimal:
    if valor_celda is None:
        return Decimal("0")
    try:
        return Decimal(str(valor_celda).replace(",", ".").strip())
    except InvalidOperation:
        return Decimal("0")


def importar_sifere_deducciones(archivo: Path | str) -> dict[str, dict[str, Decimal]]:
    """
    Lee el Excel de SIFERE Web y devuelve los totales por tipo y jurisdicción.
    Lanza ValueError si el archivo no tiene el formato esperado.
    """
    wb = openpyxl.load_workbook(str(archivo), data_only=True)
    ws = wb.active

    resultado: dict[str, dict[str, Decimal]] = {
        "retencion":    {},
        "sircreb":      {},
        "percepcion":   {},
        "perc_aduanera": {},
    }

    filas_leidas = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        codigo = _codigo(row[0] if len(row) > 0 else None)
        if codigo is None:
            continue
        resultado["retencion"][codigo]    = _decimal(row[1] if len(row) > 1 else None)
        resultado["sircreb"][codigo]      = _decimal(row[3] if len(row) > 3 else None)
        resultado["percepcion"][codigo]   = _decimal(row[5] if len(row) > 5 else None)
        resultado["perc_aduanera"][codigo] = _decimal(row[7] if len(row) > 7 else None)
        filas_leidas += 1

    if filas_leidas == 0:
        raise ValueError(
            "No se encontraron filas de datos. "
            "Verificá que el archivo sea el export de 'Datos de Deducciones' de SIFERE Web."
        )

    return resultado
