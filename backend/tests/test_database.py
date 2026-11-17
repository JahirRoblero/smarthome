"""Pruebas unitarias de SQL y repositorio; no requieren un servidor PostgreSQL."""

from datetime import datetime, timezone

from app.db import devices_repository as repo
from app.db import initialize


class CursorFalso:
    def __init__(self, filas):
        self.filas = filas
        self.consultas = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.consultas.append((sql, params))

    def fetchall(self):
        return self.filas

    def fetchone(self):
        return self.filas[0] if self.filas else None


class ConexionFalsa:
    def __init__(self, filas):
        self.cursor_falso = CursorFalso(filas)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self.cursor_falso


def fila():
    return ("led1", "LED", "APAGADO", datetime(2026, 11, 15, tzinfo=timezone.utc))


def test_esquema_crea_tablas_con_suscripciones_push():
    sql = initialize.ESQUEMA_SQL.read_text(encoding="utf-8")
    assert sql.count("CREATE TABLE IF NOT EXISTS") == 4
    for tabla in ("dispositivos", "historial", "notificaciones", "push_suscripciones"):
        assert f"CREATE TABLE IF NOT EXISTS {tabla}" in sql
    assert "estado_compatible_tipo" in sql
    assert "ON CONFLICT (identificador) DO NOTHING" in sql
    for nombre in ("led1", "luz_sala", "ventilador1", "alarma1", "puerta_principal"):
        assert f"'{nombre}'" in sql
    assert "DROP TABLE" not in sql and "TRUNCATE" not in sql


def test_inicializar_ejecuta_esquema(monkeypatch):
    con = ConexionFalsa([])
    monkeypatch.setattr(initialize, "abrir_conexion", lambda: con)
    initialize.inicializar_base_de_datos()
    sql, params = con.cursor_falso.consultas[0]
    assert "CREATE TABLE IF NOT EXISTS dispositivos" in sql
    assert params is None


def test_listar_dispositivos(monkeypatch):
    con = ConexionFalsa([fila()])
    monkeypatch.setattr(repo, "abrir_conexion", lambda: con)
    res = repo.listar_dispositivos()
    assert len(res) == 1 and res[0]["identificador"] == "led1"
    assert res[0]["estado"] == "APAGADO"
    assert "ORDER BY identificador" in con.cursor_falso.consultas[0][0]


def test_obtener_dispositivo_parametrizado(monkeypatch):
    con = ConexionFalsa([fila()])
    monkeypatch.setattr(repo, "abrir_conexion", lambda: con)
    assert repo.obtener_dispositivo("led1")["tipo"] == "LED"
    sql, params = con.cursor_falso.consultas[0]
    assert "WHERE identificador = %s" in sql
    assert params == ("led1",)


def test_dispositivo_inexistente(monkeypatch):
    monkeypatch.setattr(repo, "abrir_conexion", lambda: ConexionFalsa([]))
    assert repo.obtener_dispositivo("inexistente") is None


def test_actualizar_estado_solo_para_uso_interno(monkeypatch):
    con = ConexionFalsa([("led1", "LED", "ENCENDIDO", fila()[3])])
    monkeypatch.setattr(repo, "abrir_conexion", lambda: con)
    res = repo.actualizar_estado("led1", "ENCENDIDO")
    assert res["estado"] == "ENCENDIDO"
    sql, params = con.cursor_falso.consultas[0]
    assert "UPDATE dispositivos" in sql and "RETURNING" in sql
    assert params == ("ENCENDIDO", "led1")


def test_actualizar_inexistente(monkeypatch):
    monkeypatch.setattr(repo, "abrir_conexion", lambda: ConexionFalsa([]))
    assert repo.actualizar_estado("inventado", "ENCENDIDO") is None
