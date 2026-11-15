"""Pruebas de las rutas de lectura usando datos simulados."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import devices as routes

client = TestClient(app)


def datos():
    return [
        {"identificador": "led1", "tipo": "LED", "estado": "APAGADO",
         "actualizado_en": datetime(2026, 11, 15, tzinfo=timezone.utc)},
        {"identificador": "alarma1", "tipo": "ALARMA", "estado": "DESACTIVADA",
         "actualizado_en": datetime(2026, 11, 15, tzinfo=timezone.utc)},
    ]


def test_listado(monkeypatch):
    monkeypatch.setattr(routes, "listar_dispositivos", datos)
    r = client.get("/api/dispositivos")
    assert r.status_code == 200
    assert len(r.json()["dispositivos"]) == 2


def test_detalle(monkeypatch):
    monkeypatch.setattr(routes, "obtener_dispositivo", lambda ident: datos()[0] if ident == "led1" else None)
    r = client.get("/api/dispositivos/led1")
    assert r.status_code == 200 and r.json()["identificador"] == "led1"
    assert client.get("/api/dispositivos/inexistente").status_code == 404


def test_simbolos(monkeypatch):
    monkeypatch.setattr(routes, "listar_dispositivos", datos)
    r = client.get("/api/tabla-simbolos")
    assert r.status_code == 200
    assert r.json()["simbolos"][0]["operaciones_permitidas"] == ["ENCENDER", "APAGAR", "CONSULTAR"]


def test_base_desconectada(monkeypatch):
    def falla():
        raise ConnectionError("No se pudo conectar")
    monkeypatch.setattr(routes, "listar_dispositivos", falla)
    r = client.get("/api/dispositivos")
    assert r.status_code == 503
    assert "No se pudo conectar" not in r.text
    assert client.get("/api/tabla-simbolos").status_code == 503


def test_no_existe_endpoint_control_directo():
    assert client.post("/api/dispositivos/led1", json={"estado": "ENCENDIDO"}).status_code == 405
