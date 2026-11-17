"""Pruebas de los endpoints para React, sin servicios externos."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.routes import runtime
from app.interpreter.lexer import ErrorLexico
from app.interpreter.semantic import ErrorSemantico
from app.interpreter.executor import ErrorEjecucion
from app.interpreter.intermediate import ProgramaIR
from app.main import app

client = TestClient(app)


def test_ejecutar_compila_y_muestra_estado(monkeypatch):
    args = []
    monkeypatch.setattr(runtime, "compilar_a_ir", lambda codigo, **kwargs: args.append(("compilar", codigo)) or ProgramaIR((), 0))
    monkeypatch.setattr(runtime, "ejecutar_ir", lambda ir, fuente: args.append(("ejecutar", fuente)) or {"correcto": True, "resultados": [], "instrucciones_ir": 0})
    monkeypatch.setattr(runtime, "listar_dispositivos", lambda: [{"identificador": "led1", "tipo": "LED", "estado": "ENCENDIDO", "actualizado_en": datetime.now(timezone.utc)}])
    r = client.post("/api/ejecutar", json={"codigo": "ENCENDER led1"})
    assert r.status_code == 200
    assert r.json()["dispositivos"][0]["estado"] == "ENCENDIDO"
    assert args == [("compilar", "ENCENDER led1"), ("ejecutar", "ENCENDER led1")]


def test_no_ejecuta_codigo_lexicamente_invalido(monkeypatch):
    errores = []
    monkeypatch.setattr(runtime, "registrar_error_ejecucion", lambda codigo, error: errores.append((codigo, error)))
    def falla(_, **kwargs):
        raise ErrorLexico("carácter inválido", 1, 14)
    monkeypatch.setattr(runtime, "compilar_a_ir", falla)
    def prohibido(*_):
        raise AssertionError("No se debe ejecutar")
    monkeypatch.setattr(runtime, "ejecutar_ir", prohibido)
    r = client.post("/api/ejecutar", json={"codigo": "ENCENDER led1@"})
    assert r.status_code == 422
    assert r.json()["error"]["tipo"] == "LEXICO"
    assert errores[0][0] == "ENCENDER led1@"
    assert errores[0][1]["tipo"] == "LEXICO"


def test_error_semantico_se_registra_con_mensaje(monkeypatch):
    errores = []
    monkeypatch.setattr(runtime, "registrar_error_ejecucion", lambda codigo, error: errores.append((codigo, error)))

    def falla(_, **kwargs):
        raise ErrorSemantico(
            "operación ENCENDER incompatible con ALARMA. Las alarmas solo admiten ACTIVAR / DESACTIVAR.",
            1, 1,
        )

    monkeypatch.setattr(runtime, "compilar_a_ir", falla)
    r = client.post("/api/ejecutar", json={"codigo": "ENCENDER alarma1"})
    assert r.status_code == 422
    assert r.json()["error"]["tipo"] == "SEMANTICO"
    assert len(errores) == 1
    assert errores[0][0] == "ENCENDER alarma1"
    assert "ACTIVAR / DESACTIVAR" in errores[0][1]["descripcion"]


def test_error_ejecucion_se_registra_tras_fallar_ir(monkeypatch):
    errores = []
    monkeypatch.setattr(runtime, "registrar_error_ejecucion", lambda codigo, error: errores.append((codigo, error)))
    monkeypatch.setattr(runtime, "compilar_a_ir", lambda _, **kwargs: ProgramaIR((), 0))

    def falla(*_):
        raise ErrorEjecucion("No se pudo ejecutar la operación.", 1, 1)

    monkeypatch.setattr(runtime, "ejecutar_ir", falla)
    r = client.post("/api/ejecutar", json={"codigo": "ENCENDER led1"})
    assert r.status_code == 409
    assert errores[0][1]["tipo"] == "EJECUCION"


def test_error_de_registro_no_oculta_la_validacion(monkeypatch):
    monkeypatch.setattr(runtime, "compilar_a_ir", lambda _, **kwargs: (_ for _ in ()).throw(ErrorSemantico("incompatible", 1, 1)))
    monkeypatch.setattr(runtime, "registrar_error_ejecucion", lambda *_: (_ for _ in ()).throw(OSError("BD falló")))
    r = client.post("/api/ejecutar", json={"codigo": "ENCENDER alarma1"})
    assert r.status_code == 422
    assert r.json()["error"]["tipo"] == "SEMANTICO"


def test_error_de_infraestructura_no_expone_secretos(monkeypatch):
    monkeypatch.setattr(runtime, "compilar_a_ir", lambda _, **kwargs: ProgramaIR((), 0))
    def falla(*_):
        raise ConnectionError("Contraseña secreta")
    monkeypatch.setattr(runtime, "ejecutar_ir", falla)
    r = client.post("/api/ejecutar", json={"codigo": "ENCENDER led1"})
    assert r.status_code == 503
    assert "secreta" not in r.text


def test_largo_maximo_y_body_obligatorio():
    r = client.post("/api/ejecutar", json={"codigo": "x" * 20001})
    assert r.status_code == 413
    assert client.post("/api/ejecutar").status_code == 422


def test_historial_y_notificaciones(monkeypatch):
    monkeypatch.setattr(runtime, "listar_historial", lambda limite: [{"id": 1, "instruccion": "ENCENDER led1", "fecha": datetime.now(timezone.utc)}])
    monkeypatch.setattr(runtime, "listar_notificaciones", lambda limite: [{"id": 1, "mensaje": "Hola", "fecha": datetime.now(timezone.utc)}])
    r = client.get("/api/historial?limite=10")
    assert r.status_code == 200 and r.json()["historial"][0]["id"] == 1
    r = client.get("/api/notificaciones?limite=10")
    assert r.status_code == 200 and r.json()["notificaciones"][0]["mensaje"] == "Hola"
    assert client.get("/api/historial?limite=101").status_code == 422


def test_no_es_posible_modificar_dispositivo_por_endpoint_directo():
    assert client.post("/api/dispositivos/led1", json={"estado": "ENCENDIDO"}).status_code == 405
