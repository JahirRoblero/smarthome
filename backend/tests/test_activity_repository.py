"""Pruebas de consultas del historial y notificaciones sin PostgreSQL real."""
from datetime import datetime, timezone
from app.db import activity_repository as repo


class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = None
        self.params = None
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params):
        self.sql, self.params = sql, params
    def fetchall(self): return self.rows


class Connection:
    def __init__(self, rows):
        self.cursor_fake = Cursor(rows)
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def cursor(self): return self.cursor_fake


def test_historial_decodifica_resultados_y_parametriza_limite(monkeypatch):
    fecha = datetime(2026, 11, 15, tzinfo=timezone.utc)
    conexion = Connection([(1, "ENCENDER led1", '{"detalle":"led1: ENCENDIDO"}', "EXITOSA", fecha)])
    monkeypatch.setattr(repo, "abrir_conexion", lambda: conexion)
    filas = repo.listar_historial(10)
    assert filas[0]["resultado"]["detalle"] == "led1: ENCENDIDO"
    assert filas[0]["fecha"] == fecha
    assert conexion.cursor_fake.params == (10,)
    assert "ORDER BY id DESC LIMIT %s" in conexion.cursor_fake.sql


def test_historial_acepta_texto_legacy(monkeypatch):
    monkeypatch.setattr(repo, "abrir_conexion", lambda: Connection([(1, "CONSULTAR led1", "texto", "EXITOSA", None)]))
    assert repo.listar_historial()[0]["resultado"] == "texto"


def test_notificaciones(monkeypatch):
    fecha = datetime(2026, 11, 15, tzinfo=timezone.utc)
    conexion = Connection([(3, "Alerta", fecha)])
    monkeypatch.setattr(repo, "abrir_conexion", lambda: conexion)
    assert repo.listar_notificaciones(5) == [{"id": 3, "mensaje": "Alerta", "fecha": fecha}]
    assert conexion.cursor_fake.params == (5,)
