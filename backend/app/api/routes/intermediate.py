"""API para convertir programas SmartHome validados en código intermedio."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.routes.semantic import SolicitudPrograma
from app.interpreter.intermediate import compilar_a_ir
from app.interpreter.lexer import ErrorLexico
from app.interpreter.parser import ErrorSintactico
from app.interpreter.semantic import ErrorSemantico

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["intérprete"])


@router.post("/compilar")
def compilar(solicitud: SolicitudPrograma):
    """Genera instrucciones IR, sin ejecutar ni modificar dispositivos."""
    try:
        programa = compilar_a_ir(solicitud.codigo, optimizar=solicitud.optimizar)
    except (ErrorLexico, ErrorSintactico, ErrorSemantico) as error:
        return JSONResponse(
            status_code=422,
            content={"correcto": False, "error": error.a_diccionario()},
        )
    except Exception:
        logger.exception("No fue posible compilar SmartHome a IR")
        return JSONResponse(
            status_code=503,
            content={"correcto": False, "error": {
                "tipo": "INFRAESTRUCTURA",
                "descripcion": "No fue posible generar el código intermedio.",
            }},
        )
    return {"correcto": True, "ir": programa.a_diccionario()}
