"""Máquina virtual que ejecuta IR validado, nunca el texto SmartHome.

La base de datos se actualiza en una única transacción por programa.
El SMTP es un efecto externo: no puede deshacerse si una operación posterior falla.
Por eso no debe exponerse esta API a Internet sin autenticación/rate-limits.
"""
from __future__ import annotations

import json
import smtplib

from app.core.mailer import ErrorEnvioCorreo, enviar_correo
from app.db.connection import abrir_conexion
from .intermediate import OperacionIR, ProgramaIR


class ErrorEjecucion(ValueError):
    def __init__(self, descripcion: str, linea: int, columna: int):
        self.tipo = "EJECUCION"
        self.descripcion = descripcion
        self.linea = linea
        self.columna = columna
        super().__init__(descripcion)

    def a_diccionario(self):
        return {"tipo": self.tipo, "linea": self.linea,
                "columna": self.columna, "descripcion": self.descripcion}


def enviar_correo_prueba(destinatario: str, mensaje: str) -> dict[str, str]:
    """Compatibilidad con el ejecutor existente; cambia el proveedor por configuración.

    En modo Resend se comunica con la API HTTPS de Resend; en modo Mailpit
    utiliza SMTP local. Ninguna credencial llega al frontend ni al IR.
    """
    return enviar_correo(destinatario, mensaje)


def ejecutar_ir(programa: ProgramaIR, codigo_fuente: str = "") -> dict:
    """Ejecuta IR secuencialmente con PostgreSQL.

    El texto original se usa EXCLUSIVAMENTE como etiqueta del historial;
    no se interpreta ni se convierte a comandos dentro del ejecutor.
    """
    if not isinstance(programa, ProgramaIR):
        raise TypeError("El ejecutor requiere un ProgramaIR.")
    lineas = codigo_fuente.splitlines()
    resultados: list[dict] = []
    temporales: dict[str, str | bool] = {}
    instrucciones = programa.instrucciones
    pc = 0
    # Estadísticas reales de ejecución; el IR compilado solo conoce el máximo
    # de escrituras posibles, no el estado actual de PostgreSQL.
    escrituras_reales = 0
    evitadas_por_estado = 0
    optimizacion_habilitada = programa.resumen_optimizacion()["habilitada"]

    with abrir_conexion() as conexion:
        with conexion.cursor() as cursor:
            def registrar(instr, estado: str, detalle: str, *, guardar_en_historial: bool = True, **extra):
                evento = {
                    "linea": instr.linea,
                    "operacion": (
                        OperacionIR.ASIGNAR_ESTADO.value
                        if instr.operacion is OperacionIR.REGISTRAR_ESTADO_LOGICO
                        else instr.operacion.value
                    ),
                    "estado": estado,
                    "detalle": detalle,
                    **extra,
                }
                texto = (lineas[instr.linea - 1].strip()
                         if 0 < instr.linea <= len(lineas) else
                         f"{instr.operacion.value} {' '.join(map(str, instr.argumentos))}")
                if guardar_en_historial:
                    cursor.execute(
                        "INSERT INTO historial (instruccion, resultado, estado_ejecucion) "
                        "VALUES (%s, %s, %s)",
                        (texto, json.dumps(evento, ensure_ascii=False), estado),
                    )
                resultados.append(evento)

            while pc < len(instrucciones):
                instr = instrucciones[pc]
                op = instr.operacion
                args = instr.argumentos

                if op is OperacionIR.ASIGNAR_ESTADO:
                    identificador, estado = args

                    if optimizacion_habilitada:
                        # El estado persiste entre peticiones. Se bloquea la fila
                        # para que dos solicitudes simultáneas no escriban/logueen
                        # redundantemente el mismo estado.
                        cursor.execute(
                            "SELECT estado FROM dispositivos WHERE identificador = %s FOR UPDATE",
                            (identificador,),
                        )
                        actual = cursor.fetchone()
                        if actual is None:
                            raise ErrorEjecucion(
                                f"El dispositivo {identificador} ya no existe.",
                                instr.linea, instr.columna,
                            )
                        if actual[0] == estado:
                            evitadas_por_estado += 1
                            registrar(
                                instr, "OMITIDA",
                                f"{identificador} ya estaba {estado}; no se modificó.",
                                guardar_en_historial=False,
                                dispositivo=identificador, valor=estado,
                                optimizada=True,
                            )
                            pc += 1
                            continue

                    cursor.execute(
                        "UPDATE dispositivos SET estado = %s, actualizado_en = NOW() "
                        "WHERE identificador = %s RETURNING estado",
                        (estado, identificador),
                    )
                    fila = cursor.fetchone()
                    if fila is None:
                        raise ErrorEjecucion(
                            f"El dispositivo {identificador} ya no existe.",
                            instr.linea, instr.columna,
                        )
                    escrituras_reales += 1
                    registrar(instr, "EXITOSA", f"{identificador}: {estado}",
                              dispositivo=identificador, valor=estado)

                elif op is OperacionIR.REGISTRAR_ESTADO_LOGICO:
                    # Es un evento lógico: no ejecuta UPDATE ni INSERT en historial.
                    # Se entrega en la respuesta para explicar la optimización.
                    identificador, estado = args
                    registrar(
                        instr, "EXITOSA", f"{identificador}: {estado}",
                        guardar_en_historial=False,
                        dispositivo=identificador, valor=estado, optimizada=True,
                    )

                elif op is OperacionIR.CONSULTAR_ESTADO:
                    identificador, = args
                    cursor.execute(
                        "SELECT estado FROM dispositivos WHERE identificador = %s",
                        (identificador,),
                    )
                    fila = cursor.fetchone()
                    if fila is None:
                        raise ErrorEjecucion(
                            f"El dispositivo {identificador} ya no existe.",
                            instr.linea, instr.columna,
                        )
                    registrar(instr, "EXITOSA", f"{identificador}: {fila[0]}",
                              dispositivo=identificador, valor=fila[0])

                elif op is OperacionIR.LISTAR_DISPOSITIVOS:
                    cursor.execute(
                        "SELECT identificador, tipo, estado FROM dispositivos ORDER BY identificador"
                    )
                    dispositivos = [
                        {"identificador": f[0], "tipo": f[1], "estado": f[2]}
                        for f in cursor.fetchall()
                    ]
                    registrar(instr, "EXITOSA", f"{len(dispositivos)} dispositivos",
                              dispositivos=dispositivos)

                elif op is OperacionIR.REGISTRAR_NOTIFICACION:
                    mensaje, = args
                    cursor.execute(
                        "INSERT INTO notificaciones (mensaje) VALUES (%s) RETURNING id",
                        (mensaje,),
                    )
                    fila = cursor.fetchone()
                    registrar(instr, "EXITOSA", mensaje, notificacion_id=fila[0])

                elif op is OperacionIR.ENVIAR_CORREO:
                    destinatario, mensaje = args
                    try:
                        confirmacion = enviar_correo_prueba(destinatario, mensaje)
                    except ErrorEnvioCorreo as error:
                        raise ErrorEjecucion(
                            str(error), instr.linea, instr.columna
                        ) from error
                    except (smtplib.SMTPException, OSError) as error:
                        raise ErrorEjecucion(
                            "No se pudo enviar el correo al servidor SMTP de pruebas.",
                            instr.linea, instr.columna,
                        ) from error

                    proveedor = (
                        confirmacion.get("proveedor", "mailpit")
                        if isinstance(confirmacion, dict) else "mailpit"
                    )
                    detalle = (
                        f"Resend aceptó el correo dirigido a {destinatario}"
                        if proveedor == "resend"
                        else f"Correo de prueba enviado a {destinatario} (Mailpit)"
                    )
                    extra = {"destinatario": destinatario, "proveedor": proveedor}
                    if isinstance(confirmacion, dict) and confirmacion.get("id"):
                        extra["id_envio"] = confirmacion["id"]
                    registrar(instr, "EXITOSA", detalle, **extra)

                elif op is OperacionIR.LEER_ESTADO:
                    identificador, temporal = args
                    cursor.execute(
                        "SELECT estado FROM dispositivos WHERE identificador = %s FOR UPDATE",
                        (identificador,),
                    )
                    fila = cursor.fetchone()
                    if fila is None:
                        raise ErrorEjecucion(
                            f"El dispositivo {identificador} ya no existe.",
                            instr.linea, instr.columna,
                        )
                    temporales[temporal] = fila[0]

                elif op is OperacionIR.COMPARAR_IGUAL:
                    origen, valor, destino = args
                    if origen not in temporales:
                        raise ErrorEjecucion(
                            "Temporal no inicializado.", instr.linea, instr.columna
                        )
                    temporales[destino] = temporales[origen] == valor

                elif op is OperacionIR.SALTAR_SI_FALSO:
                    temporal, destino = args
                    if temporal not in temporales or not isinstance(temporales[temporal], bool):
                        raise ErrorEjecucion(
                            "Condición sin resultado booleano.", instr.linea, instr.columna
                        )
                    if not temporales[temporal]:
                        if not isinstance(destino, int) or not pc < destino <= len(instrucciones):
                            raise ErrorEjecucion(
                                "Dirección de salto inválida.", instr.linea, instr.columna
                            )
                        registrar(instr, "OMITIDA", "Condición falsa: acción omitida")
                        pc = destino
                        continue
                else:
                    raise ErrorEjecucion(
                        f"Operación IR desconocida: {op}", instr.linea, instr.columna
                    )
                pc += 1
    resumen = dict(programa.resumen_optimizacion())
    resumen["escrituras_fisicas"] = escrituras_reales
    resumen["escrituras_evitadas"] = (
        resumen["asignaciones_originales"] - escrituras_reales
    )
    resumen["evitadas_por_estado"] = evitadas_por_estado
    return {
        "correcto": True,
        "resultados": resultados,
        "instrucciones_ir": len(instrucciones),
        "optimizacion": resumen,
    }
