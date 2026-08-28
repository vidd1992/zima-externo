"""Modelos Pydantic = EL CONTRATO con los sistemas externos.

FastAPI valida cada petición contra estos modelos y genera la documentación
interactiva (/externo/docs) automáticamente. Convenciones idénticas a las que el
hospital ya usa con el bot: cédula CON prefijo de tipo (C/R/P), fechas ISO local
de Ecuador (YYYY-MM-DDTHH:MM:SS), códigos de especialidad E##, ids de aseguradora.

La llave de TODO es `id_chatbot` (nuestro id): su sistema ya tiene esa columna en
cada cita — para las del bot ya viene llena; para las suyas, la llenan con el id
que les devolvemos al registrar.
"""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_CEDULA = re.compile(r"^[CRP]\d{9,13}$")


def _valida_fecha_iso(v: str) -> str:
    try:
        datetime.fromisoformat(v)
    except ValueError as e:
        raise ValueError(
            f"fecha inválida {v!r}: se espera ISO local YYYY-MM-DDTHH:MM:SS") from e
    return v


class CitaEntrante(BaseModel):
    """POST /externo/citas — una cita agendada en el sistema del hospital."""
    cita_hospital: int = Field(gt=0, description="Número de la cita en SU sistema")
    paciente: str = Field(min_length=5, description="Nombres completos")
    cedula: str = Field(description="Con prefijo de tipo: C0102030405 / R... / P...")
    celular: str = Field(min_length=7)
    email: str = ""
    especialidad: str = Field(description="Código, ej. E59")
    nombre_especialidad: str = ""
    id_medico: int = Field(gt=0)
    nombre_medico: str = ""
    fecha_aten: str = Field(description="ISO local, ej. 2026-08-25T11:00:00")
    empresa: int = Field(ge=0, description="Id de la aseguradora")
    usuario: str = Field(min_length=3, description="Quién lo hizo en su sistema")
    recordatorios: bool = Field(
        default=False, description="Si true, el paciente recibe recordatorios de WhatsApp")

    @field_validator("cedula")
    @classmethod
    def _cedula_con_prefijo(cls, v: str) -> str:
        if not _CEDULA.match(v):
            raise ValueError(
                f"cédula {v!r} inválida: debe llevar prefijo de tipo, ej. C0102030405")
        return v

    @field_validator("fecha_aten")
    @classmethod
    def _fecha(cls, v: str) -> str:
        return _valida_fecha_iso(v)


class Reagendamiento(BaseModel):
    """PUT /externo/citas — mover una cita nuestra a otra fecha/hora."""
    id_chatbot: int = Field(gt=0, description="Nuestro id (el idChatbot de su tabla)")
    fecha_nueva: str = Field(description="ISO local, ej. 2026-08-28T16:30:00")
    usuario: str = Field(min_length=3)
    notificar: bool = Field(default=False, description="Avisar al paciente por WhatsApp (F2)")

    @field_validator("fecha_nueva")
    @classmethod
    def _fecha(cls, v: str) -> str:
        return _valida_fecha_iso(v)


class Cancelacion(BaseModel):
    """POST /externo/citas/cancelar — cancelar una cita nuestra."""
    id_chatbot: int = Field(gt=0)
    motivo: str = Field(min_length=3)
    usuario: str = Field(min_length=3)
    notificar: bool = False
