"""Pruebas de la representación intermedia SmartHome (sin PostgreSQL)."""

import json

import pytest

from app.interpreter.ast_nodes import Programa
from app.interpreter.intermediate import (
    ESTADOS_DE_OPERACION,
    GeneradorIR,
    OperacionIR,
    compilar_a_ir,
    generar_codigo_intermedio,
)
from app.interpreter.lexer import ErrorLexico
from app.interpreter.parser import ErrorSintactico
from app.interpreter.semantic import ErrorSemantico
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


@pytest.mark.parametrize("codigo,estado", [
    ("ENCENDER led1", "ENCENDIDO"),
    ("APAGAR led1", "APAGADO"),
    ("ENCENDER luz_sala", "ENCENDIDO"),
    ("APAGAR ventilador1", "APAGADO"),
    ("ACTIVAR alarma1", "ACTIVADA"),
    ("DESACTIVAR alarma1", "DESACTIVADA"),
    ("ABRIR puerta_principal", "ABIERTA"),
    ("CERRAR puerta_principal", "CERRADA"),
])
def test_control_se_convierte_en_estado_canonico(tabla, codigo, estado):
    ir = compilar_a_ir(codigo, tabla)
    assert len(ir.instrucciones) == 1
    instruccion = ir.instrucciones[0]
    assert instruccion.operacion is OperacionIR.ASIGNAR_ESTADO
    assert instruccion.argumentos == (codigo.split()[1], estado)
    assert (instruccion.linea, instruccion.columna) == (1, 1)
    assert ir.temporales == 0


@pytest.mark.parametrize("codigo,operacion,args", [
    ("CONSULTAR led1", OperacionIR.CONSULTAR_ESTADO, ("led1",)),
    ("LISTAR DISPOSITIVOS", OperacionIR.LISTAR_DISPOSITIVOS, ()),
    ('NOTIFICAR "Hola"', OperacionIR.REGISTRAR_NOTIFICACION, ("Hola",)),
    ('ENVIAR CORREO A "prueba@ejemplo.com" MENSAJE "Hola"',
     OperacionIR.ENVIAR_CORREO, ("prueba@ejemplo.com", "Hola")),
])
def test_otros_comandos(tabla, codigo, operacion, args):
    ir = compilar_a_ir(codigo, tabla)
    assert [(i.operacion, i.argumentos) for i in ir.instrucciones] == [(operacion, args)]


def test_condicional_produce_lectura_comparacion_y_salto(tabla):
    ir = compilar_a_ir("SI alarma1 == ACTIVADA ENTONCES DESACTIVAR alarma1", tabla)
    assert len(ir.instrucciones) == 4
    assert ir.temporales == 2
    assert [i.operacion for i in ir.instrucciones] == [
        OperacionIR.LEER_ESTADO,
        OperacionIR.COMPARAR_IGUAL,
        OperacionIR.SALTAR_SI_FALSO,
        OperacionIR.ASIGNAR_ESTADO,
    ]
    assert ir.instrucciones[0].argumentos == ("alarma1", "t0")
    assert ir.instrucciones[1].argumentos == ("t0", "ACTIVADA", "t1")
    assert ir.instrucciones[2].argumentos == ("t1", 4)
    assert ir.instrucciones[3].argumentos == ("alarma1", "DESACTIVADA")
    assert ir.instrucciones[0].columna == 4
    assert ir.instrucciones[2].columna == 1
    assert ir.instrucciones[3].columna == 33


def test_salto_a_despues_de_condicion_pero_antes_de_siguiente_linea(tabla):
    ir = compilar_a_ir(
        'SI led1 == ENCENDIDO ENTONCES NOTIFICAR "Hola"\nCONSULTAR led1', tabla
    )
    assert [i.operacion for i in ir.instrucciones] == [
        OperacionIR.LEER_ESTADO, OperacionIR.COMPARAR_IGUAL,
        OperacionIR.SALTAR_SI_FALSO, OperacionIR.REGISTRAR_NOTIFICACION,
        OperacionIR.CONSULTAR_ESTADO,
    ]
    assert ir.instrucciones[2].argumentos == ("t1", 4)
    assert ir.instrucciones[4].linea == 2


def test_temporales_y_saltos_no_colisionan_en_dos_condiciones(tabla):
    ir = compilar_a_ir(
        'SI led1 == APAGADO ENTONCES ENCENDER led1\n'
        'SI led1 == ENCENDIDO ENTONCES APAGAR led1\n'
        'LISTAR DISPOSITIVOS', tabla
    )
    assert ir.temporales == 4
    assert len(ir.instrucciones) == 9
    assert ir.instrucciones[2].argumentos == ("t1", 4)
    assert ir.instrucciones[6].argumentos == ("t3", 8)
    assert ir.instrucciones[8].operacion is OperacionIR.LISTAR_DISPOSITIVOS


def test_no_evalua_condicional_ni_congela_estado_durante_compilacion(tabla):
    # El LED está apagado en la tabla, pero se conserva el condicional.
    ir = compilar_a_ir("SI led1 == ENCENDIDO ENTONCES APAGAR led1", tabla)
    assert len(ir.instrucciones) == 4
    assert ir.instrucciones[0].operacion is OperacionIR.LEER_ESTADO


def test_programa_original_del_documento(tabla):
    programa = '\n'.join([
        'ENCENDER led1',
        'ENCENDER luz_sala',
        'CONSULTAR luz_sala',
        'ACTIVAR alarma1',
        'SI alarma1 == ACTIVADA ENTONCES NOTIFICAR "Alarma activa"',
        'LISTAR DISPOSITIVOS',
        'ENVIAR CORREO A "prueba@ejemplo.com" MENSAJE "Sistema listo"',
    ])
    ir = compilar_a_ir(programa, tabla)
    assert len(ir.instrucciones) == 10
    assert ir.temporales == 2
    assert ir.instrucciones[4].argumentos == ("alarma1", "t0")
    assert ir.instrucciones[6].argumentos == ("t1", 8)
    assert ir.instrucciones[7].operacion is OperacionIR.REGISTRAR_NOTIFICACION
    assert ir.instrucciones[8].operacion is OperacionIR.LISTAR_DISPOSITIVOS
    assert ir.instrucciones[9].operacion is OperacionIR.ENVIAR_CORREO
    assert [i.linea for i in ir.instrucciones] == [1, 2, 3, 4, 5, 5, 5, 5, 6, 7]


def test_lineas_vacias_y_archivo_vacio(tabla):
    vacio = compilar_a_ir("\n\r\n", tabla)
    assert vacio.instrucciones == () and vacio.temporales == 0
    ir = compilar_a_ir("\nENCENDER led1\n\nCONSULTAR led1\n", tabla)
    assert [i.linea for i in ir.instrucciones] == [2, 4]


def test_json_serializable_y_direccion_en_base_cero(tabla):
    ir = compilar_a_ir('SI led1 == APAGADO ENTONCES ENCENDER led1', tabla)
    data = json.loads(json.dumps(ir.a_diccionario()))
    assert data["tipo"] == "PROGRAMA_IR"
    assert [i["indice"] for i in data["instrucciones"]] == list(range(4))
    assert data["instrucciones"][2]["argumentos"] == ["t1", 4]
    assert data["instrucciones"][0]["operacion"] == "LEER_ESTADO"


@pytest.mark.parametrize("codigo,error", [
    ("ENCENDER led1@", ErrorLexico),
    ("ENCENDER", ErrorSintactico),
    ("ENCENDER alarma1", ErrorSemantico),
    ("ENCENDER inexistente", ErrorSemantico),
    ('NOTIFICAR ""', ErrorSemantico),
    ('ENVIAR CORREO A "invalido" MENSAJE "Hola"', ErrorSemantico),
    ('SI alarma1 == ENCENDIDO ENTONCES DESACTIVAR alarma1', ErrorSemantico),
])
def test_no_compila_codigo_invalido(tabla, codigo, error):
    with pytest.raises(error):
        compilar_a_ir(codigo, tabla)


def test_una_linea_invalida_impide_todo_el_programa(tabla):
    with pytest.raises(ErrorSemantico):
        compilar_a_ir("ENCENDER led1\nENCENDER alarma1\nNOTIFICAR \"Hola\"", tabla)


def test_ir_no_modifica_ningun_estado(tabla):
    antes = [(s.identificador, s.estado) for s in tabla.listar()]
    compilar_a_ir("ENCENDER led1\nACTIVAR alarma1", tabla)
    despues = [(s.identificador, s.estado) for s in tabla.listar()]
    assert antes == despues


def test_generador_exige_ast_y_solo_se_utiliza_una_vez():
    with pytest.raises(TypeError, match="Programa"):
        generar_codigo_intermedio("ENCENDER led1")
    gen = GeneradorIR()
    assert gen.generar(Programa(())).instrucciones == ()
    with pytest.raises(RuntimeError, match="nuevo"):
        gen.generar(Programa(()))


def test_recompilar_reinicia_temporales(tabla):
    programa = "SI led1 == ENCENDIDO ENTONCES APAGAR led1"
    p = compilar_a_ir(programa, tabla)
    q = compilar_a_ir(programa, tabla)
    assert p.a_diccionario() == q.a_diccionario()
    assert p.instrucciones[0].argumentos[1] == "t0"


def test_diccionario_completo_contiene_estados_de_lenguaje():
    assert set(ESTADOS_DE_OPERACION) == {
        "ENCENDER", "APAGAR", "ACTIVAR", "DESACTIVAR", "ABRIR", "CERRAR"
    }
