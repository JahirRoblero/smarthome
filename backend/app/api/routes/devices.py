"""API de consulta de dispositivos y tabla de símbolos. Solo lectura."""

import logging

from fastapi import APIRouter, HTTPException

from app.db.devices_repository import listar_dispositivos, obtener_dispositivo
from app.interpreter.symbols import TablaSimbolos


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["dispositivos"])


def _error_base_de_datos(error: Exception) -> HTTPException:
    logger.exception("Fallo al consultar dispositivos SmartHome: %s", error)
    return HTTPException(status_code=503, detail="Base de datos no disponible")


@router.get("/dispositivos")
def dispositivos():
    try:
        return {"dispositivos": listar_dispositivos()}
    except Exception as error:
        raise _error_base_de_datos(error) from error


@router.get("/dispositivos/{identificador}")
def dispositivo(identificador: str):
    try:
        resultado = obtener_dispositivo(identificador)
    except Exception as error:
        raise _error_base_de_datos(error) from error
    if resultado is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return resultado


@router.get("/tabla-simbolos")
def tabla_simbolos():
    try:
        simbolos = TablaSimbolos(listar_dispositivos())
    except Exception as error:
        raise _error_base_de_datos(error) from error
    return {"simbolos": [simbolo.a_diccionario() for simbolo in simbolos.listar()]}
