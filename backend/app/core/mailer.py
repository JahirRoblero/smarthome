"""Envío de correo por Mailpit (local) o Resend (real).

Este módulo es el único lugar donde se necesita la clave de Resend.
No registra credenciales ni expone respuestas internas del proveedor.
SmartHome permite enviar a cualquier destinatario cuyo correo sea válido.
"""

from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import config


class ErrorEnvioCorreo(RuntimeError):
    """Error controlado del proveedor, seguro para mostrar al cliente."""


def _mailpit(destinatario: str, mensaje: str) -> dict[str, str]:
    email = EmailMessage()
    email["From"] = "smarthome@localhost"
    email["To"] = destinatario
    email["Subject"] = "Notificación SmartHome"
    email.set_content(mensaje)
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=8) as cliente:
            cliente.send_message(email)
    except (smtplib.SMTPException, OSError) as error:
        raise ErrorEnvioCorreo("No se pudo enviar el correo al servidor SMTP de pruebas (Mailpit).") from error
    return {"proveedor": "mailpit"}


def _resend(destinatario: str, mensaje: str) -> dict[str, str]:
    if not config.RESEND_API_KEY:
        raise ErrorEnvioCorreo("Falta configurar RESEND_API_KEY en el backend.")
    if not config.RESEND_FROM_EMAIL:
        raise ErrorEnvioCorreo("Falta configurar RESEND_FROM_EMAIL en el backend.")

    datos = json.dumps(
        {
            "from": config.RESEND_FROM_EMAIL,
            "to": [destinatario],
            "subject": "Notificación SmartHome",
            "text": mensaje,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    solicitud = Request(
        "https://api.resend.com/emails",
        data=datos,
        headers={
            "Authorization": f"Bearer {config.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(solicitud, timeout=10) as respuesta:
            resultado = json.load(respuesta)
    except HTTPError as error:
        # Nunca incluir el cuerpo remoto, ya que puede contener datos sensibles.
        if error.code in (401, 403):
            descripcion = "Resend rechazó la autorización (HTTP %s). Revisa la API key y el dominio verificado." % error.code
        elif error.code in (400, 422):
            descripcion = "Resend rechazó el correo (HTTP %s). Comprueba el remitente y la verificación DNS." % error.code
        else:
            descripcion = "Resend no pudo aceptar el envío (HTTP %s)." % error.code
        raise ErrorEnvioCorreo(descripcion) from error
    except (URLError, TimeoutError, OSError) as error:
        raise ErrorEnvioCorreo("No fue posible conectarse a la API de Resend.") from error
    except (ValueError, TypeError) as error:
        raise ErrorEnvioCorreo("Resend devolvió una respuesta que no es JSON válido.") from error

    if not isinstance(resultado, dict) or not isinstance(resultado.get("id"), str):
        raise ErrorEnvioCorreo("Resend no confirmó la aceptación del correo.")
    return {"proveedor": "resend", "id": resultado["id"]}


def enviar_correo(destinatario: str, mensaje: str) -> dict[str, str]:
    """Solicita un envío; aceptado por Resend no garantiza entrega en bandeja."""
    proveedor = config.MAIL_PROVIDER.strip().lower()
    if proveedor == "mailpit":
        return _mailpit(destinatario, mensaje)
    if proveedor == "resend":
        return _resend(destinatario, mensaje)
    raise ErrorEnvioCorreo(
        "MAIL_PROVIDER debe ser 'mailpit' o 'resend'."
    )
