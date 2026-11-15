# Etapa 4 — Parser y AST

Implementación del analizador sintáctico para SmartHome Script 1.0 según `docs/Diseno_lenguaje_SmartHome.pdf`.

## Módulos

- `lexer.py`: reconoce tokens (sin cambios).
- `parser.py`: parser descendente recursivo que recibe tokens y valida la gramática.
- `ast_nodes.py`: nodos inmutables para control, consulta, listado, notificación, correo, condición, condicional y programa.
- `tests/test_parser.py`: pruebas de comandos válidos, errores y condiciones.

## Uso

Ejecutar desde `backend/`:

```bash
python -m app.interpreter.parser --texto "ENCENDER led1"
python -m app.interpreter.parser --texto "SI alarma1 == ACTIVADA ENTONCES NOTIFICAR \"Alerta\""
python -m app.interpreter.parser --texto "ENCENDER"
python -m pytest -q
```

Para varias líneas, crear un archivo UTF-8 y pasar `--archivo ruta/al/programa.txt`.

El parser devuelve `{"correcto": true, "ast": ...}` si la sintaxis es válida, o `{"correcto": false, "error": {"tipo": "SINTACTICO", "linea": ..., "columna": ..., "descripcion": ...}}` cuando no lo es. Los errores léxicos continúan conservando el tipo `LEXICO`.

## Contrato

- Una instrucción por línea; líneas vacías permitidas.
- `SI ... ENTONCES` admite una única instrucción simple, no otro `SI`.
- Se rechaza texto adicional después de terminar una instrucción.
- La posición del error procede del token inesperado.
- El AST no realiza operaciones reales, no consulta PostgreSQL y no envía correos.
- La existencia de dispositivos, la compatibilidad de estados y los mensajes vacíos se validarán en **análisis semántico**, no en el parser.

## Verificación

El parser se ha probado localmente junto con el lexer del proyecto. Antes de integrar, ejecutar la batería completa de Pytest en tu entorno o en CI.
