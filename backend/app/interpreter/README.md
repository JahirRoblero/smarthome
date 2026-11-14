# Intérprete SmartHome Script 1.0

La sintaxis oficial es `docs/Diseno_lenguaje_SmartHome.pdf`.

## Implementado — Etapa 3 (Lexer)

- `lexer.py`: transforma código fuente en tokens y reporta errores léxicos con línea y columna.
- `Token`: tipo, valor interpretado, línea, columna y lexema original.
- `TipoToken`: siete clases exactas de la especificación.
- `ErrorLexico`: error estructurado sin efectos secundarios.
- `analizar_lexico(texto)`: interfaz estable para el parser (Etapa 4).

La función solo **reconoce tokens**. No valida sintaxis completa, semántica,
existencia de dispositivos, estados ni ejecuta operaciones.

### Pruebas rápidas

Desde `backend/`:

```bash
python -m app.interpreter.lexer --texto "ENCENDER led1"
python -m app.interpreter.lexer --texto "ENCENDER led1@"
python -m app.interpreter.lexer --archivo programa.smarthome
pytest -q tests/test_lexer.py
```

El comando CLI imprime JSON y utiliza código de salida 0 (correcto) o 1 (error
léxico). `--archivo` lee un programa UTF-8. También se pueden llamar las clases
manualmente desde Python.

### Contrato del lexer

- Comandos y estados: en MAYÚSCULAS exactas.
- Identificadores: `[a-z][a-z0-9_]*`.
- Cadenas: comillas dobles, con escapes `\\` y `\"`.
- Separación de tokens de texto: espacios o tabulaciones; operadores como `==`
  pueden delimitar tokens sin espacios.
- Una línea de programa se separa de otra con LF o CRLF; las líneas vacías son
  legales y se emite `SALTO_LINEA` por cada una.
- Coordenadas: línea y columna empiezan en 1. La posición `FIN_ARCHIVO` es la
  siguiente posición disponible después del último carácter.
- La entrada `ENCENDER` es *léxicamente válida*; su falta de identificador
  será un **error sintáctico** en la próxima etapa.
- La entrada `ENCENDER alarma1` es *léxicamente válida*; su incompatibilidad
  será un **error semántico** en otra etapa.

## Pendientes posteriores

`parser.py`, `ast_nodes.py`, `semantic.py`, `symbols.py`,
`intermediate.py`, `optimizer.py`, `executor.py`.
