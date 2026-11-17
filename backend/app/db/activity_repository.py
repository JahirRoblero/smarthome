"""Registro de errores y lectura del historial/notificaciones de PostgreSQL."""
from __future__ import annotations
import json

from .connection import abrir_conexion


def registrar_error_ejecucion(codigo: str, error: dict) -> None:
    """Persiste el intento fallido en una transacción independiente.

    Si una ejecución IR falla, su transacción se revierte; por eso el registro
    de ERROR ocurre después del rollback, en una nueva conexión.
    """
    lineas = codigo.splitlines()
    numero = error.get("linea")
    if isinstance(numero, int) and not isinstance(numero, bool) and 1 <= numero <= len(lineas):
        instruccion = lineas[numero - 1].strip()
    else:
        instruccion = codigo.strip()

    evento = {
        "estado": "ERROR",
        "tipo": error.get("tipo", "EJECUCION"),
        "linea": numero,
        "columna": error.get("columna"),
        "detalle": error.get("descripcion", "No fue posible ejecutar la instrucción."),
    }
    with abrir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "INSERT INTO historial (instruccion, resultado, estado_ejecucion) "
                "VALUES (%s, %s, %s)",
                (instruccion, json.dumps(evento, ensure_ascii=False), "ERROR"),
            )


def listar_historial(limite: int = 30) -> list[dict]:
    with abrir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT id, instruccion, resultado, estado_ejecucion, fecha "
                "FROM historial ORDER BY id DESC LIMIT %s",
                (limite,),
            )
            filas = cursor.fetchall()
    historial = []
    for id_, instruccion, resultado, estado, fecha in filas:
        try:
            detalle = json.loads(resultado) if resultado else None
        except (ValueError, TypeError):
            detalle = resultado
        historial.append({
            "id": id_, "instruccion": instruccion, "resultado": detalle,
            "estado_ejecucion": estado, "fecha": fecha,
        })
    return historial


def listar_notificaciones(limite: int = 30) -> list[dict]:
    with abrir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT id, mensaje, fecha FROM notificaciones ORDER BY id DESC LIMIT %s",
                (limite,),
            )
            filas = cursor.fetchall()
    return [{"id": id_, "mensaje": mensaje, "fecha": fecha}
            for id_, mensaje, fecha in filas]
