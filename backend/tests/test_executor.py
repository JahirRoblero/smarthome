"""Pruebas del ejecutor IR sin necesitar PostgreSQL ni SMTP reales."""
import pytest

from app.interpreter.executor import ErrorEjecucion, ejecutar_ir
from app.interpreter.intermediate import compilar_a_ir
from app.interpreter.symbols import TablaSimbolos
from app.interpreter import executor


class BaseFalsa:
    def __init__(self):
        self.estados = {"led1": "APAGADO", "alarma1": "DESACTIVADA"}
        self.tipos = {"led1": "LED", "alarma1": "ALARMA"}
        self.historial = []
        self.notificaciones = []
        self.siguiente = None
        self.ultimo_sql = ""
        self.rollback = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        self.rollback = exc_type is not None
        return False

    def cursor(self):
        return self

    def execute(self, sql, valores=None):
        self.ultimo_sql = sql
        if sql.startswith("UPDATE dispositivos"):
            estado, nombre = valores
            self.siguiente = None
            if nombre in self.estados:
                self.estados[nombre] = estado
                self.siguiente = (estado,)
        elif sql.startswith("SELECT estado FROM dispositivos"):
            self.siguiente = (self.estados[valores[0]],) if valores[0] in self.estados else None
        elif sql.startswith("SELECT identificador, tipo, estado"):
            self.siguiente = [(nombre, self.tipos[nombre], estado) for nombre, estado in sorted(self.estados.items())]
        elif sql.startswith("INSERT INTO historial"):
            self.historial.append(valores)
        elif sql.startswith("INSERT INTO notificaciones"):
            self.notificaciones.append(valores[0])
            self.siguiente = (len(self.notificaciones),)
        else:
            raise AssertionError("SQL inesperado: " + sql)

    def fetchone(self):
        return self.siguiente

    def fetchall(self):
        return self.siguiente


@pytest.fixture
def entorno(monkeypatch):
    base = BaseFalsa()
    tabla = TablaSimbolos([
        {"identificador": nombre, "tipo": base.tipos[nombre], "estado": estado}
        for nombre, estado in base.estados.items()
    ])
    monkeypatch.setattr(executor, "abrir_conexion", lambda: base)
    return base, tabla


def test_actualiza_y_consulta_persistencia(entorno):
    base, tabla = entorno
    codigo = "ENCENDER led1\nCONSULTAR led1"
    resultado = ejecutar_ir(compilar_a_ir(codigo, tabla), codigo)
    assert base.estados["led1"] == "ENCENDIDO"
    assert [r["valor"] for r in resultado["resultados"]] == ["ENCENDIDO", "ENCENDIDO"]
    assert len(base.historial) == 2
    assert base.historial[0][0] == "ENCENDER led1"
    assert base.historial[1][0] == "CONSULTAR led1"


def test_condicion_verdadera_y_notificacion(entorno):
    base, tabla = entorno
    codigo = 'ENCENDER led1\nSI led1 == ENCENDIDO ENTONCES NOTIFICAR "Listo"'
    resultado = ejecutar_ir(compilar_a_ir(codigo, tabla), codigo)
    assert base.notificaciones == ["Listo"]
    assert len(resultado["resultados"]) == 2
    assert resultado["resultados"][1]["operacion"] == "REGISTRAR_NOTIFICACION"


def test_condicion_falsa_omite_accion(entorno):
    base, tabla = entorno
    codigo = 'SI led1 == ENCENDIDO ENTONCES NOTIFICAR "NO"'
    resultado = ejecutar_ir(compilar_a_ir(codigo, tabla), codigo)
    assert base.notificaciones == []
    assert resultado["resultados"][0]["estado"] == "OMITIDA"
    assert len(base.historial) == 1


def test_lista_dispositivos(entorno):
    base, tabla = entorno
    ir = compilar_a_ir("LISTAR DISPOSITIVOS", tabla)
    r = ejecutar_ir(ir, "LISTAR DISPOSITIVOS")
    assert len(r["resultados"][0]["dispositivos"]) == 2


def test_dos_condicionales_se_ejecutan_en_orden(entorno):
    base, tabla = entorno
    codigo = ('SI led1 == APAGADO ENTONCES ENCENDER led1\n'
              'SI led1 == ENCENDIDO ENTONCES APAGAR led1')
    r = ejecutar_ir(compilar_a_ir(codigo, tabla), codigo)
    assert base.estados["led1"] == "APAGADO"
    assert len(r["resultados"]) == 2


def test_el_ejecutor_no_lee_codigo_fuente(entorno):
    base, tabla = entorno
    ir = compilar_a_ir("ENCENDER led1", tabla)
    ejecutar_ir(ir, "ESTE TEXTO NO ES UN COMANDO")
    assert base.estados["led1"] == "ENCENDIDO"


def test_envia_por_smtp_de_prueba(entorno, monkeypatch):
    base, tabla = entorno
    enviados = []
    monkeypatch.setattr(executor, "enviar_correo_prueba", lambda destino, mensaje: enviados.append((destino, mensaje)))
    codigo = 'ENVIAR CORREO A "ejemplo@correo.com" MENSAJE "Hola"'
    r = ejecutar_ir(compilar_a_ir(codigo, tabla), codigo)
    assert enviados == [("ejemplo@correo.com", "Hola")]
    assert r["resultados"][0]["operacion"] == "ENVIAR_CORREO"


def test_fallo_smtp_no_se_reporta_como_exito(entorno, monkeypatch):
    import smtplib
    base, tabla = entorno
    def falla(*_):
        raise smtplib.SMTPException("error")
    monkeypatch.setattr(executor, "enviar_correo_prueba", falla)
    codigo = 'ENVIAR CORREO A "ejemplo@correo.com" MENSAJE "Hola"'
    with pytest.raises(ErrorEjecucion, match="servidor SMTP"):
        ejecutar_ir(compilar_a_ir(codigo, tabla), codigo)
    assert base.rollback is True
    assert len(base.historial) == 0
