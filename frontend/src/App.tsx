import { useCallback, useEffect, useState } from "react";

type Dispositivo = { identificador: string; tipo: string; estado: string; actualizado_en: string };
type Evento = { linea: number; operacion: string; estado: string; detalle: string };
type Historial = { id: number; instruccion: string; resultado: Evento | string | null; estado_ejecucion: string; fecha: string };
type Notificacion = { id: number; mensaje: string; fecha: string };
type Salud = { database: string };
type Respuesta = { correcto: boolean; resultados: Evento[]; dispositivos: Dispositivo[] };
type ErrorApi = { error?: { descripcion: string; linea?: number; columna?: number }; detail?: string };
const EJEMPLO = ['ENCENDER led1', 'SI led1 == ENCENDIDO ENTONCES NOTIFICAR "Luz encendida"', 'CONSULTAR led1', 'LISTAR DISPOSITIVOS'].join("\n");
const iconos: Record<string, string> = { LED: "◉", LUZ: "✳", VENTILADOR: "✺", ALARMA: "◇", PUERTA: "▣" };
const nombres: Record<string, string> = { led1: "LED de prueba", luz_sala: "Luz de sala", ventilador1: "Ventilador", alarma1: "Alarma", puerta_principal: "Puerta principal" };
const activos = new Set(["ENCENDIDO", "ACTIVADA", "ABIERTA"]);

function accion(d: Dispositivo): string {
  if (d.tipo === "ALARMA") return activos.has(d.estado) ? "DESACTIVAR" : "ACTIVAR";
  if (d.tipo === "PUERTA") return activos.has(d.estado) ? "CERRAR" : "ABRIR";
  return activos.has(d.estado) ? "APAGAR" : "ENCENDER";
}
function fechaCorta(valor: string): string {
  const fecha = new Date(valor);
  return Number.isNaN(fecha.getTime()) ? valor : fecha.toLocaleString("es-MX", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
async function peticion<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  let datos: unknown = null;
  try { datos = await response.json(); } catch { /* Respuesta sin JSON. */ }
  if (!response.ok) {
    const e = (datos || {}) as ErrorApi;
    const ubicacion = e.error?.linea ? " (línea " + e.error.linea + ", columna " + (e.error.columna ?? "?") + ")" : "";
    throw new Error((e.error?.descripcion ?? e.detail ?? "Error HTTP " + response.status) + ubicacion);
  }
  return datos as T;
}

export default function App() {
  const [dispositivos, setDispositivos] = useState<Dispositivo[]>([]);
  const [historial, setHistorial] = useState<Historial[]>([]);
  const [notificaciones, setNotificaciones] = useState<Notificacion[]>([]);
  const [salud, setSalud] = useState<Salud | null>(null);
  const [codigo, setCodigo] = useState(EJEMPLO);
  const [resultados, setResultados] = useState<Evento[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [errorConexion, setErrorConexion] = useState<string | null>(null);
  const [ejecutando, setEjecutando] = useState(false);
  const [pestana, setPestana] = useState<"historial" | "notificaciones">("historial");

  const actualizar = useCallback(async () => {
    const respuestas = await Promise.allSettled([
      peticion<{ dispositivos: Dispositivo[] }>("/api/dispositivos"),
      peticion<{ historial: Historial[] }>("/api/historial?limite=30"),
      peticion<{ notificaciones: Notificacion[] }>("/api/notificaciones?limite=30"),
      peticion<Salud>("/api/health"),
    ]);
    if (respuestas[0].status === "fulfilled") {
      setDispositivos(respuestas[0].value.dispositivos);
      setErrorConexion(null);
    } else {
      setErrorConexion("No se pudo conectar con FastAPI o PostgreSQL.");
    }
    if (respuestas[1].status === "fulfilled") setHistorial(respuestas[1].value.historial);
    if (respuestas[2].status === "fulfilled") setNotificaciones(respuestas[2].value.notificaciones);
    if (respuestas[3].status === "fulfilled") setSalud(respuestas[3].value);
  }, []);

  useEffect(() => {
    void actualizar();
    const intervalo = window.setInterval(() => { void actualizar(); }, 15000);
    return () => window.clearInterval(intervalo);
  }, [actualizar]);

  async function ejecutar(programa = codigo) {
    if (ejecutando || !programa.trim()) return;
    setEjecutando(true);
    setError(null);
    try {
      const respuesta = await peticion<Respuesta>("/api/ejecutar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ codigo: programa }),
      });
      setResultados(respuesta.resultados);
      setDispositivos(respuesta.dispositivos);
      await actualizar();
    } catch (e) {
      setResultados([]);
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally { setEjecutando(false); }
  }

  const activosAhora = dispositivos.filter((d) => activos.has(d.estado)).length;
  const conectado = salud?.database === "connected" && !errorConexion;
  return (
    <main className="app">
      <aside className="rail" aria-label="Navegación">
        <div className="rail-logo">⌂</div>
        <a href="#inicio" title="Inicio">▦</a>
        <a href="#consola" title="Consola">⌘</a>
        <a href="#actividad" title="Actividad">◷</a>
      </aside>
      <div className="workspace" id="inicio">
        <header className="topbar">
          <div className="brand"><span className="brand-logo">⌂</span><div><strong>SmartHome</strong><small>Control inteligente · Script 1.0</small></div></div>
          <div className="topbar-right">
            <span className={"status-chip " + (conectado ? "connected" : "offline")}><b />{conectado ? "Sistema conectado" : "Sin conexión"}</span>
            <button className="refresh" onClick={() => { void actualizar(); }} title="Actualizar">↻</button>
          </div>
        </header>

        <section className="hero">
          <div><span className="kicker">PANEL DE CONTROL · SMART HOME</span><h1>Tu hogar, <em>bajo control.</em></h1><p>Controla dispositivos virtuales usando las instrucciones de tu propio lenguaje.</p></div>
          <span className="hero-art" aria-hidden="true">⌂</span>
        </section>

        <section className="stats" aria-label="Indicadores">
          <div className="stat"><span className="stat-symbol cyan">▦</span><div><small>Dispositivos</small><strong>{dispositivos.length}</strong><span>Registrados</span></div></div>
          <div className="stat"><span className="stat-symbol mint">◉</span><div><small>Activos</small><strong>{activosAhora}</strong><span>En funcionamiento</span></div></div>
          <div className="stat"><span className="stat-symbol lilac">⌘</span><div><small>Actividad</small><strong>{historial.length}</strong><span>Últimos registros</span></div></div>
        </section>
        {errorConexion && <p className="connection-error" role="alert">{errorConexion}</p>}

        <div className="section-title"><div><span className="kicker">TU CASA</span><h2>Dispositivos conectados</h2></div><span>Estados guardados en PostgreSQL</span></div>
        <section className="devices" aria-label="Dispositivos">
          {dispositivos.length === 0 && <p className="empty">No hay dispositivos disponibles.</p>}
          {dispositivos.map((d) => {
            const encendido = activos.has(d.estado);
            const comando = accion(d) + " " + d.identificador;
            return (
              <article className={"device " + (encendido ? "on" : "")} key={d.identificador}>
                <div className="device-head"><span className={"device-icon " + d.tipo.toLowerCase()}>{iconos[d.tipo] ?? "◎"}</span><span className={"device-badge " + (encendido ? "on" : "")}><b />{encendido ? "Activo" : "Inactivo"}</span></div>
                <small className="device-type">{d.tipo}</small>
                <h3>{nombres[d.identificador] ?? d.identificador}</h3><p>{d.estado}</p>
                <div className="device-footer"><code>{d.identificador}</code><button type="button" className={"switch " + (encendido ? "on" : "")} title={comando} aria-label={comando} onClick={() => { void ejecutar(comando); }} disabled={ejecutando}><span /></button></div>
              </article>
            );
          })}
        </section>

        <div className="bottom-grid">
          <section className="panel console" id="consola">
            <div className="panel-heading"><div><span className="kicker">INTÉRPRETE</span><h2>Consola de comandos</h2></div><span className="live">● LIVE</span></div>
            <p className="description">Una instrucción por línea. El backend la valida, compila a IR y ejecuta.</p>
            <div className="editor">
              <div className="editor-bar"><span><i /><i /><i /></span><label htmlFor="codigo">smarthome.script</label><span>UTF-8</span></div>
              <div className="editor-content"><div className="gutter" aria-hidden="true">{codigo.split("\n").map((_, index) => <span key={index}>{index + 1}</span>)}</div><textarea id="codigo" spellCheck={false} value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="ENCENDER led1" /></div>
            </div>
            <div className="actions"><button className="secondary" onClick={() => setCodigo(EJEMPLO)}>Cargar ejemplo</button><button className="primary" disabled={ejecutando || !codigo.trim()} onClick={() => { void ejecutar(); }}>{ejecutando ? "Ejecutando…" : "▶  Ejecutar programa"}</button></div>
            <div className="results-title"><h3>Resultados</h3><small>{resultados.length} eventos</small></div>
            <div className="output" aria-live="polite">
              {error ? <p className="error" role="alert">✕ {error}</p> : resultados.length === 0 ? <p className="placeholder">Aquí verás los resultados de tu programa.</p> : resultados.map((r, index) => <p className="output-row" key={index}><b>{r.estado === "OMITIDA" ? "↷" : "✓"}</b><span>L{r.linea}</span>{r.detalle}</p>)}
            </div>
          </section>

          <section className="panel activity" id="actividad">
            <div className="panel-heading"><div><span className="kicker">REGISTRO</span><h2>Actividad reciente</h2></div><span className="clock">◷</span></div>
            <div className="tabs" role="tablist" aria-label="Actividad"><button role="tab" aria-selected={pestana === "historial"} className={pestana === "historial" ? "active" : ""} onClick={() => setPestana("historial")}>Historial ({historial.length})</button><button role="tab" aria-selected={pestana === "notificaciones"} className={pestana === "notificaciones" ? "active" : ""} onClick={() => setPestana("notificaciones")}>Notificaciones ({notificaciones.length})</button></div>
            <div className="activity-list">
              {pestana === "historial" ? (historial.length === 0 ? <p className="empty">Aún no se ejecutan instrucciones.</p> : historial.map((h) => <article className="activity-entry" key={h.id}><span className="entry-icon">⌘</span><div><strong>{h.instruccion}</strong><p>{typeof h.resultado === "object" && h.resultado !== null ? h.resultado.detalle : h.resultado ?? h.estado_ejecucion}</p><small>{fechaCorta(h.fecha)} · {h.estado_ejecucion}</small></div></article>)) : (notificaciones.length === 0 ? <p className="empty">Sin notificaciones.</p> : notificaciones.map((n) => <article className="activity-entry" key={n.id}><span className="entry-icon notice">✳</span><div><strong>Notificación</strong><p>{n.mensaje}</p><small>{fechaCorta(n.fecha)}</small></div></article>))}
            </div>
          </section>
        </div>
        <footer>SmartHome Script 1.0 · Lenguajes y Autómatas II <span>React · FastAPI · PostgreSQL · Mailpit</span></footer>
      </div>
    </main>
  );
}
