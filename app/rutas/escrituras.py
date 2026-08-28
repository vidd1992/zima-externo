"""Escrituras: agendar, reagendar y cancelar — SOLO sobre nuestra tabla.

Principios (lecciones del incidente de idChatbot del 08/2026):
- Referencia explícita por `id_chatbot`; jamás se adivina qué cita es.
- Nunca `ok:true` sin haber hecho el trabajo: cada respuesta refleja lo que pasó,
  y los fallos vienen con `motivo` legible.
- `?simular=true` en las tres: valida y responde qué haría, sin escribir nada.
- Idempotencia en el alta: reintentar el mismo `cita_hospital` no duplica.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from app.db import conexion
from app.modelos import Cancelacion, CitaEntrante, Reagendamiento
from app.seguridad import requiere_token
from app.whatsapp import notificar_cancelacion, notificar_reagenda

router = APIRouter(prefix="/externo/citas", tags=["escrituras"],
                   dependencies=[Depends(requiere_token)])

_ACTIVAS = ("confirmada", "pendiente")


def _partes(fecha_iso: str) -> tuple[str, str]:
    dt = datetime.fromisoformat(fecha_iso)
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")


def _celular_wpp(celular: str) -> str:
    """Normaliza a formato de WhatsApp EC (593...), igual que el bot."""
    d = "".join(c for c in celular if c.isdigit())
    if d.startswith("593"):
        return d
    if d.startswith("0"):
        return "593" + d[1:]
    if len(d) == 9:
        return "593" + d
    return d


@router.post("")
async def agendar(cita: CitaEntrante, simular: bool = False):
    fecha, hora = _partes(cita.fecha_aten)
    async with await conexion() as con:
        cur = con.cursor()
        # Idempotencia: si su nº de cita ya fue registrado, devolvemos el id existente.
        await cur.execute(
            "SELECT id FROM citas_solicitadas WHERE cita_hospital=%s", (cita.cita_hospital,))
        ya = await cur.fetchone()
        if ya:
            return {"ok": True, "id_chatbot": ya["id"], "cita_hospital": cita.cita_hospital,
                    "nota": "ya estaba registrada (idempotente): no se duplicó"}
        # Anti-duplicado funcional: misma cédula + especialidad + fecha con cita activa.
        cedula_sin = cita.cedula[1:]
        await cur.execute(
            """SELECT id, estado FROM citas_solicitadas
               WHERE (cedula=%s OR cedula=%s) AND especialidad=%s AND fecha_cita=%s
                 AND estado = ANY(%s)""",
            (cita.cedula, cedula_sin, cita.especialidad, fecha, list(_ACTIVAS)))
        dup = await cur.fetchone()
        if dup:
            return {"ok": False,
                    "motivo": f"ya existe una cita activa (id_chatbot {dup['id']}, estado "
                              f"{dup['estado']}) para esa cédula, especialidad y fecha"}
        if simular:
            return {"ok": True, "simulado": True,
                    "haria": f"insertar cita de {cita.paciente} el {fecha} {hora} "
                             f"(origen=hospital, usuario={cita.usuario})"}
        await cur.execute(
            """INSERT INTO citas_solicitadas
               (nombres_completos, cedula, correo, edad, celular, celular_whatsapp,
                seguro, especialidad, medico, fecha_cita, horario_cita,
                nombre_especialidad, nombre_medico, manejahorario, estado,
                fecha_confirmada_paciente, hora_confirmada_paciente,
                nombre_especialidad_confirmada, nombre_medico_confirmada,
                origen, cita_hospital, recordatorios_habilitados, nota)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,'confirmada',
                       %s,%s,%s,%s,'hospital',%s,%s,%s)
               RETURNING id""",
            (cita.paciente, cita.cedula, cita.email, 0, cita.celular,
             _celular_wpp(cita.celular), cita.empresa, cita.especialidad, cita.id_medico,
             fecha, hora, cita.nombre_especialidad, cita.nombre_medico,
             fecha, hora, cita.nombre_especialidad, cita.nombre_medico,
             cita.cita_hospital, cita.recordatorios,
             f"registrada por hospital · {cita.usuario}"))
        nuevo = (await cur.fetchone())["id"]
        await con.commit()
        print(f"[externo] ALTA cita #{nuevo} (hospital {cita.cita_hospital}) "
              f"por {cita.usuario}")
        return {"ok": True, "id_chatbot": nuevo, "cita_hospital": cita.cita_hospital,
                "nota": "guarden id_chatbot en su columna idChatbot para futuras gestiones"}


@router.put("")
async def reagendar(r: Reagendamiento, simular: bool = False):
    fecha, hora = _partes(r.fecha_nueva)
    async with await conexion() as con:
        cur = con.cursor()
        await cur.execute(
            "SELECT id, estado, nombres_completos, fecha_cita, nota, celular, "
            "celular_whatsapp, nombre_especialidad, nombre_medico, piso, consultorio "
            "FROM citas_solicitadas WHERE id=%s", (r.id_chatbot,))
        fila = await cur.fetchone()
        if not fila:
            return {"ok": False, "motivo": f"no existe cita con id_chatbot {r.id_chatbot}"}
        if fila["estado"] not in _ACTIVAS:
            return {"ok": False,
                    "motivo": f"la cita {r.id_chatbot} está '{fila['estado']}': "
                              f"no se puede reagendar"}
        if simular:
            return {"ok": True, "simulado": True,
                    "haria": f"mover la cita {r.id_chatbot} de {fila['fecha_cita']} "
                             f"a {fecha} {hora}"}
        await cur.execute(
            """UPDATE citas_solicitadas SET
                 fecha_cita=%s, horario_cita=%s,
                 fecha_confirmada_paciente=%s, hora_confirmada_paciente=%s,
                 cita_reagendada=TRUE,
                 nota = TRIM(BOTH ' ·' FROM COALESCE(nota,'') || %s)
               WHERE id=%s""",
            (fecha, hora, fecha, hora,
             f" · reagendada por hospital ({r.usuario}) a {fecha} {hora}", r.id_chatbot))
        await con.commit()
        print(f"[externo] REAGENDA cita #{r.id_chatbot} -> {fecha} {hora} por {r.usuario}")
        out = {"ok": True, "id_chatbot": r.id_chatbot, "fecha": fecha, "hora": hora}
        if r.notificar:
            out["notificacion"] = await notificar_reagenda(dict(fila), fecha, hora)
        return out


@router.post("/cancelar")
async def cancelar(c: Cancelacion, simular: bool = False):
    async with await conexion() as con:
        cur = con.cursor()
        await cur.execute(
            "SELECT id, estado, nombres_completos, celular, celular_whatsapp, "
            "nombre_especialidad FROM citas_solicitadas WHERE id=%s", (c.id_chatbot,))
        fila = await cur.fetchone()
        if not fila:
            return {"ok": False, "motivo": f"no existe cita con id_chatbot {c.id_chatbot}"}
        if fila["estado"] == "cancelada":
            return {"ok": True, "id_chatbot": c.id_chatbot,
                    "nota": "ya estaba cancelada (idempotente)"}
        if simular:
            return {"ok": True, "simulado": True,
                    "haria": f"cancelar la cita {c.id_chatbot} de {fila['nombres_completos']}"}
        await cur.execute(
            """UPDATE citas_solicitadas SET estado='cancelada',
                 nota = TRIM(BOTH ' ·' FROM COALESCE(nota,'') || %s)
               WHERE id=%s""",
            (f" · cancelada por hospital ({c.usuario}): {c.motivo}", c.id_chatbot))
        await con.commit()
        print(f"[externo] CANCELA cita #{c.id_chatbot} por {c.usuario}: {c.motivo}")
        out = {"ok": True, "id_chatbot": c.id_chatbot, "estado": "cancelada"}
        if c.notificar:
            out["notificacion"] = await notificar_cancelacion(dict(fila), c.motivo)
        return out
