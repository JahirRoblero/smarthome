"""API para validar comandos sin ejecutarlos (Etapa 6)."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, StrictStr

from app.interpreter.lexer import ErrorLexico
from app.interpreter.parser import ErrorSintactico
from app.interpreter.semantic import ErrorSemantico, analizar_semantico

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["intérprete"])


class SolicitudAnalisis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: StrictStr


@router.post("/analizar")
def analizar(solicitud: SolicitudAnalisis):
    """Comprueba todo el programa y devuelve su AST sin ejecutar instrucciones."""
    try:
        ast = analizar_semantico(solicitud.codigo)
    except (ErrorLexico, ErrorSintactico, ErrorSemantico) as error:
        return JSONResponse(
            status_code=422,
            content={"correcto": False, "error": error.a_diccionario()},
        )
    except Exception:
        logger.exception("No fue posible cargar la tabla de símbolos de SmartHome")
        return JSONResponse(
            status_code=503,
            content={"correcto": False, "error": {
                "tipo": "INFRAESTRUCTURA",
                "descripcion": "No fue posible acceder a la tabla de símbolos."
            }},
        )
    return {
        "correcto": True,
        "instrucciones_validadas": len(ast.instrucciones),
        "ast": ast.a_diccionario(),
    }
