# GitHub: preparacion manual inicial

El archivo ZIP contiene el repositorio de trabajo. En GitHub cree un repositorio **privado**
llamado `smarthome` bajo su cuenta. **No seleccione** crear README, .gitignore ni licencia
porque el paquete ya los incluye.

Desde la carpeta extraida en Windows PowerShell:

```powershell
git init -b main
git add .
git commit -m "chore: iniciar arquitectura SmartHome"
git remote add origin https://github.com/JahirRoblero/smarthome.git
git push -u origin main
git switch -c develop
git push -u origin develop
```

Cuenta GitHub conectada: `JahirRoblero`. Si el repositorio se crea bajo otra cuenta, cambie la URL. Para trabajo del equipo:

```powershell
git switch develop
git switch -c feature/lexer
git push -u origin feature/lexer
```

Crear ramas de trabajo segun cada necesidad: `feature/parser-ast`,
`feature/semantic`, `feature/intermediate`, `feature/executor`,
`feature/frontend`, `feature/postgres`, `feature/mailpit`, `feature/docker`.
No es necesario crear todas las ramas antes de comenzar a usarlas.

## Tablero Kanban

1. En GitHub: **Projects → New project → Board**.
2. Nombrar: **SmartHome - Proyecto integrador**.
3. Columnas: `Backlog`, `Por hacer`, `En progreso`, `En revision`, `Terminado`.
4. Abrir `docs/kanban.csv` e incorporar cada tarea como issue al repositorio.
5. Agregar issues al proyecto, asignar responsables y mover estados.

> La carga automatica de issues/tablero no viene activada en este repositorio local;
> el CSV es una plantilla de trabajo, no un tablero online ya creado.

## Proteccion recomendada

En Settings > Branches (o Rulesets), solicitar PR y CI antes de fusionar en `main`.
Esto depende de la configuracion y permisos de GitHub del repositorio.
