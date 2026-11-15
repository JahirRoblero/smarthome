"""Tabla de símbolos del intérprete construida desde PostgreSQL.

La tabla es una instantánea de los dispositivos persistidos. Las operaciones y
estados válidos son reglas del lenguaje, no columnas duplicadas en la BD.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable


REGLAS_POR_TIPO = {
    "LED": (("ENCENDIDO", "APAGADO"), ("ENCENDER", "APAGAR", "CONSULTAR")),
    "LUZ": (("ENCENDIDO", "APAGADO"), ("ENCENDER", "APAGAR", "CONSULTAR")),
    "VENTILADOR": (("ENCENDIDO", "APAGADO"), ("ENCENDER", "APAGAR", "CONSULTAR")),
    "ALARMA": (("ACTIVADA", "DESACTIVADA"), ("ACTIVAR", "DESACTIVAR", "CONSULTAR")),
    "PUERTA": (("ABIERTA", "CERRADA"), ("ABRIR", "CERRAR", "CONSULTAR")),
}


@dataclass(frozen=True, slots=True)
class SimboloDispositivo:
    identificador: str
    tipo: str
    estado: str
    estados_permitidos: tuple[str, ...]
    operaciones_permitidas: tuple[str, ...]

    def a_diccionario(self) -> dict:
        return {
            "identificador": self.identificador,
            "tipo": self.tipo,
            "estado": self.estado,
            "estados_permitidos": list(self.estados_permitidos),
            "operaciones_permitidas": list(self.operaciones_permitidas),
        }


class TablaSimbolos:
    def __init__(self, dispositivos: Iterable[dict]) -> None:
        simbolos: dict[str, SimboloDispositivo] = {}
        for dispositivo in dispositivos:
            identificador = dispositivo["identificador"]
            tipo = dispositivo["tipo"]
            estado = dispositivo["estado"]
            if identificador in simbolos:
                raise ValueError(f"Identificador duplicado: {identificador}.")
            if tipo not in REGLAS_POR_TIPO:
                raise ValueError(f"Tipo de dispositivo desconocido: {tipo}.")
            estados, operaciones = REGLAS_POR_TIPO[tipo]
            if estado not in estados:
                raise ValueError(f"Estado {estado} incompatible con {tipo}.")
            simbolos[identificador] = SimboloDispositivo(
                identificador, tipo, estado, estados, operaciones
            )
        self._simbolos = simbolos

    def buscar(self, identificador: str) -> SimboloDispositivo | None:
        return self._simbolos.get(identificador)

    def existe(self, identificador: str) -> bool:
        return identificador in self._simbolos

    def listar(self) -> list[SimboloDispositivo]:
        return list(self._simbolos.values())

    def __len__(self) -> int:
        return len(self._simbolos)


def cargar_tabla_simbolos() -> TablaSimbolos:
    # Se carga en cada solicitud/validación para no usar estados obsoletos.
    from app.db.devices_repository import listar_dispositivos
    return TablaSimbolos(listar_dispositivos())
