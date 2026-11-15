"""Pruebas de /api/analizar usando TablaSimbolos en memoria."""

from fastapi.testclient import TestClient
from app.main import app
from app.interpreter import semantic
from app.interpreter.symbols import TablaSimbolos

client = TestClient(app)


def preparar(monkeypatch):
    tabla = TablaSimbolos([
        {'identificador':'led1','tipo':'LED','estado':'APAGADO'},
        {'identificador':'alarma1','tipo':'ALARMA','estado':'DESACTIVADA'},
    ])
    monkeypatch.setattr(semantic, 'cargar_tabla_simbolos', lambda: tabla)


def test_validacion_correcta(monkeypatch):
    preparar(monkeypatch)
    response = client.post('/api/analizar', json={'codigo':'ENCENDER led1\nCONSULTAR led1'})
    assert response.status_code == 200
    result = response.json()
    assert result['correcto'] is True
    assert result['instrucciones_validadas'] == 2
    assert result['ast']['tipo'] == 'PROGRAMA'


def test_error_semantico(monkeypatch):
    preparar(monkeypatch)
    r = client.post('/api/analizar', json={'codigo':'ENCENDER alarma1'})
    assert r.status_code == 422
    assert r.json()['error']['tipo'] == 'SEMANTICO'


def test_error_lexico(monkeypatch):
    preparar(monkeypatch)
    r = client.post('/api/analizar', json={'codigo':'ENCENDER led1@'})
    assert r.status_code == 422
    assert r.json()['error']['tipo'] == 'LEXICO'


def test_error_sintactico(monkeypatch):
    preparar(monkeypatch)
    r = client.post('/api/analizar', json={'codigo':'ENCENDER'})
    assert r.status_code == 422
    assert r.json()['error']['tipo'] == 'SINTACTICO'


def test_tabla_no_disponible(monkeypatch):
    def falla():
        raise ConnectionError('Contraseña secreta de prueba')
    monkeypatch.setattr(semantic, 'cargar_tabla_simbolos', falla)
    r = client.post('/api/analizar', json={'codigo':'ENCENDER led1'})
    assert r.status_code == 503
    assert r.json()['error']['tipo'] == 'INFRAESTRUCTURA'
    assert 'secreta' not in r.text


def test_parametros_api_invalidos(monkeypatch):
    preparar(monkeypatch)
    assert client.post('/api/analizar',json={'codigo':123}).status_code == 422
    assert client.post('/api/analizar',json={'texto':'ENCENDER led1'}).status_code == 422


def test_no_ejecuta_actualizacion(monkeypatch):
    preparar(monkeypatch)
    from app.db import devices_repository
    def prohibido(*args,**kwargs):
        raise AssertionError('no puede actualizar estados en esta etapa')
    monkeypatch.setattr(devices_repository,'actualizar_estado',prohibido)
    r=client.post('/api/analizar',json={'codigo':'ENCENDER led1'})
    assert r.status_code == 200
