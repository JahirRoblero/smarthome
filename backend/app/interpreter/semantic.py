"""Análisis semántico de SmartHome Script 1.0 (Etapa 6).

Valida el AST completo usando la tabla de símbolos obtenida de PostgreSQL.
No ejecuta operaciones, envía correos ni modifica dispositivos.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .ast_nodes import (
    Condicion,
    Condicional,
    Consulta,
    Control,
    Correo,
    Listado,
    Notificacion,
    Programa,
)
from .lexer import ErrorLexico
from .parser import ErrorSintactico, analizar_sintactico
from .symbols import TablaSimbolos, cargar_tabla_simbolos


# Versión deliberadamente sencilla: formato de correo usual, sin espacios ni @ extra.
PATRON_CORREO = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
TIPOS_SIMPLES = (Control, Consulta, Listado, Notificacion, Correo)


class ErrorSemantico(ValueError):
    """Error de significado de una instrucción, con línea y columna."""

    def __init__(self, descripcion: str, linea: int, columna: int) -> None:
        self.tipo = "SEMANTICO"
        self.descripcion = descripcion
        self.linea = linea
        self.columna = columna
        super().__init__(
            f"Error semántico, línea {linea}, columna {columna}: {descripcion}"
        )

    def a_diccionario(self) -> dict[str, str | int]:
        return {
            "tipo": self.tipo,
            "linea": self.linea,
            "columna": self.columna,
            "descripcion": self.descripcion,
        }


class AnalizadorSemantico:
    """Comprueba todos los nodos sin alterar la tabla de símbolos."""

    def __init__(self, tabla: TablaSimbolos) -> None:
        self.tabla = tabla

    @staticmethod
    def _error(descripcion: str, nodo: object) -> None:
        raise ErrorSemantico(
            descripcion, getattr(nodo, "linea", 1), getattr(nodo, "columna", 1)
        )

    def _dispositivo(self, identificador: str, nodo: object):
        if not isinstance(identificador, str):
            self._error("el identificador del dispositivo debe ser texto.", nodo)
        simbolo = self.tabla.buscar(identificador)
        if simbolo is None:
            self._error(f"dispositivo inexistente: {identificador}.", nodo)
        return simbolo

    def _validar_simple(self, nodo: object) -> None:
        if isinstance(nodo, Control):
            simbolo = self._dispositivo(nodo.dispositivo, nodo)
            if not isinstance(nodo.operacion, str):
                self._error("la operación debe ser texto.", nodo)
            if nodo.operacion not in simbolo.operaciones_permitidas:
                # CONSULTAR es una operación general, no una acción de control.
                acciones = [
                    operacion for operacion in simbolo.operaciones_permitidas
                    if operacion != "CONSULTAR"
                ]
                tipos = {
                    "LED": "Los LED",
                    "LUZ": "Las luces",
                    "VENTILADOR": "Los ventiladores",
                    "ALARMA": "Las alarmas",
                    "PUERTA": "Las puertas",
                }
                sujeto = tipos.get(simbolo.tipo, f"Los dispositivos {simbolo.tipo}")
                permitidas = " / ".join(acciones)
                self._error(
                    f"operación {nodo.operacion} incompatible con {simbolo.tipo}. "
                    f"{sujeto} solo admiten {permitidas}.",
                    nodo,
                )
            return

        if isinstance(nodo, Consulta):
            self._dispositivo(nodo.dispositivo, nodo)
            return

        if isinstance(nodo, Listado):
            return

        if isinstance(nodo, Notificacion):
            if not isinstance(nodo.mensaje, str):
                self._error("el mensaje de NOTIFICAR debe ser texto.", nodo)
            if not nodo.mensaje.strip():
                self._error("el mensaje de NOTIFICAR no puede estar vacío.", nodo)
            return

        if isinstance(nodo, Correo):
            if not isinstance(nodo.destinatario, str):
                self._error("el destinatario de CORREO debe ser texto.", nodo)
            if not PATRON_CORREO.fullmatch(nodo.destinatario):
                self._error("dirección de correo electrónico inválida.", nodo)
            if not isinstance(nodo.mensaje, str):
                self._error("el mensaje de CORREO debe ser texto.", nodo)
            if not nodo.mensaje.strip():
                self._error("el mensaje de CORREO no puede estar vacío.", nodo)
            return

        self._error("instrucción simple no reconocida.", nodo)

    def _validar_condicion(self, nodo: Condicion) -> None:
        simbolo = self._dispositivo(nodo.dispositivo, nodo)
        if not isinstance(nodo.operador, str) or nodo.operador != "==":
            self._error("la condición solo admite el operador ==.", nodo)
        if not isinstance(nodo.estado, str):
            self._error("el estado de una condición debe ser texto.", nodo)
        if nodo.estado not in simbolo.estados_permitidos:
            self._error(
                f"el estado {nodo.estado} no es válido para {simbolo.tipo}.", nodo
            )

    def analizar(self, programa: Programa) -> Programa:
        if not isinstance(programa, Programa):
            raise TypeError("El análisis semántico requiere un AST de tipo Programa.")
        # Validación completa y sin efectos; no se ejecuta ninguna de sus líneas.
        for instruccion in programa.instrucciones:
            if isinstance(instruccion, Condicional):
                if not isinstance(instruccion.condicion, Condicion):
                    self._error("se esperaba una condición válida.", instruccion)
                self._validar_condicion(instruccion.condicion)
                if not isinstance(instruccion.accion, TIPOS_SIMPLES):
                    self._error(
                        "SI...ENTONCES requiere una instrucción simple, sin anidamientos.",
                        instruccion,
                    )
                # La acción se valida aunque la condición pudiera ser falsa al ejecutar.
                self._validar_simple(instruccion.accion)
            else:
                self._validar_simple(instruccion)
        return programa


def analizar_semantico(
    texto: str, tabla_simbolos: TablaSimbolos | None = None
) -> Programa:
    """Analiza lexer → parser → semántica. Devuelve AST intacto o lanza un error.

    Para producción obtiene símbolos de PostgreSQL. Las pruebas pueden pasar una
    TablaSimbolos en memoria sin abrir conexiones.
    """
    ast = analizar_sintactico(texto)
    tabla = tabla_simbolos if tabla_simbolos is not None else cargar_tabla_simbolos()
    return AnalizadorSemantico(tabla).analizar(ast)


def main() -> int:
    cli = argparse.ArgumentParser(description="Validar semántica de SmartHome Script 1.0")
    entrada = cli.add_mutually_exclusive_group(required=True)
    entrada.add_argument("--texto", help="Código fuente SmartHome")
    entrada.add_argument("--archivo", type=Path, help="Archivo UTF-8 con instrucciones")
    args = cli.parse_args()
    if args.archivo is not None:
        try:
            texto = args.archivo.read_text(encoding="utf-8")
        except OSError as error:
            cli.error(str(error))
    else:
        texto = args.texto

    try:
        ast = analizar_semantico(texto)
        resultado = {
            "correcto": True,
            "instrucciones_validadas": len(ast.instrucciones),
            "ast": ast.a_diccionario(),
        }
    except (ErrorLexico, ErrorSintactico, ErrorSemantico) as error:
        resultado = {"correcto": False, "error": error.a_diccionario()}
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
