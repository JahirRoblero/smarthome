"""Endpoints para ejecutar SmartHome y leer historial y notificaciones."""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from app.api.routes.semantic import SolicitudPrograma
from app.core.push_notifications import enviar_notificaciones_push
from app.db.activity_repository import listar_historial, listar_notificaciones, registrar_error_ejecucion
from app.db.devices_repository import listar_dispositivos
from app.interpreter.executor import ErrorEjecucion, ejecutar_ir
from app.interpreter.intermediate import compilar_a_ir
from app.interpreter.lexer import ErrorLexico
from app.interpreter.parser import ErrorSintactico
from app.interpreter.semantic import ErrorSemantico

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ejecución"])


def guardar_error(codigo: str, error: ErrorLexico | ErrorSintactico | ErrorSemantico | ErrorEjecucion) -> None:
    """Anota comandos inválidos sin ocultar el error original si falla PostgreSQL."""
    try:
        registrar_error_ejecucion(codigo, error.a_diccionario())
    except Exception:
        logger.exception("No se pudo guardar una operación fallida en el historial")


@router.post("/ejecutar")
def ejecutar(solicitud: SolicitudPrograma, background_tasks: BackgroundTasks):
    """Compila, valida y ejecuta exclusivamente el código intermedio."""
    if len(solicitud.codigo) > 20000:
        return JSONResponse(
            status_code=413,
            content={"correcto": False, "error": {
                "tipo": "ENTRADA", "descripcion": "El programa excede 20000 caracteres."
            }},
        )
    try:
        programa_ir = compilar_a_ir(solicitud.codigo, optimizar=solicitud.optimizar)
    except (ErrorLexico, ErrorSintactico, ErrorSemantico) as error:
        guardar_error(solicitud.codigo, error)
        return JSONResponse(
            status_code=422, content={"correcto": False, "error": error.a_diccionario()}
        )
    except Exception:
        logger.exception("Fallo al compilar para ejecución")
        return JSONResponse(
            status_code=503,
            content={"correcto": False, "error": {
                "tipo": "INFRAESTRUCTURA", "descripcion": "No fue posible validar el programa."
            }},
        )
    try:
        resultado = ejecutar_ir(programa_ir, solicitud.codigo)
        resultado["dispositivos"] = listar_dispositivos()
        # La transacción del intérprete terminó: entregar solo avisos confirmados.
        ids = [evento["notificacion_id"] for evento in resultado["resultados"]
               if evento.get("estado") == "EXITOSA" and "notificacion_id" in evento]
        if ids:
            background_tasks.add_task(enviar_notificaciones_push, ids)
        return resultado
    except ErrorEjecucion as error:
        # El ejecutor ha revertido su transacción; guardamos ERROR aparte.
        guardar_error(solicitud.codigo, error)
        return JSONResponse(
            status_code=409, content={"correcto": False, "error": error.a_diccionario()}
        )
    except Exception:
        logger.exception("Fallo al ejecutar instrucciones SmartHome")
        return JSONResponse(
            status_code=503,
            content={"correcto": False, "error": {
                "tipo": "INFRAESTRUCTURA",
                "descripcion": "No fue posible ejecutar el programa."
            }},
        )


@router.get("/historial")
def historial(limite: int = Query(30, ge=1, le=100)):
    try:
        return {"historial": listar_historial(limite)}
    except Exception:
        logger.exception("Fallo al consultar historial")
        return JSONResponse(status_code=503, content={"detail": "Historial no disponible"})


@router.get("/notificaciones")
def notificaciones(limite: int = Query(30, ge=1, le=100)):
    try:
        return {"notificaciones": listar_notificaciones(limite)}
    except Exception:
        logger.exception("Fallo al consultar notificaciones")
        return JSONResponse(status_code=503, content={"detail": "Notificaciones no disponibles"})
