"""Configuracion de desarrollo mediante variables de entorno."""
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://smarthome:smarthome_dev_only@localhost:5432/smarthome"
)
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
