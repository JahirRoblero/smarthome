# Etapa 5 — PostgreSQL y tabla de símbolos

## Objetivo
Guardar los cinco dispositivos de SmartHome en PostgreSQL y construir una tabla de símbolos en memoria. Todavía no se ejecutan comandos ni se envían correos.

## Tablas
- dispositivos: identificador (PK), tipo, estado, actualizado_en
- historial: id (PK), instruccion, resultado, estado_ejecucion, fecha
- notificaciones: id (PK), mensaje, fecha

El archivo backend/app/db/schema.sql contiene el esquema, restricciones CHECK para impedir estados incompatibles y los cinco registros iniciales: led1 (LED/APAGADO), luz_sala (LUZ/APAGADO), ventilador1 (VENTILADOR/APAGADO), alarma1 (ALARMA/DESACTIVADA) y puerta_principal (PUERTA/CERRADA).

La inicialización es idempotente: ON CONFLICT DO NOTHING conserva estados registrados. Docker Compose utiliza el volumen postgres_data; no utilizar docker compose down -v para apagar el sistema si necesitas conservar los datos.

## Ejecutar con Docker
1. Copiar .env.example como .env, si no existe.
2. Desde la raíz, ejecutar: docker compose up --build
3. El backend inicializa automáticamente las tablas antes de arrancar Uvicorn.
4. Consultar:
   - http://localhost:8000/api/health
   - http://localhost:8000/api/dispositivos
   - http://localhost:8000/api/dispositivos/led1
   - http://localhost:8000/api/tabla-simbolos
   - http://localhost:8000/docs

Si el puerto 5432 está ocupado, cambiar POSTGRES_PORT en .env. La conexión interna del backend sigue apuntando a postgres:5432.

## Ejecutar sin Docker
Crear primero la base PostgreSQL y configurar DATABASE_URL. Desde backend ejecutar:
1. python -m pip install -r requirements-dev.txt
2. python -m app.db.initialize
3. uvicorn app.main:app --reload

## Demostrar la persistencia
Con Docker Compose levantado:
1. Consultar http://localhost:8000/api/dispositivos/led1 (debería estar APAGADO).
2. Modificar temporalmente el estado directamente en la base usando psql:
   docker compose exec postgres psql -U smarthome -d smarthome -c "UPDATE dispositivos SET estado='ENCENDIDO', actualizado_en=NOW() WHERE identificador='led1';"
3. Reiniciar solo el backend: docker compose restart backend
4. Volver a consultar /api/dispositivos/led1: debe seguir ENCENDIDO.
5. Restaurar el estado si se desea:
   docker compose exec postgres psql -U smarthome -d smarthome -c "UPDATE dispositivos SET estado='APAGADO', actualizado_en=NOW() WHERE identificador='led1';"

Si modificaste usuario o base en .env, ajusta los argumentos de psql.

## Tabla de símbolos
backend/app/interpreter/symbols.py convierte los registros de PostgreSQL en símbolos con identificador, tipo, estado, estados_permitidos y operaciones_permitidas. Las reglas viven en Python; no se necesita una cuarta tabla SQL.

La tabla se reconstruye desde PostgreSQL en cada consulta para reflejar el estado persistido. En la próxima etapa el analizador semántico la utilizará para validar existencia y operaciones compatibles.

## Pruebas y alcance
- Ejecutar desde backend: python -m pytest -q
- Las pruebas unitarias usan conexiones simuladas. No reemplazan la verificación manual de persistencia con PostgreSQL real.
- La API en esta etapa es de solo lectura. La función interna actualizar_estado se reserva para el motor de ejecución posterior.
- historial y notificaciones están preparados, pero el intérprete aún no los utiliza.
- Lexer, Parser y AST anteriores permanecen intactos.
