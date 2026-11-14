# Etapa 3 · Analizador léxico SmartHome Script 1.0

## 1. Objetivo

Implementar un analizador léxico para convertir un programa de instrucciones en
una secuencia verificable de tokens, sin depender de React, FastAPI, PostgreSQL
ni Mailpit. La especificación formal de referencia es
`Diseno_lenguaje_SmartHome.pdf`, apartados 4 y 5.

## 2. Archivos implementados

| Archivo | Función |
|---|---|
| `backend/app/interpreter/lexer.py` | Escáner, tokens, posiciones, mensajes de error y utilidad CLI. |
| `backend/tests/test_lexer.py` | Pruebas unitarias y de aceptación del lexer. |
| `backend/app/interpreter/README.md` | Contrato para el futuro parser. |

## 3. Tokens implementados

| Tipo | Reconocimiento | Ejemplo |
|---|---|---|
| `PALABRA_RESERVADA` | Comando o conector exacto | `ENCENDER`, `SI`, `MENSAJE` |
| `ESTADO` | Estado exacto | `ENCENDIDO`, `CERRADA` |
| `IDENTIFICADOR` | `[a-z][a-z0-9_]*` | `led1`, `puerta_principal` |
| `CADENA` | Texto entre comillas dobles | `"Aviso"` |
| `IGUALDAD` | Símbolo doble igual | `==` |
| `SALTO_LINEA` | LF o CRLF | Final de línea |
| `FIN_ARCHIVO` | Final de la entrada | EOF |

Los tipos conservan los nombres definidos por el equipo en la versión 1.0.

## 4. Algoritmo

1. Inicializar `linea = 1`, `columna = 1` y cursor al inicio del texto.
2. Ignorar espacios y tabulaciones fuera de cadenas.
3. Leer palabras en mayúsculas y comprobar si son reservadas o estados.
4. Leer identificadores que comienzan con minúscula.
5. Leer cadenas entre comillas, permitiendo `\"` y `\\`.
6. Emitir `IGUALDAD` si hay dos signos `=` consecutivos.
7. Emitir un `SALTO_LINEA` por cada LF o CRLF y avanzar el contador de línea.
8. Detener el análisis con un `ErrorLexico` si hay un carácter inválido,
   palabra en mayúsculas desconocida, falta de separador, cadena sin cierre
   o escape no permitido.
9. Al terminar, agregar el token `FIN_ARCHIVO`.

Cada token tiene **tipo, valor, lexema, línea y columna**. Para cadenas, el
valor desescapado puede diferir del lexema original. Los espacios se descartan,
pero los saltos de línea se conservan para el futuro parser.

## 5. Prueba demostrable: entrada válida

Desde la carpeta `backend`:

```powershell
python -m app.interpreter.lexer --texto "SI led1 == ENCENDIDO ENTONCES APAGAR led1"
```

Los tokens emitidos, en orden, son:

1. `PALABRA_RESERVADA(SI)`
2. `IDENTIFICADOR(led1)`
3. `IGUALDAD(==)`
4. `ESTADO(ENCENDIDO)`
5. `PALABRA_RESERVADA(ENTONCES)`
6. `PALABRA_RESERVADA(APAGAR)`
7. `IDENTIFICADOR(led1)`
8. `FIN_ARCHIVO`

Este resultado **no** implica que el lexer haya evaluado la condición.

## 6. Prueba demostrable: error léxico

```powershell
python -m app.interpreter.lexer --texto "ENCENDER led1@"
```

Resultado:

```json
{
  "correcto": false,
  "error": {
    "tipo": "LEXICO",
    "linea": 1,
    "columna": 14,
    "descripcion": "carácter '@' no reconocido."
  }
}
```

## 7. Pruebas automatizadas

Desde `backend`:

```powershell
python -m pytest -q
```

Se prueban comandos y estados completos, identificadores, cadenas Unicode,
comillas escapadas, barras invertidas, programa multilínea, LF/CRLF, lineas
vacías, separadores, caracteres inválidos, escapes inválidos y posicionamiento.

El lexer no ejecuta ni modifica dispositivos; tampoco requiere PostgreSQL.
En esta etapa no se cambian los endpoints de la API ni el frontend.

## 8. Límites y siguiente etapa

- `ENCENDER` debe producir tokens válidos; el **parser** informará que falta un ID.
- `ENCENDER alarma1` debe producir tokens válidos; el **analizador semántico**
  informará que una alarma no admite ENCENDER.
- `SI temperatura > 30 ...` queda fuera de SmartHome Script 1.0 porque `>` y
  los números no forman parte de la gramática definida por el equipo.
- El lexer no crea AST ni interactúa con la base de datos.

**Siguiente etapa:** `parser.py` y `ast_nodes.py`, con pruebas sintácticas basadas
exclusivamente en la EBNF del documento de diseño del lenguaje.
