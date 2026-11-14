# Distribucion de responsabilidades (6 integrantes)

| Rol | Responsabilidad | Entregable verificable |
|---|---|---|
| Lider tecnico | Arquitectura, repo, CI, integracion y seguimiento | PRs revisados, README, tablero |
| Frontend | React, consola, panel, estados, errores, historial | Pantallas y pruebas de integracion |
| Backend/API | FastAPI, PostgreSQL, servicios SMTP | Endpoints y persistencia |
| Lenguaje | Lexer, parser, AST, gramática y errores | Modulos e implementacion de tests |
| Semantica | Tabla de simbolos, tipos, validaciones y generacion de IR | Pruebas semanticas e IR |
| Ejecucion/DevOps | Optimizador, ejecutor, Docker y pruebas | Pruebas de equivalencia y contenedores |

Si son 5 integrantes, combinar **lider tecnico + backend**, manteniendo las contribuciones
individuales en git. Asignar nombres reales en el tablero cuando el equipo lo decida.

## Regla de colaboracion

- Trabajar en `feature/...`; abrir PR contra `develop`.
- Un compañero revisa el PR; no subir cambios a `main` directamente.
- Integrar `develop` a `main` solo cuando se pruebe una entrega.
- Cada tarjeta tiene responsable, descripcion y criterios de aceptacion.
