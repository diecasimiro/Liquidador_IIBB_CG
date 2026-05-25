from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from iibb.models.contribuyente import (
    Contribuyente, CoeficienteAnual, Alicuota,
    JurisdiccionInscripta, ActividadInscripta,
)


# ── Lectura ─────────────────────────────────────────────────────────────────

def listar_contribuyentes(session: Session) -> list[Contribuyente]:
    return (
        session.query(Contribuyente)
        .filter_by(activo=True)
        .order_by(Contribuyente.razon_social)
        .all()
    )


def obtener_contribuyente(session: Session, contribuyente_id: int) -> Contribuyente | None:
    return session.get(Contribuyente, contribuyente_id)


def obtener_por_cuit(session: Session, cuit: str) -> Contribuyente | None:
    return session.query(Contribuyente).filter_by(cuit=cuit).first()


def obtener_coeficientes(session: Session, contribuyente_id: int, anio: int) -> list[CoeficienteAnual]:
    return (
        session.query(CoeficienteAnual)
        .filter_by(contribuyente_id=contribuyente_id, anio=anio)
        .all()
    )


def obtener_alicuotas(session: Session, contribuyente_id: int, anio: int) -> list[Alicuota]:
    return (
        session.query(Alicuota)
        .filter_by(contribuyente_id=contribuyente_id, anio=anio)
        .all()
    )


def obtener_jurisdicciones_activas(session: Session, contribuyente_id: int) -> list[JurisdiccionInscripta]:
    return (
        session.query(JurisdiccionInscripta)
        .filter_by(contribuyente_id=contribuyente_id, activa=True)
        .all()
    )


def validar_suma_coeficientes(coeficientes: list[CoeficienteAnual]) -> tuple[bool, Decimal]:
    suma = sum((c.valor for c in coeficientes), Decimal("0"))
    return abs(suma - Decimal("1.0000")) <= Decimal("0.0001"), suma


# ── Validación CUIT ──────────────────────────────────────────────────────────

def validar_cuit(cuit: str) -> tuple[bool, str]:
    """
    Valida el dígito verificador del CUIT argentino.
    Devuelve (es_valido, cuit_formateado) — ej: "30-71223438-1".
    """
    digits = cuit.replace("-", "").replace(" ", "").strip()
    if not digits.isdigit() or len(digits) != 11:
        return False, cuit
    mults = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(d) * m for d, m in zip(digits[:10], mults))
    resto = total % 11
    if resto == 0:
        dv = 0
    elif resto == 1:
        return False, cuit
    else:
        dv = 11 - resto
    if int(digits[10]) != dv:
        return False, cuit
    return True, f"{digits[:2]}-{digits[2:10]}-{digits[10]}"


# ── Creación ─────────────────────────────────────────────────────────────────

def crear_contribuyente(
    session: Session,
    *,
    cuit: str,
    razon_social: str,
    nro_inscripcion_cm: str | None = None,
    jurisdiccion_sede: str | None = None,
    naturaleza_juridica: str | None = None,
    cierre_ejercicio_mes: int | None = None,
    cierre_ejercicio_dia: int | None = None,
    domicilio_fiscal: str | None = None,
    domicilio_actividades: str | None = None,
    tipo_contribuyente: str | None = None,
    notas: str | None = None,
    tenant_id: int = 1,
    # Relaciones
    jurisdicciones: list[dict] | None = None,
    actividades: list[dict] | None = None,
    coeficientes: list[dict] | None = None,
    alicuotas: list[dict] | None = None,
) -> Contribuyente:
    """
    Crea un contribuyente con todas sus relaciones en una sola transacción.

    jurisdicciones: [{"codigo": "901", "fecha_alta": date(...)}]
    actividades: [{"codigo_cuacm": "...", "descripcion": "...", "articulo_cm": "art2",
                   "es_principal": True, "fecha_alta": date(...)}]
    coeficientes: [{"anio": 2026, "jurisdiccion_codigo": "901", "valor": Decimal("0.6496")}]
    alicuotas: [{"anio": 2026, "jurisdiccion_codigo": "901",
                 "codigo_actividad": "266090", "valor": Decimal("0.01")}]
    """
    existente = obtener_por_cuit(session, cuit)
    if existente:
        raise ValueError(f"Ya existe un contribuyente con CUIT {cuit}.")

    contrib = Contribuyente(
        tenant_id=tenant_id,
        cuit=cuit,
        razon_social=razon_social.strip().upper(),
        nro_inscripcion_cm=nro_inscripcion_cm,
        jurisdiccion_sede=jurisdiccion_sede,
        naturaleza_juridica=naturaleza_juridica,
        cierre_ejercicio_mes=cierre_ejercicio_mes,
        cierre_ejercicio_dia=cierre_ejercicio_dia,
        domicilio_fiscal=domicilio_fiscal,
        domicilio_actividades=domicilio_actividades,
        tipo_contribuyente=tipo_contribuyente,
        notas=notas,
        activo=True,
    )
    session.add(contrib)
    session.flush()

    for j in (jurisdicciones or []):
        session.add(JurisdiccionInscripta(
            tenant_id=tenant_id,
            contribuyente_id=contrib.id,
            jurisdiccion_codigo=j["codigo"],
            fecha_alta=j.get("fecha_alta"),
            activa=True,
        ))

    for a in (actividades or []):
        session.add(ActividadInscripta(
            tenant_id=tenant_id,
            contribuyente_id=contrib.id,
            codigo_cuacm=a["codigo_cuacm"],
            descripcion=a["descripcion"],
            articulo_cm=a.get("articulo_cm", "art2"),
            es_principal=a.get("es_principal", False),
            fecha_alta=a.get("fecha_alta"),
            activa=True,
        ))

    for c in (coeficientes or []):
        session.add(CoeficienteAnual(
            tenant_id=tenant_id,
            contribuyente_id=contrib.id,
            anio=c["anio"],
            jurisdiccion_codigo=c["jurisdiccion_codigo"],
            valor=Decimal(str(c["valor"])),
        ))

    for al in (alicuotas or []):
        session.add(Alicuota(
            tenant_id=tenant_id,
            contribuyente_id=contrib.id,
            anio=al["anio"],
            jurisdiccion_codigo=al["jurisdiccion_codigo"],
            codigo_actividad=al["codigo_actividad"],
            valor=Decimal(str(al["valor"])),
        ))

    session.flush()
    return contrib


# ── Edición ──────────────────────────────────────────────────────────────────

def actualizar_datos_basicos(
    session: Session,
    contribuyente_id: int,
    **campos,
) -> Contribuyente:
    contrib = session.get(Contribuyente, contribuyente_id)
    if not contrib:
        raise ValueError("Contribuyente no encontrado.")
    for k, v in campos.items():
        if hasattr(contrib, k):
            setattr(contrib, k, v)
    session.flush()
    return contrib


def guardar_coeficientes_anio(
    session: Session,
    contribuyente_id: int,
    anio: int,
    coeficientes: list[dict],
    tenant_id: int = 1,
) -> None:
    """Reemplaza todos los coeficientes del año dado por los nuevos valores."""
    session.query(CoeficienteAnual).filter_by(
        contribuyente_id=contribuyente_id, anio=anio
    ).delete()
    for c in coeficientes:
        session.add(CoeficienteAnual(
            tenant_id=tenant_id,
            contribuyente_id=contribuyente_id,
            anio=anio,
            jurisdiccion_codigo=c["jurisdiccion_codigo"],
            valor=Decimal(str(c["valor"])),
        ))
    session.flush()


def guardar_alicuotas_anio(
    session: Session,
    contribuyente_id: int,
    anio: int,
    alicuotas: list[dict],
    tenant_id: int = 1,
) -> None:
    """Reemplaza todas las alícuotas del año dado por las nuevas."""
    session.query(Alicuota).filter_by(
        contribuyente_id=contribuyente_id, anio=anio
    ).delete()
    for al in alicuotas:
        session.add(Alicuota(
            tenant_id=tenant_id,
            contribuyente_id=contribuyente_id,
            anio=anio,
            jurisdiccion_codigo=al["jurisdiccion_codigo"],
            codigo_actividad=al["codigo_actividad"],
            valor=Decimal(str(al["valor"])),
        ))
    session.flush()


def agregar_jurisdiccion(
    session: Session,
    contribuyente_id: int,
    jurisdiccion_codigo: str,
    fecha_alta: date | None = None,
    tenant_id: int = 1,
) -> JurisdiccionInscripta:
    existente = (
        session.query(JurisdiccionInscripta)
        .filter_by(contribuyente_id=contribuyente_id, jurisdiccion_codigo=jurisdiccion_codigo)
        .first()
    )
    if existente:
        existente.activa = True
        existente.fecha_alta = fecha_alta or existente.fecha_alta
        session.flush()
        return existente
    ji = JurisdiccionInscripta(
        tenant_id=tenant_id,
        contribuyente_id=contribuyente_id,
        jurisdiccion_codigo=jurisdiccion_codigo,
        fecha_alta=fecha_alta,
        activa=True,
    )
    session.add(ji)
    session.flush()
    return ji


def dar_de_baja_contribuyente(session: Session, contribuyente_id: int) -> None:
    contrib = session.get(Contribuyente, contribuyente_id)
    if contrib:
        contrib.activo = False
        session.flush()
