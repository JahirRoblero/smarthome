"""Árbol sintáctico abstracto (AST) de SmartHome Script 1.0.

Los nodos solamente representan instrucciones: no consultan la base de datos,
no verifican dispositivos y no ejecutan acciones.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class Control:
    operacion: str
    dispositivo: str
    linea: int
    columna: int

    def a_diccionario(self) -> dict:
        return {"tipo": "CONTROL", "operacion": self.operacion,
                "dispositivo": self.dispositivo, "linea": self.linea, "columna": self.columna}


@dataclass(frozen=True, slots=True)
class Consulta:
    dispositivo: str
    linea: int
    columna: int

    def a_diccionario(self) -> dict:
        return {"tipo": "CONSULTA", "dispositivo": self.dispositivo,
                "linea": self.linea, "columna": self.columna}


@dataclass(frozen=True, slots=True)
class Listado:
    linea: int
    columna: int

    def a_diccionario(self) -> dict:
        return {"tipo": "LISTADO", "recurso": "DISPOSITIVOS",
                "linea": self.linea, "columna": self.columna}


@dataclass(frozen=True, slots=True)
class Notificacion:
    mensaje: str
    linea: int
    columna: int

    def a_diccionario(self) -> dict:
        return {"tipo": "NOTIFICACION", "mensaje": self.mensaje,
                "linea": self.linea, "columna": self.columna}


@dataclass(frozen=True, slots=True)
class Correo:
    destinatario: str
    mensaje: str
    linea: int
    columna: int

    def a_diccionario(self) -> dict:
        return {"tipo": "CORREO", "destinatario": self.destinatario,
                "mensaje": self.mensaje, "linea": self.linea, "columna": self.columna}


InstruccionSimple: TypeAlias = Control | Consulta | Listado | Notificacion | Correo


@dataclass(frozen=True, slots=True)
class Condicion:
    dispositivo: str
    operador: str
    estado: str
    linea: int
    columna: int

    def a_diccionario(self) -> dict:
        return {"tipo": "COMPARACION_ESTADO", "dispositivo": self.dispositivo,
                "operador": self.operador, "estado": self.estado,
                "linea": self.linea, "columna": self.columna}


@dataclass(frozen=True, slots=True)
class Condicional:
    condicion: Condicion
    accion: InstruccionSimple
    linea: int
    columna: int

    def a_diccionario(self) -> dict:
        return {"tipo": "CONDICIONAL", "condicion": self.condicion.a_diccionario(),
                "accion": self.accion.a_diccionario(),
                "linea": self.linea, "columna": self.columna}


Instruccion: TypeAlias = InstruccionSimple | Condicional


@dataclass(frozen=True, slots=True)
class Programa:
    instrucciones: tuple[Instruccion, ...]

    def a_diccionario(self) -> dict:
        return {"tipo": "PROGRAMA", "instrucciones": [n.a_diccionario() for n in self.instrucciones]}
