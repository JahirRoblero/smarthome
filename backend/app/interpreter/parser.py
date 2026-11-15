"""Parser descendente recursivo para SmartHome Script 1.0.

Entrada: lista de tokens del lexer. Salida: AST sin efectos secundarios.
Respeta una instrucción por línea y prohíbe condicionales anidados.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections.abc import Sequence

from .ast_nodes import (
    Condicion, Condicional, Consulta, Control, Correo, InstruccionSimple,
    Listado, Notificacion, Programa,
)
from .lexer import ErrorLexico, TipoToken, Token, analizar_lexico


OPERACIONES_CONTROL = frozenset(
    {"ENCENDER", "APAGAR", "ACTIVAR", "DESACTIVAR", "ABRIR", "CERRAR"}
)


class ErrorSintactico(ValueError):
    """Error de estructura gramatical con posición en base 1."""

    def __init__(self, descripcion: str, linea: int, columna: int) -> None:
        self.tipo = "SINTACTICO"
        self.descripcion = descripcion
        self.linea = linea
        self.columna = columna
        super().__init__(f"Error sintáctico, línea {linea}, columna {columna}: {descripcion}")

    def a_diccionario(self) -> dict[str, str | int]:
        return {"tipo": self.tipo, "linea": self.linea,
                "columna": self.columna, "descripcion": self.descripcion}


class Parser:
    """Interpreta tokens estructuralmente, sin validar ni ejecutar dispositivos."""

    def __init__(self, tokens: Sequence[Token]) -> None:
        if not tokens or tokens[-1].tipo is not TipoToken.FIN_ARCHIVO:
            raise ValueError("La secuencia de tokens debe terminar en FIN_ARCHIVO.")
        self.tokens = tuple(tokens)
        self.posicion = 0

    def _actual(self) -> Token:
        return self.tokens[self.posicion]

    def _avanzar(self) -> Token:
        token = self._actual()
        if token.tipo is not TipoToken.FIN_ARCHIVO:
            self.posicion += 1
        return token

    def _error(self, descripcion: str) -> None:
        token = self._actual()
        raise ErrorSintactico(descripcion, token.linea, token.columna)

    def _consumir_tipo(self, tipo: TipoToken, descripcion: str) -> Token:
        token = self._actual()
        if token.tipo is not tipo:
            self._error(descripcion)
        return self._avanzar()

    def _consumir_palabra(self, palabra: str) -> Token:
        token = self._actual()
        if token.tipo is not TipoToken.PALABRA_RESERVADA or token.valor != palabra:
            self._error(f"se esperaba {palabra}.")
        return self._avanzar()

    def _instruccion_simple(self) -> InstruccionSimple:
        inicio = self._actual()
        if inicio.tipo is not TipoToken.PALABRA_RESERVADA:
            self._error("se esperaba una instrucción válida.")

        palabra = inicio.valor
        if palabra in OPERACIONES_CONTROL:
            self._avanzar()
            ident = self._consumir_tipo(
                TipoToken.IDENTIFICADOR,
                f"se esperaba IDENTIFICADOR después de {palabra}.",
            )
            return Control(palabra, ident.valor, inicio.linea, inicio.columna)

        if palabra == "CONSULTAR":
            self._avanzar()
            ident = self._consumir_tipo(
                TipoToken.IDENTIFICADOR,
                "se esperaba IDENTIFICADOR después de CONSULTAR.",
            )
            return Consulta(ident.valor, inicio.linea, inicio.columna)

        if palabra == "LISTAR":
            self._avanzar()
            self._consumir_palabra("DISPOSITIVOS")
            return Listado(inicio.linea, inicio.columna)

        if palabra == "NOTIFICAR":
            self._avanzar()
            mensaje = self._consumir_tipo(
                TipoToken.CADENA, "se esperaba CADENA después de NOTIFICAR."
            )
            return Notificacion(mensaje.valor, inicio.linea, inicio.columna)

        if palabra == "ENVIAR":
            self._avanzar()
            self._consumir_palabra("CORREO")
            self._consumir_palabra("A")
            destinatario = self._consumir_tipo(
                TipoToken.CADENA, "se esperaba CADENA con el destinatario del correo."
            )
            self._consumir_palabra("MENSAJE")
            mensaje = self._consumir_tipo(
                TipoToken.CADENA, "se esperaba CADENA con el mensaje del correo."
            )
            return Correo(destinatario.valor, mensaje.valor, inicio.linea, inicio.columna)

        self._error(f"la palabra {palabra!r} no inicia una instrucción simple válida.")

    def _instruccion(self):
        inicio = self._actual()
        if inicio.tipo is TipoToken.PALABRA_RESERVADA and inicio.valor == "SI":
            self._avanzar()
            ident = self._consumir_tipo(
                TipoToken.IDENTIFICADOR, "se esperaba IDENTIFICADOR después de SI."
            )
            self._consumir_tipo(TipoToken.IGUALDAD, "se esperaba el operador ==.")
            estado = self._consumir_tipo(TipoToken.ESTADO, "se esperaba un ESTADO válido.")
            self._consumir_palabra("ENTONCES")
            # La gramática exige instruccion_simple, de modo que SI anidados no son válidos.
            accion = self._instruccion_simple()
            condicion = Condicion(ident.valor, "==", estado.valor, ident.linea, ident.columna)
            return Condicional(condicion, accion, inicio.linea, inicio.columna)
        return self._instruccion_simple()

    def analizar(self) -> Programa:
        instrucciones = []
        while self._actual().tipo is TipoToken.SALTO_LINEA:
            self._avanzar()

        while self._actual().tipo is not TipoToken.FIN_ARCHIVO:
            instrucciones.append(self._instruccion())
            actual = self._actual()
            if actual.tipo is TipoToken.FIN_ARCHIVO:
                break
            if actual.tipo is not TipoToken.SALTO_LINEA:
                self._error("se esperaba SALTO_LINEA o fin de archivo después de la instrucción.")
            while self._actual().tipo is TipoToken.SALTO_LINEA:
                self._avanzar()
        return Programa(tuple(instrucciones))


def analizar_sintactico(texto: str) -> Programa:
    """Lexer + parser: devuelve un AST o propaga ErrorLexico/ErrorSintactico."""
    return Parser(analizar_lexico(texto)).analizar()


def main() -> int:
    parser_cli = argparse.ArgumentParser(description="Prueba del parser y AST SmartHome Script 1.0")
    entrada = parser_cli.add_mutually_exclusive_group(required=True)
    entrada.add_argument("--texto", help="Instrucción o programa en texto")
    entrada.add_argument("--archivo", type=Path, help="Ruta a un programa UTF-8")
    args = parser_cli.parse_args()
    if args.archivo is not None:
        try:
            texto = args.archivo.read_text(encoding="utf-8")
        except OSError as error:
            parser_cli.error(str(error))
    else:
        texto = args.texto

    try:
        resultado = {"correcto": True, "ast": analizar_sintactico(texto).a_diccionario()}
    except (ErrorLexico, ErrorSintactico) as error:
        print(json.dumps({"correcto": False, "error": error.a_diccionario()}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
