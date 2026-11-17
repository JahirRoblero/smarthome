"""Compara optimización activada/desactivada sin depender de PostgreSQL."""
import json

import pytest

from app.interpreter.intermediate import OperacionIR, compilar_a_ir
from app.interpreter.optimizer import optimizar_programa
from app.interpreter.symbols import TablaSimbolos
from app.interpreter import executor


def tabla():
    return TablaSimbolos([
        {"identificador": "led1", "tipo": "LED", "estado": "APAGADO"},
        {"identificador": "luz_sala", "tipo": "LUZ", "estado": "APAGADO"},
        {"identificador": "alarma1", "tipo": "ALARMA", "estado": "DESACTIVADA"},
    ])


class BaseFalsa:
    """Cuenta UPDATE físicos, eventos, correos y notificaciones."""
    def __init__(self):
        self.estados = {"led1": "APAGADO", "luz_sala": "APAGADO", "alarma1": "DESACTIVADA"}
        self.historial = []
        self.notificaciones = []
        self.updates = 0
        self.siguiente = None

    def __enter__(self): return self
    def __exit__(self, *_): return False
    def cursor(self): return self

    def execute(self, sql, parametros=None):
        if sql.startswith("UPDATE dispositivos"):
            estado, nombre = parametros
            self.updates += 1
            self.estados[nombre] = estado
            self.siguiente = (estado,)
        elif sql.startswith("INSERT INTO historial"):
            self.historial.append(parametros)
        elif sql.startswith("INSERT INTO notificaciones"):
            self.notificaciones.append(parametros[0])
            self.siguiente = (len(self.notificaciones),)
        elif sql.startswith("SELECT estado FROM dispositivos"):
            self.siguiente = (self.estados[parametros[0]],)
        elif sql.startswith("SELECT identificador, tipo, estado"):
            tipos = {"led1": "LED", "luz_sala": "LUZ", "alarma1": "ALARMA"}
            self.siguiente = [
                (nombre, tipos[nombre], estado)
                for nombre, estado in sorted(self.estados.items())
            ]
        else:
            raise AssertionError(f"SQL inesperado: {sql}")
    def fetchone(self): return self.siguiente
    def fetchall(self): return self.siguiente


def ejecutar(monkeypatch, codigo, optimizar):
    base = BaseFalsa()
    correos = []
    monkeypatch.setattr(executor, "abrir_conexion", lambda: base)
    monkeypatch.setattr(
        executor, "enviar_correo_prueba",
        lambda destino, mensaje: correos.append((destino, mensaje))
    )
    ir = compilar_a_ir(codigo, tabla(), optimizar=optimizar)
    respuesta = executor.ejecutar_ir(ir, codigo)
    return ir, respuesta, base, correos


@pytest.mark.parametrize("codigo,escrituras", [
    ("ENCENDER led1\nENCENDER led1", 1),
    ("ENCENDER led1\nAPAGAR led1", 0),
    ("ENCENDER led1\nENCENDER led1\nAPAGAR led1", 0),
    ("ENCENDER led1\nAPAGAR led1\nENCENDER led1", 1),
    ("ENCENDER led1\nCONSULTAR led1\nAPAGAR led1", 2),
    ("ENCENDER led1\nLISTAR DISPOSITIVOS\nAPAGAR led1", 2),
    ('ENCENDER led1\nNOTIFICAR "Alerta"\nAPAGAR led1', 2),
    ('ENCENDER led1\nENVIAR CORREO A "prueba@ejemplo.com" MENSAJE "Hola"\nAPAGAR led1', 2),
    ("ENCENDER led1\nENCENDER luz_sala\nAPAGAR led1", 3),
    ("SI led1 == APAGADO ENTONCES ENCENDER led1\nENCENDER led1", 1),
    ("ENCENDER led1\nSI led1 == ENCENDIDO ENTONCES APAGAR led1", 2),
    ("ACTIVAR alarma1\nDESACTIVAR alarma1", 0),
])
def test_optimizador_equivalente(monkeypatch, codigo, escrituras):
    ir_original, no, db_no, mail_no = ejecutar(monkeypatch, codigo, False)
    ir_optimizado, si, db_si, mail_si = ejecutar(monkeypatch, codigo, True)
    assert db_si.updates == escrituras
    assert db_no.updates >= db_si.updates
    assert db_si.estados == db_no.estados
    # Las instrucciones optimizadas no se registran como operaciones físicas.
    eventos_reales = [evento for evento in si["resultados"] if not evento.get("optimizada")]
    assert len(db_si.historial) == len(eventos_reales)
    assert [json.loads(fila[1]) for fila in db_si.historial] == eventos_reales
    # Sin optimizar se persisten todos los eventos de ejecución.
    assert len(db_no.historial) == len(no["resultados"])
    assert db_si.notificaciones == db_no.notificaciones
    assert mail_si == mail_no
    # Una instrucción sin UPDATE queda identificada como omitida; al
    # comparar el efecto lógico, sigue representando la misma orden validada.
    def resultado_logico(evento):
        limpio = {k: v for k, v in evento.items() if k != "optimizada"}
        if evento.get("optimizada") and evento["estado"] == "OMITIDA":
            limpio["estado"] = "EXITOSA"
            limpio["detalle"] = f'{evento["dispositivo"]}: {evento["valor"]}'
        return limpio

    assert [resultado_logico(e) for e in si["resultados"]] == no["resultados"]
    assert si["instrucciones_ir"] == no["instrucciones_ir"]
    assert len(ir_optimizado.instrucciones) == len(ir_original.instrucciones)
    assert si["optimizacion"]["escrituras_evitadas"] == db_no.updates - db_si.updates
    assert si["optimizacion"]["escrituras_fisicas"] == db_si.updates


def test_cuenta_redundantes_y_sobrescritas():
    ir = compilar_a_ir("ENCENDER led1\nENCENDER led1\nAPAGAR led1", tabla())
    resumen = ir.resumen_optimizacion()
    assert resumen["redundantes"] == 1
    assert resumen["sobrescritas"] == 1
    assert resumen["escrituras_fisicas"] == 1
    assert [i.operacion for i in ir.instrucciones] == [
        OperacionIR.REGISTRAR_ESTADO_LOGICO,
        OperacionIR.REGISTRAR_ESTADO_LOGICO,
        OperacionIR.ASIGNAR_ESTADO,
    ]
    assert [i.linea for i in ir.instrucciones] == [1, 2, 3]
    assert [i["indice"] for i in ir.a_diccionario()["instrucciones"]] == [0, 1, 2]


def test_optimizaciones_individuales():
    codigo = "ENCENDER led1\nENCENDER led1\nAPAGAR led1"
    ir = compilar_a_ir(codigo, tabla(), optimizar=False)
    redundantes = optimizar_programa(ir, sobrescritas=False)
    sobrescritas = optimizar_programa(ir, redundantes=False)
    assert redundantes.resumen_optimizacion()["redundantes"] == 1
    assert redundantes.resumen_optimizacion()["sobrescritas"] == 0
    assert sobrescritas.resumen_optimizacion()["sobrescritas"] == 2
    assert sobrescritas.resumen_optimizacion()["redundantes"] == 0


def test_condicion_falsa_con_asignaciones_posteriores(monkeypatch):
    codigo = "SI led1 == ENCENDIDO ENTONCES APAGAR led1\nENCENDER led1\nENCENDER led1"
    _, no, db_no, _ = ejecutar(monkeypatch, codigo, False)
    _, si, db_si, _ = ejecutar(monkeypatch, codigo, True)
    assert db_no.estados == db_si.estados
    assert len(db_si.historial) == len(db_no.historial) - 1
    assert [json.loads(fila[1]) for fila in db_si.historial] == [
        evento for evento in si["resultados"] if not evento.get("optimizada")
    ]
    assert [
        {clave: valor for clave, valor in evento.items() if clave != "optimizada"}
        for evento in si["resultados"]
    ] == no["resultados"]
    assert db_si.updates == 1


def test_no_muta_ir_original():
    ir = compilar_a_ir("ENCENDER led1\nENCENDER led1", tabla(), optimizar=False)
    original = json.dumps(ir.a_diccionario())
    despues = optimizar_programa(ir)
    assert ir.instrucciones[0].operacion is OperacionIR.ASIGNAR_ESTADO
    assert despues.instrucciones[0].operacion is OperacionIR.REGISTRAR_ESTADO_LOGICO
    assert json.dumps(ir.a_diccionario()) == original


def test_historial_no_registra_bloque_sin_cambios_reales(monkeypatch):
    # El LED inicia APAGADO, por lo tanto no hay escrituras físicas.
    codigo = "ENCENDER led1\nENCENDER led1\nAPAGAR led1"
    _, respuesta, db, _ = ejecutar(monkeypatch, codigo, True)
    assert len(respuesta["resultados"]) == 3
    assert db.updates == 0
    assert len(db.historial) == 0
    assert [evento.get("optimizada", False) for evento in respuesta["resultados"]] == [
        True, True, True
    ]
    assert respuesta["optimizacion"]["escrituras_fisicas"] == 0


def test_historial_registra_una_escritura_real(monkeypatch):
    codigo = "ENCENDER led1\nENCENDER led1\nENCENDER led1"
    _, respuesta, db, _ = ejecutar(monkeypatch, codigo, True)
    assert len(respuesta["resultados"]) == 3
    assert db.updates == 1
    assert len(db.historial) == 1
    assert db.historial[0][0] == "ENCENDER led1"
    assert [evento.get("optimizada", False) for evento in respuesta["resultados"]] == [
        True, True, False
    ]


def test_sin_optimizacion_conserva_historial_completo(monkeypatch):
    codigo = "ENCENDER led1\nENCENDER led1"
    _, respuesta, db, _ = ejecutar(monkeypatch, codigo, False)
    assert db.updates == 2
    assert len(db.historial) == 2
    assert all(not evento.get("optimizada") for evento in respuesta["resultados"])
