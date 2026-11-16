"""Lectura del historial y de las notificaciones persistidas en PostgreSQL."""
from __future__ import annotations
import json

from .connection import abrir_conexion


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
