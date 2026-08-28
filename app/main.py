"""Zima-Externo — API para que sistemas externos (el hospital) reflejen en NUESTRAS
tablas lo que gestionan en los suyos: agendar, reagendar, cancelar y consultar.

Regla de oro: este servicio solo escribe en nuestra base. Jamás llama a la API del
hospital (es su espejo, no su eco: evita bucles de notificación).
Documentación interactiva: /externo/docs
"""
import time

from fastapi import FastAPI, Request

from app.rutas.consultas import router as consultas_router
from app.rutas.escrituras import router as escrituras_router

app = FastAPI(title="Zima-Externo", docs_url="/externo/docs",
              openapi_url="/externo/openapi.json")
# OJO: escrituras primero — /externo/citas/cancelar debe resolverse antes que
# el GET /externo/citas/{id_chatbot} de consultas.
app.include_router(escrituras_router)
app.include_router(consultas_router)


@app.middleware("http")
async def auditoria(request: Request, call_next):
    """Bitácora de acceso: TODA petición (también consultas) queda registrada.

    Formato: [acceso] MÉTODO ruta?query -> status (ms) ip=… token=sí/no
    El cuerpo no se loguea (contiene datos de pacientes); las escrituras ya dejan su
    propia línea [externo] con id, usuario y motivo.
    """
    inicio = time.time()
    respuesta = await call_next(request)
    ms = int((time.time() - inicio) * 1000)
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else "?"))
    con_token = "sí" if request.headers.get("x-externo-token") else "no"
    q = f"?{request.url.query}" if request.url.query else ""
    if request.url.path != "/externo/salud":  # el keep-alive no ensucia la bitácora
        print(f"[acceso] {request.method} {request.url.path}{q} -> "
              f"{respuesta.status_code} ({ms}ms) ip={ip} token={con_token}")
    return respuesta


@app.get("/externo/salud")
async def salud():
    return {"ok": True, "servicio": "zima-externo"}
