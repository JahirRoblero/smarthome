from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TipoToken(str, Enum):
    PALABRA_RESERVADA = "PALABRA_RESERVADA"
    ESTADO = "ESTADO"
    IDENTIFICADOR = "IDENTIFICADOR"
    CADENA = "CADENA"
    IGUALDAD = "IGUALDAD"
    SALTO_LINEA = "SALTO_LINEA"
    FIN_ARCHIVO = "FIN_ARCHIVO"


PALABRAS_RESERVADAS = frozenset(
    {
        "ENCENDER",
        "APAGAR",
        "ACTIVAR",
        "DESACTIVAR",
        "ABRIR",
        "CERRAR",
        "CONSULTAR",
        "LISTAR",
        "DISPOSITIVOS",
        "NOTIFICAR",
        "ENVIAR",
        "CORREO",
        "A",
        "MENSAJE",
        "SI",
        "ENTONCES",
    }
)

ESTADOS = frozenset(
    {"ENCENDIDO", "APAGADO", "ACTIVADA", "DESACTIVADA", "ABIERTA", "CERRADA"}
)


@dataclass(frozen=True, slots=True)
class Token:
    tipo: TipoToken
    valor: str
    linea: int
    columna: int
    lexema: str

    def a_diccionario(self) -> dict[str, str | int]:
        """Representación estable para demostraciones y futuras APIs."""
        return {
            "tipo": self.tipo.value,
            "valor": self.valor,
            "linea": self.linea,
            "columna": self.columna,
            "lexema": self.lexema,
        }


class ErrorLexico(ValueError):
    """Fallo de reconocimiento con ubicación de inicio en base 1."""

    def __init__(self, descripcion: str, linea: int, columna: int) -> None:
        self.tipo = "LEXICO"
        self.descripcion = descripcion
        self.linea = linea
        self.columna = columna
        super().__init__(f"Error léxico, línea {linea}, columna {columna}: {descripcion}")

    def a_diccionario(self) -> dict[str, str | int]:
        return {
            "tipo": self.tipo,
            "linea": self.linea,
            "columna": self.columna,
            "descripcion": self.descripcion,
        }


class Lexer:
    """Escáner manual con posiciones, sin dependencias externas."""

    def __init__(self, texto: str) -> None:
        if not isinstance(texto, str):
            raise TypeError("El código fuente debe ser texto (str).")
        self.texto = texto
        self.posicion = 0
        self.linea = 1
        self.columna = 1

    def _actual(self) -> str | None:
        if self.posicion >= len(self.texto):
            return None
        return self.texto[self.posicion]

    def _avanzar_caracter(self) -> str:
        """Avanza un carácter no perteneciente a un salto de línea."""
        caracter = self.texto[self.posicion]
        self.posicion += 1
        self.columna += 1
        return caracter

    def _leer_palabra(self, tipo: TipoToken) -> Token:
        inicio = self.posicion
        linea, columna = self.linea, self.columna
        if tipo == TipoToken.IDENTIFICADOR:
            # El primer carácter es [a-z]; los siguientes: [a-z0-9_].
            while (c := self._actual()) is not None and (
                "a" <= c <= "z" or "0" <= c <= "9" or c == "_"
            ):
                self._avanzar_caracter()
            valor = self.texto[inicio:self.posicion]
            siguiente = self._actual()
            if siguiente is not None and ("A" <= siguiente <= "Z" or siguiente == '"'):
                raise ErrorLexico(
                    "se esperaba un separador entre tokens de texto.", self.linea, self.columna
                )
            return Token(tipo, valor, linea, columna, valor)

        # Palabras escritas en MAYÚSCULAS, sin traducción automática de caso.
        while (c := self._actual()) is not None and (
            "A" <= c <= "Z" or "0" <= c <= "9" or c == "_"
        ):
            self._avanzar_caracter()
        valor = self.texto[inicio:self.posicion]
        siguiente = self._actual()
        if siguiente is not None and ("a" <= siguiente <= "z" or siguiente == '"'):
            raise ErrorLexico(
                "se esperaba un separador entre tokens de texto.", self.linea, self.columna
            )
        if valor in PALABRAS_RESERVADAS:
            return Token(TipoToken.PALABRA_RESERVADA, valor, linea, columna, valor)
        if valor in ESTADOS:
            return Token(TipoToken.ESTADO, valor, linea, columna, valor)
        raise ErrorLexico(f"palabra en mayúsculas no reconocida: {valor!r}.", linea, columna)

    def _leer_cadena(self) -> Token:
        inicio = self.posicion
        linea, columna = self.linea, self.columna
        self._avanzar_caracter()  # Comilla de apertura.
        contenido: list[str] = []

        while True:
            actual = self._actual()
            if actual is None or actual in ("\r", "\n"):
                raise ErrorLexico("cadena sin comillas de cierre.", linea, columna)
            if actual == '"':
                self._avanzar_caracter()
                siguiente = self._actual()
                if siguiente is not None and (
                    "A" <= siguiente <= "Z" or "a" <= siguiente <= "z" or siguiente == '"'
                ):
                    raise ErrorLexico(
                        "se esperaba un separador después de la cadena.", self.linea, self.columna
                    )
                return Token(
                    TipoToken.CADENA,
                    "".join(contenido),
                    linea,
                    columna,
                    self.texto[inicio:self.posicion],
                )
            if actual == "\\":
                barra_columna = self.columna
                self._avanzar_caracter()
                escape = self._actual()
                if escape is None or escape in ("\r", "\n"):
                    raise ErrorLexico("cadena sin comillas de cierre.", linea, columna)
                if escape not in ('"', "\\"):
                    secuencia = "\\" + escape
                    raise ErrorLexico(
                        f"secuencia de escape no admitida: {secuencia!r}.",
                        self.linea,
                        barra_columna,
                    )
                contenido.append(escape)
                self._avanzar_caracter()
                continue
            contenido.append(self._avanzar_caracter())

    def analizar(self) -> list[Token]:
        tokens: list[Token] = []

        while (actual := self._actual()) is not None:
            if actual in (" ", "\t"):
                self._avanzar_caracter()
                continue

            if actual == "\n" or (actual == "\r" and self.texto[self.posicion:self.posicion + 2] == "\r\n"):
                inicio = self.posicion
                linea, columna = self.linea, self.columna
                self.posicion += 2 if actual == "\r" else 1
                tokens.append(
                    Token(TipoToken.SALTO_LINEA, "\n", linea, columna, self.texto[inicio:self.posicion])
                )
                self.linea += 1
                self.columna = 1
                continue

            if "a" <= actual <= "z":
                tokens.append(self._leer_palabra(TipoToken.IDENTIFICADOR))
                continue
            if "A" <= actual <= "Z":
                tokens.append(self._leer_palabra(TipoToken.PALABRA_RESERVADA))
                continue
            if actual == '"':
                tokens.append(self._leer_cadena())
                continue
            if actual == "=" and self.texto[self.posicion:self.posicion + 2] == "==":
                tokens.append(Token(TipoToken.IGUALDAD, "==", self.linea, self.columna, "=="))
                self._avanzar_caracter()
                self._avanzar_caracter()
                continue

            raise ErrorLexico(f"carácter {actual!r} no reconocido.", self.linea, self.columna)

        tokens.append(Token(TipoToken.FIN_ARCHIVO, "", self.linea, self.columna, ""))
        return tokens


def analizar_lexico(texto: str) -> list[Token]:
    """Punto de entrada que utilizará el parser en la etapa 4."""
    return Lexer(texto).analizar()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba del lexer SmartHome Script 1.0")
    origen = parser.add_mutually_exclusive_group(required=True)
    origen.add_argument("--texto", help="Instrucción o programa en texto")
    origen.add_argument("--archivo", type=Path, help="Ruta a un programa de texto UTF-8")
    args = parser.parse_args()
    if args.archivo:
        try:
            texto = args.archivo.read_text(encoding="utf-8")
        except OSError as error:
            parser.error(str(error))
    else:
        texto = args.texto

    try:
        resultado = {"correcto": True, "tokens": [t.a_diccionario() for t in analizar_lexico(texto)]}
    except ErrorLexico as error:
        print(json.dumps({"correcto": False, "error": error.a_diccionario()}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
