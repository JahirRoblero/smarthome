# Análisis semántico

## Objetivo

El analizador semántico recibe el AST producido por `parser.py` y usa la tabla de símbolos cargada desde PostgreSQL para verificar que el programa **tenga sentido antes de ejecutarse**. No modifica dispositivos, no guarda historial y no envía notificaciones ni correos.

## Validaciones

1. **Existencia:** `ENCENDER inexistente` se rechaza porque el dispositivo no está en la tabla de símbolos.
2. **Operación/tipo:** `ENCENDER alarma1` se rechaza porque las alarmas admiten `ACTIVAR`, `DESACTIVAR` y `CONSULTAR`.
3. **Estados compatibles:** `SI alarma1 == ENCENDIDO ENTONCES DESACTIVAR alarma1` se rechaza; una alarma solo admite `ACTIVADA` y `DESACTIVADA`.
4. **Condiciones válidas:** solo se admite `==` y no se permiten condiciones anidadas. Se validan tanto la condición como la acción del `ENTONCES`, incluso si la condición sería falsa con el estado actual. El motor de ejecución evaluará la condición más adelante.
5. **Parámetros:** identificadores y mensajes deben ser texto; `NOTIFICAR` y el mensaje del correo no pueden estar vacíos. `ENVIAR CORREO` requiere una dirección con formato simple `usuario@dominio.extension`. Los tipos de tokens ya los controla el parser.

Los programas de varias líneas se validan **completos** antes de cualquier ejecución. Si falla la tercera línea, el análisis no ha ejecutado las anteriores.

## Archivos

- `backend/app/interpreter/semantic.py`: clase `AnalizadorSemantico`, `ErrorSemantico` y `analizar_semantico`.
- `backend/app/api/routes/semantic.py`: ruta `POST /api/analizar`.
- `backend/tests/test_semantic.py` y `backend/tests/test_semantic_api.py`: pruebas sin PostgreSQL real.

El analizador devuelve el mismo `Programa` AST una vez validado. Ese será el insumo del generador de código intermedio de la siguiente etapa.

## Probar desde Bruno

**POST** `http://localhost:8000/api/analizar` con Body JSON:

```json
{"codigo": "ENCENDER led1\nSI alarma1 == ACTIVADA ENTONCES DESACTIVAR alarma1"}
```

- Correcto: HTTP 200 con `correcto: true`, `instrucciones_validadas: 2` y el AST.
- Error semántico: Body `{"codigo":"ENCENDER alarma1"}`; HTTP 422 con `tipo: SEMANTICO`, línea, columna y descripción.
- Error léxico o sintáctico: HTTP 422 con su tipo original `LEXICO` o `SINTACTICO`.
- PostgreSQL desconectado: HTTP 503, sin exponer información interna.

## Terminal

Con Docker levantado, desde la raíz del proyecto:

```bash
docker compose exec backend python -m app.interpreter.semantic --texto "ENCENDER led1"
docker compose exec backend python -m app.interpreter.semantic --texto "ENCENDER alarma1"
```

O desde `backend/` con `DATABASE_URL` configurada:

```bash
python -m app.interpreter.semantic --texto "SI led1 == APAGADO ENTONCES ENCENDER led1"
python -m pytest -q
```

El CLI imprime JSON. Termina con código 0 cuando pasa o 1 cuando encuentra un error léxico, sintáctico o semántico.

## Alcance

- No se introducen variables, funciones, recursividad ni condiciones anidadas.
- No hay nuevas tablas SQL: reutilizamos la tabla de símbolos de la Etapa 5.
- Lexer, Parser y AST no se modificaron.
- **Todavía no se ejecutan** ENCENDER, APAGAR, NOTIFICAR ni ENVIAR CORREO.
- Siguiente etapa: generación del código intermedio (IR) desde el AST validado.
