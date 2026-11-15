"""Tabla de símbolos en memoria, sin PostgreSQL."""

import pytest
from app.interpreter.symbols import TablaSimbolos, REGLAS_POR_TIPO


@pytest.fixture
def dispositivos():
    return [
        {"identificador": "led1", "tipo": "LED", "estado": "APAGADO"},
        {"identificador": "luz_sala", "tipo": "LUZ", "estado": "APAGADO"},
        {"identificador": "ventilador1", "tipo": "VENTILADOR", "estado": "APAGADO"},
        {"identificador": "alarma1", "tipo": "ALARMA", "estado": "DESACTIVADA"},
        {"identificador": "puerta_principal", "tipo": "PUERTA", "estado": "CERRADA"},
    ]


def test_todos_los_tipos_y_permisos(dispositivos):
    tabla = TablaSimbolos(dispositivos)
    assert len(tabla) == 5
    assert tabla.buscar("led1").operaciones_permitidas == ("ENCENDER", "APAGAR", "CONSULTAR")
    assert tabla.buscar("alarma1").operaciones_permitidas == ("ACTIVAR", "DESACTIVAR", "CONSULTAR")
    assert tabla.buscar("puerta_principal").estados_permitidos == ("ABIERTA", "CERRADA")
    assert tabla.existe("ventilador1")
    assert not tabla.existe("inexistente")
    assert tabla.buscar("inexistente") is None


def test_serializacion_de_simbolos(dispositivos):
    simbolo = TablaSimbolos(dispositivos).buscar("alarma1").a_diccionario()
    assert simbolo == {
        "identificador": "alarma1", "tipo": "ALARMA", "estado": "DESACTIVADA",
        "estados_permitidos": ["ACTIVADA", "DESACTIVADA"],
        "operaciones_permitidas": ["ACTIVAR", "DESACTIVAR", "CONSULTAR"],
    }


def test_no_inventa_dispositivos():
    tabla = TablaSimbolos([])
    assert len(tabla) == 0 and tabla.listar() == []


def test_tipo_inexistente():
    with pytest.raises(ValueError, match="Tipo de dispositivo desconocido"):
        TablaSimbolos([{"identificador": "x", "tipo": "TELEVISOR", "estado": "APAGADO"}])


def test_estado_incompatible():
    with pytest.raises(ValueError, match="incompatible"):
        TablaSimbolos([{"identificador": "alarma1", "tipo": "ALARMA", "estado": "ENCENDIDO"}])


def test_identificador_duplicado():
    with pytest.raises(ValueError, match="duplicado"):
        TablaSimbolos([{"identificador": "led1", "tipo": "LED", "estado": "APAGADO"}] * 2)


def test_carga_desde_repositorio(monkeypatch, dispositivos):
    from app.db import devices_repository
    from app.interpreter.symbols import cargar_tabla_simbolos
    monkeypatch.setattr(devices_repository, "listar_dispositivos", lambda: dispositivos)
    assert cargar_tabla_simbolos().buscar("led1").tipo == "LED"


@pytest.mark.parametrize("tipo", ["LED", "LUZ", "VENTILADOR", "ALARMA", "PUERTA"])
def test_reglas_completas(tipo):
    estados, operaciones = REGLAS_POR_TIPO[tipo]
    assert len(estados) == 2
    assert "CONSULTAR" in operaciones
