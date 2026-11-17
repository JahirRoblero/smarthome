"""Optimizaciones locales del IR que mantienen los eventos lógicos.

Se optimizan únicamente asignaciones consecutivas del mismo dispositivo,
sin consultas, condiciones ni efectos externos entre ellas.
El esquema SmartHome no contiene triggers de UPDATE y toda ejecución usa una
transacción: las escrituras intermedias no son visibles sin COMMIT.
"""
from __future__ import annotations

from dataclasses import replace

from .intermediate import InstruccionIR, OperacionIR, ProgramaIR


def optimizar_programa(
    programa: ProgramaIR, *, habilitada: bool = True,
    redundantes: bool = True, sobrescritas: bool = True
) -> ProgramaIR:
    """Reducir UPDATE, conservando orden y número de instrucciones y saltos."""
    if not isinstance(programa, ProgramaIR):
        raise TypeError("El optimizador requiere un ProgramaIR.")

    fuente = programa.instrucciones
    salida: list[InstruccionIR] = list(fuente)
    originales = sum(i.operacion is OperacionIR.ASIGNAR_ESTADO for i in fuente)
    contadores = {"redundantes": 0, "sobrescritas": 0}

    # Impedimos agrupar una acción ejecutada condicionalmente.
    protegidas = {
        indice + 1 for indice, instr in enumerate(fuente)
        if instr.operacion is OperacionIR.SALTAR_SI_FALSO
    }

    if habilitada:
        inicio = 0
        while inicio < len(fuente):
            primero = fuente[inicio]
            if primero.operacion is not OperacionIR.ASIGNAR_ESTADO or inicio in protegidas:
                inicio += 1
                continue

            fin = inicio + 1
            while (
                fin < len(fuente)
                and fin not in protegidas
                and fuente[fin].operacion is OperacionIR.ASIGNAR_ESTADO
                and fuente[fin].argumentos[0] == primero.argumentos[0]
            ):
                fin += 1

            for pos in range(inicio, fin - 1):
                actual = fuente[pos].argumentos[1]
                siguiente = fuente[pos + 1].argumentos[1]
                final = fuente[fin - 1].argumentos[1]

                if actual == siguiente and redundantes:
                    tecnica = "redundantes"
                elif sobrescritas and (redundantes or actual != final):
                    # Con ambas técnicas activas, toda asignación anterior
                    # queda sobrescrita por la última del bloque.
                    tecnica = "sobrescritas"
                else:
                    continue

                salida[pos] = replace(
                    fuente[pos], operacion=OperacionIR.REGISTRAR_ESTADO_LOGICO
                )
                contadores[tecnica] += 1

            inicio = fin

    fisicas = sum(i.operacion is OperacionIR.ASIGNAR_ESTADO for i in salida)
    estadisticas = {
        "habilitada": habilitada,
        "asignaciones_originales": originales,
        "escrituras_fisicas": fisicas,
        "escrituras_evitadas": originales - fisicas,
        **contadores,
    }
    return ProgramaIR(tuple(salida), programa.temporales, estadisticas)
