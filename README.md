# SmartHome

Proyecto integrador de **Lenguajes y Autómatas II** del Instituto Tecnológico de Oaxaca.

SmartHome es una aplicación web que permite controlar dispositivos simulados con instrucciones escritas. El usuario escribe un comando en la consola, el intérprete revisa que sea válido y ejecuta la acción. Los cambios se muestran en la interfaz y se guardan en PostgreSQL.

- **Aplicación:** https://smarthome.votaya.com.mx/
- **Video:** https://www.youtube.com/watch?v=YYJXMtfYT7o
- **Kanban:** https://trello.com/b/7NeeEbkV

## Qué hace el proyecto

- Controla un LED, una luz, un ventilador, una alarma y una puerta.
- Ejecuta varios comandos separados por saltos de línea.
- Permite consultar estados y listar los dispositivos registrados.
- Acepta condiciones sencillas con `SI ... ENTONCES ...`.
- Identifica errores léxicos, sintácticos, semánticos y de ejecución.
- Muestra el código intermedio y permite activar o desactivar las optimizaciones.
- Guarda los estados e historial de operaciones en PostgreSQL.
- Registra notificaciones y puede enviar avisos Web Push a navegadores suscritos.
- Envía correos a Mailpit durante las pruebas o mediante Resend si está configurado.

## Comandos disponibles

```text
ENCENDER led1
APAGAR luz_sala
ACTIVAR alarma1
DESACTIVAR alarma1
ABRIR puerta_principal
CERRAR puerta_principal
CONSULTAR ventilador1
LISTAR DISPOSITIVOS
NOTIFICAR "Prueba de notificación"
ENVIAR CORREO A "prueba@ejemplo.com" MENSAJE "Hola desde SmartHome"
SI alarma1 == ACTIVADA ENTONCES NOTIFICAR "Alarma activada"
```

Los comandos y estados van en mayúsculas; los identificadores de dispositivos, en minúsculas. El lenguaje tiene una gramática definida: no interpreta cualquier frase escrita en lenguaje natural.

## Cómo funciona

```text
Consola (React)
     |
     v
API (FastAPI)
     |
     v
Lexer -> Parser -> AST -> Análisis semántico
     |
     v
Código intermedio -> Optimizador -> Ejecutor
     |
     v
PostgreSQL / Mailpit / Resend / Web Push
```

El sistema valida el programa antes de ejecutar las instrucciones. El botón **Validar** revisa el código sin cambiar dispositivos; **Ver IR** permite consultar las operaciones intermedias.

### Optimizaciones

El optimizador reduce escrituras de estado que no hacen falta:

- **Redundantes:** `ENCENDER led1` dos veces seguidas no necesita dos escrituras físicas.
- **Sobrescritas:** `ENCENDER led1` seguido inmediatamente de `APAGAR led1` puede conservar solo el estado final, si no hay lecturas o efectos intermedios.

Las instrucciones optimizadas siguen apareciendo en el resultado de la consola, pero no generan un cambio físico ni una fila de historial por esa operación omitida. Las consultas, condiciones, notificaciones y correos impiden que se combinen escrituras a través de ellas. También se pueden comparar los resultados con la optimización activada y desactivada.

Más información: [Optimizaciones](docs/optimizaciones.md).

## Tecnologías

| Componente | Herramientas |
| --- | --- |
| Interfaz | React, TypeScript, Vite |
| API e intérprete | Python, FastAPI |
| Base de datos | PostgreSQL 17 |
| Correos | Mailpit, Resend |
| Notificaciones | Web Push |
| Contenedores | Docker, Docker Compose |
| Pruebas e integración continua | pytest, GitHub Actions |
| Organización del proyecto | Git, GitHub, Trello |

## Instalación con Docker

Se necesitan Git, Docker y Docker Compose.

**1. Clonar el repositorio**

```bash
git clone https://github.com/JahirRoblero/smarthome.git
cd smarthome
```

**2. Crear el archivo de configuración**

En Linux o macOS:

```bash
cp .env.example .env
```

En PowerShell:

```powershell
Copy-Item .env.example .env
```

Los valores de `.env.example` son para desarrollo. No deben utilizarse como credenciales de producción.

**3. Iniciar los servicios**

```bash
docker compose up --build -d
```

Al iniciar, el backend prepara las tablas y los dispositivos sin sobrescribir los estados que ya estén guardados.

**4. Abrir la aplicación**

| Servicio | URL |
| --- | --- |
| SmartHome | http://localhost:5173 |
| Documentación de API | http://localhost:8000/docs |
| Estado del backend | http://localhost:8000/api/health |
| Buzón de Mailpit | http://localhost:8025 |

Para ver los contenedores o detenerlos:

```bash
docker compose ps
docker compose down
```

Evita `docker compose down -v` si necesitas conservar la base de datos y las claves de Web Push.

## Desarrollo local sin Docker

Se requiere Python 3.12+, Node.js 22+ y PostgreSQL configurado. El backend necesita una conexión válida en `DATABASE_URL`.

Backend:

```bash
cd backend
python -m venv .venv
```

Activa el entorno virtual (en Linux/macOS con `source .venv/bin/activate` o en PowerShell con `.venv\Scripts\Activate.ps1`) y ejecuta:

```bash
pip install -r requirements-dev.txt
python -m app.db.initialize
uvicorn app.main:app --reload
```

Frontend (en otra terminal, desde la raíz del proyecto):

```bash
cd frontend
npm install
npm run dev
```

## API

FastAPI permite consultar y probar los endpoints desde `http://localhost:8000/docs`.

| Método | Ruta | Uso |
| --- | --- | --- |
| GET | `/api/dispositivos` | Listar dispositivos |
| GET | `/api/dispositivos/{identificador}` | Consultar un dispositivo |
| GET | `/api/tabla-simbolos` | Consultar la tabla de símbolos |
| POST | `/api/analizar` | Validar el código y obtener el AST |
| POST | `/api/compilar` | Generar código intermedio |
| POST | `/api/ejecutar` | Ejecutar instrucciones |
| GET | `/api/historial` | Consultar operaciones |
| GET | `/api/notificaciones` | Consultar notificaciones |

Ejemplo para `POST /api/ejecutar`:

```json
{
  "codigo": "ENCENDER led1\nCONSULTAR led1",
  "optimizar": true
}
```

## Pruebas

Las pruebas del backend se ejecutan con:

```bash
cd backend
python -m pytest -q
```

Para comprobar la compilación del frontend:

```bash
cd frontend
npm run build
```

El repositorio incluye un flujo de GitHub Actions para ejecutar las pruebas, compilar el frontend y validar la configuración de Docker Compose en cambios a `main` y `develop`.

## Correo y notificaciones

En desarrollo, `MAIL_PROVIDER=mailpit` envía el correo al buzón de pruebas en `http://localhost:8025`.

Para solicitar envíos externos se puede configurar `MAIL_PROVIDER=resend`, `RESEND_API_KEY` y `RESEND_FROM_EMAIL` en el archivo `.env` del servidor. El dominio del remitente debe estar verificado. Que Resend acepte una solicitud no garantiza que el correo llegue a la bandeja de entrada.

Las notificaciones Web Push requieren permiso del navegador. Se pueden activar o desactivar desde la aplicación.

- [Configuración de Resend](docs/correo-resend.md)
- [Notificaciones Web Push](docs/notificaciones-push.md)

**Aviso:** la aplicación pública no cuenta con inicio de sesión. No se deben utilizar sus comandos de correo y notificaciones para información privada o envíos masivos. Para un uso abierto más amplio hacen falta autenticación y límites de uso.

## Despliegue en el VPS

El proyecto cuenta con un script para actualizar la instalación en el servidor Ubuntu. Desde la carpeta del repositorio:

```bash
git pull --ff-only origin main
bash deploy/actualizar-vps.sh
```

El script reconstruye los servicios, compila el frontend y publica los archivos estáticos sin borrar el volumen de PostgreSQL. La configuración de HTTPS y el servidor web se explica en [despliegue-vps.md](docs/despliegue-vps.md).

## Documentación

- [Diseño del lenguaje](docs/diseno-lenguaje-smarthome.pdf)
- [Arquitectura](docs/arquitectura.md)
- [Analizador léxico](docs/analisis-lexico.md)
- [Parser y AST](docs/parser-y-ast.md)
- [PostgreSQL y tabla de símbolos](docs/postgresql-y-simbolos.md)
- [Análisis semántico](docs/analisis-semantico.md)
- [Código intermedio](docs/codigo-intermedio.md)
- [Optimizaciones](docs/optimizaciones.md)
- [Integración de la aplicación](docs/integracion-web.md)
- [Configuración inicial del repositorio](docs/configuracion-repositorio.md)
- [Roles del equipo](docs/roles-equipo.md)
- [Kanban](docs/kanban.md)

## Equipo

Proyecto desarrollado para Lenguajes y Autómatas II, grupo **7SA**, Instituto Tecnológico de Oaxaca.

| Integrante | Rol | Responsabilidades |
| --- | --- | --- |
| Angel Jahir Gomez Roblero | Líder técnico y DevOps | Arquitectura, integración del sistema, Docker, pruebas y seguimiento del proyecto |
| Antonio Contreras Alan | Desarrollador backend | API con FastAPI, PostgreSQL, servicios y ejecución de instrucciones |
| Aparicio Ingrid | Desarrolladora frontend | Consola de instrucciones, panel de dispositivos e interfaz en React |
| Gandarillas Melissa | Desarrolladora de lenguaje | Analizador léxico, parser, gramática y AST |
| López Herrera Noel | Desarrollador semántico | Tabla de símbolos, validaciones, código intermedio y optimizaciones |

La distribución agrupa algunas funciones porque el equipo está formado por cinco integrantes.
