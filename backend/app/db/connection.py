"""Comprobacion de PostgreSQL; modelos y tablas se agregaran en otra etapa."""
from app.core.config import DATABASE_URL


def database_is_available() -> bool:
    try:
        import psycopg
    except ImportError:
        return False

    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=2) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)
    except (psycopg.Error, OSError):
        return False
