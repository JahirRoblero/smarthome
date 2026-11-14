import { useEffect, useState } from "react";

type Health = {
  service: string;
  status: "ok" | "degraded";
  database: "connected" | "disconnected";
  smtp: { host: string; port: number; status: string };
};

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/health", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok)
          throw new Error(`La API respondió con ${response.status}`);
        return (await response.json()) as Health;
      })
      .then(setHealth)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(String(reason));
      });
    return () => controller.abort();
  }, []);

  return (
    <main className="layout">
      <header>
        <div className="logo">⌂</div>
        <div>
          <p className="overline">Lenguajes y Autómatas II</p>
          <h1>SmartHome</h1>
        </div>
      </header>
      <section className="hero">
        <span className="tag">Etapa 2 · Arquitectura</span>
        <h2>La infraestructura está preparada.</h2>
        <p>
          Esta pantalla verifica la comunicación entre React y FastAPI. La
          consola, los dispositivos simulados y el intérprete se implementarán
          en las siguientes etapas.
        </p>
      </section>
      <section className="status-grid" aria-label="Estado de servicios">
        <article className="status">
          <span>Backend FastAPI</span>
          <strong>
            {error ? "Sin conexión" : health ? "Conectado" : "Comprobando…"}
          </strong>
        </article>
        <article className="status">
          <span>PostgreSQL</span>
          <strong>
            {health
              ? health.database === "connected"
                ? "Conectado"
                : "No disponible"
              : "Pendiente"}
          </strong>
        </article>
        <article className="status">
          <span>Mailpit SMTP</span>
          <strong>{health ? "Configurado (sin probar)" : "Pendiente"}</strong>
        </article>
      </section>
      {error && <p className="error">No se pudo consultar la API: {error}</p>}
      <footer>
        <span>Diseño del lenguaje v1.0</span>
        <span>Python + FastAPI · React + TypeScript · PostgreSQL</span>
      </footer>
    </main>
  );
}
