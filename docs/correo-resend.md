# Envío de correo con Resend

El comando del lenguaje **no cambia**:

    ENVIAR CORREO A "tu-cuenta@gmail.com" MENSAJE "Hola desde SmartHome"

## 1. Verificar el dominio en Resend

1. Abre https://resend.com/domains y revisa **smarthome.votaya.com.mx**.
2. Añade en el panel DNS de GoDaddy los registros exactos que Resend muestre (DKIM y los registros de sending/SPF).
3. No copies solamente los nombres ni inventes valores. GoDaddy puede mostrar la zona votaya.com.mx y los nombres DNS serán relativos a esa zona.
4. Espera a que Resend indique **Verified** o que **Sending** esté verificado. Si todavía muestra **Pending**, revisa los registros.
5. En https://resend.com/api-keys crea una clave con permiso de envío. **No la publiques en GitHub, en React ni en capturas.** Si se expuso, revócala y crea otra.

El remitente predeterminado será notificaciones@smarthome.votaya.com.mx.
No requiere que exista una bandeja Gmail con esa dirección, pero el dominio de envío debe estar verificado.

## 2. Configuración local de Docker

En la **raíz** del repositorio, copia .env.example a .env si todavía no existe. No borres ni sobrescribas los valores de PostgreSQL que ya tengas.

Agrega o cambia estas variables en .env:

    MAIL_PROVIDER=resend
    RESEND_API_KEY=re_TU_CLAVE_PRIVADA_REAL
    RESEND_FROM_EMAIL=notificaciones@smarthome.votaya.com.mx

* Cambia la clave de ejemplo por tu API key real.
* Se permiten destinatarios de cualquier proveedor (Gmail, Outlook, Yahoo, etc.) con un formato de correo válido. **Advertencia:** como la API pública no tiene autenticación ni límites de solicitudes, podría ser utilizada por terceros para enviar mensajes desde tu cuenta de Resend.
* El archivo .env está ignorado por Git. Código, pruebas y plantillas no contienen claves reales.
* La clave **solo** se utiliza en el backend Python; nunca uses VITE_RESEND_API_KEY.

Recrea el contenedor del backend para que reciba las nuevas variables (no afecta el volumen PostgreSQL):

    docker compose up -d --no-deps --force-recreate backend

Si el contenedor no estaba construido:

    docker compose up -d --build backend

No necesitas reconstruir React.

## 3. Prueba en SmartHome

Abre http://localhost:5173, entra en la consola y escribe:

    ENVIAR CORREO A "tu-cuenta@gmail.com" MENSAJE "Hola desde SmartHome"

El destinatario puede ser **cualquier correo válido**; no necesita estar registrado en el archivo .env.

Si Resend acepta el envío, la respuesta dirá **Resend aceptó el correo dirigido a ...**. Esto confirma la aceptación de la solicitud por Resend, **no garantiza entrega en Gmail**. Revisa el panel de Resend para estado de entrega, rebotes o errores; revisa también spam/promociones en Gmail.

Si falta la API key, los DNS siguen pendientes o Resend rechaza el mensaje, el backend devuelve un error controlado y no afirma haber enviado el mensaje.

## 4. Mailpit (pruebas sin correo real)

Para volver a la simulación cambia esta variable de .env:

    MAIL_PROVIDER=mailpit

Recrea el backend:

    docker compose up -d --no-deps --force-recreate backend

Los mensajes se muestran en http://localhost:8025 y **no llegan a Gmail**.

## 5. Arquitectura y seguridad

- backend/app/core/mailer.py implementa los dos proveedores.
- backend/app/core/config.py obtiene los parámetros del entorno.
- backend/app/interpreter/executor.py interpreta ENVIAR CORREO desde el IR y llama al módulo de correo.
- La API HTTP, el Lexer, el Parser, la gramática, el AST, el IR y las optimizaciones siguen igual.
- Para Resend se usa HTTPS POST https://api.resend.com/emails con cabecera Authorization Bearer y from, to, subject, text.
- Una respuesta aceptada debe incluir id.
- Los envíos reales tienen efecto externo: un rollback posterior de PostgreSQL **no** puede retirar un mensaje ya aceptado por Resend.
- Actualmente /api/ejecutar es público y permite enviar correo a cualquier destinatario válido; esto supone un riesgo de abuso de la cuenta Resend, además de los límites que aplica el propio proveedor.

## 6. Pruebas automatizadas

Desde backend/:

    python -m pytest -q

test_mailer.py simula respuestas de Resend y SMTP: no envía correos reales ni necesita credenciales.
