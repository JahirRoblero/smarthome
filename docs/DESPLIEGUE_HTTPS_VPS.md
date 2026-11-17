# HTTPS de SmartHome en VPS Ubuntu

Dominio final: https://smarthome.votaya.com.mx (sin :5173).

## Diseño

- React se compila con Vite a archivos estáticos en frontend/dist/.
- Nginx o Apache del HOST entrega esos archivos desde /var/www/smarthome/.
- /api/ se envía a FastAPI por http://127.0.0.1:8000/api/.
- Docker Compose publica sus puertos de desarrollo SOLO en 127.0.0.1.
- Certbot/Let's Encrypt habilita TLS y renovación. No se requiere certificado diferente para FastAPI: navegador HTTPS -> proxy -> HTTP local.
- No cambiar los registros DKIM/SPF de Resend al configurar el dominio web; son servicios distintos.
- SmartHome todavía no tiene login; los ejemplos de Nginx/Apache incluyen autenticación básica para no exponer el ejecutor ni Resend sin control.

**No instalar Nginx en un VPS donde Apache ya ocupa 80/443, ni al revés.** Los virtual hosts de diferentes dominios comparten 80/443 sin detener otros sitios.

## 1. Comprobar DNS y servidor actual

En el VPS, dentro del repositorio:

    git pull origin main
    getent ahostsv4 smarthome.votaya.com.mx | head -n 1
    sudo ss -lntp | grep -E ':(80|443)[[:space:]]' || true

Comprueba que la IP resuelta coincida con la IP pública DE ESTE VPS. Si no coincide, corrige el registro A de smarthome en la zona votaya.com.mx antes de pedir el certificado.

La salida de ss dirá si están ocupados los puertos por nginx o apache2.

El firewall de Ubuntu y el Security Group de AWS (si aplica) deben permitir TCP 80 y 443. No hace falta abrir 5173, 8000, 5432 o 8025 al exterior.

## 2. Actualizar SmartHome y crear el build

Desde la raíz del repositorio:

    sudo apt-get update
    sudo apt-get install -y rsync
    bash deploy/actualizar-vps.sh

Esto levanta backend/PostgreSQL/Mailpit con Docker, compila React mediante el contenedor de Vite, copia archivos a /var/www/smarthome/ y detiene el contenedor Vite. Los datos de PostgreSQL persisten; no se eliminan volúmenes.

Verifica el backend desde el mismo VPS:

    curl -i http://127.0.0.1:8000/api/health

La API ya no debe exponerse en la interfaz pública del VPS.

## 3A. Si el servidor existente es Nginx

No sustituyas ni borres los sitios de EcoRuta o VotaYa: añade solo el nuevo vhost.

    sudo apt-get install -y python3-certbot-nginx apache2-utils
    sudo htpasswd -c /etc/nginx/.smarthome-htpasswd smarthomeadmin
    sudo cp deploy/nginx/smarthome.conf /etc/nginx/sites-available/smarthome.votaya.com.mx
    sudo ln -s /etc/nginx/sites-available/smarthome.votaya.com.mx /etc/nginx/sites-enabled/smarthome.votaya.com.mx
    sudo nginx -t
    sudo systemctl reload nginx
    sudo certbot --nginx -d smarthome.votaya.com.mx --redirect

Crea una contraseña fuerte cuando htpasswd la solicite. El navegador pedirá ese usuario y contraseña antes de acceder a SmartHome; no son las credenciales del usuario Linux ni de PostgreSQL.

Si Nginx no está instalado y nadie escucha en 80/443, instala nginx antes de copiar la configuración:

    sudo apt-get install -y nginx

Si en el VPS ya corre Apache en esos puertos, usa 3B, NO instales Nginx para pelear por los mismos puertos.

## 3B. Si el servidor existente es Apache

Usa esta alternativa EN VEZ DE 3A:

    sudo apt-get install -y python3-certbot-apache apache2-utils
    sudo a2enmod proxy proxy_http rewrite headers ssl
    sudo htpasswd -c /etc/apache2/.smarthome-htpasswd smarthomeadmin
    sudo cp deploy/apache/smarthome.conf /etc/apache2/sites-available/smarthome.conf
    sudo a2ensite smarthome.conf
    sudo apachectl configtest
    sudo systemctl reload apache2
    sudo certbot --apache -d smarthome.votaya.com.mx --redirect

Si Apache no está instalado y no hay otro servidor en 80/443, puede instalarse con sudo apt-get install -y apache2. Pero si Nginx ya atiende esos puertos, usa 3A.

## 4. Verificar HTTPS

    curl -I https://smarthome.votaya.com.mx
    sudo certbot certificates
    sudo certbot renew --dry-run

Una respuesta 401 Unauthorized en la primera petición HTTPS es CORRECTA: el sitio requiere las credenciales de autenticación básica configuradas en 3A o 3B. El certificado debe ser válido; no debe aparecer error TLS.

Abre https://smarthome.votaya.com.mx y autentícate. Comprueba los dispositivos y ejecuta, por ejemplo, CONSULTAR led1.

Si Certbot falla, revisa DNS, puerto 80 público, el servidor que ocupa 80/443 y los logs de Nginx con:

    sudo journalctl -u nginx --no-pager -n 30

Para Apache, cambia nginx por apache2.

## 5. Actualizaciones posteriores

Después de cada push a GitHub:

    git pull --ff-only origin main
    bash deploy/actualizar-vps.sh

Esto construye la última versión de React y FastAPI, copia el frontend y conserva la configuración HTTPS existente en Nginx/Apache. No necesitas volver a pedir el certificado.

## 6. Seguridad

- Resend solo recibe su API key desde el .env del backend. Nunca en React ni en GitHub.
- Los hosts públicos deben exponer TCP 80/443 y SSH 22 según la política del VPS. Revisa además el firewall del proveedor.
- No publiques los puertos de PostgreSQL, Mailpit, FastAPI ni Vite. Docker Compose los liga a loopback y los contenedores se comunican internamente mediante la red Docker.
- La autenticación básica protege el sitio por HTTPS, pero no equivale a autenticación y roles dentro de SmartHome.
- Si se comparte usuario y contraseña, cualquiera con acceso podrá ejecutar comandos. Cambia las credenciales cuando dejen de necesitarse.
- Para correo real, configura MAIL_PROVIDER=resend, RESEND_API_KEY, RESEND_FROM_EMAIL y RESEND_ALLOWED_RECIPIENTS en .env local y recrea backend.
- El dominio web y la verificación del dominio de correo Resend son independientes.

Referencia Certbot: https://ubuntu.com/server/docs/how-to/security/obtain-tls-certificates/
