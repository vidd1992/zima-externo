"""Conexión a Postgres. Servicio de bajo volumen: una conexión por petición.

Este servicio SOLO toca `citas_solicitadas` (en producción, con un usuario de BD
restringido a esa tabla). Jamás llama a la API del hospital: es su espejo, no su eco.
"""
import psycopg
from psycopg.rows import dict_row

from app.config import settings


async def conexion() -> psycopg.AsyncConnection:
    return await psycopg.AsyncConnection.connect(
        settings.database_url, row_factory=dict_row, connect_timeout=10)
