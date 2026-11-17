"""Pruebas de /api/compilar, sin servidores de base de datos."""

from fastapi.testclient import TestClient

from app.main import app
from app.interpreter import semantic
from app.interpreter.symbols import TablaSimbolos

client = TestClient(app)


def preparar(monkeypatch):
    tabla = TablaSimbolos([
        {"identificador": "led1", "tipo": "LED", "estado": "APAGADO"},
        {"identificador": "alarma1", "tipo": "ALARMA", "estado": "DESACTIVADA"},
    ])
    monkeypatch.setattr(semantic, "cargar_tabla_simbolos", lambda: tabla)


def test_compilacion_correcta(monkeypatch):
    preparar(monkeypatch)
    r = client.post("/api/compilar", json={"codigo": "ENCENDER led1"})
    assert r.status_code == 200
    assert r.json()["correcto"] is True
    assert r.json()["ir"]["instrucciones"][0]["argumentos"] == ["led1", "ENCENDIDO"]


def test_optimizar_opcional_en_api(monkeypatch):
    preparar(monkeypatch)
    codigo = "ENCENDER led1\nENCENDER led1\nAPAGAR led1"
    con = client.post("/api/compilar", json={"codigo": codigo, "optimizar": True})
    sin = client.post("/api/compilar", json={"codigo": codigo, "optimizar": False})
    assert con.status_code == sin.status_code == 200
    ir_con = con.json()["ir"]
    ir_sin = sin.json()["ir"]
    assert ir_con["optimizacion"]["escrituras_evitadas"] == 2
    assert ir_sin["optimizacion"]["escrituras_evitadas"] == 0
    assert len(ir_con["instrucciones"]) == len(ir_sin["instrucciones"]) == 3
    assert client.post("/api/compilar", json={
        "codigo": codigo, "optimizar": "si"
    }).status_code == 422


def test_condicional_y_saltos(monkeypatch):
    preparar(monkeypatch)
    r = client.post("/api/compilar", json={"codigo": "SI led1 == APAGADO ENTONCES ENCENDER led1"})
    assert r.status_code == 200
    assert r.json()["ir"]["instrucciones"][2]["argumentos"] == ["t1", 4]


def test_errores_lexico_sintactico_semantico(monkeypatch):
    preparar(monkeypatch)
    for codigo, tipo in [
        ("ENCENDER led1@", "LEXICO"),
        ("ENCENDER", "SINTACTICO"),
        ("ENCENDER alarma1", "SEMANTICO"),
    ]:
        r = client.post("/api/compilar", json={"codigo": codigo})
        assert r.status_code == 422
        assert r.json()["correcto"] is False
        assert r.json()["error"]["tipo"] == tipo


def test_pydantic_rechaza_body_incompleto(monkeypatch):
    preparar(monkeypatch)
    assert client.post("/api/compilar").status_code == 422
    assert client.post("/api/compilar", json={"codigo": 123}).status_code == 422


def test_base_desconectada_responde_503(monkeypatch):
    def falla():
        raise ConnectionError("Contraseña de PostgreSQL nunca mostrar")
    monkeypatch.setattr(semantic, "cargar_tabla_simbolos", falla)
    r = client.post("/api/compilar", json={"codigo": "ENCENDER led1"})
    assert r.status_code == 503
    assert r.json()["error"]["tipo"] == "INFRAESTRUCTURA"
    assert "Contraseña" not in r.text


def test_ir_no_ejecuta_dispositivos(monkeypatch):
    preparar(monkeypatch)
    from app.db import devices_repository

    def prohibido(*args, **kwargs):
        raise AssertionError("¡No se deben actualizar estados al generar el IR!")
    monkeypatch.setattr(devices_repository, "actualizar_estado", prohibido)
    r = client.post("/api/compilar", json={"codigo": "ENCENDER led1"})
    assert r.status_code == 200


def test_analizar_original_sigue_funcionando(monkeypatch):
    preparar(monkeypatch)
    r = client.post("/api/analizar", json={"codigo": "CONSULTAR led1"})
    assert r.status_code == 200
    assert r.json()["ast"]["tipo"] == "PROGRAMA"
