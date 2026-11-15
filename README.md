# SmartHome Script · Proyecto integrador

Aplicacion web de **Lenguajes y Automatas II** para interpretar instrucciones
sobre dispositivos simulados. Tecnologias: **React + TypeScript**,
**Python + FastAPI**, **PostgreSQL** y **Mailpit**, orquestadas con Docker Compose.

> **Estado actual: ETAPA 6 — Análisis semántico implementado.** Lexer,
> Parser, AST, PostgreSQL, tabla de símbolos y semántica están preparados.
> La API POST /api/analizar comprueba comandos y devuelve el AST sin ejecutarlos.
> **IR, optimizador y ejecución quedan pendientes.**

## Estructura

```text
smarthome/
├── frontend/                 React + TypeScript + Vite
├── backend/                  FastAPI, pruebas y lexer implementado
├── docs/                     Especificacion PDF, arquitectura, tablero, roles
├── .github/                  CI, plantilla de PR e issues
├── compose.yaml              React + FastAPI + PostgreSQL + Mailpit
└── .env.example              Variables de entorno de desarrollo
```

## Requisitos

- Docker Desktop con Compose, **o** Python 3.12+, Node.js 22+, PostgreSQL 17 local.
- Git para publicar y colaborar.

## Inicio rapido con Docker (recomendado)

1. Copiar variables: `cp .env.example .env` (Linux/macOS) o `Copy-Item .env.example .env` (PowerShell).
2. Iniciar en la raiz: `docker compose up --build`.
3. Verificar enlaces:

| Servicio | Direccion |
|---|---|
| Interfaz React | http://localhost:5173 |
| API / Docs | http://localhost:8000/docs |
| Ping backend | http://localhost:8000/api/ping |
| Estado de servicios | http://localhost:8000/api/health |
| Mailpit (buzon) | http://localhost:8025 |
| PostgreSQL | localhost:5432 (desarrollo) |

Detener: `docker compose down` (conserva BD); **no** usar `down -v` salvo que
quiera borrar la base local. Si los puertos estan ocupados, cambie `.env`.

## Ejecucion SIN Docker (desarrollo local)

Usar PostgreSQL local y crear usuario/base de datos definidos en `backend/app/core/config.py`,
o establecer `DATABASE_URL` en el entorno. No es obligatorio tener Mailpit para mostrar
la pagina; su conectividad SMTP se comprobara en una etapa posterior.

Terminal 1 (backend):

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Terminal 2 (frontend):

```bash
cd frontend
npm install
npm run dev
```

La interfaz de Vite usa proxy `/api` a `http://127.0.0.1:8000` por defecto.
En Docker se configura el proxy hacia el servicio `backend`.

## Pruebas (etapa 3)

```bash
cd backend
pytest -q
```

```bash
cd frontend
npm run build
```

GitHub Actions ejecuta ambas validaciones automaticamente al hacer push/PR a
`main` y `develop`.

### Demostrar el lexer (sin levantar Docker)

```bash
cd backend
python -m app.interpreter.lexer --texto "ENCENDER led1"
python -m app.interpreter.lexer --texto "ENCENDER led1@"
python -m pytest -q tests/test_lexer.py
```

Se muestran tokens y errores en JSON. El comando devuelve código de salida 1
ante un error léxico, como debe ser. `parser.py` ya genera el AST sin ejecutar operaciones.

### Preparar PostgreSQL y mostrar los dispositivos

Con Docker Compose el backend ejecuta la inicialización automáticamente:

```bash
docker compose up --build
```

Sin Docker, con PostgreSQL local preparado:

```bash
cd backend
python -m app.db.initialize
uvicorn app.main:app --reload
```

Rutas: `/api/dispositivos`, `/api/dispositivos/{identificador}` y
`/api/tabla-simbolos`. Se puede revisar la persistencia siguiendo
`docs/ETAPA_5_POSTGRES_SIMBOLOS.md`.

## Análisis semántico (Etapa 6)

Desde Bruno enviar **POST** a `http://localhost:8000/api/analizar` con Body JSON:

```json
{"codigo":"ENCENDER led1\nCONSULTAR led1"}
```

La API responde con AST validado o con errores LEXICO, SINTACTICO o SEMANTICO
ubicados por línea y columna. Este análisis **no cambia estados ni envía correos**.

## Documentacion y plan de desarrollo

- [Diseno formal del lenguaje](docs/Diseno_lenguaje_SmartHome.pdf)
- [Etapa 6: Análisis semántico](docs/ETAPA_6_ANALISIS_SEMANTICO.md)
- [Etapa 5: PostgreSQL y tabla de símbolos](docs/ETAPA_5_POSTGRES_SIMBOLOS.md)
- [Etapa 4: Parser y AST](docs/ETAPA_4_PARSER_AST.md)
- [Etapa 3: Lexer, ejemplos y pruebas](docs/ETAPA_3_LEXER.md)
- [Arquitectura y limites](docs/arquitectura.md)
- [Roles del equipo](docs/roles-equipo.md)
- [Tareas Kanban](docs/kanban.csv)
- [Guia de la etapa 2 (Windows/PowerShell)](docs/GUIA_ETAPA_2.md)
- [Publicacion inicial en GitHub](docs/github-proyecto.md)

## Seguridad y limites

- `.env` esta ignorado por Git. El archivo `.env.example` tiene credenciales de **desarrollo**, no de produccion.
- Nunca use Mailpit para enviar correos reales ni exponga este compose local a Internet.
- No implementa autenticacion, sensores fisicos ni variables de usuario.
