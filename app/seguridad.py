"""Autenticación: todas las rutas exigen el encabezado X-Externo-Token."""
from fastapi import Header, HTTPException

from app.config import settings


async def requiere_token(x_externo_token: str = Header(default="")) -> None:
    if not settings.externo_token or x_externo_token != settings.externo_token:
        raise HTTPException(status_code=401, detail="token inválido o ausente")
