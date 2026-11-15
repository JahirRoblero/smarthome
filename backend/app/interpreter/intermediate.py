"""Generador de código intermedio (IR) de SmartHome Script 1.0.

El IR solo representa operaciones; NO accede a PostgreSQL ni ejecuta acciones.
Para compilar desde texto de manera segura usa compilar_a_ir(), que ejecuta
primero lexer, parser y la validación semántica de TODO el programa.

La máquina virtual futura interpretará estas operaciones, no el texto fuente.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import TypeAlias

from .ast_nodes import (
    Condicional,
    Consulta,
    Control,
    Correo,
    InstruccionSimple,
    Listado,
    Notificacion,
    Programa,
)
from .lexer import ErrorLexico
from .parser import ErrorSintactico
from .semantic import ErrorSemantico, analizar_semantico
from .symbols import TablaSimbolos


class OperacionIR(str, Enum):
    ASIGNAR_ESTADO = "ASIGNAR_ESTADO"
    CONSULTAR_ESTADO = "CONSULTAR_ESTADO"
    LISTAR_DISPOSITIVOS = "LISTAR_DISPOSITIVOS"
    REGISTRAR_NOTIFICACION = "REGISTRAR_NOTIFICACION"
    ENVIAR_CORREO = "ENVIAR_CORREO"
    LEER_ESTADO = "LEER_ESTADO"
    COMPARAR_IGUAL = "COMPARAR_IGUAL"
    SALTAR_SI_FALSO = "SALTAR_SI_FALSO"


ArgumentoIR: TypeAlias = str | int

# Operaciones de control -> estados canónicos, acordados en la especificación.
ESTADOS_DE_OPERACION = {
    "ENCENDER": "ENCENDIDO",
    "APAGAR": "APAGADO",
    "ACTIVAR": "ACTIVADA",
    "DESACTIVAR": "DESACTIVADA",
    "ABRIR": "ABIERTA",
    "CERRAR": "CERRADA",
}


@dataclass(frozen=True, slots=True)
class InstruccionIR:
    operacion: OperacionIR
    argumentos: tuple[ArgumentoIR, ...]
    linea: int
    columna: int

    def a_diccionario(self, indice: int) -> dict:
        return {
            "indice": indice,
            "operacion": self.operacion.value,
            "argumentos": list(self.argumentos),
            "linea": self.linea,
            "columna": self.columna,
        }


@dataclass(frozen=True, slots=True)
class ProgramaIR:
    instrucciones: tuple[InstruccionIR, ...]
    temporales: int

    def a_diccionario(self) -> dict:
        return {
            "tipo": "PROGRAMA_IR",
            "temporales": self.temporales,
            "instrucciones": [
                instruccion.a_diccionario(indice)
                for indice, instruccion in enumerate(self.instrucciones)
            ],
        }


class GeneradorIR:
    """Transforma un Programa AST *ya validado* en instrucciones lineales.

    Cada instancia genera una sola vez. Esto evita pérdidas de referencias
    al reutilizar temporales o direcciones entre programas diferentes.
    """

    def __init__(self) -> None:
        self._instrucciones: list[InstruccionIR] = []
        self._temporales = 0
        self._generado = False

    def _nuevo_temporal(self) -> str:
        temporal = f"t{self._temporales}"
        self._temporales += 1
        return temporal

    def _emitir(self, op: OperacionIR, args: tuple[ArgumentoIR, ...], nodo: object) -> int:
        indice = len(self._instrucciones)
        self._instrucciones.append(
            InstruccionIR(op, args, getattr(nodo, "linea"), getattr(nodo, "columna"))
        )
        return indice

    def _simple(self, nodo: InstruccionSimple) -> None:
        if isinstance(nodo, Control):
            estado = ESTADOS_DE_OPERACION[nodo.operacion]
            self._emitir(OperacionIR.ASIGNAR_ESTADO, (nodo.dispositivo, estado), nodo)
        elif isinstance(nodo, Consulta):
            self._emitir(OperacionIR.CONSULTAR_ESTADO, (nodo.dispositivo,), nodo)
        elif isinstance(nodo, Listado):
            self._emitir(OperacionIR.LISTAR_DISPOSITIVOS, (), nodo)
        elif isinstance(nodo, Notificacion):
            self._emitir(OperacionIR.REGISTRAR_NOTIFICACION, (nodo.mensaje,), nodo)
        elif isinstance(nodo, Correo):
            self._emitir(OperacionIR.ENVIAR_CORREO, (nodo.destinatario, nodo.mensaje), nodo)
        else:
            raise TypeError("El generador solo admite nodos simples del AST validado.")

    def _condicional(self, nodo: Condicional) -> None:
        # No evaluamos el estado actual aquí. El ejecutor lo leerá cuando llegue
        # a la instrucción, respetando cambios producidos por líneas anteriores.
        estado_temporal = self._nuevo_temporal()
        booleano_temporal = self._nuevo_temporal()
        self._emitir(
            OperacionIR.LEER_ESTADO,
            (nodo.condicion.dispositivo, estado_temporal),
            nodo.condicion,
        )
        self._emitir(
            OperacionIR.COMPARAR_IGUAL,
            (estado_temporal, nodo.condicion.estado, booleano_temporal),
            nodo.condicion,
        )
        # Reservamos el salto y posteriormente rellenamos la dirección exacta.
        indice_salto = self._emitir(
            OperacionIR.SALTAR_SI_FALSO, (booleano_temporal, -1), nodo
        )
        self._simple(nodo.accion)
        destino = len(self._instrucciones)  # puede señalar al fin del programa
        self._instrucciones[indice_salto] = replace(
            self._instrucciones[indice_salto],
            argumentos=(booleano_temporal, destino),
        )

    def generar(self, programa: Programa) -> ProgramaIR:
        if not isinstance(programa, Programa):
            raise TypeError("El generador IR necesita un AST de tipo Programa.")
        if self._generado:
            raise RuntimeError("Crea un GeneradorIR nuevo para cada programa.")
        self._generado = True
        for nodo in programa.instrucciones:
            if isinstance(nodo, Condicional):
                self._condicional(nodo)
            else:
                self._simple(nodo)
        return ProgramaIR(tuple(self._instrucciones), self._temporales)


def generar_codigo_intermedio(programa_validado: Programa) -> ProgramaIR:
    """Conversión pura AST -> IR. El llamador debe validar el AST primero."""
    return GeneradorIR().generar(programa_validado)


def compilar_a_ir(texto: str, tabla_simbolos: TablaSimbolos | None = None) -> ProgramaIR:
    """Punto de entrada público: texto -> léxico -> sintaxis -> semántica -> IR.

    Si existe un error de validación no devuelve un IR parcial.
    """
    programa_validado = analizar_semantico(texto, tabla_simbolos)
    return generar_codigo_intermedio(programa_validado)


def main() -> int:
    cli = argparse.ArgumentParser(description="Generador IR de SmartHome Script 1.0")
    origen = cli.add_mutually_exclusive_group(required=True)
    origen.add_argument("--texto", help="Programa fuente de SmartHome")
    origen.add_argument("--archivo", type=Path, help="Archivo UTF-8 con el programa")
    args = cli.parse_args()
    if args.archivo is not None:
        try:
            texto = args.archivo.read_text(encoding="utf-8")
        except OSError as error:
            cli.error(str(error))
    else:
        texto = args.texto
    try:
        resultado = {"correcto": True, "ir": compilar_a_ir(texto).a_diccionario()}
    except (ErrorLexico, ErrorSintactico, ErrorSemantico) as error:
        resultado = {"correcto": False, "error": error.a_diccionario()}
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
