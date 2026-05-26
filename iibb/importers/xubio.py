"""
Importador de comprobantes emitidos desde la API REST de Xubio.

Autenticación: OAuth2 client_credentials (Client ID + Secret ID).
Endpoint: GET /comprobanteBean con filtro fechaDesde / fechaHasta.

Si Xubio cambia los nombres de los campos, ajustar _mapear_comprobante().
"""
import base64
import calendar
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from loguru import logger

from iibb.calculo.cm03 import parse_decimal
from iibb.importers.arca_comprobantes import ComprobanteRow

_API_BASE = "https://xubio.com/API/1.1"
_TIMEOUT = 30

_NC_KEYWORDS = {"nota de crédito", "nota de credito", "nota credito", "nc"}


def _es_nota_credito(tipo: str) -> bool:
    t = tipo.lower()
    return any(k in t for k in _NC_KEYWORDS)


def _get_token(client_id: str, secret_id: str) -> str:
    credentials = base64.b64encode(f"{client_id}:{secret_id}".encode()).decode()
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(
        f"{_API_BASE}/TokenEndpoint",
        data=data,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise ValueError(f"Error de autenticación Xubio ({e.code}): {e.read().decode()}") from e

    token = body.get("access_token")
    if not token:
        raise ValueError(f"Xubio no devolvió access_token. Respuesta: {body}")
    return token


def _fetch_raw(token: str, anio: int, mes: int) -> list[dict]:
    last_day = calendar.monthrange(anio, mes)[1]
    params = urllib.parse.urlencode({
        "fechaDesde": f"{anio:04d}-{mes:02d}-01",
        "fechaHasta": f"{anio:04d}-{mes:02d}-{last_day:02d}",
    })
    req = urllib.request.Request(
        f"{_API_BASE}/comprobanteBean?{params}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise ValueError(f"Error al consultar comprobantes Xubio ({e.code}): {e.read().decode()}") from e

    # Xubio puede devolver {"list": [...]} o directamente [...]
    if isinstance(body, list):
        return body
    return body.get("list", body.get("data", []))


def _parse_fecha(raw: dict):
    for key in ("fecha", "fechaEmision", "fecha_emision"):
        val = raw.get(key)
        if val:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(str(val)[:10], fmt).date()
                except ValueError:
                    continue
    return None


def _mapear(raw: dict) -> ComprobanteRow | None:
    tipo = str(raw.get("tipo") or raw.get("tipoComprobante") or "").strip()
    if not tipo:
        return None

    cliente = raw.get("cliente") or {}
    if isinstance(cliente, dict):
        cuit_raw = str(cliente.get("cuit") or "").replace("-", "").replace(" ", "")
        receptor_cuit = cuit_raw if len(cuit_raw) == 11 else None
        receptor_nombre = str(cliente.get("nombre") or cliente.get("razonSocial") or "").strip() or None
    else:
        receptor_cuit = None
        receptor_nombre = None

    def _safe_int(keys):
        for k in keys:
            try:
                v = int(raw.get(k) or 0)
                if v:
                    return v
            except (TypeError, ValueError):
                pass
        return None

    neto_gravado   = parse_decimal(raw.get("netoGravado")   or raw.get("neto_gravado")   or 0)
    neto_no_gravado = parse_decimal(raw.get("netoNoGravado") or raw.get("neto_no_gravado") or 0)
    op_exentas     = parse_decimal(raw.get("exento")        or raw.get("operacionesExentas") or 0)
    iva            = parse_decimal(raw.get("iva")            or raw.get("montoIva")       or 0)
    total          = parse_decimal(raw.get("total")          or raw.get("montoTotal")     or 0)

    return ComprobanteRow(
        fecha=_parse_fecha(raw),
        tipo=tipo,
        punto_venta=_safe_int(["puntoDeVenta", "numeroPuntoVenta", "punto_venta"]),
        numero=_safe_int(["numero", "nroComprobante", "nro_comprobante"]),
        receptor_cuit=receptor_cuit,
        receptor_nombre=receptor_nombre,
        neto_gravado=neto_gravado,
        neto_no_gravado=neto_no_gravado,
        op_exentas=op_exentas,
        iva=iva,
        total=total,
        signo=-1 if _es_nota_credito(tipo) else 1,
    )


def importar_comprobantes_xubio(
    client_id: str,
    secret_id: str,
    anio: int,
    mes: int,
) -> list[ComprobanteRow]:
    """Autentica con Xubio y devuelve comprobantes del mes como lista de ComprobanteRow."""
    token = _get_token(client_id, secret_id)
    raw_list = _fetch_raw(token, anio, mes)
    resultado = []
    for raw in raw_list:
        row = _mapear(raw)
        if row is not None:
            resultado.append(row)
        else:
            logger.warning(f"Comprobante Xubio ignorado (sin tipo): {raw}")
    logger.info(f"Xubio: {len(resultado)} comprobantes importados para {mes:02d}/{anio}.")
    return resultado
