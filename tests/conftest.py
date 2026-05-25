"""
Genera los fixtures sinteticos para los tests.
Replica exactamente los datos de American Implant Abril 2026
descriptos en el prompt maestro, sin necesitar los archivos reales.
"""
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest
import openpyxl
from openpyxl.styles import Font


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_fixtures_dir():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Fixture 1: Mis Comprobantes Emitidos (ARCA) - xlsx
# ---------------------------------------------------------------------------
# 41 Facturas A  → neto gravado total $314.420.530,00
# 2 Notas de Crédito A → neto gravado total $7.167.290,00
# Neto neto = $307.253.240,00
#
# Distribucion facturas:
#   40 facturas x $7.610.506,00 = $304.420.240,00
#   1  factura  x $10.000.290,00
#   Total       = $314.420.530,00
#
# NC:
#   NC1 (13/04): $1.149.200,00  a GLOBAL SURGERY SRL
#   NC2 (30/04): $6.018.090,00  a GLOBAL SURGERY SRL

def build_mis_comprobantes_xlsx() -> Path:
    dest = FIXTURES_DIR / "mis_comprobantes_abril_2026.xlsx"
    if dest.exists():
        return dest

    _ensure_fixtures_dir()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Comprobantes"

    # Fila 1: vacía (a veces ARCA pone metadata aquí)
    ws.append([""] * 28)

    # Fila 2: headers (columnas 0-27)
    headers = [
        "Fecha",             # 0
        "Tipo",              # 1
        "Punto de Venta",    # 2
        "Número Desde",      # 3
        "Número Hasta",      # 4
        "Cod. Autorización", # 5
        "Tipo Doc. Receptor",# 6
        "Nro. Doc. Receptor",# 7
        "Denominación Receptor", # 8
        "Moneda",            # 9
        "Tipo de Cambio",    # 10
        "Col11", "Col12", "Col13", "Col14", "Col15",  # 11-15
        "Col16", "Col17", "Col18", "Col19", "Col20",  # 16-20
        "Col21",             # 21
        "Neto Gravado Total",# 22
        "Neto No Gravado",   # 23
        "Op. Exentas",       # 24
        "Otros Tributos",    # 25
        "Total IVA",         # 26
        "Imp. Total",        # 27
    ]
    ws.append(headers)

    def _row(fecha: date, tipo: str, pv: int, num: int,
             cuit_rec: str, nombre_rec: str,
             neto: float, iva: float) -> list:
        row = [""] * 28
        row[0] = fecha.strftime("%d/%m/%Y")
        row[1] = tipo
        row[2] = pv
        row[3] = num
        row[4] = num
        row[5] = ""
        row[6] = "CUIT"
        row[7] = cuit_rec
        row[8] = nombre_rec
        row[22] = neto
        row[23] = 0
        row[24] = 0
        row[25] = 0
        row[26] = round(iva, 2)
        row[27] = round(neto + iva, 2)
        return row

    # 40 facturas a $7.610.506,00 cada una
    for i in range(1, 41):
        neto = 7_610_506.00
        iva = round(neto * 0.21, 2)
        ws.append(_row(
            date(2026, 4, i if i <= 30 else 30),
            "1 - Factura A",
            1, 1000 + i,
            "30-00000000-0", f"CLIENTE {i} S.A.",
            neto, iva,
        ))

    # 1 factura a $10.000.290,00
    neto = 10_000_290.00
    iva = round(neto * 0.21, 2)
    ws.append(_row(
        date(2026, 4, 30),
        "1 - Factura A",
        1, 1041,
        "30-00000001-0", "CLIENTE ESPECIAL S.A.",
        neto, iva,
    ))

    # NC 1: $1.149.200,00
    nc1_neto = 1_149_200.00
    nc1_iva = round(nc1_neto * 0.21, 2)
    ws.append(_row(
        date(2026, 4, 13),
        "3 - Nota de Crédito A",
        1, 501,
        "30-99999999-0", "GLOBAL SURGERY SRL",
        nc1_neto, nc1_iva,
    ))

    # NC 2: $6.018.090,00
    nc2_neto = 6_018_090.00
    nc2_iva = round(nc2_neto * 0.21, 2)
    ws.append(_row(
        date(2026, 4, 30),
        "3 - Nota de Crédito A",
        1, 502,
        "30-99999999-0", "GLOBAL SURGERY SRL",
        nc2_neto, nc2_iva,
    ))

    wb.save(dest)
    return dest


# ---------------------------------------------------------------------------
# Fixture 2: SIRCREB CABA (AGIP) - CSV con header "sep=,"
# ---------------------------------------------------------------------------
# Total importeRecaudadoPorJuris = $1.420.239,56

AGIP_ROWS = [
    ("20-00000001-1", "BANCO DE GALICIA Y BUENOS AIRES S.A.", "15/04/2026",
     "0", "308316.10", "1.0", "308316.10", "CA", "0000001"),
    ("20-00000001-1", "BANCO DE GALICIA Y BUENOS AIRES S.A.", "23/04/2026",
     "0", "38865.97", "1.0", "38865.97", "CA", "0000002"),
    ("20-00000002-2", "BANCO SANTANDER ARGENTINA S.A.", "16/04/2026",
     "0", "880089.22", "1.0", "880089.22", "CA", "0000003"),
    ("20-00000002-2", "BANCO SANTANDER ARGENTINA S.A.", "24/04/2026",
     "0", "192968.27", "1.0", "192968.27", "CA", "0000004"),
]

def build_sircreb_caba_csv() -> Path:
    dest = FIXTURES_DIR / "sircreb_caba_abril_2026.csv"
    if dest.exists():
        return dest

    _ensure_fixtures_dir()
    with open(dest, "w", newline="", encoding="utf-8") as f:
        f.write("sep=,\n")
        f.write("cuit,razonSocial,fechaPresentacion,importeCR,importeRecaudado,"
                "coeficienteJurisdiccion,importeRecaudadoPorJuris,tipoCuenta,CBU\n")
        writer = csv.writer(f)
        for row in AGIP_ROWS:
            writer.writerow(row)

    return dest


# ---------------------------------------------------------------------------
# Fixture 3: SIRCREB Buenos Aires (ARBA) - xlsx (misma estructura que xls)
# ---------------------------------------------------------------------------
# Col 0: CUIT agente, Col 1: Fecha, Col 10: Importe
# Total = $100.546,32

ARBA_ROWS = [
    # (cuit_agente, fecha, importe_col10)
    ("30500001735", "01/04/2026", 22_475.17),
    ("30500008454", "01/04/2026", 78_071.15),
]

def build_sircreb_bsas_xlsx() -> Path:
    """Creamos como .xlsx; el importador acepta ambos formatos."""
    dest = FIXTURES_DIR / "sircreb_bsas_abril_2026.xls"
    if dest.exists():
        return dest

    # Usamos openpyxl pero guardamos con extension .xls
    # El importador detecta .xls y usa xlrd, que fallaria con este formato.
    # Lo guardamos como .xlsx renombrado; al ejecutar el test
    # pasamos la ruta como .xls pero el importador lo maneja via xlsx como fallback.
    # SOLUCION MAS LIMPIA: guardarlo como .xlsx con el nombre correcto y
    # hacer que el fixture use la version xlsx.
    dest_xlsx = FIXTURES_DIR / "sircreb_bsas_abril_2026.xlsx"

    _ensure_fixtures_dir()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SIRCREB"

    # Header
    header = [""] * 11
    header[0] = "CUIT Agente"
    header[1] = "Fecha"
    header[10] = "Importe"
    ws.append(header)

    for cuit_ag, fecha, importe in ARBA_ROWS:
        row = [""] * 11
        row[0] = cuit_ag
        row[1] = fecha
        row[10] = importe
        ws.append(row)

    wb.save(dest_xlsx)

    # Crear una copia binaria simple para que el test pueda usar .xls
    # Como xlrd 1.2 no puede leer archivos xlsx, usamos el .xlsx directamente
    # y el test importa desde la ruta .xlsx
    return dest_xlsx


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def fixture_mis_comprobantes():
    return build_mis_comprobantes_xlsx()


@pytest.fixture(scope="session")
def fixture_sircreb_caba():
    return build_sircreb_caba_csv()


@pytest.fixture(scope="session")
def fixture_sircreb_bsas():
    return build_sircreb_bsas_xlsx()


@pytest.fixture(scope="session", autouse=True)
def build_all_fixtures():
    """Genera todos los fixtures al iniciar la sesión de tests."""
    build_mis_comprobantes_xlsx()
    build_sircreb_caba_csv()
    build_sircreb_bsas_xlsx()
