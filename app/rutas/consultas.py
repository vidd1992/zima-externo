"""Consultas de solo lectura: listar y ver citas de nuestra tabla."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db import conexion
from app.seguridad import requiere_token

router = APIRouter(prefix="/externo/citas", tags=["consultas"],
                   dependencies=[Depends(requiere_token)])

_CAMPOS = """id AS id_chatbot, cita_hospital, nombres_completos AS paciente, cedula,
             celular, estado, origen,
             COALESCE(fecha_confirmada_paciente, fecha_cita)::text AS fecha,
             COALESCE(hora_confirmada_paciente, horario_cita) AS hora,
             COALESCE(nombre_medico_confirmada, nombre_medico) AS medico,
             COALESCE(nombre_especialidad_confirmada, nombre_especialidad) AS especialidad,
             COALESCE(nota,'') AS nota,
             to_char(creada AT TIME ZONE 'America/Guayaquil',
                     'YYYY-MM-DD HH24:MI') AS registrada"""


@router.get("")
async def listar(cedula: str = "", celular: str = "", fecha: str = "",
                 estado: str = "", origen: str = "", limite: int = 50):
    """Lista citas con filtros. `cedula` acepta con o sin prefijo; `fecha` = YYYY-MM-DD."""
    limite = max(1, min(limite, 200))
    cond, args = ["TRUE"], []
    if cedula:
        sin = cedula[1:] if cedula[:1].isalpha() else cedula
        cond.append("(cedula=%s OR cedula=%s OR cedula=%s)")
        args += [cedula, sin, "C" + sin]
    if celular:
        d = "".join(c for c in celular if c.isdigit())
        cond.append("(celular LIKE %s OR celular_whatsapp LIKE %s)")
        args += [f"%{d[-9:]}", f"%{d[-9:]}"]
    if fecha:
        cond.append("COALESCE(fecha_confirmada_paciente, fecha_cita)=%s")
        args.append(fecha)
    if estado:
        cond.append("estado=%s")
        args.append(estado)
    if origen:
        cond.append("origen=%s")
        args.append(origen)
    async with await conexion() as con:
        cur = con.cursor()
        await cur.execute(
            f"SELECT {_CAMPOS} FROM citas_solicitadas WHERE {' AND '.join(cond)} "
            f"ORDER BY id DESC LIMIT %s", (*args, limite))
        filas = await cur.fetchall()
    return {"ok": True, "total": len(filas), "citas": filas}


@router.get("/{id_chatbot}")
async def ver(id_chatbot: int):
    async with await conexion() as con:
        cur = con.cursor()
        await cur.execute(
            f"SELECT {_CAMPOS} FROM citas_solicitadas WHERE id=%s", (id_chatbot,))
        fila = await cur.fetchone()
    if not fila:
        return {"ok": False, "motivo": f"no existe cita con id_chatbot {id_chatbot}"}
    return {"ok": True, "cita": fila}
