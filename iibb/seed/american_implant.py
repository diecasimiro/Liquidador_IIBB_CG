from datetime import date
from decimal import Decimal
from iibb.models.catalogos import Tenant
from iibb.models.contribuyente import (
    Contribuyente,
    JurisdiccionInscripta,
    ActividadInscripta,
    CoeficienteAnual,
    Alicuota,
)


def seed_tenant(session) -> Tenant:
    tenant = session.query(Tenant).filter_by(nombre="Estudio CG").first()
    if not tenant:
        tenant = Tenant(nombre="Estudio CG", email="dcasimiro@cgestudiocontable.com")
        session.add(tenant)
        session.flush()
    return tenant


def seed_american_implant(session, tenant_id: int):
    contrib = session.query(Contribuyente).filter_by(cuit="30-71223438-1").first()
    if contrib:
        return contrib

    contrib = Contribuyente(
        tenant_id=tenant_id,
        cuit="30-71223438-1",
        razon_social="AMERICAN IMPLANT S.A.",
        nro_inscripcion_cm="901-663948-1",
        jurisdiccion_sede="901",
        naturaleza_juridica="Sociedad Anónima (I.G.J. N° 11324, fecha 25/06/2010, duración 99 años)",
        cierre_ejercicio_mes=6,
        cierre_ejercicio_dia=30,
        domicilio_fiscal="ALVAREZ JONTE AV. 1647, Piso 11, Of. F - CAPITAL FEDERAL (1416)",
        domicilio_actividades="Cerrito 1079, Ituzaingo - ITUZAINGO (1714)",
        tipo_contribuyente="Resto",
        activo=True,
        notas="Contribuyente demo. Datos de validación del cálculo CM03.",
    )
    session.add(contrib)
    session.flush()

    # Jurisdicciones inscriptas
    juris = [
        JurisdiccionInscripta(
            tenant_id=tenant_id,
            contribuyente_id=contrib.id,
            jurisdiccion_codigo="901",
            fecha_alta=date(2012, 4, 1),
            activa=True,
        ),
        JurisdiccionInscripta(
            tenant_id=tenant_id,
            contribuyente_id=contrib.id,
            jurisdiccion_codigo="902",
            fecha_alta=date(2012, 4, 1),
            activa=True,
        ),
    ]
    for j in juris:
        session.add(j)

    # Actividad principal
    session.add(
        ActividadInscripta(
            tenant_id=tenant_id,
            contribuyente_id=contrib.id,
            codigo_cuacm="266090",
            descripcion="Fabricación de equipo médico y quirúrgico y de aparatos ortopédicos n.c.p.",
            articulo_cm="art2",
            es_principal=True,
            fecha_alta=date(2012, 4, 1),
            activa=True,
        )
    )

    # Coeficientes 2026
    coefs = [
        CoeficienteAnual(
            tenant_id=tenant_id,
            contribuyente_id=contrib.id,
            anio=2026,
            jurisdiccion_codigo="901",
            valor=Decimal("0.6496"),
        ),
        CoeficienteAnual(
            tenant_id=tenant_id,
            contribuyente_id=contrib.id,
            anio=2026,
            jurisdiccion_codigo="902",
            valor=Decimal("0.3504"),
        ),
    ]
    for c in coefs:
        session.add(c)

    # Alícuotas 2026 (actividad 266090)
    alics = [
        Alicuota(
            tenant_id=tenant_id,
            contribuyente_id=contrib.id,
            anio=2026,
            jurisdiccion_codigo="901",
            codigo_actividad="266090",
            valor=Decimal("0.010000"),
        ),
        Alicuota(
            tenant_id=tenant_id,
            contribuyente_id=contrib.id,
            anio=2026,
            jurisdiccion_codigo="902",
            codigo_actividad="266090",
            valor=Decimal("0.015000"),
        ),
    ]
    for a in alics:
        session.add(a)

    session.flush()
    return contrib
