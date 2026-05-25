"""
TEST CRITICO E2E - American Implant S.A. - Abril 2026
======================================================
Valida que el motor de calculo produce exactamente:
  CABA  monto a pagar: $  575.677,49
  BsAs  monto a pagar: $1.514.376,71
  TOTAL monto a pagar: $2.090.054,20

Si este test falla, hay un bug en el motor de calculo.
NO modificar los asserts sin autorización.
"""
from decimal import Decimal
from pathlib import Path

import pytest

from iibb.calculo.cm03 import (
    JurisdiccionInput,
    DeduccionInput,
    calcular_cm03,
)
from iibb.importers.arca_comprobantes import (
    import_mis_comprobantes_emitidos,
    summarize_comprobantes,
)
from iibb.importers.agip_sircreb import import_agip_sircreb, total_imputado_agip
from iibb.importers.arba_sircreb import import_arba_sircreb, total_imputado_arba

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Tests de importadores (verifican que los fixtures tienen los datos correctos)
# ---------------------------------------------------------------------------

class TestImportadorArcaComprobantes:
    def test_importa_43_comprobantes(self):
        rows = import_mis_comprobantes_emitidos(FIXTURES / "mis_comprobantes_abril_2026.xlsx")
        assert len(rows) == 43  # 41 facturas + 2 NC

    def test_cant_facturas_y_nc(self):
        rows = import_mis_comprobantes_emitidos(FIXTURES / "mis_comprobantes_abril_2026.xlsx")
        facturas = [r for r in rows if r.signo == 1]
        ncs = [r for r in rows if r.signo == -1]
        assert len(facturas) == 41
        assert len(ncs) == 2

    def test_neto_gravado_facturas(self):
        rows = import_mis_comprobantes_emitidos(FIXTURES / "mis_comprobantes_abril_2026.xlsx")
        resumen = summarize_comprobantes(rows)
        assert resumen["neto_gravado_facturas"] == Decimal("314420530.00")

    def test_neto_gravado_nc(self):
        rows = import_mis_comprobantes_emitidos(FIXTURES / "mis_comprobantes_abril_2026.xlsx")
        resumen = summarize_comprobantes(rows)
        assert resumen["neto_gravado_notas_credito"] == Decimal("7167290.00")

    def test_neto_gravado_neto(self):
        rows = import_mis_comprobantes_emitidos(FIXTURES / "mis_comprobantes_abril_2026.xlsx")
        resumen = summarize_comprobantes(rows)
        assert resumen["neto_gravado_neto"] == Decimal("307253240.00")


class TestImportadorAgipSircreb:
    def test_importa_4_filas(self):
        rows = import_agip_sircreb(FIXTURES / "sircreb_caba_abril_2026.csv")
        assert len(rows) == 4

    def test_total_imputado_caba(self):
        rows = import_agip_sircreb(FIXTURES / "sircreb_caba_abril_2026.csv")
        assert total_imputado_agip(rows) == Decimal("1420239.56")


class TestImportadorArbaSircreb:
    def test_importa_2_filas(self):
        rows = import_arba_sircreb(FIXTURES / "sircreb_bsas_abril_2026.xlsx")
        assert len(rows) == 2

    def test_total_imputado_bsas(self):
        rows = import_arba_sircreb(FIXTURES / "sircreb_bsas_abril_2026.xlsx")
        assert total_imputado_arba(rows) == Decimal("100546.32")


# ---------------------------------------------------------------------------
# Test de calculo puro (sin importadores - solo numeros hardcodeados)
# ---------------------------------------------------------------------------

class TestCalculoCM03Puro:
    def test_base_imponible_caba(self):
        liq = calcular_cm03(
            contribuyente_cuit="30-71223438-1",
            contribuyente_razon="AMERICAN IMPLANT S.A.",
            anio=2026, mes=4,
            ingresos_totales=Decimal("307253240.00"),
            jurisdicciones=[
                JurisdiccionInput("901", "CABA", Decimal("0.6496"), Decimal("0.0100")),
                JurisdiccionInput("902", "Buenos Aires", Decimal("0.3504"), Decimal("0.0150")),
            ],
            deducciones=[],
        )
        caba = next(r for r in liq.resultados if r.codigo == "901")
        assert caba.base_imponible == Decimal("199591704.70")

    def test_base_imponible_bsas(self):
        liq = calcular_cm03(
            contribuyente_cuit="30-71223438-1",
            contribuyente_razon="AMERICAN IMPLANT S.A.",
            anio=2026, mes=4,
            ingresos_totales=Decimal("307253240.00"),
            jurisdicciones=[
                JurisdiccionInput("901", "CABA", Decimal("0.6496"), Decimal("0.0100")),
                JurisdiccionInput("902", "Buenos Aires", Decimal("0.3504"), Decimal("0.0150")),
            ],
            deducciones=[],
        )
        bsas = next(r for r in liq.resultados if r.codigo == "902")
        assert bsas.base_imponible == Decimal("107661535.30")

    def test_impuesto_determinado_caba(self):
        liq = calcular_cm03(
            contribuyente_cuit="30-71223438-1",
            contribuyente_razon="AMERICAN IMPLANT S.A.",
            anio=2026, mes=4,
            ingresos_totales=Decimal("307253240.00"),
            jurisdicciones=[
                JurisdiccionInput("901", "CABA", Decimal("0.6496"), Decimal("0.0100")),
                JurisdiccionInput("902", "Buenos Aires", Decimal("0.3504"), Decimal("0.0150")),
            ],
            deducciones=[],
        )
        caba = next(r for r in liq.resultados if r.codigo == "901")
        assert caba.impuesto_determinado == Decimal("1995917.05")

    def test_impuesto_determinado_bsas(self):
        liq = calcular_cm03(
            contribuyente_cuit="30-71223438-1",
            contribuyente_razon="AMERICAN IMPLANT S.A.",
            anio=2026, mes=4,
            ingresos_totales=Decimal("307253240.00"),
            jurisdicciones=[
                JurisdiccionInput("901", "CABA", Decimal("0.6496"), Decimal("0.0100")),
                JurisdiccionInput("902", "Buenos Aires", Decimal("0.3504"), Decimal("0.0150")),
            ],
            deducciones=[],
        )
        bsas = next(r for r in liq.resultados if r.codigo == "902")
        assert bsas.impuesto_determinado == Decimal("1614923.03")

    def test_suma_coeficientes_invalida_lanza_error(self):
        # 0.5000 + 0.6000 = 1.1000, claramente fuera de la tolerancia 0.0001
        with pytest.raises(ValueError, match="suma de coeficientes"):
            calcular_cm03(
                contribuyente_cuit="30-71223438-1",
                contribuyente_razon="TEST",
                anio=2026, mes=4,
                ingresos_totales=Decimal("100000.00"),
                jurisdicciones=[
                    JurisdiccionInput("901", "CABA", Decimal("0.5000"), Decimal("0.01")),
                    JurisdiccionInput("902", "BsAs", Decimal("0.6000"), Decimal("0.015")),
                ],
                deducciones=[],
            )


# ---------------------------------------------------------------------------
# TEST CRITICO E2E COMPLETO
# ---------------------------------------------------------------------------

def test_american_implant_abril_2026():
    """
    TEST MAESTRO: verifica el resultado completo de la liquidacion
    de American Implant S.A. para Abril 2026.

    Resultado esperado:
      CABA  base imponible:       $ 199.591.704,70
      BsAs  base imponible:       $ 107.661.535,30
      CABA  impuesto determinado: $   1.995.917,05
      BsAs  impuesto determinado: $   1.614.923,03
      CABA  SIRCREB:              $   1.420.239,56
      BsAs  SIRCREB:              $     100.546,32
      CABA  monto a pagar:        $     575.677,49
      BsAs  monto a pagar:        $   1.514.376,71
      TOTAL monto a pagar:        $   2.090.054,20
    """
    # --- Importar comprobantes ---
    rows_comp = import_mis_comprobantes_emitidos(FIXTURES / "mis_comprobantes_abril_2026.xlsx")
    resumen = summarize_comprobantes(rows_comp)
    assert resumen["neto_gravado_neto"] == Decimal("307253240.00"), (
        f"Neto gravado incorrecto: {resumen['neto_gravado_neto']}"
    )

    # --- Importar SIRCREB CABA ---
    rows_caba = import_agip_sircreb(FIXTURES / "sircreb_caba_abril_2026.csv")
    sircreb_caba = total_imputado_agip(rows_caba)
    assert sircreb_caba == Decimal("1420239.56"), f"SIRCREB CABA incorrecto: {sircreb_caba}"

    # --- Importar SIRCREB BsAs ---
    rows_bsas = import_arba_sircreb(FIXTURES / "sircreb_bsas_abril_2026.xlsx")
    sircreb_bsas = total_imputado_arba(rows_bsas)
    assert sircreb_bsas == Decimal("100546.32"), f"SIRCREB BsAs incorrecto: {sircreb_bsas}"

    # --- Calcular liquidacion ---
    liq = calcular_cm03(
        contribuyente_cuit="30-71223438-1",
        contribuyente_razon="AMERICAN IMPLANT S.A.",
        anio=2026,
        mes=4,
        ingresos_totales=resumen["neto_gravado_neto"],
        jurisdicciones=[
            JurisdiccionInput("901", "CABA", Decimal("0.6496"), Decimal("0.0100")),
            JurisdiccionInput("902", "Buenos Aires", Decimal("0.3504"), Decimal("0.0150")),
        ],
        deducciones=[
            DeduccionInput("901", "sircreb", sircreb_caba),
            DeduccionInput("902", "sircreb", sircreb_bsas),
        ],
    )

    caba = next(r for r in liq.resultados if r.codigo == "901")
    bsas = next(r for r in liq.resultados if r.codigo == "902")

    # Bases imponibles
    assert caba.base_imponible == Decimal("199591704.70"), f"Base CABA: {caba.base_imponible}"
    assert bsas.base_imponible == Decimal("107661535.30"), f"Base BsAs: {bsas.base_imponible}"

    # Impuesto determinado
    assert caba.impuesto_determinado == Decimal("1995917.05"), f"Imp CABA: {caba.impuesto_determinado}"
    assert bsas.impuesto_determinado == Decimal("1614923.03"), f"Imp BsAs: {bsas.impuesto_determinado}"

    # SIRCREB imputado
    assert caba.sircreb == Decimal("1420239.56"), f"SIRCREB CABA: {caba.sircreb}"
    assert bsas.sircreb == Decimal("100546.32"), f"SIRCREB BsAs: {bsas.sircreb}"

    # Montos a pagar por jurisdiccion
    assert caba.monto_a_pagar == Decimal("575677.49"), f"A pagar CABA: {caba.monto_a_pagar}"
    assert bsas.monto_a_pagar == Decimal("1514376.71"), f"A pagar BsAs: {bsas.monto_a_pagar}"

    # TOTAL - el numero que no puede fallar jamas
    assert liq.monto_total_a_pagar == Decimal("2090054.20"), (
        f"TOTAL A PAGAR INCORRECTO: {liq.monto_total_a_pagar} (esperado: 2090054.20)"
    )
