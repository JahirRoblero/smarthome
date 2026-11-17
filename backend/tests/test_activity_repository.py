"""Pruebas de consultas del historial y notificaciones sin PostgreSQL real."""
from datetime import datetime, timezone
import json
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


def test_registra_error_en_transaccion_independiente(monkeypatch):
    conexion = Connection([])
    monkeypatch.setattr(repo, "abrir_conexion", lambda: conexion)
    repo.registrar_error_ejecucion(
        "ENCENDER led1\nENCENDER alarma1",
        {
            "tipo": "SEMANTICO", "linea": 2, "columna": 1,
            "descripcion": "Las alarmas solo admiten ACTIVAR / DESACTIVAR.",
        },
    )
    sql = conexion.cursor_fake.sql
    instruccion, resultado, estado = conexion.cursor_fake.params
    assert "INSERT INTO historial" in sql
    assert instruccion == "ENCENDER alarma1"
    assert estado == "ERROR"
    datos = json.loads(resultado)
    assert datos["estado"] == "ERROR"
    assert datos["tipo"] == "SEMANTICO"
    assert datos["linea"] == 2
    assert "ACTIVAR / DESACTIVAR" in datos["detalle"]


def test_error_sin_linea_usa_texto_original(monkeypatch):
    conexion = Connection([])
    monkeypatch.setattr(repo, "abrir_conexion", lambda: conexion)
    repo.registrar_error_ejecucion("  ENCENDER led1@  ", {
        "tipo": "LEXICO",
        "descripcion": "Carácter inválido",
    })
    instruccion, resultado, estado = conexion.cursor_fake.params
    assert instruccion == "ENCENDER led1@"
    assert json.loads(resultado)["tipo"] == "LEXICO"
    assert estado == "ERROR"
