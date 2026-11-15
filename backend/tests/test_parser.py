"""Pruebas del Parser + AST, SmartHome Script 1.0."""

import json
import pytest

from app.interpreter.ast_nodes import (
    Programa, Control, Consulta, Listado, Notificacion, Correo, Condicional,
)
from app.interpreter.lexer import ErrorLexico, analizar_lexico
from app.interpreter.parser import ErrorSintactico, Parser, analizar_sintactico


@pytest.mark.parametrize(("codigo", "clase"), [
    ("ENCENDER led1", Control),
    ("APAGAR luz_sala", Control),
    ("ACTIVAR alarma1", Control),
    ("DESACTIVAR alarma1", Control),
    ("ABRIR puerta_principal", Control),
    ("CERRAR puerta_principal", Control),
    ("CONSULTAR led1", Consulta),
    ("LISTAR DISPOSITIVOS", Listado),
    ('NOTIFICAR "Prueba"', Notificacion),
    ('ENVIAR CORREO A "a@b.com" MENSAJE "Hola"', Correo),
])
def test_comandos_simples(codigo, clase):
    programa = analizar_sintactico(codigo)
    assert isinstance(programa, Programa)
    assert len(programa.instrucciones) == 1
    nodo = programa.instrucciones[0]
    assert isinstance(nodo, clase)
    assert (nodo.linea, nodo.columna) == (1, 1)


@pytest.mark.parametrize("estado", [
    "ENCENDIDO", "APAGADO", "ACTIVADA",
    "DESACTIVADA", "ABIERTA", "CERRADA",
])
def test_condicion_acepta_estados_del_lenguaje(estado):
    nodo = analizar_sintactico(
        f"SI led1 == {estado} ENTONCES APAGAR led1"
    ).instrucciones[0]
    assert isinstance(nodo, Condicional)
    assert nodo.condicion.estado == estado
    assert isinstance(nodo.accion, Control)


@pytest.mark.parametrize("accion,clase", [
    ("ENCENDER led1", Control),
    ("CONSULTAR led1", Consulta),
    ("LISTAR DISPOSITIVOS", Listado),
    ('NOTIFICAR "Hola"', Notificacion),
    ('ENVIAR CORREO A "a@b.com" MENSAJE "Hola"', Correo),
])
def test_condicion_con_accion_simple(accion, clase):
    nodo = analizar_sintactico(
        f"SI alarma1 == ACTIVADA ENTONCES {accion}"
    ).instrucciones[0]
    assert isinstance(nodo, Condicional)
    assert isinstance(nodo.accion, clase)


def test_programa_de_la_especificacion():
    programa = analizar_sintactico(
        'ENCENDER led1\n'
        'ENCENDER luz_sala\n'
        'CONSULTAR luz_sala\n'
        'ACTIVAR alarma1\n'
        'SI alarma1 == ACTIVADA ENTONCES NOTIFICAR "Alarma activa"\n'
        'LISTAR DISPOSITIVOS\n'
        'ENVIAR CORREO A "prueba@ejemplo.com" MENSAJE "Sistema listo"'
    )
    assert len(programa.instrucciones) == 7
    assert [n.linea for n in programa.instrucciones] == list(range(1, 8))
    assert isinstance(programa.instrucciones[4], Condicional)
    assert isinstance(programa.instrucciones[-1], Correo)
    assert json.loads(json.dumps(programa.a_diccionario()))["tipo"] == "PROGRAMA"


@pytest.mark.parametrize("codigo", ["", "\n", "\n\n", " \t", "\r\n\r\n"])
def test_archivo_vacio_y_lineas_vacias(codigo):
    assert analizar_sintactico(codigo).instrucciones == ()


def test_lineas_crlf_y_columnas():
    programa = analizar_sintactico("\r\n  ENCENDER led1\r\n\r\n\tLISTAR DISPOSITIVOS\r\n")
    assert len(programa.instrucciones) == 2
    assert (programa.instrucciones[0].linea, programa.instrucciones[0].columna) == (2, 3)
    assert (programa.instrucciones[1].linea, programa.instrucciones[1].columna) == (4, 2)


def test_valores_escapados_y_cadenas_vacias():
    programa = analizar_sintactico(r'NOTIFICAR "Dijo \"hola\" en C:\\casa"' + '\nNOTIFICAR ""')
    assert [n.mensaje for n in programa.instrucciones] == ['Dijo "hola" en C:\\casa', ""]


@pytest.mark.parametrize("codigo,fragmento", [
    ("ENCENDER", "IDENTIFICADOR"),
    ("ENCENDER\n", "IDENTIFICADOR"),
    ("APAGAR ENCENDER", "IDENTIFICADOR"),
    ("CONSULTAR", "IDENTIFICADOR"),
    ("LISTAR", "DISPOSITIVOS"),
    ("LISTAR led1", "DISPOSITIVOS"),
    ("NOTIFICAR", "CADENA"),
    ("NOTIFICAR led1", "CADENA"),
    ("ENVIAR", "CORREO"),
    ("ENVIAR CORREO", "A"),
    ("ENVIAR CORREO A", "destinatario"),
    ('ENVIAR CORREO A "a@b.com"', "MENSAJE"),
    ('ENVIAR CORREO A "a@b.com" MENSAJE', "mensaje"),
    ("SI", "IDENTIFICADOR"),
    ("SI led1", "=="),
    ("SI led1 ==", "ESTADO"),
    ("SI led1 == ENCENDIDO", "ENTONCES"),
    ("SI led1 == ENCENDIDO ENTONCES", "instrucción"),
    ("SI led1 == ENCENDIDO ENTONCES SI led1 == APAGADO ENTONCES ENCENDER led1", "simple"),
    ("ENCENDER led1 APAGAR led1", "SALTO_LINEA"),
    ("ENCENDER led1 led2", "SALTO_LINEA"),
    ("encender led1", "instrucción"),
    ("DISPOSITIVOS", "no inicia"),
    ("LISTAR DISPOSITIVOS CORREO", "SALTO_LINEA"),
])
def test_error_sintactico(codigo, fragmento):
    with pytest.raises(ErrorSintactico) as captura:
        analizar_sintactico(codigo)
    error = captura.value
    assert error.tipo == "SINTACTICO"
    assert fragmento.lower() in error.descripcion.lower()
    assert error.linea >= 1 and error.columna >= 1
    assert set(error.a_diccionario()) == {"tipo", "linea", "columna", "descripcion"}


def test_error_ubicado_en_segunda_linea():
    with pytest.raises(ErrorSintactico) as captura:
        analizar_sintactico("ENCENDER led1\nLISTAR led1")
    assert (captura.value.linea, captura.value.columna) == (2, 8)


def test_error_lexico_se_conserva():
    with pytest.raises(ErrorLexico) as captura:
        analizar_sintactico("ENCENDER led1@")
    assert (captura.value.linea, captura.value.columna) == (1, 14)


def test_interfaz_con_tokens_directos():
    programa = Parser(analizar_lexico("APAGAR led1")).analizar()
    assert isinstance(programa.instrucciones[0], Control)


def test_exige_fin_archivo():
    with pytest.raises(ValueError, match="FIN_ARCHIVO"):
        Parser([])
    with pytest.raises(ValueError, match="FIN_ARCHIVO"):
        Parser(analizar_lexico("ENCENDER led1")[:-1])


def test_sintaxis_no_es_semantica():
    assert analizar_sintactico("ENCENDER dispositivo99").instrucciones[0].dispositivo == "dispositivo99"
    assert analizar_sintactico("ENCENDER alarma1").instrucciones[0].dispositivo == "alarma1"
