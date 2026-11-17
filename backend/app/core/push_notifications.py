"""Notificaciones Web Push (VAPID): claves privadas persistentes y entrega opt-in.

Una suscripción corresponde a un navegador que aceptó expresamente recibir
notificaciones. No se requiere una cuenta ni se envían claves al frontend.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pywebpush import WebPushException, webpush

from app.db.connection import abrir_conexion

logger = logging.getLogger(__name__)
VAPID_KEY_PATH = Path(os.getenv("VAPID_PRIVATE_KEY_PATH", "/app/.secrets/vapid_private.pem"))
VAPID_SUBJECT = "mailto:notificaciones@smarthome.votaya.com.mx"

# La API de suscripción es pública. Restringir destinos evita usar el VPS
# para realizar peticiones arbitrarias a la red interna (SSRF).
SERVIDORES_PUSH_PERMITIDOS = frozenset({
    "fcm.googleapis.com",
    "fcmregistrations.googleapis.com",
    "updates.push.services.mozilla.com",
    "push.services.mozilla.com",
    "web.push.apple.com",
})


def validar_endpoint(endpoint: str) -> bool:
    try:
        url = urlsplit(endpoint)
    except ValueError:
        return False
    return (
        url.scheme == "https"
        and url.hostname in SERVIDORES_PUSH_PERMITIDOS
        and url.port in (None, 443)
        and not url.username
        and not url.password
        and bool(url.path and url.path != "/")
    )


def asegurar_clave_vapid() -> Path:
    """Crear una vez; la carpeta se monta en un volumen persistente privado."""
    ruta = VAPID_KEY_PATH
    ruta.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not ruta.exists():
        privada = ec.generate_private_key(ec.SECP256R1())
        contenido = privada.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
        try:
            descriptor = os.open(str(ruta), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "wb") as archivo:
                archivo.write(contenido)
    # Validar el archivo antes de publicar una clave para la suscripción.
    leer_clave_vapid()
    return ruta


def leer_clave_vapid():
    privada = serialization.load_pem_private_key(VAPID_KEY_PATH.read_bytes(), password=None)
    if not isinstance(privada, ec.EllipticCurvePrivateKey) or not isinstance(privada.curve, ec.SECP256R1):
        raise ValueError("La clave VAPID debe ser ECDSA P-256.")
    return privada


def clave_publica_vapid() -> str:
    asegurar_clave_vapid()
    publica = leer_clave_vapid().public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    return base64.urlsafe_b64encode(publica).rstrip(b"=").decode("ascii")


def registrar_suscripcion(endpoint: str, p256dh: str, auth: str) -> None:
    if not validar_endpoint(endpoint):
        raise ValueError("El proveedor de notificaciones no es compatible.")
    with abrir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "INSERT INTO push_suscripciones (endpoint, p256dh, auth) "
                "VALUES (%s, %s, %s) "
                "ON CONFLICT (endpoint) DO UPDATE SET "
                "p256dh = EXCLUDED.p256dh, auth = EXCLUDED.auth, "
                "actualizado_en = CURRENT_TIMESTAMP",
                (endpoint, p256dh, auth),
            )


def quitar_suscripcion(endpoint: str) -> None:
    with abrir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("DELETE FROM push_suscripciones WHERE endpoint = %s", (endpoint,))


def enviar_notificaciones_push(ids: list[int]) -> None:
    """Enviar tras el commit de ejecución; los fallos no revierten el programa."""
    if not ids:
        return
    try:
        asegurar_clave_vapid()
        with abrir_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT id, mensaje FROM notificaciones WHERE id = ANY(%s) ORDER BY id",
                    (ids,),
                )
                notificaciones = cursor.fetchall()
                cursor.execute("SELECT endpoint, p256dh, auth FROM push_suscripciones")
                suscripciones = cursor.fetchall()
    except Exception:
        logger.exception("No se pudieron preparar las notificaciones Web Push")
        return

    caducadas: set[str] = set()
    for id_, mensaje in notificaciones:
        payload = json.dumps({"id": id_, "mensaje": mensaje}, ensure_ascii=False)
        for endpoint, p256dh, auth in suscripciones:
            if endpoint in caducadas:
                continue
            if not validar_endpoint(endpoint):
                caducadas.add(endpoint)
                continue
            try:
                webpush(
                    subscription_info={
                        "endpoint": endpoint,
                        "keys": {"p256dh": p256dh, "auth": auth},
                    },
                    data=payload,
                    vapid_private_key=str(VAPID_KEY_PATH),
                    vapid_claims={"sub": VAPID_SUBJECT},
                    ttl=3600,
                    timeout=8,
                )
            except WebPushException as error:
                if error.status_code in (404, 410):
                    caducadas.add(endpoint)
                else:
                    logger.warning("Proveedor Web Push rechazó el envío (HTTP %s)", error.status_code)
            except Exception:
                logger.exception("Error de conexión al enviar notificación Web Push")

    for endpoint in caducadas:
        try:
            quitar_suscripcion(endpoint)
        except Exception:
            logger.exception("No se pudo retirar una suscripción caducada")


if __name__ == "__main__":
    asegurar_clave_vapid()
    print("Clave VAPID disponible en el volumen privado (no se muestra su contenido).")
