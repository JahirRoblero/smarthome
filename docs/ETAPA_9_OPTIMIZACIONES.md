# Etapa 9 — Optimización conservadora del código intermedio

## Objetivo

Dos técnicas: eliminar escrituras redundantes y escrituras cuyo valor se
sobrescribe, sin cambiar el comportamiento observable del programa.

- \`ENCENDER led1\` dos veces: dos eventos lógicos, una sola escritura real.
- \`ENCENDER led1\` seguido de \`APAGAR led1\`: dos eventos lógicos,
  una sola escritura real del valor final.

## Estrategia

El IR se valida primero. Luego, solamente en grupos de asignaciones
**consecutivas al mismo dispositivo**, algunas instrucciones
\`ASIGNAR_ESTADO\` se convierten en \`REGISTRAR_ESTADO_LOGICO\`.
No se eliminan instrucciones, ni cambian sus argumentos, índices, líneas,
columnas o direcciones de salto.

El ejecutor conserva el mismo resultado de cada instrucción y el mismo
registro en el historial, pero ejecuta menos \`UPDATE dispositivos\`.

Las consultas, listados, condiciones, notificaciones y correos cortan los
grupos de optimización; ninguna acción condicional se optimiza.
No se reordenan ni se omiten correos.

El esquema actual no tiene triggers sobre UPDATE. En PostgreSQL, todos los
cambios se ejecutan dentro de una sola transacción, por lo que los estados
transitorios sin COMMIT no son observables por consultas externas.
**Si se agregan triggers, eventos externos por escritura o alguna lectura
intermedia nueva, deben revisarse estas reglas antes de habilitar optimización.**

## Activación

React muestra la casilla "Optimizar escrituras de estado (Etapa 9)".
Afecta a **Ejecutar** y **Ver IR**; no afecta a **Validar**.

Se admite \`optimizar: true/false\` en POST \`/api/ejecutar\` y
\`/api/compilar\`, por defecto \`true\`.

Ejemplo:

\`\`\`json
{"codigo":"ENCENDER led1\nAPAGAR led1","optimizar":true}
\`\`\`

El resultado incluye \`optimizacion\` con conteos de asignaciones
originales, escrituras físicas, evitadas, redundantes y sobrescritas.

## Pruebas

\`\`\`bash
cd backend
python -m pytest -q
\`\`\`

Se comparan estados finales, resultados por línea, historial lógico,
notificaciones y correos con y sin optimización, además de conteos de
escrituras físicas y barreras de observación.
