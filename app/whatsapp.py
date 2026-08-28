"""Aviso opcional al paciente por WhatsApp cuando el hospital reagenda/cancela.

Envío directo por la Cloud API de Meta (mismas credenciales que el bot, vía variables de
entorno propias de este servicio). DOBLE seguro:
- Solo se intenta si la petición trae "notificar": true.
- Solo sale de verdad si EXTERNO_ENVIO_REAL=true (default: false → se responde "simulada").

Limitación conocida (Meta): fuera de la ventana de 24 h desde el último mensaje del paciente,
solo llegan PLANTILLAS aprobadas. Para reagendamientos usamos la plantilla de confirmación de
cita (misma que el bot usa con asegurados, con la fecha nueva). Para cancelaciones no existe
plantilla aprobada aún: se intenta mensaje de sesión (llega solo dentro de la ventana) y se
informa el resultado en la respuesta — nunca se promete lo que no se pudo enviar.
"""
from __future__ import annotations

import httpx

from app.config import settings


def _digits(cel: str) -> str:
    d = "".join(c for c in cel if c.isdigit())
    if d.startswith("593"):
        return d
    if d.startswith("0"):
        return "593" + d[1:]
    return ("593" + d) if len(d) == 9 else d


async def _post(payload: dict) -> tuple[bool, str]:
    url = (f"https://graph.facebook.com/v20.0/"
           f"{settings.whatsapp_phone_number_id}/messages")
    try:
        async with httpx.AsyncClient(timeout=15) as cli:
            r = await cli.post(url, json=payload, headers={
                "Authorization": f"Bearer {settings.whatsapp_token}"})
        if r.status_code < 300:
            return True, "enviada"
        return False, f"fallo Meta {r.status_code}: {r.text[:120]}"
    except Exception as e:  # noqa: BLE001
        return False, f"fallo: {type(e).__name__}"


async def notificar_reagenda(cita: dict, fecha: str, hora: str) -> str:
    """Plantilla de confirmación con la fecha NUEVA (llega aun fuera de ventana)."""
    if not settings.externo_envio_real:
        return "simulada (EXTERNO_ENVIO_REAL=false)"
    if not (settings.whatsapp_token and settings.whatsapp_phone_number_id
            and settings.plantilla_confirmacion):
        return "no configurada (faltan credenciales de WhatsApp)"
    lugar = "Hospital del Río"
    if cita.get("consultorio") or cita.get("piso"):
        lugar = f"Consultorio {cita.get('consultorio') or ''}, Piso {cita.get('piso') or ''}"
    dd, mm, aa = fecha[8:10], fecha[5:7], fecha[0:4]
    params = [str(cita.get("nombres_completos") or "").title(),
              cita.get("nombre_especialidad") or "su especialidad",
              str(cita.get("nombre_medico") or "").title(),
              f"{dd}/{mm}/{aa}", hora, lugar]
    ok, res = await _post({
        "messaging_product": "whatsapp",
        "to": _digits(cita.get("celular") or cita.get("celular_whatsapp") or ""),
        "type": "template",
        "template": {"name": settings.plantilla_confirmacion,
                     "language": {"code": "es"},
                     "components": [{"type": "body", "parameters": [
                         {"type": "text", "text": p} for p in params]}]}})
    return res


async def notificar_cancelacion(cita: dict, motivo: str) -> str:
    """Texto de sesión (solo llega dentro de la ventana de 24 h — mejor esfuerzo)."""
    if not settings.externo_envio_real:
        return "simulada (EXTERNO_ENVIO_REAL=false)"
    if not (settings.whatsapp_token and settings.whatsapp_phone_number_id):
        return "no configurada (faltan credenciales de WhatsApp)"
    texto = (f"Estimado(a) {str(cita.get('nombres_completos') or '').title()}, "
             f"le informamos que su cita de {cita.get('nombre_especialidad') or ''} "
             f"fue CANCELADA por el hospital. Motivo: {motivo}. "
             f"Si desea reagendar, escríbanos por este medio. Hospital del Río.")
    ok, res = await _post({
        "messaging_product": "whatsapp",
        "to": _digits(cita.get("celular") or cita.get("celular_whatsapp") or ""),
        "type": "text", "text": {"body": texto}})
    return res if ok else res + " (probable fuera de ventana de 24h)"
