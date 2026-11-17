# SmartHome — Integración web, motor de ejecución e historial

Esta entrega conecta **React + FastAPI + PostgreSQL** y utiliza el lenguaje SmartHome Script 1.0 para controlar dispositivos simulados. La fase de **optimizaciones (Etapa 9)** todavía está pendiente: el ejecutor actual recibe IR validado sin optimización.

## Arquitectura de extremo a extremo

1. React envía el programa a POST /api/ejecutar (Body JSON: {"codigo":"ENCENDER led1"}).
2. FastAPI ejecuta lexer, parser, AST, análisis semántico y genera el IR.
3. El ejecutor interpreta **exclusivamente el IR**, sin analizar el texto original.
4. PostgreSQL guarda los estados, los eventos de historial y las notificaciones.
5. FastAPI devuelve los resultados y los dispositivos actualizados. React refresca además historial y notificaciones.
6. Los correos de prueba usan SMTP Mailpit y pueden consultarse en http://localhost:8025.

El texto original solo se usa como etiqueta del historial; no se vuelve a analizar dentro del ejecutor.

## Endpoints

| Método | Ruta | Uso |
| --- | --- | --- |
| POST | /api/ejecutar | Ejecutar programa y devolver resultados y estados |
| GET | /api/dispositivos | Dispositivos y estados actuales |
| GET | /api/dispositivos/{identificador} | Un dispositivo |
| GET | /api/historial?limite=30 | Últimos eventos (1 a 100) |
| GET | /api/notificaciones?limite=30 | Últimas notificaciones (1 a 100) |
| POST | /api/analizar | Validar y producir AST sin ejecutar |
| POST | /api/compilar | Validar y producir IR sin ejecutar |

## Prueba de extremo a extremo

Desde la carpeta raíz del repositorio:

1. git switch main
2. git pull origin main
3. docker compose up --build -d
4. docker compose ps

Luego abrir http://localhost:5173.

**Caso de demostración desde la consola:**

    ENCENDER led1
    SI led1 == ENCENDIDO ENTONCES NOTIFICAR "Luz de prueba encendida"
    CONSULTAR led1
    LISTAR DISPOSITIVOS

Debe mostrarse el LED con estado ENCENDIDO, resultados de ejecución, historial y la nueva notificación. Los botones rápidos de los dispositivos también generan comandos SmartHome enviados a /api/ejecutar.

Probar condición falsa:

    SI led1 == APAGADO ENTONCES NOTIFICAR "No debería registrarse"

Cuando el LED está ENCENDIDO, esa acción se omite y el historial muestra OMITIDA.

Probar error semántico:

    ENCENDER alarma1

Debe devolver HTTP 422 tipo SEMANTICO y **no modificar dispositivos**.

Probar correo de muestra con Mailpit:

    ENVIAR CORREO A "prueba@ejemplo.com" MENSAJE "Hola desde SmartHome"

El resultado se registra como correcto solo después de entregar el mensaje al SMTP de prueba. Abrir http://localhost:8025 para ver el buzón. No se entrega a la casilla real de prueba@ejemplo.com.

## Persistencia

- Los estados, el historial y las notificaciones utilizan las tres tablas de la Etapa 5.
- POST /api/ejecutar también guarda en `historial` los intentos con errores léxicos, sintácticos, semánticos y de ejecución (`estado_ejecucion = ERROR`), junto con la instrucción responsable y el mensaje de diagnóstico. POST /api/analizar y POST /api/compilar siguen siendo de solo lectura.
- Si la ejecución IR falla, la transacción de dispositivos se revierte; el error se registra a continuación en una nueva transacción. Los errores de infraestructura o de formato HTTP no se insertan cuando no hay una ejecución válida que registrar.
- docker compose restart backend reinicia FastAPI sin borrar datos.
- docker compose down conserva el volumen PostgreSQL.
- **No ejecutar docker compose down -v** si deseas conservar los datos.

## Pruebas

Backend: desde backend ejecutar python -m pytest -q.
Frontend: desde frontend ejecutar npm install && npm run build.

GitHub Actions ejecuta las pruebas y la compilación en cada cambio a main. Las pruebas automatizadas usan dobles de PostgreSQL y SMTP: **la prueba completa de persistencia y del buzón Mailpit debe realizarse también con Docker local**.

## Limitaciones y siguientes pasos

- La implementación está diseñada para **desarrollo local**, sin autenticación, autorización ni limitación de frecuencia. No publicar la API directamente en Internet.
- Los comandos se validan **todos antes de empezar a ejecutar**. Las operaciones de PostgreSQL se realizan en una transacción por programa.
- El correo SMTP es un efecto externo: si hay una falla posterior en la base de datos, no se puede deshacer un correo ya enviado. Para producción utilizar una cola/outbox transaccional.
- Las optimizaciones del IR permanecen pendientes (Etapa 9).
- La aplicación no utiliza sensores físicos.
- Mailpit es exclusivamente un buzón de pruebas, no un proveedor de correo real.

## Etapa 9 — Optimización del IR

El backend ofrece el campo booleano `optimizar` (por defecto `true`)
en `POST /api/compilar` y `POST /api/ejecutar`. Se conserva la respuesta
lógica de todas las instrucciones, pero las asignaciones optimizadas sin
`UPDATE` ya no se guardan en la tabla `historial`; las demás operaciones
y los errores mantienen su registro. El historial preexistente no se borra.
Más detalles: [Etapa 9](ETAPA_9_OPTIMIZACIONES.md).
