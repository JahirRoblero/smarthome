"""Suscripción opcional a notificaciones del navegador."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.push_notifications import (
    clave_publica_vapid,
    quitar_suscripcion,
    registrar_suscripcion,
    validar_endpoint,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/push", tags=["notificaciones push"])


class ClavesPush(BaseModel):
    p256dh: str = Field(min_length=10, max_length=256)
    auth: str = Field(min_length=8, max_length=128)


class SuscripcionPush(BaseModel):
    endpoint: str = Field(min_length=16, max_length=4096)
    keys: ClavesPush


class CancelacionPush(BaseModel):
    endpoint: str = Field(min_length=16, max_length=4096)


@router.get("/clave-publica")
def clave_publica():
    try:
        return {"publicKey": clave_publica_vapid()}
    except Exception:
        logger.exception("No fue posible obtener la clave pública de Web Push")
        raise HTTPException(status_code=503, detail="Web Push no disponible")


@router.post("/suscribir")
def suscribir(suscripcion: SuscripcionPush):
    if not validar_endpoint(suscripcion.endpoint):
        raise HTTPException(status_code=422, detail="Servicio push no compatible")
    try:
        registrar_suscripcion(
            suscripcion.endpoint, suscripcion.keys.p256dh, suscripcion.keys.auth
        )
    except Exception:
        logger.exception("No fue posible guardar la suscripción Web Push")
        raise HTTPException(status_code=503, detail="No fue posible activar las notificaciones")
    return {"correcto": True}


@router.post("/cancelar")
def cancelar(suscripcion: CancelacionPush):
    try:
        quitar_suscripcion(suscripcion.endpoint)
    except Exception:
        logger.exception("No fue posible cancelar la suscripción Web Push")
        raise HTTPException(status_code=503, detail="No fue posible desactivar las notificaciones")
    return {"correcto": True}
