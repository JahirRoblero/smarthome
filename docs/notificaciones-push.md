# Notificaciones Web Push

La instrucción `NOTIFICAR "mensaje"` ahora hace dos cosas:

1. Guarda el mensaje en la tabla `notificaciones` de PostgreSQL (igual que antes).
2. Después de confirmar la transacción, intenta enviarlo a los navegadores que se hayan suscrito voluntariamente a Web Push.

**No cambia la gramática de SmartHome Script.** `ENVIAR CORREO` sigue usando Resend de forma independiente.

## Despliegue (VPS Ubuntu)

Desde `/home/ubuntu/smarthome`:

```bash
git pull --ff-only origin main
sudo bash deploy/actualizar-vps.sh
```

El arranque del backend crea la tabla `push_suscripciones` con `CREATE TABLE IF NOT EXISTS` y genera automáticamente una clave privada VAPID en el volumen Docker `push_secrets`. La **clave privada jamás se incluye en GitHub ni en el frontend**. La clave pública se obtiene desde `GET /api/push/clave-publica`.

No borres el volumen `push_secrets`: las suscripciones existentes dependen de que se conserve la misma clave VAPID. **No uses `docker compose down -v`** si quieres conservar tanto PostgreSQL como las suscripciones.

Verificación rápida:

```bash
curl -sS https://smarthome.votaya.com.mx/api/push/clave-publica
sudo docker compose ps
```

La respuesta JSON debe contener `publicKey`, con una clave pública base64url.

## Uso desde el navegador

1. Abre **https://smarthome.votaya.com.mx** (HTTPS obligatorio, salvo localhost).
2. Baja al panel **Notificaciones** y pulsa **Activar avisos**.
3. Acepta el permiso solicitado por el navegador.
4. Ejecuta en SmartHome la instrucción:

   ```text
   NOTIFICAR "Prueba de notificación real"
   ```

5. Debe aparecer un aviso del sistema operativo. Puedes cerrar la pestaña y repetir la prueba desde otro navegador o equipo que tenga SmartHome abierto.

Para cancelar la recepción en ese navegador, pulsa **Desactivar avisos**.

## Consideraciones

- No se solicitan permisos automáticamente: cada usuario debe pulsar **Activar avisos**.
- La entrega de Web Push depende del navegador, el sistema operativo, su configuración de notificaciones y la conectividad del dispositivo. Puede haber retrasos y no se garantiza la entrega inmediata.
- En iOS/iPadOS, para Web Push normalmente se necesita añadir la aplicación web a la pantalla de inicio y activar sus notificaciones desde allí.
- El navegador puede mostrar avisos aunque la pestaña esté cerrada; la disponibilidad con el navegador totalmente cerrado depende de su sistema operativo.
- Si el navegador responde `NotAllowedError`, revisa los permisos del sitio. Si responde `NotSupportedError`, el dispositivo/navegador no admite esa modalidad.
- Si no llega una notificación, comprueba `sudo docker compose logs --tail=80 backend`, permisos del navegador y configuración de avisos del sistema.
- Los endpoints de suscripción aceptan solo proveedores Web Push conocidos para impedir que la API pública se use para acceder a servidores internos (SSRF).
- Como SmartHome no usa autenticación, **cualquier visitante puede ejecutar NOTIFICAR** y el mensaje se envía a los navegadores que hayan optado por recibir avisos. No utilizar para avisos privados, críticos o confidenciales sin implementar primero autenticación y autorización.
