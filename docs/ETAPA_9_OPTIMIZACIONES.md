# Etapa 9 — Optimización conservadora del código intermedio

## Objetivo

Dos técnicas: eliminar escrituras redundantes y escrituras cuyo valor se
sobrescribe, sin cambiar el comportamiento observable del programa.

- `ENCENDER led1` dos veces: dos eventos lógicos, una sola escritura real.
- `ENCENDER led1` seguido de `APAGAR led1`: dos eventos lógicos,
  una sola escritura real del valor final.

## Estrategia

El IR se valida primero. Luego, solamente en grupos de asignaciones
**consecutivas al mismo dispositivo**, algunas instrucciones
`ASIGNAR_ESTADO` se convierten en `REGISTRAR_ESTADO_LOGICO`.
No se eliminan instrucciones, ni cambian sus argumentos, índices, líneas,
columnas o direcciones de salto.

El ejecutor conserva las respuestas lógicas de las instrucciones, pero
**solo guarda en la tabla `historial` los eventos que realmente se ejecutan**:
las asignaciones sustituidas por `REGISTRAR_ESTADO_LOGICO` no generan
`UPDATE dispositivos` ni `INSERT INTO historial`. En la respuesta de la
consola estas instrucciones llevan la marca `optimizada: true` y una
explicación visible. Las consultas, notificaciones, correos, asignaciones
físicas y errores siguen registrándose como antes.

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

Se admite `optimizar: true/false` en POST `/api/ejecutar` y
`/api/compilar`, por defecto `true`.

Ejemplo:

```json
{"codigo":"ENCENDER led1\nAPAGAR led1","optimizar":true}
```

El resultado incluye `optimizacion` con conteos de asignaciones
originales, escrituras físicas, evitadas, redundantes y sobrescritas.

## Pruebas

```bash
cd backend
python -m pytest -q
```

Se comparan estados finales, resultados lógicos por línea, notificaciones
y correos con y sin optimización. También se verifica que el historial
persistido omite únicamente las asignaciones sin escritura física y que los
conteos de `UPDATE` corresponden a las asignaciones realmente ejecutadas.

La optimización solo se aplica dentro de **una misma solicitud**, no entre
ejecuciones distintas de la consola. El historial ya guardado antes de esta
actualización se conserva; no se modifican ni borran registros históricos.

## Evitar escrituras repetidas entre ejecuciones independientes

La optimización del IR actúa dentro de cada programa. Adicionalmente, con
`optimizar=true`, el ejecutor compara cada asignación física pendiente con
el **estado persistido actual** del dispositivo mediante
`SELECT ... FOR UPDATE`. Si coincide, no realiza `UPDATE` ni
`INSERT INTO historial`; devuelve a la consola un evento `OMITIDA`
con `optimizada=true` para explicarlo.

Por ejemplo, en tres peticiones independientes de `ENCENDER led1`, si el
LED inicialmente está apagado, solo la primera genera una escritura y una
fila de historial. Si después se ejecuta `APAGAR led1`, se realiza y
registra ese nuevo cambio.

Las consultas siguen ejecutándose y registrándose normalmente. Al desmarcar
la casilla de optimización se mantiene el comportamiento original con
escrituras repetidas. El cálculo de `escrituras_fisicas` y
`escrituras_evitadas` en **/api/ejecutar** refleja las escrituras realmente
realizadas; en **/api/compilar** es una estimación estática sin conexión
al estado actual.

Los registros creados por versiones anteriores no se eliminan ni se
reinterpretan retroactivamente. No se debe confundir la presencia de filas
antiguas con escrituras nuevas de la versión optimizada.
