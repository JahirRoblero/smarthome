"""Crear esquema y sembrar dispositivos sin sobrescribir cambios persistidos.

Se ejecuta explícitamente con: python -m app.db.initialize
Docker Compose lo ejecuta antes de arrancar la API.
"""

from pathlib import Path

from .connection import abrir_conexion


ESQUEMA_SQL = Path(__file__).with_name("schema.sql")


def inicializar_base_de_datos() -> None:
    sql = ESQUEMA_SQL.read_text(encoding="utf-8")
    with abrir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(sql)
    # psycopg realiza commit al salir del contexto sin error.


def main() -> None:
    inicializar_base_de_datos()
    print("Esquema SmartHome preparado: dispositivos, historial y notificaciones.")


if __name__ == "__main__":
    main()
