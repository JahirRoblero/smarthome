# Código intermedio (IR)

## Objetivo

Transformar un programa validado (AST) en instrucciones internas, sin ejecutar acciones ni volver a interpretar el texto fuente. El motor de ejecución de la siguiente etapa consumirá exclusivamente el IR.

## Flujo

`texto → lexer → parser/AST → análisis semántico (tabla de símbolos de PostgreSQL) → generador IR → ProgramaIR`

El punto de entrada seguro es `compilar_a_ir(texto, tabla_simbolos=None)`: valida **todas** las instrucciones antes de generar IR. `generar_codigo_intermedio(programa_validado)` se reserva a quien ya tiene un AST validado.

## Operaciones soportadas

| Operación | Argumentos | Función futura |
|---|---|---|
| `ASIGNAR_ESTADO` | dispositivo, estado | Cambia el estado persistente |
| `CONSULTAR_ESTADO` | dispositivo | Recupera estado para mostrarlo |
| `LISTAR_DISPOSITIVOS` | ninguno | Lista todos los dispositivos |
| `REGISTRAR_NOTIFICACION` | mensaje | Guarda una notificación |
| `ENVIAR_CORREO` | destinatario, mensaje | Envía a Mailpit |
| `LEER_ESTADO` | dispositivo, temporal | Carga estado actual para la condición |
| `COMPARAR_IGUAL` | temporal_estado, estado_esperado, temporal_booleano | Compara valores en tiempo de ejecución |
| `SALTAR_SI_FALSO` | temporal_booleano, indice_destino | Salta a una instrucción si la condición es falsa |

Los índices empiezan en **0**. Se permite que un salto apunte a `len(instrucciones)` para finalizar el programa. Los temporales se llaman `t0`, `t1`... y son exclusivos de la compilación de cada programa.

## Ejemplos

`ENCENDER led1` se convierte en `ASIGNAR_ESTADO led1 ENCENDIDO`.

`SI led1 == ENCENDIDO ENTONCES APAGAR led1` se convierte en:

| Índice | Operación | Argumentos |
|---|---|---|
| 0 | `LEER_ESTADO` | `led1`, `t0` |
| 1 | `COMPARAR_IGUAL` | `t0`, `ENCENDIDO`, `t1` |
| 2 | `SALTAR_SI_FALSO` | `t1`, `4` |
| 3 | `ASIGNAR_ESTADO` | `led1`, `APAGADO` |

La comparación **no se calcula al compilar**. Aunque el LED esté apagado ahora, el IR conserva la condición, porque otros comandos anteriores podrían cambiar el estado antes de evaluarla. El destino `4` significa que se omite la acción y se continúa fuera de este bloque.

## Probar desde Bruno

1. Método: `POST`.
2. URL: `http://localhost:8000/api/compilar`.
3. En **Body → JSON**, enviar:

```json
{
  "codigo": "ENCENDER led1\nSI led1 == ENCENDIDO ENTONCES APAGAR led1"
}
```

Debe devolver HTTP 200, `correcto: true` y un objeto `ir` con `tipo: PROGRAMA_IR`, `temporales` e `instrucciones`.

`{"codigo":"ENCENDER alarma1"}` devuelve HTTP 422 con error `SEMANTICO`. Un cuerpo ausente o no válido también produce 422, pero como validación HTTP de FastAPI. PostgreSQL inaccesible produce 503.

## Probar por terminal

Desde la raíz, con Docker Compose activo:

```bash
docker compose exec backend python -m app.interpreter.intermediate --texto "ENCENDER led1"
docker compose exec backend python -m app.interpreter.intermediate --texto "SI alarma1 == ACTIVADA ENTONCES DESACTIVAR alarma1"
docker compose exec backend python -m pytest -q
```

Las pruebas locales requieren `requirements-dev.txt`; la imagen Docker de producción instala `requirements.txt`, así que para ejecutar Pytest **desde el contenedor** tendrías que instalar las dependencias de desarrollo. Lo recomendado es ejecutar `cd backend` y `python -m pytest -q` desde tu entorno Python local.

## Alcance y límites

- El generador no llama a `actualizar_estado`, PostgreSQL para escrituras, SMTP ni notificaciones.
- `ProgramaIR` y `InstruccionIR` son inmutables y serializables a JSON.
- El generador valida el AST indirectamente mediante `compilar_a_ir`; no se debe alimentar el generador puro con AST no validado.
- El ejecutor de la Etapa 8 interpretará **solo** estas ocho operaciones, no el texto del usuario.
- Todavía no hay optimizaciones; se integrarán después del generador y antes del ejecutor, conservando efectos observables.