"""Pruebas de aceptación de la especificación del lenguaje SmartHome v1.0."""

import pytest

from app.interpreter.lexer import (
    ESTADOS,
    PALABRAS_RESERVADAS,
    ErrorLexico,
    Lexer,
    TipoToken,
    analizar_lexico,
)


def test_todos_los_comandos_y_conectores_son_palabras_reservadas():
    # Lexemas independientes, aunque una línea no forme una oración sintáctica.
    tokens = analizar_lexico(" ".join(sorted(PALABRAS_RESERVADAS)))
    assert [token.valor for token in tokens[:-1]] == sorted(PALABRAS_RESERVADAS)
    assert all(token.tipo is TipoToken.PALABRA_RESERVADA for token in tokens[:-1])


def test_todos_los_estados_estan_reconocidos():
    tokens = analizar_lexico(" ".join(sorted(ESTADOS)))
    assert [token.valor for token in tokens[:-1]] == sorted(ESTADOS)
    assert all(token.tipo is TipoToken.ESTADO for token in tokens[:-1])


@pytest.mark.parametrize("identificador", ["led1", "luz_sala", "puerta_principal", "a", "a_0", "a0_2"])
def test_identificadores_validos(identificador):
    tokens = analizar_lexico(identificador)
    assert [t.tipo for t in tokens] == [TipoToken.IDENTIFICADOR, TipoToken.FIN_ARCHIVO]
    assert tokens[0].valor == identificador
    assert tokens[0].linea == 1
    assert tokens[0].columna == 1


@pytest.mark.parametrize(
    ("texto", "esperados"),
    [
        ("ENCENDER led1", [TipoToken.PALABRA_RESERVADA, TipoToken.IDENTIFICADOR, TipoToken.FIN_ARCHIVO]),
        ("LISTAR DISPOSITIVOS", [TipoToken.PALABRA_RESERVADA, TipoToken.PALABRA_RESERVADA, TipoToken.FIN_ARCHIVO]),
        ("NOTIFICAR \"Prueba\"", [TipoToken.PALABRA_RESERVADA, TipoToken.CADENA, TipoToken.FIN_ARCHIVO]),
        ("SI led1 == ENCENDIDO ENTONCES APAGAR led1", [
            TipoToken.PALABRA_RESERVADA, TipoToken.IDENTIFICADOR, TipoToken.IGUALDAD,
            TipoToken.ESTADO, TipoToken.PALABRA_RESERVADA, TipoToken.PALABRA_RESERVADA,
            TipoToken.IDENTIFICADOR, TipoToken.FIN_ARCHIVO,
        ]),
        ("ENVIAR CORREO A \"prueba@ejemplo.com\" MENSAJE \"Hola\"", [
            TipoToken.PALABRA_RESERVADA, TipoToken.PALABRA_RESERVADA,
            TipoToken.PALABRA_RESERVADA, TipoToken.CADENA,
            TipoToken.PALABRA_RESERVADA, TipoToken.CADENA, TipoToken.FIN_ARCHIVO,
        ]),
    ],
)
def test_reconoce_ejemplos_de_la_gramatica(texto, esperados):
    assert [t.tipo for t in analizar_lexico(texto)] == esperados


def test_multiples_lineas_lf_y_crlf_con_posiciones():
    tokens = analizar_lexico("ENCENDER led1\r\n\t APAGAR luz_sala\nNOTIFICAR \"Hola\"")
    assert [(t.tipo, t.linea, t.columna) for t in tokens] == [
        (TipoToken.PALABRA_RESERVADA, 1, 1),
        (TipoToken.IDENTIFICADOR, 1, 10),
        (TipoToken.SALTO_LINEA, 1, 14),
        (TipoToken.PALABRA_RESERVADA, 2, 3),
        (TipoToken.IDENTIFICADOR, 2, 10),
        (TipoToken.SALTO_LINEA, 2, 18),
        (TipoToken.PALABRA_RESERVADA, 3, 1),
        (TipoToken.CADENA, 3, 11),
        (TipoToken.FIN_ARCHIVO, 3, 17),
    ]
    assert tokens[2].lexema == "\r\n"
    assert tokens[5].lexema == "\n"


def test_lineas_vacias_y_archivo_vacio():
    assert [t.tipo for t in analizar_lexico("")] == [TipoToken.FIN_ARCHIVO]
    tokens = analizar_lexico("\n\n")
    assert [t.tipo for t in tokens] == [TipoToken.SALTO_LINEA, TipoToken.SALTO_LINEA, TipoToken.FIN_ARCHIVO]
    assert (tokens[-1].linea, tokens[-1].columna) == (3, 1)


def test_cadena_acepta_texto_unicode_y_arroba_dentro_de_comillas():
    tokens = analizar_lexico('NOTIFICAR "¡Alarma activa! aviso@casa.mx"')
    assert tokens[1].tipo is TipoToken.CADENA
    assert tokens[1].valor == "¡Alarma activa! aviso@casa.mx"


def test_cadena_puede_estar_vacia_sin_que_lexer_la_rechace():
    # El rechazo de mensaje vacío es SEMÁNTICO, no léxico.
    tokens = analizar_lexico('NOTIFICAR ""')
    assert tokens[1].tipo is TipoToken.CADENA
    assert tokens[1].valor == ""


def test_escapes_permitidos_y_lexema_original():
    origen = r'NOTIFICAR "Dijo \"hola\" en C:\\casa"'
    tokens = analizar_lexico(origen)
    assert tokens[1].valor == 'Dijo "hola" en C:\\casa'
    assert tokens[1].lexema == r'"Dijo \"hola\" en C:\\casa"'


def test_analisis_independiente_no_guarda_estado_entre_llamadas():
    assert analizar_lexico("ENCENDER led1")[-1].columna == 14
    assert analizar_lexico("APAGAR led1")[0].linea == 1


@pytest.mark.parametrize(
    ("texto", "linea", "columna", "texto_error"),
    [
        ("ENCENDER led1@", 1, 14, "@"),
        ("ENCENDER led1\nAPAGAR led1@", 2, 12, "@"),
        ("ENCENDER led1#", 1, 14, "#"),
        ("SI led1 = ENCENDIDO", 1, 9, "="),
        ("SI temperatura > 30", 1, 16, ">"),
        ("ENCENDERR led1", 1, 1, "ENCENDERR"),
        ("ENCENDER 1led", 1, 10, "1"),
        ("ENCENDER led-1", 1, 13, "-"),
        ("ENCENDER léd1", 1, 11, "é"),
        ("ENCENDER led1\rAPAGAR led1", 1, 14, "\\r"),
        ('NOTIFICAR "Hola', 1, 11, "cadena sin comillas"),
        ('NOTIFICAR "Hola\nMundo"', 1, 11, "cadena sin comillas"),
        (r'NOTIFICAR "abc\n"', 1, 15, "escape"),
    ],
)
def test_errores_lexicos_con_linea_y_columna(texto, linea, columna, texto_error):
    with pytest.raises(ErrorLexico) as captura:
        analizar_lexico(texto)
    error = captura.value
    assert error.tipo == "LEXICO"
    assert (error.linea, error.columna) == (linea, columna)
    assert texto_error in error.descripcion or texto_error in str(error)
    assert set(error.a_diccionario()) == {"tipo", "linea", "columna", "descripcion"}


def test_palabra_reservada_en_minusculas_se_lexea_como_identificador():
    # Es el parser el que rechazará este comando por no cumplir mayúsculas.
    tokens = analizar_lexico("encender led1")
    assert [t.tipo for t in tokens] == [TipoToken.IDENTIFICADOR, TipoToken.IDENTIFICADOR, TipoToken.FIN_ARCHIVO]


def test_token_es_inmutable_y_serializable():
    token = analizar_lexico("APAGAR led1")[0]
    assert token.a_diccionario() == {
        "tipo": "PALABRA_RESERVADA", "valor": "APAGAR", "linea": 1,
        "columna": 1, "lexema": "APAGAR",
    }
    with pytest.raises(AttributeError):
        token.valor = "ENCENDER"


def test_lexer_no_modifica_el_programa_fuente():
    programa = 'ENCENDER led1\nNOTIFICAR "¡Listo!"'
    lexer = Lexer(programa)
    lexer.analizar()
    assert lexer.texto == programa


def test_entrada_no_textual_genera_error_explicito():
    with pytest.raises(TypeError, match="texto"):
        analizar_lexico(None)


def test_orden_incompleta_es_lexicamente_valida():
    assert [t.tipo for t in analizar_lexico("ENCENDER")] == [TipoToken.PALABRA_RESERVADA, TipoToken.FIN_ARCHIVO]


@pytest.mark.parametrize(
    "texto",
    ["ENCENDERled1", "led1ENCENDER", 'NOTIFICAR"Hola"', 'NOTIFICAR "hola"MENSAJE', '"a""b"'],
)
def test_textos_adyacentes_sin_separador_se_rechazan(texto):
    with pytest.raises(ErrorLexico, match="separador"):
        analizar_lexico(texto)


def test_operadores_pueden_delimitar_tokens_sin_espacios():
    tokens = analizar_lexico("SI led1==ENCENDIDO ENTONCES APAGAR led1")
    assert [token.valor for token in tokens if token.tipo is TipoToken.IGUALDAD] == ["=="]


def test_programa_completo_de_especificacion():
    programa = (
        'ENCENDER led1\n'
        'ENCENDER luz_sala\n'
        'CONSULTAR luz_sala\n'
        'ACTIVAR alarma1\n'
        'SI alarma1 == ACTIVADA ENTONCES NOTIFICAR "Alarma activa"\n'
        'LISTAR DISPOSITIVOS\n'
        'ENVIAR CORREO A "prueba@ejemplo.com" MENSAJE "Sistema listo"'
    )
    tokens = analizar_lexico(programa)
    assert sum(t.tipo is TipoToken.SALTO_LINEA for t in tokens) == 6
    assert sum(t.tipo is TipoToken.CADENA for t in tokens) == 3
    assert tokens[-1].tipo is TipoToken.FIN_ARCHIVO
    assert (tokens[-1].linea, tokens[-1].columna) == (7, len(programa.splitlines()[-1]) + 1)
