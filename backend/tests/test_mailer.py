"""Pruebas aisladas del proveedor Resend y del modo de prueba Mailpit."""

import io
import json
from urllib.error import HTTPError, URLError

import pytest

from app.core import config
from app.core import mailer


@pytest.fixture
def modo_resend(monkeypatch):
    monkeypatch.setattr(config, "MAIL_PROVIDER", "resend")
    monkeypatch.setattr(config, "RESEND_API_KEY", "re_clave_de_prueba_nunca_real")
    monkeypatch.setattr(config, "RESEND_FROM_EMAIL", "notificaciones@smarthome.votaya.com.mx")


def test_mailpit_por_defecto(monkeypatch):
    monkeypatch.setattr(config, "MAIL_PROVIDER", "mailpit")
    monkeypatch.setattr(config, "SMTP_HOST", "mailpit")
    monkeypatch.setattr(config, "SMTP_PORT", 1025)
    enviados = []

    class SmtpFalso:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("mailpit", 1025, 8)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def send_message(self, mensaje):
            enviados.append(mensaje)

    monkeypatch.setattr(mailer.smtplib, "SMTP", SmtpFalso)
    respuesta = mailer.enviar_correo("destino@gmail.com", "Hola")
    assert respuesta == {"proveedor": "mailpit"}
    assert enviados[0]["To"] == "destino@gmail.com"
    assert enviados[0].get_content().strip() == "Hola"


def test_resend_envia_json_por_https(modo_resend, monkeypatch):
    solicitudes = []

    class Respuesta:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, *_):
            return b'{"id":"email_123"}'

    def urlopen_falso(req, timeout):
        assert timeout == 10
        solicitudes.append(req)
        return Respuesta()

    monkeypatch.setattr(mailer, "urlopen", urlopen_falso)
    resultado = mailer.enviar_correo("destino@gmail.com", "Mensaje de prueba")
    assert resultado == {"proveedor": "resend", "id": "email_123"}
    req = solicitudes[0]
    assert req.full_url == "https://api.resend.com/emails"
    assert req.get_method() == "POST"
    assert req.get_header("Authorization") == "Bearer re_clave_de_prueba_nunca_real"
    datos = json.loads(req.data)
    assert datos == {
        "from": "notificaciones@smarthome.votaya.com.mx",
        "to": ["destino@gmail.com"],
        "subject": "Notificación SmartHome",
        "text": "Mensaje de prueba",
    }


def test_permite_cualquier_direccion_valida(modo_resend, monkeypatch):
    solicitudes = []

    class Respuesta:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self, *_): return b'{"id":"email_456"}'

    def enviar(req, timeout):
        solicitudes.append(json.loads(req.data))
        return Respuesta()

    monkeypatch.setattr(mailer, "urlopen", enviar)

    destinos = [
        "destino@gmail.com",
        "estudiante@outlook.com",
        "persona@yahoo.com",
        "contacto@universidad.edu.mx",
    ]
    for direccion in destinos:
        assert mailer.enviar_correo(direccion, "Hola")["id"] == "email_456"

    assert [solicitud["to"][0] for solicitud in solicitudes] == destinos


def test_falta_api_key(modo_resend, monkeypatch):
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    with pytest.raises(mailer.ErrorEnvioCorreo, match="RESEND_API_KEY"):
        mailer.enviar_correo("destino@gmail.com", "Hola")


def test_falta_remitente(modo_resend, monkeypatch):
    monkeypatch.setattr(config, "RESEND_FROM_EMAIL", "")
    with pytest.raises(mailer.ErrorEnvioCorreo, match="RESEND_FROM_EMAIL"):
        mailer.enviar_correo("destino@gmail.com", "Hola")


def test_resend_rechaza_dominio_y_no_filtra_secretos(modo_resend, monkeypatch):
    def falla(_req, timeout):
        raise HTTPError(
            "https://api.resend.com/emails",
            422, "Invalid sender secret-value", {}, io.BytesIO(b'{"message":"secret-value"}'),
        )
    monkeypatch.setattr(mailer, "urlopen", falla)
    with pytest.raises(mailer.ErrorEnvioCorreo, match="verificación DNS") as capturado:
        mailer.enviar_correo("destino@gmail.com", "Hola")
    assert "secret-value" not in str(capturado.value)


def test_resend_no_confirma_sin_id(modo_resend, monkeypatch):
    class Respuesta:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self, *_): return b'{"status":"ok"}'
    monkeypatch.setattr(mailer, "urlopen", lambda *_args, **_kwargs: Respuesta())
    with pytest.raises(mailer.ErrorEnvioCorreo, match="no confirmó"):
        mailer.enviar_correo("destino@gmail.com", "Hola")


def test_errores_de_red(modo_resend, monkeypatch):
    def falla(*_args, **_kwargs): raise URLError("network down")
    monkeypatch.setattr(mailer, "urlopen", falla)
    with pytest.raises(mailer.ErrorEnvioCorreo, match="conectarse"):
        mailer.enviar_correo("destino@gmail.com", "Hola")


def test_proveedor_desconocido(monkeypatch):
    monkeypatch.setattr(config, "MAIL_PROVIDER", "invalido")
    with pytest.raises(mailer.ErrorEnvioCorreo, match="MAIL_PROVIDER"):
        mailer.enviar_correo("destino@gmail.com", "Hola")
