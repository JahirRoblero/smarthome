"""Acceso a dispositivos persistentes mediante consultas parametrizadas.

Todas las operaciones de esta etapa son de lectura salvo la actualización interna
que utilizará el futuro motor de ejecución. No se expone una ruta HTTP para cambiar
estados sin pasar por el intérprete.
"""

from __future__ import annotations

from .connection import abrir_conexion


COLUMNAS = "identificador, tipo, estado, actualizado_en"


def _como_dispositivo(fila: tuple) -> dict:
    return {
        "identificador": fila[0],
        "tipo": fila[1],
        "estado": fila[2],
        "actualizado_en": fila[3],
    }


def listar_dispositivos() -> list[dict]:
    with abrir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                f"SELECT {COLUMNAS} FROM dispositivos ORDER BY identificador"
            )
            return [_como_dispositivo(fila) for fila in cursor.fetchall()]


def obtener_dispositivo(identificador: str) -> dict | None:
    with abrir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                f"SELECT {COLUMNAS} FROM dispositivos WHERE identificador = %s",
                (identificador,),
            )
            fila = cursor.fetchone()
            return _como_dispositivo(fila) if fila else None


def actualizar_estado(identificador: str, estado: str) -> dict | None:
    """Acción interna futura; los CHECK de PostgreSQL rechazan estados incompatibles."""
    with abrir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE dispositivos SET estado = %s, actualizado_en = CURRENT_TIMESTAMP "
                f"WHERE identificador = %s RETURNING {COLUMNAS}",
                (estado, identificador),
            )
            fila = cursor.fetchone()
            return _como_dispositivo(fila) if fila else None
