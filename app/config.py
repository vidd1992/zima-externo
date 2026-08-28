"""Configuración del microservicio (variables de entorno / .env)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    externo_token: str = ""

    # Aviso opcional al paciente (F2). El envío REAL exige EXTERNO_ENVIO_REAL=true.
    externo_envio_real: bool = False
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    plantilla_confirmacion: str = "confirmacion_cita"


settings = Settings()
