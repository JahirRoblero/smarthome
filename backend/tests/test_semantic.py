"""Pruebas semánticas de SmartHome: no utilizan PostgreSQL real."""

import pytest

from app.interpreter.ast_nodes import Control, Condicion, Condicional, Notificacion, Programa
from app.interpreter.lexer import ErrorLexico
from app.interpreter.parser import ErrorSintactico, analizar_sintactico
from app.interpreter.semantic import (
    AnalizadorSemantico, ErrorSemantico, analizar_semantico,
)
from app.interpreter.symbols import TablaSimbolos


@pytest.fixture
def tabla():
    return TablaSimbolos([
        {"identificador": "led1", "tipo": "LED", "estado": "APAGADO"},
        {"identificador": "luz_sala", "tipo": "LUZ", "estado": "APAGADO"},
        {"identificador": "ventilador1", "tipo": "VENTILADOR", "estado": "APAGADO"},
        {"identificador": "alarma1", "tipo": "ALARMA", "estado": "DESACTIVADA"},
        {"identificador": "puerta_principal", "tipo": "PUERTA", "estado": "CERRADA"},
    ])


@pytest.mark.parametrize("codigo", [
    "ENCENDER led1", "APAGAR led1", "ENCENDER luz_sala", "APAGAR ventilador1",
    "ACTIVAR alarma1", "DESACTIVAR alarma1", "ABRIR puerta_principal",
    "CERRAR puerta_principal", "CONSULTAR led1", "LISTAR DISPOSITIVOS",
    'NOTIFICAR "Hola"', 'ENVIAR CORREO A "prueba@ejemplo.com" MENSAJE "Listo"',
    "SI led1 == APAGADO ENTONCES ENCENDER led1",
    "SI alarma1 == ACTIVADA ENTONCES DESACTIVAR alarma1",
    "SI puerta_principal == CERRADA ENTONCES ABRIR puerta_principal",
    'SI alarma1 == ACTIVADA ENTONCES NOTIFICAR "Alerta"',
    'SI led1 == ENCENDIDO ENTONCES ENVIAR CORREO A "prueba@ejemplo.com" MENSAJE "Sí"',
])
def test_codigo_valido(tabla, codigo):
    ast = analizar_semantico(codigo, tabla)
    assert isinstance(ast, Programa)
    assert len(ast.instrucciones) == 1


@pytest.mark.parametrize("codigo,fragmento", [
    ("ENCENDER desconocido", "dispositivo inexistente"),
    ("CONSULTAR desconocido", "dispositivo inexistente"),
    ("SI desconocido == ENCENDIDO ENTONCES APAGAR led1", "dispositivo inexistente"),
    ("SI led1 == ENCENDIDO ENTONCES APAGAR desconocido", "dispositivo inexistente"),
    ("ENCENDER alarma1", "incompatible"),
    ("APAGAR puerta_principal", "incompatible"),
    ("ACTIVAR luz_sala", "incompatible"),
    ("CERRAR ventilador1", "incompatible"),
    ("SI alarma1 == ENCENDIDO ENTONCES DESACTIVAR alarma1", "no es válido"),
    ("SI led1 == ACTIVADA ENTONCES APAGAR led1", "no es válido"),
    ("SI puerta_principal == APAGADO ENTONCES CERRAR puerta_principal", "no es válido"),
    ('NOTIFICAR ""', "vacío"),
    ('NOTIFICAR "   "', "vacío"),
    ('ENVIAR CORREO A "" MENSAJE "Hola"', "inválida"),
    ('ENVIAR CORREO A "usuario" MENSAJE "Hola"', "inválida"),
    ('ENVIAR CORREO A "usuario@dominio" MENSAJE "Hola"', "inválida"),
    ('ENVIAR CORREO A "usuario@@ejemplo.com" MENSAJE "Hola"', "inválida"),
    ('ENVIAR CORREO A "usuario @ejemplo.com" MENSAJE "Hola"', "inválida"),
    ('ENVIAR CORREO A "usuario@ejemplo.com" MENSAJE ""', "vacío"),
    ('ENVIAR CORREO A "usuario@ejemplo.com" MENSAJE "  "', "vacío"),
    ("SI led1 == APAGADO ENTONCES ENCENDER alarma1", "incompatible"),
])
def test_error_semantico(tabla, codigo, fragmento):
    with pytest.raises(ErrorSemantico) as captura:
        analizar_semantico(codigo, tabla)
    error = captura.value
    assert error.tipo == "SEMANTICO"
    assert fragmento in error.descripcion
    assert error.linea >= 1 and error.columna >= 1
    assert set(error.a_diccionario()) == {"tipo", "linea", "columna", "descripcion"}


def test_rechaza_programa_completo_sin_efectos(tabla):
    original = [(s.identificador, s.estado) for s in tabla.listar()]
    with pytest.raises(ErrorSemantico) as captura:
        analizar_semantico('ENCENDER led1\nNOTIFICAR "Hola"\nENCENDER alarma1', tabla)
    assert captura.value.linea == 3
    assert [(s.identificador, s.estado) for s in tabla.listar()] == original


def test_no_evalua_el_valor_de_la_condicion(tabla):
    # Este SI es falso con el estado actual; la validación igual debe aceptarlo.
    ast = analizar_semantico('SI led1 == ENCENDIDO ENTONCES APAGAR led1', tabla)
    assert len(ast.instrucciones) == 1


def test_no_omite_validacion_de_accion_si_condicion_falsa(tabla):
    with pytest.raises(ErrorSemantico, match="incompatible"):
        analizar_semantico('SI led1 == ENCENDIDO ENTONCES ENCENDER alarma1', tabla)


def test_linea_y_columna_segundo_comando(tabla):
    with pytest.raises(ErrorSemantico) as captura:
        analizar_semantico('ENCENDER led1\n  ACTIVAR led1', tabla)
    assert (captura.value.linea, captura.value.columna) == (2, 3)


def test_programa_completo_validado(tabla):
    origen = '\n'.join([
        'ENCENDER led1', 'ENCENDER luz_sala', 'CONSULTAR luz_sala',
        'ACTIVAR alarma1', 'SI alarma1 == ACTIVADA ENTONCES NOTIFICAR "Alarma activa"',
        'LISTAR DISPOSITIVOS', 'ENVIAR CORREO A "prueba@ejemplo.com" MENSAJE "Sistema listo"',
    ])
    ast = analizar_semantico(origen, tabla)
    assert len(ast.instrucciones) == 7
    assert [n.linea for n in ast.instrucciones] == list(range(1, 8))
    assert ast.a_diccionario() == analizar_sintactico(origen).a_diccionario()


def test_texto_vacio(tabla):
    assert analizar_semantico('\n\n', tabla).instrucciones == ()


def test_error_lexico_antes_de_semantico(tabla):
    with pytest.raises(ErrorLexico):
        analizar_semantico('ENCENDER led1@', tabla)


def test_error_sintactico_antes_de_semantico(tabla):
    with pytest.raises(ErrorSintactico):
        analizar_semantico('ENCENDER', tabla)


def test_analisis_requiere_programa(tabla):
    with pytest.raises(TypeError, match='Programa'):
        AnalizadorSemantico(tabla).analizar('ENCENDER led1')


def test_carga_tabla_solo_despues_de_parser(monkeypatch):
    from app.interpreter import semantic
    solicitudes = []
    monkeypatch.setattr(semantic, 'cargar_tabla_simbolos', lambda: solicitudes.append(1) or TablaSimbolos([]))
    with pytest.raises(ErrorSintactico):
        semantic.analizar_semantico('ENCENDER')
    assert not solicitudes
    with pytest.raises(ErrorSemantico):
        semantic.analizar_semantico('ENCENDER led1')
    assert len(solicitudes) == 1


def test_parametros_ast_incorrectos(tabla):
    casos = [
        (Control('ENCENDER', 42, 1, 1), 'identificador'),
        (Control(123, 'led1', 1, 1), 'operación'),
        (Notificacion(123, 1, 1), 'texto'),
        (Condicional(Condicion('led1', '>', 'ENCENDIDO', 1, 4), Control('ENCENDER','led1',1,1),1,1), '=='),
        (Condicional(Condicion('led1','==',42,1,4), Control('ENCENDER','led1',1,1),1,1), 'texto'),
    ]
    for nodo, esperado in casos:
        with pytest.raises(ErrorSemantico, match=esperado):
            AnalizadorSemantico(tabla).analizar(Programa((nodo,)))


def test_anidamiento_ast_manual_invalido(tabla):
    condicion = Condicion('led1','==','ENCENDIDO',1,4)
    sub = Condicional(condicion,Control('ENCENDER','led1',1,1),1,1)
    with pytest.raises(ErrorSemantico, match='sin anidamientos'):
        AnalizadorSemantico(tabla).analizar(Programa((Condicional(condicion,sub,1,1),)))
