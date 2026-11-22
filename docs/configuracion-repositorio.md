# Preparación del repositorio

## Objetivo

Preparar un solo repositorio GitHub (monorepo) con frontend React, backend FastAPI, PostgreSQL y Mailpit como servicios separados. **No se implementa aún el intérprete**.

## 1. Crear repositorio en GitHub

1. En https://github.com/new seleccionar el propietario de la cuenta.
2. Nombre recomendado: `smarthome`.
3. Elegir **Private** durante el desarrollo; cambiar visibilidad solo si el equipo lo decide.
4. No inicializar con README, licencia ni .gitignore (ya están incluidos).
5. Crear el repositorio.

## 2. Publicar el proyecto (PowerShell)

Extraer `SmartHome_Etapa2_Arquitectura.zip` y abrir una terminal en la carpeta `SmartHome`:

```powershell
git init -b main
git add .
git commit -m "chore: iniciar arquitectura SmartHome"
git remote add origin https://github.com/JahirRoblero/smarthome.git
git push -u origin main
git switch -c develop
git push -u origin develop
```

> Si no se crea en la cuenta `JahirRoblero`, sustituir el usuario en la URL por el propietario real.
> Si git solicita identidad, configurar `user.name` y `user.email` con los datos de GitHub del desarrollador.

## 3. Crear tablero GitHub Projects

1. Abrir GitHub **Projects** y elegir **New project → Board**.
2. Título: `SmartHome - Proyecto integrador`.
3. Estados/columnas recomendados: `Backlog`, `Por hacer`, `En progreso`, `En revisión`, `Terminado`.
4. Abrir `docs/kanban.csv` para consultar las **28 tareas**.
5. Crear un issue por tarea, incluyendo el criterio de aceptación y el rol como responsable provisional.
6. Agregar issues al tablero y asignar a cada integrante cuando se conozcan los usuarios.

El CSV **no es un tablero publicado**; se entrega como lista de importación manual.

## 4. Preparar entorno (.env)

```powershell
Copy-Item .env.example .env
```

Los valores de `.env.example` se usan **solo en desarrollo local**. `.env` no se sube a GitHub.

## 5. Levantar los cuatro servicios (Docker Desktop)

```powershell
docker compose up --build
```

Enlaces: React `http://localhost:5173`, FastAPI `http://localhost:8000/docs`, Mailpit `http://localhost:8025`, estado `http://localhost:8000/api/health`.

Cuando esté funcionando, `/api/health` debe informar `"database": "connected"`. Mailpit tendrá estado `configured_not_tested`, porque el envío se integra más adelante.

Detener sin borrar datos:

```powershell
docker compose down
```

## 6. Comprobar las pruebas

Para las pruebas del backend, se utiliza el entorno de desarrollo con `requirements-dev.txt` (el contenedor de ejecucion no incluye Pytest). GitHub Actions ejecutara estos tests automaticamente una vez publicado el repositorio.

Pruebas locales en backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
pytest -q
```

Volver a la raíz y comprobar el frontend con `npm install` y `npm run build`.

## 7. Finalización de etapa

- Repositorio publicado y compartido con el equipo.
- Ramas `main` y `develop`; ramas `feature/...` según necesidad.
- CI ejecuta pruebas básicas y build del frontend al subir cambios.
- React y FastAPI se comunican; PostgreSQL conecta; Mailpit abre.
- 28 tareas registradas en GitHub Projects y asignadas.
- Especificación formal del lenguaje preservada en `docs/`.

## Lo siguiente

Etapa 3: construir `lexer.py`, emitir tokens y errores léxicos según la gramática v1.0.
