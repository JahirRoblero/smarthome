/* Service Worker de SmartHome: Web Push real, incluso con la pestaña cerrada. */
self.addEventListener("push", (event) => {
  let datos = {};
  if (event.data) {
    try {
      datos = event.data.json();
    } catch {
      datos = { mensaje: event.data.text() };
    }
  }

  const mensaje = typeof datos.mensaje === "string" ? datos.mensaje : "Tienes una nueva notificación.";
  event.waitUntil(
    self.registration.showNotification("SmartHome", {
      body: mensaje,
      tag: `smarthome-${datos.id || Date.now()}`,
      data: { url: "/" },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(async (ventanas) => {
      const destino = new URL("/", self.location.origin).href;
      for (const ventana of ventanas) {
        if (ventana.url.startsWith(self.location.origin) && "focus" in ventana) {
          return ventana.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(destino);
      }
    }),
  );
});
