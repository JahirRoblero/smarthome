"""Pruebas de Web Push, sin enviar mensajes ni conectarse a PostgreSQL."""
import base64
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import push as rutas_push
from app.core import push_notifications as push


def test_clave_vapid_se_crea_una_sola_vez(tmp_path, monkeypatch):
    ruta = tmp_path / "secrets" / "vapid_private.pem"
    monkeypatch.setattr(push, "VAPID_KEY_PATH", ruta)
    primera = push.clave_publica_vapid()
    contenido = ruta.read_bytes()
    segunda = push.clave_publica_vapid()

    assert primera == segunda
    assert ruta.read_bytes() == contenido
    assert len(base64.urlsafe_b64decode(primera + "=")) == 65
    assert b"PRIVATE KEY" in contenido


def test_solo_proveedores_push_autorizados():
    assert push.validar_endpoint("https://fcm.googleapis.com/fcm/send/prueba")
    assert push.validar_endpoint("https://fcmregistrations.googleapis.com/v1/prueba")
    assert push.validar_endpoint("https://updates.push.services.mozilla.com/wpush/v2/prueba")
    assert push.validar_endpoint("https://web.push.apple.com/Qabc")
    for endpoint in (
        "http://fcm.googleapis.com/privado",
        "https://localhost/servicio",
        "https://127.0.0.1/servicio",
        "https://fcm.googleapis.com.malicioso.com/fcm/send/x",
        "https://usuario@fcm.googleapis.com/servicio",
        "https://fcm.googleapis.com:8080/servicio",
        "https://fcm.googleapis.com/",
    ):
        assert not push.validar_endpoint(endpoint)


def test_api_publica_clave_y_suscripcion(monkeypatch):
    guardadas = []
    quitadas = []
    monkeypatch.setattr(rutas_push, "clave_publica_vapid", lambda: "clave-falsa")
    monkeypatch.setattr(rutas_push, "registrar_suscripcion",
                        lambda endpoint, p256dh, auth: guardadas.append((endpoint, p256dh, auth)))
    monkeypatch.setattr(rutas_push, "quitar_suscripcion", quitadas.append)
    cliente = TestClient(app)
    assert cliente.get("/api/push/clave-publica").json()["publicKey"] == "clave-falsa"
    sub = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/ejemplo",
        "keys": {"p256dh": "clave-publica-ejemplo", "auth": "autenticacion-1234"},
    }
    assert cliente.post("/api/push/suscribir", json=sub).status_code == 200
    assert guardadas == [(sub["endpoint"], sub["keys"]["p256dh"], sub["keys"]["auth"])]
    assert cliente.post("/api/push/suscribir", json={**sub, "endpoint": "https://localhost/secret"}).status_code == 422
    assert cliente.post("/api/push/cancelar", json={"endpoint": sub["endpoint"]}).status_code == 200
    assert quitadas == [sub["endpoint"]]


class ConexionFalsa:
    def __init__(self):
        self.consultas = []
        self.resultado = []
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def cursor(self):
        return self
    def execute(self, sql, params=None):
        self.consultas.append((sql, params))
        self.resultado = (
            [(11, "Alerta real")]
            if "FROM notificaciones" in sql
            else [("https://fcm.googleapis.com/fcm/send/xyz", "p256dh", "auth")]
        )
    def fetchall(self):
        return self.resultado


def test_notificacion_push_envia_payload_tras_commit(monkeypatch, tmp_path):
    enviadas = []
    base = ConexionFalsa()
    monkeypatch.setattr(push, "abrir_conexion", lambda: base)
    monkeypatch.setattr(push, "asegurar_clave_vapid", lambda: Path("vapid_privada.pem"))
    monkeypatch.setattr(push, "webpush", lambda **kwargs: enviadas.append(kwargs))
    push.enviar_notificaciones_push([11])
    assert len(enviadas) == 1
    assert "Alerta real" in enviadas[0]["data"]
    assert enviadas[0]["vapid_claims"]["sub"].startswith("mailto:")
