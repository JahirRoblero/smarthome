"""Endpoints de verificacion para la etapa de arquitectura."""
from fastapi import APIRouter
from app.core.config import SMTP_HOST, SMTP_PORT
from app.db.connection import database_is_available

router = APIRouter(prefix="/api", tags=["sistema"])


@router.get("/ping")
def ping():
    return {"service": "smarthome-backend", "status": "ok", "stage": 2}


@router.get("/health")
def health():
    database_ok = database_is_available()
    return {
        "service": "smarthome-backend",
        "status": "ok" if database_ok else "degraded",
        "database": "connected" if database_ok else "disconnected",
        "smtp": {"host": SMTP_HOST, "port": SMTP_PORT, "status": "configured_not_tested"},
    }
